"""
Agent 6 — Assessment Director  (Education layer)

Measures learning across four outcome types. Owns the Competency Graph — the learner-side mirror of the knowledge graph.

Gate: Assessment Reliability Index (ARI)
P0 failure: A high-stakes score that misrepresents actual competency.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=6,
    identity='Assessment Director',
    layer='Education',
    mandate='Measures learning across four outcome types. Owns the Competency Graph — the learner-side mirror of the knowledge graph.',
    gate_code='Assessment Reliability Index (ARI)',
    inherits_principles=['P6'],
    inherits_patterns=[2],
    reads=['Learning DNA', 'learner responses', 'CKG'],
    writes=['Competency Graph updates', 'diagnostic assessments'],
    validated_by=['ARI gate', 'Agent 13'],
    p0_failure='A high-stakes score that misrepresents actual competency.',
    deferred_build=['four outcome types', 'diagnostic distractors', 'Competency Graph schema'],
)


class AssessmentAgent(BaseAgent):
    """MINIMAL build (Phase 5). One outcome type of the four (objective
    position-judgement); the rest, diagnostic distractors, and the full
    Competency Graph schema stay deferred (see README).

    Two constitutional anchors:
      * Questions are RENDERED FROM VERIFIED DATA, never generated (Pattern #4,
        Verified Rendering): the question is always "given this position and
        side to move, what is the objective result?", and the answer key is
        the claimed_result Agent 3 CONFIRMED. There is no way for a question
        or its key to be hallucinated — no LLM is involved at all.
      * The Competency Graph is a projection of COMPETENCY_UPDATED events
        (exactly what events.py declares) — same event-sourcing discipline the
        knowledge graph proved in Step 4.1. `competency_projection()` rebuilds
        it from the log; nothing else stores it.

    P0 guard (a score that misrepresents competency): unanswered questions are
    reported as unanswered — never counted as right OR wrong — and mastery is
    computed only over what the learner actually attempted."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Assessment Reliability Index (ARI).
    gate = Gate(code='Assessment Reliability Index (ARI)', title='Assessment Reliability Index (ARI)', dimensions=())

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        #: populated by decide(), for callers to inspect after run_cycle()
        self.result: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"learner_id": str, "node_ids": [str], "responses": {node_id: answer}}.
        Omit "responses" (or leave empty) to only render the diagnostic."""
        nodes = [n for n in (self.api.get_node(nid) for nid in context["node_ids"])
                 if n is not None]
        return {"learner_id": context["learner_id"], "nodes": nodes,
                "responses": context.get("responses", {})}

    def interpret(self, observation: dict) -> dict:
        """Render one question per assessable node. A node is assessable only
        if it has a FEN, a claimed_result, and a CONFIRMED verdict — assessing
        a learner against unverified knowledge would be the P0 in the making,
        so such nodes are excluded and reported, not silently dropped."""
        questions, excluded = [], []
        for node in observation["nodes"]:
            p = node.payload
            state = (next(iter(node.verdict.dimension_results.values())).value
                     if node.verdict else None)
            if p.get("fen") and p.get("claimed_result") and state == "confirmed":
                questions.append({
                    "node_id": node.node_id,
                    "concept": node.concept,
                    "fen": p["fen"],
                    "stipulation": p.get("stipulation"),
                    "prompt": (f"Position: {p['fen']} — {p.get('stipulation', 'side to move')}. "
                               f"What is the objective result with best play: win, draw, or loss?"),
                    "answer_key": p["claimed_result"],   # Agent 3 CONFIRMED this
                    "evidence_ref": node.verdict.evidence_ref,
                })
            else:
                excluded.append({"node_id": node.node_id,
                                 "reason": f"not assessable (verdict={state}, fen={bool(p.get('fen'))})"})
        return {"learner_id": observation["learner_id"], "questions": questions,
                "excluded": excluded, "responses": observation["responses"]}

    def decide(self, interpretation: dict) -> dict:
        """Score only what was actually answered. Mastery per node is 1.0/0.0
        on this single attempt (Phase-A structural — Agent 13 recalibrates
        with outcome data later, P9)."""
        scored, unanswered = [], []
        for q in interpretation["questions"]:
            answer = interpretation["responses"].get(q["node_id"])
            if answer is None:
                unanswered.append(q["node_id"])
                continue
            correct = str(answer).strip().lower() == q["answer_key"]
            scored.append({**q, "answer": answer, "correct": correct,
                           "mastery": 1.0 if correct else 0.0})

        attempted = len(scored)
        result = {
            "learner_id": interpretation["learner_id"],
            "questions": interpretation["questions"],
            "excluded": interpretation["excluded"],
            "scored": scored,
            "unanswered": unanswered,
            "attempted": attempted,
            "correct": sum(1 for s in scored if s["correct"]),
            # None, never a made-up number, when nothing was attempted (P16)
            "accuracy": (sum(1 for s in scored if s["correct"]) / attempted) if attempted else None,
        }
        self.result = result
        return result

    def act(self, decision: dict) -> list[Event]:
        """One COMPETENCY_UPDATED event per scored answer — the Competency
        Graph is the projection of these (P6). Unanswered questions emit
        nothing: no evidence, no update."""
        return [
            Event(
                type=EventType.COMPETENCY_UPDATED,
                actor_agent=self.spec.number,
                subject_id=decision["learner_id"],
                payload={"node_id": s["node_id"], "concept": s["concept"],
                         "answer": s["answer"], "answer_key": s["answer_key"],
                         "correct": s["correct"], "mastery": s["mastery"],
                         "evidence_ref": s["evidence_ref"]},
            )
            for s in decision["scored"]
        ]


def competency_projection(events: list[dict]) -> dict[str, dict[str, dict]]:
    """Fold COMPETENCY_UPDATED events into the Competency Graph:
    {learner_id: {node_id: {mastery, attempts, correct}}}. Later attempts
    update mastery to the latest value and accumulate counts — the projection
    is rebuildable from the log at any time, exactly like the knowledge graph
    (Step 4.1)."""
    graph: dict[str, dict[str, dict]] = {}
    for ev in events:
        if ev["type"] != EventType.COMPETENCY_UPDATED.value:
            continue
        p = ev["payload"]
        node = graph.setdefault(ev["subject_id"], {}).setdefault(
            p["node_id"], {"mastery": 0.0, "attempts": 0, "correct": 0})
        node["attempts"] += 1
        node["correct"] += 1 if p["correct"] else 0
        node["mastery"] = p["mastery"]
    return graph
