"""
ROADMAP Step 2.4 — the truth slice end-to-end: book -> candidates -> verify -> commit.

Chains the real Agent 1 -> Agent 3 -> Agent 2 pipeline on the real book in one command,
against the real persistent LocalKnowledgeAPI (Step 2.3's binding — no Neo4j on this
machine, see PROGRESS.md). Vision (board-diagram -> FEN) is on by default here, capped
by --vision-limit to control cost/runtime; every one of the (up to) 201 real candidates
still goes through Agent 3, so candidates outside the vision-limited subset correctly
come back INAPPLICABLE (no FEN) rather than being silently dropped — the objective/
non-objective split IS part of the honest result this step is supposed to report.

Usage:
    python scripts/run_truth_slice.py [--book path.pdf] [--vision-limit 20] [--show-refs 3]
    python scripts/run_truth_slice.py --no-vision   # text-only, all candidates INAPPLICABLE
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from collections import Counter

from cfaios.agents.agent01_extraction.agent import ExtractionAgent
from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.agents.agent03_accuracy.agent import AccuracyAgent
from cfaios.infra.chess_engine import StockfishEngine
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI
from cfaios.infra.llm_google import GoogleClient

BOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "books"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full truth slice (Agents 1 -> 3 -> 2)")
    parser.add_argument("--book", type=pathlib.Path, default=None,
                        help="book to run (default: first PDF in data/books/)")
    parser.add_argument("--no-vision", action="store_true",
                        help="skip board-diagram -> FEN vision entirely (all candidates "
                             "will come back INAPPLICABLE — useful as a fast dry run)")
    parser.add_argument("--vision-limit", type=int, default=20,
                        help="cap how many study pages get a vision call (default 20; "
                             "0 = no limit, all detected study pages — takes several "
                             "minutes and real API quota)")
    parser.add_argument("--vision-delay", type=float, default=1.0,
                        help="seconds to sleep between vision calls (default 1.0)")
    parser.add_argument("--show-refs", type=int, default=3,
                        help="how many committed nodes' Evidence Ledger refs to print (default 3)")
    args = parser.parse_args()

    if args.book:
        book_path = args.book
    else:
        pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
        if not pdfs:
            print("[run_truth_slice] No PDFs found in data/books/.")
            sys.exit(1)
        book_path = pdfs[0]

    api = LocalKnowledgeAPI()  # real persistent store — the canonical local graph
    extraction = ExtractionAgent(api, GoogleClient())
    accuracy = AccuracyAgent(api, StockfishEngine(), api.object_store)
    integrity = IntegrityAgent(api)

    use_vision = not args.no_vision
    vision_limit = None if args.vision_limit == 0 else args.vision_limit

    print(f"[run_truth_slice] book   : {book_path.name}")
    print(f"[run_truth_slice] graph  : {api.root.resolve()}  (starting {api.current_version()})")
    print(f"[run_truth_slice] vision : {'ON, limit=' + str(vision_limit or 'none') if use_vision else 'OFF'}")
    print()

    # ---- Agent 1: extract -> stage ----
    extraction.run_cycle({
        "book_path": str(book_path),
        "use_vision": use_vision,
        "vision_limit": vision_limit,
        "vision_delay": args.vision_delay,
    })
    staged = list(api._staged.items())  # snapshot before Agent 2 drains any of it
    with_fen = sum(1 for _, c in staged if c.payload.get("fen"))
    vision_attempted = sum(1 for _, c in staged
                            if c.payload.get("vision_note", "").startswith("vision:")
                            and "not attempted" not in c.payload["vision_note"])
    print(f"[run_truth_slice] extracted        : {len(staged)} candidates")
    if use_vision:
        print(f"[run_truth_slice] vision attempted : {vision_attempted}")
        print(f"[run_truth_slice] vision hits (FEN): {with_fen}"
              f"  ({(with_fen / vision_attempted * 100) if vision_attempted else 0:.0f}%)")
    print()

    # ---- Agent 3: verify ----
    claims = [{"claim_id": sid, "fen": c.payload.get("fen"),
               "claimed_result": c.payload.get("claimed_result")} for sid, c in staged]
    accuracy.run_cycle({"claims": claims})
    verdict_counts = Counter(
        next(iter(accuracy.verdicts[sid].dimension_results.values())).value for sid, _ in staged)
    print(f"[run_truth_slice] verdicts         : {dict(verdict_counts)}")

    # ---- Agent 2: commit (single writer) ----
    commits = [{"candidate_id": sid, "verdict": accuracy.verdicts[sid]} for sid, _ in staged]
    integrity.run_cycle({"commits": commits})
    print(f"[run_truth_slice] committed        : {len(integrity.committed_nodes)}")
    print(f"[run_truth_slice] skipped          : {len(integrity.skipped)}  (not CONFIRMED)")
    print(f"[run_truth_slice] graph version now: {api.current_version()}")
    print()

    if integrity.committed_nodes:
        print(f"[run_truth_slice] first {min(args.show_refs, len(integrity.committed_nodes))} "
              f"committed node(s) with Evidence Ledger provenance:")
        for node in integrity.committed_nodes[:args.show_refs]:
            evidence_ref = node.verdict.evidence_ref
            fetched = api.object_store.get_evidence(evidence_ref)
            print(f"  - {node.node_id}  {node.concept!r}")
            print(f"    verdict={next(iter(node.verdict.dimension_results.values())).value}  "
                  f"tier={node.verdict.tier.name}  notes={node.verdict.notes!r}")
            print(f"    evidence_ref={evidence_ref}  ({len(fetched)} bytes, fetched back from ledger)")
    else:
        print("[run_truth_slice] Nothing committed this run "
              "(no CONFIRMED verdicts among the candidates that had a FEN).")

    accuracy.engine.close()


if __name__ == "__main__":
    main()
