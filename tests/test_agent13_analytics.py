"""Unit tests for Agent 13 (Analytics) — added 2026-07-23 to close a coverage
gap: implemented in Step 4.4 but only ever exercised live against the real
accumulated event log (run_analytics.py), never with controlled synthetic
events. Tests the pure aggregation logic in isolation."""
from __future__ import annotations

import types

from cfaios.agents.agent13_analytics.agent import AnalyticsAgent


def _event(type_, actor_agent=1, payload=None):
    return {"type": type_, "actor_agent": actor_agent, "payload": payload or {}}


def _fake_api(events):
    return types.SimpleNamespace(read_events=lambda: events, emit=lambda e: None)


def test_empty_log_yields_zero_counts_and_none_rates_not_a_crash():
    agent = AnalyticsAgent(_fake_api([]))
    agent.run_cycle({})
    r = agent.report
    assert r["total_events"] == 0
    assert r["funnel"]["confirmation_rate"] is None       # never a fabricated 0/0
    assert r["funnel"]["commit_rate_of_confirmed"] is None


def test_funnel_counts_match_a_known_synthetic_log():
    events = [
        _event("candidate_staged", actor_agent=1),
        _event("candidate_staged", actor_agent=1),
        _event("candidate_staged", actor_agent=1),
        _event("verdict_recorded", actor_agent=3, payload={"verdict_state": "confirmed"}),
        _event("verdict_recorded", actor_agent=3, payload={"verdict_state": "confirmed"}),
        _event("verdict_recorded", actor_agent=3, payload={"verdict_state": "refuted"}),
        _event("knowledge_committed", actor_agent=2),
        _event("knowledge_committed", actor_agent=2),
        _event("coaching_event", actor_agent=7),
        _event("escalation_raised", actor_agent=16),
    ]
    agent = AnalyticsAgent(_fake_api(events))
    agent.run_cycle({})
    r = agent.report

    assert r["total_events"] == 10
    assert r["funnel"] == {
        "staged": 3, "verified": 3, "confirmed": 2, "committed": 2,
        "confirmation_rate": round(2 / 3, 4), "commit_rate_of_confirmed": 1.0,
    }
    assert r["verdict_distribution"] == {"confirmed": 2, "refuted": 1}
    assert r["events_by_actor"] == {"agent_1": 3, "agent_2": 2, "agent_3": 3, "agent_7": 1, "agent_16": 1}
    assert r["coaching_sections_delivered"] == 1
    assert r["escalations_raised"] == 1


def test_verdict_states_without_key_default_to_unknown_not_dropped():
    events = [_event("verdict_recorded", actor_agent=3, payload={})]  # malformed, no verdict_state
    agent = AnalyticsAgent(_fake_api(events))
    agent.run_cycle({})
    assert agent.report["verdict_distribution"] == {"unknown": 1}


def test_confirmed_but_never_committed_shows_up_as_a_real_gap():
    """If Agent 2 never ran, commit_rate_of_confirmed correctly reports 0.0
    (a real number, not None — the denominator is non-zero here) rather than
    hiding the gap."""
    events = [_event("verdict_recorded", actor_agent=3, payload={"verdict_state": "confirmed"})]
    agent = AnalyticsAgent(_fake_api(events))
    agent.run_cycle({})
    assert agent.report["funnel"]["commit_rate_of_confirmed"] == 0.0


def test_act_emits_nothing_report_lives_on_the_agent():
    agent = AnalyticsAgent(_fake_api([]))
    events = agent.run_cycle({})
    assert events == []
    assert agent.report is not None
