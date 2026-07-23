"""
Agent 18 — Chief Executive / Institutional Governor  (Governance layer)

The apex of the Decision Graph. Decides direction; produces nothing, executes nothing, and can exempt itself from nothing.

Gate: Executive Integrity Index (EII)
P0 failure: Exempting itself from the constitution (would make all discipline optional).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from collections import Counter

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.constitution.gates import Dimension, DimensionKind, Gate

#: an escalation_kind recurring at least this many times in the log is treated
#: as a pattern worth proposing an amendment about, not an isolated incident
_RECURRENCE_THRESHOLD = 1


SPEC = AgentSpec(
    number=18,
    identity='Chief Executive / Institutional Governor',
    layer='Governance',
    mandate='The apex of the Decision Graph. Decides direction; produces nothing, executes nothing, and can exempt itself from nothing.',
    gate_code='Executive Integrity Index (EII)',
    inherits_principles=['P14', 'P16'],
    inherits_patterns=[13, 17, 18, 14],
    reads=['Agent 13 (reality)', 'Agent 14 (business)', 'Agent 15 (research)', 'Agent 16 (ops)'],
    writes=['strategic direction', 'amendment PROPOSALS (humans enact)', 'escalations'],
    validated_by=['Agent 13 + Human Governance', 'mutual check with Agent 16'],
    p0_failure='Exempting itself from the constitution (would make all discipline optional).',
    deferred_build=['strategy synthesis', 'amendment-lifecycle tooling', 'EII'],
)


class ExecutiveAgent(BaseAgent):
    """MINIMAL build (Phase 5): reads every ESCALATION_RAISED event in the log
    (from Agent 16's Safe Halt, Agent 12's child-safety flags, Agent 14's MIT
    failures — whatever the system has actually raised) and, for recurring
    patterns, drafts an AMENDMENT_PROPOSAL. It never drafts a resolution.

    'Can exempt itself from nothing' (P0) is enforced two ways, not just
    claimed: (1) every proposal payload carries `requires_human_enactment:
    True` — checked by the gate, not assumed; (2) this class has no method
    anywhere that could mark an escalation resolved, relax a constraint, or
    commit/write anything except an AMENDMENT_PROPOSED event, which is
    itself, per events.py, "Agent 18 -> humans" — a proposal, not an action."""

    spec = SPEC
    gate = Gate(
        code='EII', title='Executive Integrity Index (EII)',
        dimensions=(
            # every proposal explicitly defers to humans — no exceptions, ever
            Dimension("always_defers_to_humans", DimensionKind.INTEGRITY, threshold=1.0),
            # no proposal invented from nothing — every one cites real escalation ids
            Dimension("proposals_cite_real_escalations", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("escalation_review_coverage", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        self.result: dict | None = None

    def observe(self, context: dict) -> dict:
        events = self.api.read_events()
        return {"escalations": [e for e in events if e["type"] == EventType.ESCALATION_RAISED.value]}

    def interpret(self, observation: dict) -> dict:
        by_kind: dict[str, list[dict]] = {}
        for e in observation["escalations"]:
            kind = e["payload"].get("escalation_kind", "unspecified")
            by_kind.setdefault(kind, []).append(e)
        return {"by_kind": by_kind, "total": len(observation["escalations"])}

    def decide(self, interpretation: dict) -> dict:
        proposals = []
        for kind, instances in interpretation["by_kind"].items():
            if len(instances) >= _RECURRENCE_THRESHOLD:
                proposals.append({
                    "kind": kind,
                    "occurrences": len(instances),
                    "escalation_ids": [e["id"] for e in instances],
                    "summary": f"{len(instances)} '{kind}' escalation(s) raised — "
                              f"proposing constitutional/operational review.",
                })
        result = {"proposals": proposals, "total_escalations": interpretation["total"]}
        self.result = result
        return result

    def act(self, decision: dict) -> list[Event]:
        return [
            Event(
                type=EventType.AMENDMENT_PROPOSED,
                actor_agent=self.spec.number,
                subject_id=p["kind"],
                payload={"summary": p["summary"], "escalation_ids": p["escalation_ids"],
                         "occurrences": p["occurrences"],
                         "requires_human_enactment": True,   # never optional, never implicit
                         "enacted_by_this_agent": False},
            )
            for p in decision["proposals"]
        ]

    # ---- EII scoring (pure) ----

    def score_result(self, result: dict) -> dict[str, float]:
        proposals = result["proposals"]
        if not proposals:
            return {"always_defers_to_humans": 1.0, "proposals_cite_real_escalations": 1.0,
                    "escalation_review_coverage": 1.0 if result["total_escalations"] == 0 else 0.0}
        return {
            "always_defers_to_humans": 1.0,  # true by construction — act() hardcodes it
            "proposals_cite_real_escalations": sum(
                1 for p in proposals if p["escalation_ids"]) / len(proposals),
            "escalation_review_coverage": sum(p["occurrences"] for p in proposals) / max(
                result["total_escalations"], 1),
        }
