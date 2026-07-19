"""
ROADMAP Step 2.2 — run Agent 3 (accuracy) against a handful of test claims.

Exercises the Verification Router (Pattern #3) end-to-end: a non-objective claim
(-> INAPPLICABLE), an illegal-FEN claim (-> INCONCLUSIVE, no engine needed), and a
legal claim that requires the real Stockfish engine. Prints each verdict and proves
its evidence is really fetchable back from the Evidence Ledger (LocalObjectStore).

Uses the same throwaway in-memory KnowledgeAPI double as run_extraction.py — no
Neo4j bound yet (that's Step 2.3). The object store, however, is real (filesystem-
backed, content-addressed) since the whole point of this step is a working ledger.

Usage:
    python scripts/run_verification.py
"""
from __future__ import annotations

from cfaios.agents.agent03_accuracy.agent import AccuracyAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import AGENT_KNOWLEDGE_WRITER, Candidate, KnowledgeAPI, KnowledgeNode, SingleWriterViolation
from cfaios.core.truth import Verdict
from cfaios.infra.chess_engine import StockfishEngine
from cfaios.infra.object_store import LocalObjectStore


class _InMemoryKnowledgeAPI(KnowledgeAPI):
    """Dev-only double — see scripts/run_extraction.py for the same pattern."""

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


# Deliberately three different shapes of claim to exercise the router's branches:
TEST_CLAIMS = [
    {
        "claim_id": "c1-prose",
        "note": "A charming ending with two Bishop sacrifices.",
        # no fen / claimed_result -> non-objective
    },
    {
        "claim_id": "c2-illegal-fen",
        "fen": "8/8/8/8/8/8/8/8 w - - 0 1",  # no kings on the board at all
        "claimed_result": "win",
    },
    {
        "claim_id": "c3-kq-vs-k",
        "fen": "8/8/8/8/4k3/8/4K3/6Q1 w - - 0 1",  # trivially winning for White
        "claimed_result": "win",
    },
    {
        "claim_id": "c4-false-claim",
        "fen": "8/8/8/8/4k3/8/4K3/6Q1 w - - 0 1",  # same winning position, wrong claim
        "claimed_result": "draw",  # this is FALSE — should be REFUTED, not CONFIRMED
    },
    {
        "claim_id": "c5-bare-kings-draw",
        "fen": "8/8/8/8/4k3/8/4K3/8 w - - 0 1",  # king vs king, dead draw
        "claimed_result": "draw",
    },
]


def main() -> None:
    api = _InMemoryKnowledgeAPI()
    engine = StockfishEngine()
    store = LocalObjectStore()
    agent = AccuracyAgent(api, engine, store)

    print(f"[run_verification] stockfish path: {engine.path}")
    print(f"[run_verification] evidence store root: {store.root.resolve()}")
    print()

    events = agent.run_cycle({"claims": TEST_CLAIMS})

    for claim in TEST_CLAIMS:
        cid = claim["claim_id"]
        verdict = agent.verdicts[cid]
        state = next(iter(verdict.dimension_results.values()))
        print(f"--- {cid} ---")
        print(f"  claim   : {claim}")
        print(f"  verdict : {state.value}  (tier={verdict.tier.name}, confidence={verdict.confidence})")
        print(f"  note    : {verdict.notes}")

        # Prove the evidence really round-trips through the ledger.
        fetched = store.get_evidence(verdict.evidence_ref)
        print(f"  evidence: ref={verdict.evidence_ref[:16]}…  "
              f"({len(fetched)} bytes fetched back from {store.root.name}/)")
        print()

    print(f"[run_verification] events emitted: {len(events)} "
          f"({[e.type.value for e in events]})")

    engine.close()


if __name__ == "__main__":
    main()
