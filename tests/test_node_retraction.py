"""Tests for node retraction, added 2026-07-26 after a real investigation found
a CONFIRMED node whose extracted position was wrong on independent re-check
(see PROGRESS.md's "p.101" finding). NODE_SUPERSEDED existed in the event
schema before this but nothing on the read side honored it — these tests
prove get_node/semantic_search now correctly exclude retracted nodes while
the full history stays intact in the event log (P6)."""
from __future__ import annotations

from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import Candidate
from cfaios.core.truth import EpistemicState, EvidenceTier, TruthDimension, Verdict, VerdictState
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI, rebuild_nodes_from_events


def _commit_one(api: LocalKnowledgeAPI, concept="test study") -> str:
    candidate = Candidate(source_agent=1, concept=concept, payload={"fen": "x"},
                          evidence={}, epistemic=EpistemicState.PLAUSIBLE)
    sid = api.stage_candidate(candidate)
    api.emit(Event(type=EventType.CANDIDATE_STAGED, actor_agent=1, subject_id=sid,
                   payload={"concept": concept}))
    verdict = Verdict(dimension_results={TruthDimension.OBJECTIVE: VerdictState.CONFIRMED},
                      tier=EvidenceTier.ENGINE_SHALLOW, evidence_ref="ref", confidence=1.0, notes="")
    integrity = IntegrityAgent(api)
    integrity.run_cycle({"commits": [{"candidate_id": sid, "verdict": verdict}]})
    return integrity.committed_nodes[0].node_id


def test_retracted_node_is_hidden_from_get_node(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit_one(api)
    assert api.get_node(node_id) is not None  # sanity: visible before retraction

    api.emit(Event(type=EventType.NODE_SUPERSEDED, actor_agent=3, subject_id=node_id,
                   payload={"reason": "misextracted position, confirmed via manual re-check"}))

    assert api.get_node(node_id) is None


def test_retracted_node_is_excluded_from_semantic_search(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit_one(api, concept="rook endgame study")
    assert any(n.node_id == node_id for n in api.semantic_search("rook endgame", k=10))

    api.emit(Event(type=EventType.NODE_SUPERSEDED, actor_agent=3, subject_id=node_id,
                   payload={"reason": "bad extraction"}))

    assert not any(n.node_id == node_id for n in api.semantic_search("rook endgame", k=10))


def test_retraction_is_never_erased_from_the_raw_event_log(tmp_path):
    """P6: the log forgets nothing. A fresh LocalKnowledgeAPI on the same
    directory must still see BOTH the original commit and the retraction."""
    root = tmp_path / "g"
    api1 = LocalKnowledgeAPI(root=root)
    node_id = _commit_one(api1)
    api1.emit(Event(type=EventType.NODE_SUPERSEDED, actor_agent=3, subject_id=node_id,
                    payload={"reason": "bad extraction"}))

    api2 = LocalKnowledgeAPI(root=root)  # fresh instance, same log
    assert api2.get_node(node_id) is None  # retraction state persisted
    types_seen = [e["type"] for e in api2.read_events()]
    assert "knowledge_committed" in types_seen
    assert "node_superseded" in types_seen  # the original commit was never deleted from the log


def test_replay_reconstructs_retraction_state(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit_one(api)
    api.emit(Event(type=EventType.NODE_SUPERSEDED, actor_agent=3, subject_id=node_id,
                   payload={"reason": "bad extraction, confirmed by direct page inspection"}))

    rebuilt, warnings = rebuild_nodes_from_events(api.read_events())

    assert warnings == []
    assert rebuilt[node_id]["retracted"] is True
    assert rebuilt[node_id]["retraction_reason"] == "bad extraction, confirmed by direct page inspection"
    assert rebuilt[node_id] == api._nodes[node_id]  # exact match, including retraction fields


def test_superseding_a_never_committed_node_is_reported_not_silently_ignored(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    api.emit(Event(type=EventType.NODE_SUPERSEDED, actor_agent=3, subject_id="node-ghost",
                   payload={"reason": "does not exist"}))

    rebuilt, warnings = rebuild_nodes_from_events(api.read_events())
    assert any("node-ghost" in w for w in warnings)
