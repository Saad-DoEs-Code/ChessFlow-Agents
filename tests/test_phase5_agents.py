"""Phase 5 slice: Agent 6 (assessment), Agent 8 (PQI gate), Agent 10 (visual).
All pure paths — no LLM/API calls anywhere in these tests."""
from __future__ import annotations

import pytest

from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.agents.agent06_assessment.agent import AssessmentAgent, competency_projection
from cfaios.agents.agent08_content.agent import ContentAgent
from cfaios.agents.agent10_visual.agent import VisualAgent
from cfaios.core.knowledge_api import Candidate
from cfaios.core.truth import (
    EpistemicState, EvidenceTier, TruthDimension, Verdict, VerdictState)
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def _commit_node(api: LocalKnowledgeAPI, *, fen="8/8/8/8/4k3/8/4K3/6Q1",
                 claimed="win", state=VerdictState.CONFIRMED) -> str:
    candidate = Candidate(
        source_agent=1, concept=f"study {fen[:8]}",
        payload={"fen": fen, "claimed_result": claimed, "stipulation": "White to play and win",
                 "raw_text": "source text"},
        evidence={"book": "t.pdf", "page": 1}, epistemic=EpistemicState.PLAUSIBLE)
    sid = api.stage_candidate(candidate)
    verdict = Verdict(dimension_results={TruthDimension.OBJECTIVE: state},
                      tier=EvidenceTier.ENGINE_SHALLOW, evidence_ref="ref123",
                      confidence=1.0, notes="t")
    integrity = IntegrityAgent(api)
    integrity.run_cycle({"commits": [{"candidate_id": sid, "verdict": verdict}]})
    return integrity.committed_nodes[0].node_id if integrity.committed_nodes else None


# ---- Agent 6 ----

def test_assessment_scores_and_projects(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    nid = _commit_node(api)

    agent = AssessmentAgent(api)
    events = agent.run_cycle({"learner_id": "alice", "node_ids": [nid],
                              "responses": {nid: "win"}})

    assert agent.result["accuracy"] == 1.0
    assert len(events) == 1 and events[0].payload["correct"] is True
    graph = competency_projection(api.read_events())
    assert graph["alice"][nid] == {"mastery": 1.0, "attempts": 1, "correct": 1}


def test_assessment_unanswered_never_scored(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    nid = _commit_node(api)

    agent = AssessmentAgent(api)
    events = agent.run_cycle({"learner_id": "bob", "node_ids": [nid]})  # no responses

    assert agent.result["attempted"] == 0
    assert agent.result["accuracy"] is None      # never fabricated (P16)
    assert agent.result["unanswered"] == [nid]
    assert events == []                          # no evidence, no update


def test_assessment_wrong_answer_projects_zero_mastery(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    nid = _commit_node(api)

    agent = AssessmentAgent(api)
    agent.run_cycle({"learner_id": "carol", "node_ids": [nid], "responses": {nid: "draw"}})

    graph = competency_projection(api.read_events())
    assert graph["carol"][nid]["mastery"] == 0.0
    assert graph["carol"][nid]["attempts"] == 1


# ---- Agent 8 ----

def test_content_refuses_ungated_lesson(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = ContentAgent(api)
    with pytest.raises(ValueError, match="CQI gate"):
        agent.observe({"lesson": {"sections": []}, "gate_passed": False})


def test_pqi_blocks_orphaned_scene():
    agent = ContentAgent.__new__(ContentAgent)  # scoring only
    script = {"scenes": [
        {"node_id": "n1", "evidence_ref": "r1", "verdict_state": "confirmed",
         "narration": "good narration text here"},
        {"node_id": "n2", "evidence_ref": None, "verdict_state": "confirmed",
         "narration": "good narration text here"},
    ]}
    result = agent.evaluate_gate(agent.score_script(script))
    assert not result.passed
    assert "provenance_intact" in result.failed_integrity


# ---- Agent 10 ----

def test_visual_refuses_ungated_script(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = VisualAgent(api)
    with pytest.raises(ValueError, match="PQI gate"):
        agent.observe({"script": {"scenes": []}, "gate_passed": False})


def test_thumbnail_spec_carries_provenance_and_verbatim_fen(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    nid = _commit_node(api, fen="7k/8/8/8/8/8/8/K6Q")

    agent = VisualAgent(api)
    script = {"topic": "t", "graph_version": api.current_version(),
              "scenes": [{"scene": 1, "node_id": nid, "evidence_ref": "ref123",
                          "verdict_state": "confirmed", "fen": "7k/8/8/8/8/8/8/K6Q",
                          "narration": "x", "on_screen": "y"}]}
    agent.run_cycle({"script": script, "gate_passed": True})

    spec = agent.thumbnail_spec
    assert spec["board_fen"] == "7k/8/8/8/8/8/8/K6Q"       # verbatim, never invented
    assert spec["provenance"]["node_id"] == nid
    assert spec["provenance"]["evidence_ref"] == "ref123"
