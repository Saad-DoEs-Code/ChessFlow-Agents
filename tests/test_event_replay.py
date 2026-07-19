"""Step 4.1: the append-only event log must be able to rebuild the node
projection on its own — nodes.json is a cache, events.jsonl is the truth (P6)."""
from __future__ import annotations

from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import Candidate
from cfaios.core.truth import (
    EpistemicState, EvidenceTier, TruthDimension, Verdict, VerdictState)
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI, rebuild_nodes_from_events


def _verdict() -> Verdict:
    return Verdict(
        dimension_results={TruthDimension.OBJECTIVE: VerdictState.CONFIRMED},
        tier=EvidenceTier.ENGINE_SHALLOW, evidence_ref="cafe1234", confidence=1.0,
        notes="engine says win")


def _commit_one_via_evented_path(api: LocalKnowledgeAPI) -> str:
    """Stage with a CANDIDATE_STAGED event (as Agent 1's run_cycle does), then
    commit through Agent 2's run_cycle — the full evented path replay joins on."""
    candidate = Candidate(source_agent=1, concept="replay test concept",
                          payload={"fen": "8/8/8/8/4k3/8/4K3/6Q1", "claimed_result": "win"},
                          evidence={"book": "t.pdf", "page": 3},
                          epistemic=EpistemicState.PLAUSIBLE)
    staging_id = api.stage_candidate(candidate)
    api.emit(Event(type=EventType.CANDIDATE_STAGED, actor_agent=1, subject_id=staging_id,
                   payload={"concept": candidate.concept, "page": 3}))

    integrity = IntegrityAgent(api)
    integrity.run_cycle({"commits": [{"candidate_id": staging_id, "verdict": _verdict()}]})
    return integrity.committed_nodes[0].node_id


def test_replay_rebuilds_committed_node(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "graph")
    node_id = _commit_one_via_evented_path(api)

    rebuilt, warnings = rebuild_nodes_from_events(api.read_events())

    assert warnings == []
    assert node_id in rebuilt
    assert rebuilt[node_id] == api._nodes[node_id]  # full record, field for field


def test_replay_recovers_source_agent_from_staging_event(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "graph")
    node_id = _commit_one_via_evented_path(api)

    rebuilt, _ = rebuild_nodes_from_events(api.read_events())
    assert rebuilt[node_id]["source_agent"] == 1  # joined from CANDIDATE_STAGED


def test_replay_flags_unevented_staging_instead_of_guessing(tmp_path):
    """Staging that bypasses event emission loses provenance — replay must say
    so (source_agent None + warning), never invent a value (P3)."""
    api = LocalKnowledgeAPI(root=tmp_path / "graph")
    candidate = Candidate(source_agent=1, concept="c", payload={},
                          evidence={}, epistemic=EpistemicState.PLAUSIBLE)
    staging_id = api.stage_candidate(candidate)  # no CANDIDATE_STAGED event emitted

    integrity = IntegrityAgent(api)
    integrity.run_cycle({"commits": [{"candidate_id": staging_id, "verdict": _verdict()}]})
    node_id = integrity.committed_nodes[0].node_id

    rebuilt, warnings = rebuild_nodes_from_events(api.read_events())
    assert rebuilt[node_id]["source_agent"] is None
    assert any("source_agent unrecoverable" in w for w in warnings)
