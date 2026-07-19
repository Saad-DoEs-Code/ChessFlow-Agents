"""
Agent 13 — Analytics Scientist  (Intelligence layer)

The system's verified self-knowledge. Turns every Phase-A prediction into Phase-B reality; observational, never executive.

Gate: Outcome Effectiveness Index (OEI)
P0 failure: Dishonest data corrupting every downstream decision.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from collections import Counter

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=13,
    identity='Analytics Scientist',
    layer='Intelligence',
    mandate="The system's verified self-knowledge. Turns every Phase-A prediction into Phase-B reality; observational, never executive.",
    gate_code='Outcome Effectiveness Index (OEI)',
    inherits_principles=['P9', 'P16'],
    inherits_patterns=[13, 14, 15, 16],
    reads=['all outcome telemetry (A6-A12)', 'every Phase-A prediction system-wide'],
    writes=['validated Findings (not Recommendations)', 'recalibration signals', 'CTA drift'],
    validated_by=['human audit (grader cannot self-certify)'],
    p0_failure='Dishonest data corrupting every downstream decision.',
    deferred_build=['P9 validation engine', 'MIT / CRF / CIA / CTA', 'Data Traceability', 'metric hierarchy', 'constitutional-trajectory monitoring'],
)


class AnalyticsAgent(BaseAgent):
    """MINIMAL, instrumentation-first build (ROADMAP Step 4.4): counts what the
    event log actually says, and nothing else. Every number in the report is a
    pure aggregation over raw events readable via api.read_events() — Data
    Traceability (Pattern #15) by construction: any figure can be re-derived by
    filtering the log. Produces Findings, never Recommendations (Observation-
    Decision Separation, Pattern #13): this agent measures the pipeline; it
    does not tell anyone what to do about the measurements.

    Deferred (see README): P9 Phase-A->B validation engine, MIT/CRF/CIA/CTA,
    metric hierarchy, trajectory monitoring."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Outcome Effectiveness Index (OEI).
    gate = Gate(code='Outcome Effectiveness Index (OEI)', title='Outcome Effectiveness Index (OEI)', dimensions=())

    def __init__(self, api):
        super().__init__(api)
        #: populated by decide(), for callers to inspect after run_cycle()
        self.report: dict | None = None

    def observe(self, context: dict) -> dict:
        """Raw events only. `read_events()` is a universal read on the
        KnowledgeAPI; bindings without a persistent log return []."""
        return {"events": self.api.read_events()}

    def interpret(self, observation: dict) -> dict:
        events = observation["events"]
        by_type = Counter(e["type"] for e in events)
        by_actor = Counter(e["actor_agent"] for e in events)
        verdict_dist = Counter(
            e["payload"].get("verdict_state", "unknown")
            for e in events if e["type"] == "verdict_recorded")

        staged = by_type.get("candidate_staged", 0)
        verified = by_type.get("verdict_recorded", 0)
        committed = by_type.get("knowledge_committed", 0)
        confirmed = verdict_dist.get("confirmed", 0)

        return {
            "total_events": len(events),
            "events_by_type": dict(by_type),
            "events_by_actor": {f"agent_{k}": v for k, v in sorted(by_actor.items())},
            "verdict_distribution": dict(verdict_dist),
            "funnel": {
                "staged": staged,
                "verified": verified,
                "confirmed": confirmed,
                "committed": committed,
                # rates are None (unknown), never fabricated, when the
                # denominator is zero (P16: honest measurement before anything)
                "confirmation_rate": round(confirmed / verified, 4) if verified else None,
                "commit_rate_of_confirmed": round(committed / confirmed, 4) if confirmed else None,
            },
            "coaching_sections_delivered": by_type.get("coaching_event", 0),
            "escalations_raised": by_type.get("escalation_raised", 0),
        }

    def decide(self, interpretation: dict) -> dict:
        """Findings, not Recommendations: the report is the decision."""
        self.report = interpretation
        return interpretation

    def act(self, decision: dict) -> list[Event]:
        """Emits nothing: no EventType models 'telemetry report produced' yet,
        and inventing one isn't this minimal step's call. The report lives on
        self.report; re-deriving it is always possible from the log itself."""
        return []
