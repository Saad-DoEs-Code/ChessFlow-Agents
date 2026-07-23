"""
Agent 12 — Community Manager  (Communication layer)

The bridge where the company listens. Stewards member<->member community; hosts free discussion without granting it authority (P15).

Gate: Epistemic Moderation
P0 failure: A child-safety failure in a peer-to-peer space.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import Candidate, KnowledgeAPI
from cfaios.core.truth import EpistemicState
from cfaios.constitution.escalation import EscalationKind
from cfaios.constitution.gates import Dimension, DimensionKind, Gate

#: Bootstrap-only heuristic (the real Community Safety Layer is explicitly a
#: deferred build item — see SPEC.deferred_build). This exists only to prove
#: the escalation PATH: a flagged post must never receive ordinary epistemic
#: treatment, only escalation. It is not a real CSL and must not be presented
#: as one.
_UNSAFE_SIGNALS = ("meet up", "my address", "phone number", "send a picture", "send pics")


SPEC = AgentSpec(
    number=12,
    identity='Community Manager',
    layer='Communication',
    mandate='The bridge where the company listens. Stewards member<->member community; hosts free discussion without granting it authority (P15).',
    gate_code='Epistemic Moderation',
    inherits_principles=['P15'],
    inherits_patterns=[1, 8],
    reads=['community content', 'CKG (to assign epistemic status)', 'reputation model'],
    writes=['epistemic annotations', 'Candidate Queue entries -> A1', 'confusion signal'],
    validated_by=['CSL (child-safety)', 'human escalation'],
    p0_failure='A child-safety failure in a peer-to-peer space.',
    deferred_build=['epistemic-state classifier', 'calibration-reputation model', 'two-pipeline moderation', 'Community Safety Layer'],
)


class CommunityAgent(BaseAgent):
    """MINIMAL build (Phase 5): classify by epistemic status rather than
    suppress speech (Pattern #8), and route checkable claims into the SAME
    mediated Candidate Queue Agent 1 uses (Pattern #1) — the "Candidate Queue
    entries -> A1" write is literally `self.api.stage_candidate`, source_agent
    = this agent's number, exactly like Agent 1's own path. A community claim
    never becomes knowledge by being posted; it becomes a candidate, same as
    a book excerpt, and only Agent 3 + Agent 2 can promote it (P4/P15:
    "conversation permitted, authority earned").

    Child safety (P0) is structurally separated from epistemic moderation: a
    flagged post is escalated and NEVER ALSO given an epistemic annotation —
    checked in the gate, not just by convention. The heuristic used here is a
    bootstrap placeholder; the real Community Safety Layer is deferred (see
    README) and this must not be mistaken for it."""

    spec = SPEC
    gate = Gate(
        code='EPISTEMIC_MOD', title='Epistemic Moderation',
        dimensions=(
            # a flagged-unsafe post must escalate, never receive normal treatment
            Dimension("unsafe_escalated_not_annotated", DimensionKind.INTEGRITY, threshold=1.0),
            # every post gets SOME disposition — none silently dropped
            Dimension("no_post_silently_dropped", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("claims_routed_to_queue", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        self.result: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"posts": [{"post_id", "author", "text", "fen"?, "claimed_result"?}]}"""
        return {"posts": context.get("posts", [])}

    def interpret(self, observation: dict) -> dict:
        """Safety check first, always — an unsafe post is diverted before any
        epistemic classification is even attempted."""
        classified = []
        for post in observation["posts"]:
            text_lower = post.get("text", "").lower()
            unsafe = any(sig in text_lower for sig in _UNSAFE_SIGNALS)
            checkable = bool(post.get("fen")) and post.get("claimed_result") in ("win", "draw", "loss")
            classified.append({**post, "unsafe": unsafe, "checkable": checkable})
        return {"posts": classified}

    def decide(self, interpretation: dict) -> dict:
        dispositions = []
        for post in interpretation["posts"]:
            if post["unsafe"]:
                dispositions.append({**post, "epistemic_state": None, "escalate": True})
            elif post["checkable"]:
                dispositions.append(
                    {**post, "epistemic_state": EpistemicState.EVIDENCE_REQUESTED, "escalate": False})
            else:
                dispositions.append(
                    {**post, "epistemic_state": EpistemicState.OPEN_DISCUSSION, "escalate": False})
        result = {"dispositions": dispositions}
        self.result = result
        return result

    def act(self, decision: dict) -> list[Event]:
        events: list[Event] = []
        for post in decision["dispositions"]:
            if post["escalate"]:
                events.append(Event(
                    type=EventType.ESCALATION_RAISED,
                    actor_agent=self.spec.number,
                    subject_id=post["post_id"],
                    payload={"escalation_kind": EscalationKind.CHILD_SAFETY.value,
                             "constitutional_basis": "Rule.CSL", "urgency": "immediate",
                             "note": "bootstrap heuristic flag — human review required, "
                                     "not an automated safety determination"},
                ))
                continue

            if post["epistemic_state"] is EpistemicState.EVIDENCE_REQUESTED:
                candidate = Candidate(
                    source_agent=self.spec.number,
                    concept=f"Community claim: {post['text'][:60]}",
                    payload={"fen": post["fen"], "claimed_result": post["claimed_result"],
                             "raw_text": post["text"]},
                    evidence={"source": "community", "post_id": post["post_id"],
                             "author": post.get("author")},
                    epistemic=EpistemicState.PLAUSIBLE,
                )
                staging_id = self.api.stage_candidate(candidate)
                events.append(Event(
                    type=EventType.CANDIDATE_STAGED,
                    actor_agent=self.spec.number,
                    subject_id=staging_id,
                    payload={"post_id": post["post_id"], "epistemic_state": post["epistemic_state"].value},
                ))
            # OPEN_DISCUSSION: annotated in the result, no event — hosting free
            # discussion never grants it authority (P15), so it needs no
            # write path into the knowledge machinery at all.
        return events

    # ---- Epistemic Moderation scoring (pure) ----

    def score_moderation(self, dispositions: list[dict]) -> dict[str, float]:
        if not dispositions:
            return {"unsafe_escalated_not_annotated": 0.0, "no_post_silently_dropped": 0.0,
                    "claims_routed_to_queue": 0.0}
        n = len(dispositions)
        unsafe = [p for p in dispositions if p["unsafe"]]
        safety_ok = sum(1 for p in unsafe if p["escalate"] and p["epistemic_state"] is None)
        no_drop = sum(1 for p in dispositions if p["escalate"] or p["epistemic_state"] is not None)
        checkable = [p for p in dispositions if p["checkable"] and not p["unsafe"]]
        routed = sum(1 for p in checkable if p["epistemic_state"] is EpistemicState.EVIDENCE_REQUESTED)
        return {
            "unsafe_escalated_not_annotated": (safety_ok / len(unsafe)) if unsafe else 1.0,
            "no_post_silently_dropped": no_drop / n,
            "claims_routed_to_queue": (routed / len(checkable)) if checkable else 1.0,
        }
