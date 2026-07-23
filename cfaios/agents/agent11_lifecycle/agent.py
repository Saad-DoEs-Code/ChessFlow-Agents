"""
Agent 11 — Chief Audience Lifecycle Architect (CALA)  (Communication layer)

Designs, orchestrates, and governs the owned-audience relationship. Optimizes Relationship Equity, not engagement (P14).

Gate: Lifecycle Integrity Index (LII)
P0 failure: Manipulating a user for a metric (dark pattern in the inbox).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Dimension, DimensionKind, Gate

#: Fixed, neutral templates — no LLM generates this copy. That is the actual
#: P0 guard (manipulating a user for a metric): urgency/scarcity/streak-pressure
#: language cannot appear here because nothing capable of inventing it runs.
_TEMPLATES = {
    "review": "You attempted {concept!r} and it didn't land yet. Whenever you're "
              "ready, it's worth another look.",
    "next": "You've mastered {concept!r}. There's more verified material available "
            "whenever you want to continue.",
}

#: mechanical safety net (Rule.SAFE_HALT-adjacent, not a full manipulation
#: classifier): these substrings must never appear in generated copy.
_BANNED_SUBSTRINGS = ("last chance", "don't lose", "streak", "hurry", "limited time",
                     "act now", "before it's too late", "!!")


SPEC = AgentSpec(
    number=11,
    identity='Chief Audience Lifecycle Architect (CALA)',
    layer='Communication',
    mandate='Designs, orchestrates, and governs the owned-audience relationship. Optimizes Relationship Equity, not engagement (P14).',
    gate_code='Lifecycle Integrity Index (LII)',
    inherits_principles=['P10', 'P11', 'P12', 'P14'],
    inherits_patterns=[7],
    reads=['Competency Graph', 'Relationship Memory', 'validated content', 'A13 analytics'],
    writes=['lifecycle sequences', 'Trust Signals', 'relationship events -> A2'],
    validated_by=['LII gate', 'Agent 13', 'CFCS + P14'],
    p0_failure='Manipulating a user for a metric (dark pattern in the inbox).',
    deferred_build=['Relationship Intent Model', 'Relationship Equity model', 'Respectful Non-Intervention logic', '11-stage lifecycle engine'],
)


class LifecycleAgent(BaseAgent):
    """MINIMAL build (Phase 5): one lifecycle action per competency record,
    templated, never LLM-generated. Pattern #7 (Respectful Non-Intervention)
    is honored literally: a learner with nothing attempted and nothing new to
    offer gets NO sequence entry — silence is a valid, in fact correct,
    output here, not an edge case to paper over.

    Reads the real Competency Graph projection from Step 5 (Agent 6) and the
    blueprint's node set to know what "next" means. Full Relationship Equity
    modeling and the 11-stage lifecycle engine remain deferred (see README)."""

    spec = SPEC
    gate = Gate(
        code='LII', title='Lifecycle Integrity Index (LII)',
        dimensions=(
            # mechanical scan over the actual generated text — cheap, but real
            Dimension("no_manipulation_language", DimensionKind.INTEGRITY, threshold=1.0),
            # every action must cite a real competency record or a real unattempted node
            Dimension("grounded_in_competency", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("respectful_non_intervention", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api):
        super().__init__(api)
        self.sequence: list[dict] | None = None

    def observe(self, context: dict) -> dict:
        """context: {"learner_id": str, "competency": {node_id: {...}} (Agent 6's
        projection for this learner), "candidate_node_ids": [str] (blueprint,
        for "next" suggestions)}"""
        return {"learner_id": context["learner_id"],
                "competency": context.get("competency", {}),
                "candidate_node_ids": context.get("candidate_node_ids", [])}

    def interpret(self, observation: dict) -> dict:
        """Split into: needs review (mastery < 1.0, actually attempted) vs.
        available next (in the candidate set, never attempted). Mastered-and-
        nothing-new is the Respectful Non-Intervention case — produces neither."""
        comp = observation["competency"]
        needs_review = [nid for nid, rec in comp.items() if rec["attempts"] > 0 and rec["mastery"] < 1.0]
        attempted = set(comp.keys())
        available_next = [nid for nid in observation["candidate_node_ids"] if nid not in attempted]
        return {"learner_id": observation["learner_id"], "needs_review": needs_review,
                "available_next": available_next}

    def decide(self, interpretation: dict) -> dict:
        actions = []
        for node_id in interpretation["needs_review"]:
            node = self.api.get_node(node_id)
            if node is None:
                continue
            actions.append({"action": "review", "node_id": node_id,
                            "message": _TEMPLATES["review"].format(concept=node.concept)})
        # Respectful Non-Intervention: at most ONE "next" nudge, never a barrage
        if interpretation["available_next"]:
            node_id = interpretation["available_next"][0]
            node = self.api.get_node(node_id)
            if node is not None:
                actions.append({"action": "next", "node_id": node_id,
                                "message": _TEMPLATES["next"].format(concept=node.concept)})
        sequence = {"learner_id": interpretation["learner_id"], "actions": actions}
        self.sequence = sequence
        return sequence

    def act(self, decision: dict) -> list[Event]:
        """No EventType models a lifecycle sequence; relationship events would
        target a Relationship Memory store this build doesn't have (see
        README). Sequence lives on self.sequence."""
        return []

    # ---- LII scoring (pure) ----

    def score_sequence(self, sequence: dict) -> dict[str, float]:
        actions = sequence["actions"]
        if not actions:
            # Silence can be entirely correct (Respectful Non-Intervention) —
            # don't fail integrity for producing nothing when there's nothing
            # honest to say; only quality reflects it (scored 1.0: silence
            # WAS the respectful choice here, by construction of decide()).
            return {"no_manipulation_language": 1.0, "grounded_in_competency": 1.0,
                    "respectful_non_intervention": 1.0}
        n = len(actions)
        clean = sum(1 for a in actions
                   if not any(b in a["message"].lower() for b in _BANNED_SUBSTRINGS))
        grounded = sum(1 for a in actions if a.get("node_id"))
        return {
            "no_manipulation_language": clean / n,
            "grounded_in_competency": grounded / n,
            # never more than one unsolicited "next" nudge per sequence
            "respectful_non_intervention": 1.0 if sum(1 for a in actions if a["action"] == "next") <= 1 else 0.0,
        }
