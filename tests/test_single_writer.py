"""P4 (Single-Writer Invariant) enforcement tests against the real LocalKnowledgeAPI
binding — not a dev double. Both independent enforcement points must hold:
`commit()` and `emit()` of a KNOWLEDGE_COMMITTED event."""
from __future__ import annotations

import pytest

from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import AGENT_KNOWLEDGE_WRITER, Candidate, SingleWriterViolation
from cfaios.core.truth import EpistemicState, EvidenceTier, TruthDimension, Verdict, VerdictState
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def _make_api(tmp_path):
    return LocalKnowledgeAPI(root=tmp_path / "graph")


def _make_verdict(state: VerdictState = VerdictState.CONFIRMED) -> Verdict:
    return Verdict(
        dimension_results={TruthDimension.OBJECTIVE: state},
        tier=EvidenceTier.ENGINE_SHALLOW,
        evidence_ref="deadbeef",
        confidence=1.0,
        notes="test verdict",
    )


def _stage(api) -> str:
    candidate = Candidate(
        source_agent=1, concept="test concept", payload={"raw_text": "..."},
        evidence={"book": "test.pdf", "page": 1}, epistemic=EpistemicState.PLAUSIBLE,
    )
    return api.stage_candidate(candidate)


def test_agent_two_can_commit(tmp_path):
    api = _make_api(tmp_path)
    staging_id = _stage(api)

    node = api.commit(staging_id, _make_verdict(), _actor=AGENT_KNOWLEDGE_WRITER)

    assert node.concept == "test concept"
    assert api.get_node(node.node_id) is not None
    assert api.get_verdict(node.node_id).dimension_results[TruthDimension.OBJECTIVE] is VerdictState.CONFIRMED


def test_non_agent_two_commit_raises(tmp_path):
    api = _make_api(tmp_path)
    staging_id = _stage(api)

    with pytest.raises(SingleWriterViolation):
        api.commit(staging_id, _make_verdict(), _actor=7)  # Agent 7 attempting to write knowledge


def test_non_agent_two_emit_knowledge_committed_raises(tmp_path):
    api = _make_api(tmp_path)
    bad_event = Event(type=EventType.KNOWLEDGE_COMMITTED, actor_agent=18, subject_id="node-x")

    with pytest.raises(SingleWriterViolation):
        api.emit(bad_event)


def test_committed_node_persists_across_instances(tmp_path):
    """Not in-memory-only: a fresh LocalKnowledgeAPI pointed at the same root
    must see the committed node."""
    root = tmp_path / "graph"
    api1 = LocalKnowledgeAPI(root=root)
    staging_id = _stage(api1)
    node = api1.commit(staging_id, _make_verdict(), _actor=AGENT_KNOWLEDGE_WRITER)

    api2 = LocalKnowledgeAPI(root=root)
    reloaded = api2.get_node(node.node_id)
    assert reloaded is not None
    assert reloaded.concept == "test concept"
