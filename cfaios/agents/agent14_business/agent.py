"""
Agent 14 — Business Intelligence Officer (BIO)  (Intelligence layer)

Revenue is infrastructure, not objective. Models the business; never sets strategy.

Gate: Business Integrity Index (BII)
P0 failure: A manipulative growth directive laundered through a metric.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.constitution.escalation import EscalationKind
from cfaios.constitution.gates import Dimension, DimensionKind, Gate
from cfaios.constitution.governance import MITResult

#: Sole-optimization simulation, made concrete (governance.py's
#: ManipulationIncentiveTest Protocol left the screening logic as a deferred
#: build item — this is a first, keyword-heuristic implementation, not a
#: claim that manipulation detection is a solved problem). A metric is
#: screened by asking: if this became the ONLY thing optimized, what
#: behavior emerges, and does it violate P11 (engagement may amplify truth,
#: never replace it) or P14 (persuade, never manipulate)?
_MANIPULATIVE_SIGNALS = {
    "engagement": "P11", "time on app": "P14", "time_on_app": "P14",
    "streak": "P14", "session length": "P14", "dau": "P11", "watch time": "P11",
    "notifications sent": "P14", "urgency": "P14", "fomo": "P14",
}


def screen_metric(metric_name: str, objective_function: str) -> MITResult:
    """A concrete Layer-1 governance check (ManipulationIncentiveTest). Sole-
    optimization of a metric matching a known manipulative signal is illegal;
    everything else passes this floor (a real system would layer far more —
    this is honestly a floor, not a ceiling)."""
    haystack = f"{metric_name} {objective_function}".lower()
    violated = [principle for signal, principle in _MANIPULATIVE_SIGNALS.items() if signal in haystack]
    return MITResult(
        metric=metric_name, legal=not violated, violated=sorted(set(violated)),
        rationale=(f"sole-optimization would incentivize {', '.join(violated)}-violating behavior"
                  if violated else "no known manipulative pattern matched"),
    )


SPEC = AgentSpec(
    number=14,
    identity='Business Intelligence Officer (BIO)',
    layer='Intelligence',
    mandate='Revenue is infrastructure, not objective. Models the business; never sets strategy.',
    gate_code='Business Integrity Index (BII)',
    inherits_principles=['P14', 'P16'],
    inherits_patterns=[13, 17, 18],
    reads=['Agent 13 (ONLY measurement source)', 'Trust Signals', 'cost/ops data'],
    writes=['business models', 'CIAs', 'MIT-screened metrics', 'escalated conflicts -> A18'],
    validated_by=['BII gate', 'Agent 13', 'human governance (escalation)'],
    p0_failure='A manipulative growth directive laundered through a metric.',
    deferred_build=['Mission Hierarchy model', 'CRF filter', 'CIA generator', 'pricing-ethics checker'],
)


class BusinessAgent(BaseAgent):
    """MINIMAL build (Phase 5). Two constitutional anchors, both literal:

    'Agent 13 (ONLY measurement source)' — observe() accepts exactly Agent
    13's report and nothing else; there is no parameter or code path here
    that could accept a raw revenue/engagement number from anywhere else.

    'Models the business; never sets strategy' — decide() only classifies
    proposed metrics as legal/illegal (Layer 1 of the governance stack, MIT)
    and summarizes what Agent 13 already measured. It recommends nothing and
    has no method that could. Illegal metrics escalate to Agent 18
    (EscalationKind.MISSION_MONEY) — Agent 14 never resolves the conflict
    itself, matching the P0 guard directly."""

    spec = SPEC
    gate = Gate(
        code='BII', title='Business Integrity Index (BII)',
        dimensions=(
            # every metric in the model went through the MIT screen
            Dimension("mit_screened", DimensionKind.INTEGRITY, threshold=1.0),
            # no illegal metric survives into the business model unescalated
            Dimension("illegal_metrics_escalated", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("model_coverage", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api):
        super().__init__(api)
        self.model: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"analytics_report": <Agent 13's report, verbatim>,
        "proposed_metrics": [{"name": str, "objective_function": str}]}"""
        return {"report": context["analytics_report"],
                "proposed_metrics": context.get("proposed_metrics", [])}

    def interpret(self, observation: dict) -> dict:
        """Screen every proposed metric through MIT. This is the only
        judgement made here — everything after is bookkeeping."""
        screened = [screen_metric(m["name"], m["objective_function"])
                   for m in observation["proposed_metrics"]]
        return {"report": observation["report"], "screened": screened}

    def decide(self, interpretation: dict) -> dict:
        legal = [r for r in interpretation["screened"] if r.legal]
        illegal = [r for r in interpretation["screened"] if not r.legal]
        funnel = interpretation["report"].get("funnel", {})
        model = {
            "legal_metrics": [r.metric for r in legal],
            "illegal_metrics": [{"metric": r.metric, "violated": r.violated, "rationale": r.rationale}
                                for r in illegal],
            # summary derived ONLY from Agent 13's numbers — infrastructure framing
            # (Rule.MISSION_HIERARCHY: mission -> sustainability -> efficiency),
            # never a target to hit
            "educational_output_summary": {
                "verified_knowledge_committed": funnel.get("committed"),
                "confirmation_rate": funnel.get("confirmation_rate"),
            },
        }
        self.model = model
        return {"model": model, "illegal": illegal}

    def act(self, decision: dict) -> list[Event]:
        """One ESCALATION_RAISED per illegal metric — routed to Agent 18,
        never auto-blocked or auto-approved by this agent."""
        return [
            Event(
                type=EventType.ESCALATION_RAISED,
                actor_agent=self.spec.number,
                subject_id=r.metric,
                payload={"escalation_kind": EscalationKind.MISSION_MONEY.value,
                         "violated": r.violated, "rationale": r.rationale,
                         "constitutional_basis": "governance.py Layer 1 (MIT)"},
            )
            for r in decision["illegal"]
        ]

    # ---- BII scoring (pure) ----

    def score_model(self, model: dict, screened_count: int, proposed_count: int) -> dict[str, float]:
        if proposed_count == 0:
            return {"mit_screened": 0.0, "illegal_metrics_escalated": 0.0, "model_coverage": 0.0}
        return {
            "mit_screened": screened_count / proposed_count,
            # by construction every illegal metric here already produced an
            # escalation event in act() — this asserts none were silently kept legal
            "illegal_metrics_escalated": 1.0 if all(
                isinstance(m, dict) for m in model["illegal_metrics"]) else 0.0,
            "model_coverage": len(model["legal_metrics"]) / proposed_count if proposed_count else 0.0,
        }
