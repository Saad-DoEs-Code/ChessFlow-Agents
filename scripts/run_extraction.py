"""
ROADMAP Step 2.1 — run Agent 1 (extraction) on one real book.

Runs ExtractionAgent.run_cycle() against a book in data/books/ and prints every
staged candidate with its source evidence. Uses a throwaway in-memory KnowledgeAPI
double (no Neo4j/vector/object store bound yet) — good enough to prove Agent 1 only
stages candidates and never writes the graph (P4), which is the only thing this
step needs to demonstrate. A real KnowledgeAPI implementation is Step 2.3.

Usage:
    python scripts/run_extraction.py [--book path/to/file.pdf] [--limit 10]
    python scripts/run_extraction.py --vision --vision-limit 10   # opt-in board->FEN vision
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from cfaios.agents.agent01_extraction.agent import ExtractionAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import AGENT_KNOWLEDGE_WRITER, Candidate, KnowledgeAPI, KnowledgeNode, SingleWriterViolation
from cfaios.core.truth import Verdict
from cfaios.infra.llm_google import GoogleClient

BOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "books"


class _InMemoryKnowledgeAPI(KnowledgeAPI):
    """Dev-only double. Staging works for real; every read/commit path is a stub —
    nothing here is bound to Neo4j/vector/object stores yet (that's Step 2.3)."""

    def __init__(self) -> None:
        self._staged: dict[str, Candidate] = {}
        self.events: list[Event] = []

    def get_node(self, node_id: str, *, version: str | None = None) -> KnowledgeNode | None:
        return None

    def semantic_search(self, query: str, *, k: int = 10) -> list[KnowledgeNode]:
        return []

    def get_verdict(self, node_id: str) -> Verdict | None:
        return None

    def current_version(self) -> str:
        return "dev-inmemory"

    def stage_candidate(self, candidate: Candidate) -> str:
        staging_id = f"stg-{len(self._staged) + 1:04d}"
        self._staged[staging_id] = candidate
        return staging_id

    def emit(self, event: Event) -> None:
        if event.type is EventType.KNOWLEDGE_COMMITTED and event.actor_agent != AGENT_KNOWLEDGE_WRITER:
            raise SingleWriterViolation(
                f"actor {event.actor_agent} may not emit KNOWLEDGE_COMMITTED")
        self.events.append(event)

    def commit(self, candidate_id: str, verdict: Verdict, *, _actor: int) -> KnowledgeNode:
        if _actor != AGENT_KNOWLEDGE_WRITER:
            raise SingleWriterViolation(f"actor {_actor} may not commit (P4)")
        raise NotImplementedError("dev stub — a real commit path is Step 2.3")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Agent 1 extraction on one book")
    parser.add_argument("--book", type=pathlib.Path, default=None,
                        help="book to extract (default: first PDF in data/books/)")
    parser.add_argument("--limit", type=int, default=10,
                        help="how many staged candidates to print in full (default 10)")
    parser.add_argument("--vision", action="store_true",
                        help="opt in to board-diagram -> FEN vision (calls the Gemini API)")
    parser.add_argument("--vision-limit", type=int, default=10,
                        help="cap how many study pages get a vision call (default 10; "
                             "0 = no limit, all detected study pages)")
    parser.add_argument("--vision-delay", type=float, default=1.0,
                        help="seconds to sleep between vision calls (default 1.0)")
    args = parser.parse_args()

    if args.book:
        book_path = args.book
    else:
        pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
        if not pdfs:
            print("[run_extraction] No PDFs found in data/books/.")
            sys.exit(1)
        book_path = pdfs[0]

    api = _InMemoryKnowledgeAPI()
    agent = ExtractionAgent(api, GoogleClient())

    print(f"[run_extraction] book: {book_path.name}")
    if args.vision:
        limit = None if args.vision_limit == 0 else args.vision_limit
        print(f"[run_extraction] vision: ON  (limit={limit or 'none'}, "
              f"model={agent.vision_client.model}, delay={args.vision_delay}s)")
    else:
        print("[run_extraction] vision: OFF (pass --vision to attach FENs)")
    print()

    events = agent.run_cycle({
        "book_path": str(book_path),
        "use_vision": args.vision,
        "vision_limit": None if args.vision_limit == 0 else args.vision_limit,
        "vision_delay": args.vision_delay,
    })

    non_stage_events = [e for e in events if e.type is not EventType.CANDIDATE_STAGED]
    print(f"[run_extraction] candidates staged     : {len(api._staged)}")
    print(f"[run_extraction] CANDIDATE_STAGED events: {len(events) - len(non_stage_events)}")
    print(f"[run_extraction] other event types      : {[e.type.value for e in non_stage_events]}")
    print(f"[run_extraction] graph writes attempted : 0 (act() only calls stage_candidate)")
    print()

    for i, (sid, cand) in enumerate(list(api._staged.items())[:args.limit], 1):
        print(f"{i}. [{sid}] {cand.concept}")
        print(f"    evidence : page {cand.evidence['page']} of {cand.evidence['book']}")
        if cand.payload.get("source_label"):
            print(f"    source   : {cand.payload['source_label']}")
        print(f"    stip     : {cand.payload.get('stipulation')}")
        if args.vision:
            print(f"    fen      : {cand.payload.get('fen')}  ({cand.payload.get('vision_note')})")
        snippet = " ".join(cand.payload["raw_text"].split())[:220]
        print(f"    text     : {snippet}…")
        print()

    if len(api._staged) > args.limit:
        print(f"... and {len(api._staged) - args.limit} more (use --limit to show more)")

    if args.vision:
        attempted = [c for c in api._staged.values() if c.payload.get("vision_note", "").startswith("vision:") and "not attempted" not in c.payload["vision_note"]]
        hits = [c for c in attempted if c.payload.get("fen")]
        print()
        print(f"[run_extraction] vision attempted: {len(attempted)}  hits: {len(hits)}"
              f"  ({(len(hits) / len(attempted) * 100) if attempted else 0:.0f}%)")


if __name__ == "__main__":
    main()
