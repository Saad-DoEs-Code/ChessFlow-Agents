"""
Agent 7 — Chief Coaching Intelligence (CCI)  (Communication layer)

The face of the company and runtime orchestrator. Composes verified objects into live coaching; never creates content (P10).

Gate: Coaching Quality Index (CQI)
P0 failure: Hallucinating chess to a live learner.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.constitution.gates import Dimension, DimensionKind, Gate
from cfaios.infra.llm_groq import GroqClient


SPEC = AgentSpec(
    number=7,
    identity='Chief Coaching Intelligence (CCI)',
    layer='Communication',
    mandate='The face of the company and runtime orchestrator. Composes verified objects into live coaching; never creates content (P10).',
    gate_code='Coaching Quality Index (CQI)',
    inherits_principles=['P10'],
    inherits_patterns=[10],
    reads=['Competency Graph', 'Learning DNA', 'CKG (via API)', 'Agent 3 inline'],
    writes=['Coaching Events -> A2', 'Relationship Memory (shared w/ A11)'],
    validated_by=['CQI gate', 'Agent 13', 'CFCS conduct'],
    p0_failure='Hallucinating chess to a live learner.',
    deferred_build=['verification router (real-time)', 'Adaptive Socratic Engine', 'Motivation Engine', 'three-layer memory'],
)


_SYSTEM_PROMPT = (
    "You are a chess coach explaining ONE verified endgame study to a learner. "
    "You are given: the position (FEN), what the side to move is claimed to achieve, "
    "a verification verdict from a chess engine, and an excerpt of the original "
    "source text describing the study. Explain the idea in clear, encouraging "
    "teaching language, 3-5 sentences. "
    "You MUST NOT invent any move, variation, or claim that is not present in the "
    "source text or the facts given to you. If the source text is garbled or unclear "
    "in places, say so rather than guessing what it meant. Teach the position "
    "naturally — do not mention that you were handed a verdict or source excerpt."
)


class CoachingAgent(BaseAgent):
    """MINIMAL build (ROADMAP Step 3.2). Takes Agent 5's blueprint, retrieves the
    referenced verified nodes (P10: retrieve BEFORE generation — nothing here
    originates a chess claim), and asks the LLM to EXPLAIN each one individually,
    strictly from what was retrieved. One explanation per node, each explicitly
    tagged with the node_id it came from — "every chess claim maps to a node ID"
    is true by construction (one verified node in, one attributed section out),
    not by post-hoc scanning of free-form prose for hallucinations. Full claim-
    level attribution inside a single generated paragraph, the real-time
    Verification Router, Adaptive Socratic Engine, and three-layer memory all
    remain deferred (see README) — this is the smallest version that can't
    silently invent chess."""

    spec = SPEC
    # The first REAL gate in the system (ROADMAP Step 4.3). Integrity dimensions
    # block unconditionally (Integrity-First Optimization); quality dimensions
    # form the weighted score. All scores are Phase-A structural predictions
    # until Agent 13 has outcome data to recalibrate against (P9).
    gate = Gate(
        code='CQI', title='Coaching Quality Index (CQI)',
        dimensions=(
            # Every section must trace to a retrieved node with a ledger ref —
            # a single ungrounded section is a P0 (hallucinating chess), so this
            # blocks at anything below 100%.
            Dimension("grounding", DimensionKind.INTEGRITY, threshold=1.0),
            # Only CONFIRMED knowledge may be taught. Agent 2 should make this
            # impossible to violate upstream; the gate re-checks anyway —
            # External Validation, not trust.
            Dimension("verified_only", DimensionKind.INTEGRITY, threshold=1.0),
            # Quality: did generation actually produce teaching text …
            Dimension("explanation_generated", DimensionKind.QUALITY, weight=2.0),
            # … of a plausible teaching length (not truncated, not a token dump).
            Dimension("explanation_length", DimensionKind.QUALITY, weight=1.0),
        ))

    #: sane band for a 3-5 sentence explanation, in characters
    _MIN_EXPLANATION_CHARS = 120
    _MAX_EXPLANATION_CHARS = 1400

    def __init__(self, api: KnowledgeAPI, llm_client: GroqClient | None = None):
        super().__init__(api)
        # NOTE: ROADMAP.md names cfaios/infra/llm_anthropic.py for this step, but
        # CFAIOS_ANTHROPIC_API_KEY is still an unfilled placeholder (see
        # PROGRESS.md) — Groq is bound and proven working end-to-end, so this
        # uses GroqClient instead. Swappable: AnthropicClient exposes the same
        # generate() shape once a real key is bound.
        self.llm_client = llm_client or GroqClient()
        #: populated by decide(), for callers to inspect after run_cycle()
        self.lesson: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"blueprint": <Agent 5's blueprint dict>}"""
        blueprint = context["blueprint"]
        nodes = [n for n in (self.api.get_node(s["node_id"]) for s in blueprint["sections"])
                 if n is not None]
        return {"topic": blueprint["topic"], "graph_version": blueprint["graph_version"], "nodes": nodes}

    def interpret(self, observation: dict) -> dict:
        """Structure each retrieved node's grounding facts. No generation yet —
        this is the "retrieve" half of P10, kept strictly separate from "generate"."""
        grounded = []
        for node in observation["nodes"]:
            payload = node.payload
            state = (next(iter(node.verdict.dimension_results.values())).value
                     if node.verdict else "unknown")
            grounded.append({
                "node_id": node.node_id,
                "concept": node.concept,
                "fen": payload.get("fen"),
                "claimed_result": payload.get("claimed_result"),
                "verdict_state": state,
                "evidence_ref": node.verdict.evidence_ref if node.verdict else None,
                "source_excerpt": " ".join(payload.get("raw_text", "").split())[:800],
            })
        return {"topic": observation["topic"], "graph_version": observation["graph_version"],
                "grounded": grounded}

    def decide(self, interpretation: dict) -> dict:
        """Generation happens here, last (P10) — one explanation per node,
        strictly from what interpret() already retrieved and structured."""
        sections = []
        for g in interpretation["grounded"]:
            user_prompt = (
                f"Position (FEN): {g['fen']}\n"
                f"Claim: side to move achieves \"{g['claimed_result']}\"\n"
                f"Verification verdict: {g['verdict_state']}\n"
                f"Source text excerpt:\n{g['source_excerpt']}\n\n"
                "Explain this study to a learner in 3-5 sentences."
            )
            try:
                explanation = self.llm_client.generate(
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=300,
                )
            except Exception as exc:  # a bad LLM call must not kill the whole lesson
                explanation = f"(explanation unavailable: {exc})"
            sections.append({**g, "explanation": explanation})

        lesson = {"topic": interpretation["topic"], "graph_version": interpretation["graph_version"],
                  "sections": sections}
        self.lesson = lesson
        return lesson

    def act(self, decision: dict) -> list[Event]:
        """One COACHING_EVENT per explained node — the audit trail proving
        which verified node backed which generated section. Never writes the
        graph (P4) — Agent 7 explains committed knowledge, it doesn't alter it."""
        return [
            Event(
                type=EventType.COACHING_EVENT,
                actor_agent=self.spec.number,
                subject_id=s["node_id"],
                payload={"concept": s["concept"], "verdict_state": s["verdict_state"],
                         "evidence_ref": s["evidence_ref"]},
            )
            for s in decision["sections"]
        ]

    # ---- CQI scoring (feeds evaluate_gate; pure — no LLM, no I/O) ----

    def score_lesson(self, lesson: dict) -> dict[str, float]:
        """Score a lesson for the CQI gate. Callers do
        `agent.evaluate_gate(agent.score_lesson(lesson))` and must not ship the
        lesson downstream unless the result passes (Pattern #2)."""
        sections = lesson["sections"]
        if not sections:
            # An empty lesson has nothing grounded — fail integrity, don't
            # vacuously pass on 0/0.
            return {"grounding": 0.0, "verified_only": 0.0,
                    "explanation_generated": 0.0, "explanation_length": 0.0}

        n = len(sections)
        grounded = sum(1 for s in sections if s.get("node_id") and s.get("evidence_ref"))
        verified = sum(1 for s in sections if s.get("verdict_state") == "confirmed")
        generated = sum(1 for s in sections
                        if s.get("explanation")
                        and not s["explanation"].startswith("(explanation unavailable"))
        sane_length = sum(
            1 for s in sections
            if self._MIN_EXPLANATION_CHARS <= len(s.get("explanation", "")) <= self._MAX_EXPLANATION_CHARS)

        return {"grounding": grounded / n, "verified_only": verified / n,
                "explanation_generated": generated / n, "explanation_length": sane_length / n}
