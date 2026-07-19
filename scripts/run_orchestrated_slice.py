"""
ROADMAP Step 4.2 — the truth slice, driven by Agent 16 instead of by hand.

Same Agents 1 -> 3 -> 2 chain as scripts/run_truth_slice.py, but declared as a
pipeline of PipelineSteps and executed by OrchestratorAgent.run_cycle(). The glue
(context builders / after-hooks) lives here in the script; Agent 16 only sequences,
halts on failure, and raises escalations. --every/--times gives a minimal "run
cycles on schedule" loop (a real Institutional Clock is deferred).

Usage:
    python scripts/run_orchestrated_slice.py [--vision-limit 3] [--no-vision]
    python scripts/run_orchestrated_slice.py --every 3600 --times 3   # scheduled runs
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

from cfaios.agents.agent01_extraction.agent import ExtractionAgent
from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.agents.agent03_accuracy.agent import AccuracyAgent
from cfaios.agents.agent16_orchestrator.agent import OrchestratorAgent, PipelineStep
from cfaios.infra.chess_engine import StockfishEngine
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI
from cfaios.infra.llm_google import GoogleClient

BOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "books"


def build_pipeline(api: LocalKnowledgeAPI, accuracy: AccuracyAgent,
                   integrity: IntegrityAgent) -> list[PipelineStep]:
    """The truth slice as data. Handoffs between agents happen via the shared
    state dict, written by after-hooks and read by the next build_context."""

    def extraction_ctx(state: dict) -> dict:
        return {"book_path": state["book_path"], "use_vision": state["use_vision"],
                "vision_limit": state["vision_limit"], "vision_delay": 1.0}

    def after_extraction(state: dict, agent, events) -> None:
        state["staged"] = list(api._staged.items())

    def accuracy_ctx(state: dict) -> dict:
        return {"claims": [{"claim_id": sid, "fen": c.payload.get("fen"),
                            "claimed_result": c.payload.get("claimed_result")}
                           for sid, c in state["staged"]]}

    def integrity_ctx(state: dict) -> dict:
        return {"commits": [{"candidate_id": sid, "verdict": accuracy.verdicts[sid]}
                            for sid, _ in state["staged"]]}

    return [
        PipelineStep("extract", "extraction", extraction_ctx, after_extraction),
        PipelineStep("verify", "accuracy", accuracy_ctx),
        PipelineStep("commit", "integrity", integrity_ctx),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Truth slice driven by Agent 16")
    parser.add_argument("--book", type=pathlib.Path, default=None)
    parser.add_argument("--no-vision", action="store_true")
    parser.add_argument("--vision-limit", type=int, default=3,
                        help="vision calls per run (default 3, kept small for scheduled use)")
    parser.add_argument("--every", type=float, default=None,
                        help="seconds between scheduled runs (omit for a single run)")
    parser.add_argument("--times", type=int, default=1, help="how many scheduled runs (default 1)")
    args = parser.parse_args()

    book_path = args.book or next(iter(sorted(BOOKS_DIR.glob("*.pdf"))), None)
    if book_path is None:
        print("[orchestrator] No PDFs in data/books/.")
        sys.exit(1)

    api = LocalKnowledgeAPI()
    accuracy = AccuracyAgent(api, StockfishEngine(), api.object_store)
    integrity = IntegrityAgent(api)
    registry = {
        "extraction": ExtractionAgent(api, GoogleClient()),
        "accuracy": accuracy,
        "integrity": integrity,
    }
    orchestrator = OrchestratorAgent(api, registry)
    pipeline = build_pipeline(api, accuracy, integrity)

    for run in range(1, args.times + 1):
        print(f"[orchestrator] run {run}/{args.times}  (graph {api.current_version()})")
        integrity.committed_nodes.clear()
        integrity.skipped.clear()

        escalations = orchestrator.run_cycle({
            "pipeline": pipeline,
            "state": {"book_path": str(book_path), "use_vision": not args.no_vision,
                      "vision_limit": None if args.vision_limit == 0 else args.vision_limit},
        })

        for r in orchestrator.last_run:
            print(f"  step {r['step']:<8} : {r['status']}"
                  + (f"  ({r['events_emitted']} events)" if "events_emitted" in r else ""))
        print(f"  committed      : {len(integrity.committed_nodes)}")
        print(f"  escalations    : {len(escalations)}")
        for e in escalations:
            print(f"    ! {e.payload}")
        print(f"  graph now      : {api.current_version()}")
        print()

        if args.every is not None and run < args.times:
            print(f"[orchestrator] sleeping {args.every:.0f}s until next scheduled run …")
            time.sleep(args.every)

    accuracy.engine.close()


if __name__ == "__main__":
    main()
