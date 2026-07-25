"""Unit tests for Agent 16 (Orchestrator) — added 2026-07-23 to close a
coverage gap: implemented in Step 4.2 and exercised live (both a clean run and
a deliberate failure) via run_orchestrated_slice.py, but never under pytest
with controlled fake sub-agents. Confirms Safe Halt, escalation payloads, and
the unregistered-agent guard precisely."""
from __future__ import annotations

import types

from cfaios.agents.agent16_orchestrator.agent import OrchestratorAgent, PipelineStep
from cfaios.core.events import Event, EventType


class _FakeAgent:
    """Minimal stand-in: run_cycle() either returns scripted events or raises."""

    def __init__(self, *, events=None, raises=None):
        self._events = events or []
        self._raises = raises
        self.received_contexts: list[dict] = []

    def run_cycle(self, context: dict):
        self.received_contexts.append(context)
        if self._raises:
            raise self._raises
        return self._events


def _null_api():
    return types.SimpleNamespace(emit=lambda e: None)


def test_successful_pipeline_threads_state_through_steps():
    a1 = _FakeAgent(events=[Event(type=EventType.CANDIDATE_STAGED, actor_agent=1, subject_id="x")])
    a2 = _FakeAgent(events=[])
    orchestrator = OrchestratorAgent(_null_api(), registry={"a1": a1, "a2": a2})

    def after_a1(state, agent, events):
        state["a1_events"] = len(events)

    pipeline = [
        PipelineStep("step-one", "a1", lambda state: {"n": 1}, after_a1),
        PipelineStep("step-two", "a2", lambda state: {"n": state["a1_events"]}),
    ]
    escalations = orchestrator.run_cycle({"pipeline": pipeline, "state": {}})

    assert escalations == []
    assert [r["status"] for r in orchestrator.last_run] == ["ok", "ok"]
    assert a2.received_contexts == [{"n": 1}]  # state really threaded through the after-hook


def test_failure_halts_remaining_steps_and_raises_escalation():
    a1 = _FakeAgent(events=[])
    a2 = _FakeAgent(raises=FileNotFoundError("book missing"))
    a3 = _FakeAgent(events=[])
    orchestrator = OrchestratorAgent(_null_api(), registry={"a1": a1, "a2": a2, "a3": a3})

    pipeline = [
        PipelineStep("extract", "a1", lambda state: {}),
        PipelineStep("verify", "a2", lambda state: {}),
        PipelineStep("commit", "a3", lambda state: {}),
    ]
    escalations = orchestrator.run_cycle({"pipeline": pipeline, "state": {}})

    assert len(escalations) == 1
    ev = escalations[0]
    assert ev.type is EventType.ESCALATION_RAISED
    assert ev.actor_agent == 16
    assert ev.subject_id == "verify"
    assert "book missing" in ev.payload["error"]
    assert ev.payload["remaining_steps_halted"] is True

    statuses = {r["step"]: r["status"] for r in orchestrator.last_run}
    assert statuses["extract"] == "ok"
    assert "FAILED" in statuses["verify"]
    assert statuses["commit"] == "skipped (pipeline halted)"
    assert a3.received_contexts == []  # never actually invoked


def test_unregistered_agent_key_raises_before_running_anything():
    a1 = _FakeAgent(events=[])
    orchestrator = OrchestratorAgent(_null_api(), registry={"a1": a1})
    pipeline = [PipelineStep("ghost", "does-not-exist", lambda state: {})]

    try:
        orchestrator.run_cycle({"pipeline": pipeline, "state": {}})
        assert False, "expected KeyError"
    except KeyError as e:
        assert "does-not-exist" in str(e)
    assert a1.received_contexts == []


def test_empty_pipeline_is_a_no_op():
    orchestrator = OrchestratorAgent(_null_api(), registry={})
    escalations = orchestrator.run_cycle({"pipeline": [], "state": {}})
    assert escalations == []
    assert orchestrator.last_run == []
