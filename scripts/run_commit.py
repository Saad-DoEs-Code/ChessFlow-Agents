"""
ROADMAP Step 2.3 — Agent 2 commits a real, Agent-3-verified candidate.

Chains just enough of the truth slice to prove Step 2.3's acceptance test: stage a
candidate, get it a real Verdict from Agent 3 (Stockfish-backed), commit it via
Agent 2, and show it persisted as a real node — then show a spoofed commit attempt
from another agent raising SingleWriterViolation. Also runs a REFUTED claim through
to prove Agent 2 correctly refuses to commit it.

The full "book -> 201 candidates -> verify -> commit" pipeline is Step 2.4
(scripts/run_truth_slice.py) — this script deliberately stays small.

Usage:
    python scripts/run_commit.py
"""
from __future__ import annotations

from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.agents.agent03_accuracy.agent import AccuracyAgent
from cfaios.core.knowledge_api import Candidate, SingleWriterViolation
from cfaios.core.truth import EpistemicState
from cfaios.infra.chess_engine import StockfishEngine
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI
from cfaios.infra.object_store import LocalObjectStore


def main() -> None:
    api = LocalKnowledgeAPI()  # real persistent store, default .cfaios_data/graph
    engine = StockfishEngine()
    accuracy = AccuracyAgent(api, engine, LocalObjectStore())
    integrity = IntegrityAgent(api)

    print(f"[run_commit] graph store: {api.root.resolve()}")
    print(f"[run_commit] starting version: {api.current_version()}")
    print()

    # Two candidates: one objectively TRUE claim, one objectively FALSE claim.
    # Both go through the same pipeline — only the true one should end up committed.
    candidates = [
        Candidate(source_agent=1, concept="KQ vs K is a win for White",
                  payload={"fen": "8/8/8/8/4k3/8/4K3/6Q1 w - - 0 1"},
                  evidence={"book": "demo", "page": 0}, epistemic=EpistemicState.PLAUSIBLE),
        Candidate(source_agent=1, concept="KQ vs K is (falsely claimed) a draw",
                  payload={"fen": "8/8/8/8/4k3/8/4K3/6Q1 w - - 0 1"},
                  evidence={"book": "demo", "page": 0}, epistemic=EpistemicState.PLAUSIBLE),
    ]
    claimed_results = ["win", "draw"]  # second one is false on purpose

    staging_ids = [api.stage_candidate(c) for c in candidates]

    claims = [{"claim_id": sid, "fen": c.payload["fen"], "claimed_result": result}
              for sid, c, result in zip(staging_ids, candidates, claimed_results)]
    accuracy.run_cycle({"claims": claims})

    commits = [{"candidate_id": sid, "verdict": accuracy.verdicts[sid]} for sid in staging_ids]
    integrity.run_cycle({"commits": commits})

    print(f"[run_commit] committed : {len(integrity.committed_nodes)}")
    for node in integrity.committed_nodes:
        print(f"  -> {node.node_id}  {node.concept!r}  version={node.graph_version}")
    print(f"[run_commit] skipped   : {len(integrity.skipped)}")
    for item in integrity.skipped:
        state = next(iter(item["verdict"].dimension_results.values()))
        print(f"  -> {item['candidate_id']} skipped (verdict={state.value}, "
              f"not committed — correctly refused)")
    print()

    # Prove persistence: read the committed node back through the API, not from
    # local variables.
    for node in integrity.committed_nodes:
        reread = api.get_node(node.node_id)
        print(f"[run_commit] re-read {node.node_id}: concept={reread.concept!r}, "
              f"verdict={next(iter(reread.verdict.dimension_results.values())).value}")
    print(f"[run_commit] graph version now: {api.current_version()}")
    print()

    # Prove the single-writer invariant actually holds against this real binding.
    other_staging_id = api.stage_candidate(candidates[0])
    try:
        api.commit(other_staging_id, accuracy.verdicts[staging_ids[0]], _actor=7)
        print("[run_commit] !! SingleWriterViolation was NOT raised — this is a bug.")
    except SingleWriterViolation as exc:
        print(f"[run_commit] Agent 7 commit attempt correctly rejected: {exc}")

    engine.close()


if __name__ == "__main__":
    main()
