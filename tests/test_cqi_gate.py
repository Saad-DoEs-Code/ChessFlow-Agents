"""Step 4.3: Agent 7's CQI is the first real gate — integrity dimensions must
block unconditionally, regardless of quality scores (Integrity-First
Optimization). Scoring is pure, so no LLM/API is involved here."""
from __future__ import annotations

from cfaios.agents.agent07_coaching.agent import CoachingAgent


def _agent() -> CoachingAgent:
    return CoachingAgent.__new__(CoachingAgent)  # scoring/gate only — no api/llm needed


def _section(**overrides) -> dict:
    base = {"node_id": "node-1", "evidence_ref": "abc123", "verdict_state": "confirmed",
            "explanation": "A clear teaching explanation of this endgame study. " * 4}
    return {**base, **overrides}


def test_fully_grounded_lesson_passes():
    agent = _agent()
    lesson = {"sections": [_section(), _section(node_id="node-2")]}
    result = agent.evaluate_gate(agent.score_lesson(lesson))
    assert result.passed
    assert result.score > 0.9


def test_one_ungrounded_section_blocks_regardless_of_quality():
    agent = _agent()
    lesson = {"sections": [_section(), _section(evidence_ref=None)]}
    result = agent.evaluate_gate(agent.score_lesson(lesson))
    assert not result.passed
    assert "grounding" in result.failed_integrity
    # quality dimensions may still score high — integrity blocks anyway
    assert result.detail["explanation_generated"] == 1.0


def test_unverified_section_blocks():
    agent = _agent()
    lesson = {"sections": [_section(verdict_state="refuted")]}
    result = agent.evaluate_gate(agent.score_lesson(lesson))
    assert not result.passed
    assert "verified_only" in result.failed_integrity


def test_empty_lesson_fails_not_vacuously_passes():
    agent = _agent()
    result = agent.evaluate_gate(agent.score_lesson({"sections": []}))
    assert not result.passed


def test_failed_generation_lowers_quality_but_is_not_integrity():
    agent = _agent()
    lesson = {"sections": [_section(explanation="(explanation unavailable: boom)")]}
    result = agent.evaluate_gate(agent.score_lesson(lesson))
    # grounding/verified are intact -> integrity passes; quality is poor
    assert result.passed
    assert result.score < 0.5
