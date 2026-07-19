"""
Agent 8 — Chief Educational Content Architect (CECA)  (Communication layer)

Writes the movie, doesn't film it. Owns video scripts as a Video Graph; guardian of communicative truth.

Gate: Production Quality Index (PQI)
P0 failure: A viral video stating false chess (permanent, at scale).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.constitution.gates import Dimension, DimensionKind, Gate
from cfaios.infra.llm_groq import GroqClient


SPEC = AgentSpec(
    number=8,
    identity='Chief Educational Content Architect (CECA)',
    layer='Communication',
    mandate="Writes the movie, doesn't film it. Owns video scripts as a Video Graph; guardian of communicative truth.",
    gate_code='Production Quality Index (PQI)',
    inherits_principles=['P10', 'P11'],
    inherits_patterns=[6],
    reads=['CKG', 'Learning DNA', 'lesson blueprints (A5)', 'Agent 3 + Agent 4 inline'],
    writes=['Video Graphs (scripts)', 'claim-strength metadata', 'L5 objects -> staging'],
    validated_by=['3-stage accuracy gate', 'PQI', 'reach+claim human review'],
    p0_failure='A viral video stating false chess (permanent, at scale).',
    deferred_build=['Topic Opportunity Engine', 'Claim Faithfulness Score', 'Series Engine', 'Video Experience Architecture'],
)


_SCRIPT_SYSTEM_PROMPT = (
    "You are converting ONE section of an already-verified chess lesson into a short "
    "video scene script. You get the lesson section's explanation text, the position "
    "(FEN), and what the side to move achieves. Write: (1) NARRATION — 2-4 spoken "
    "sentences a presenter reads aloud, energetic but accurate; (2) ON-SCREEN — one "
    "short caption line. "
    "This is a PRESENTATION transformation only: you MUST NOT add any chess move, "
    "evaluation, or claim that is not in the given explanation. Same meaning, new "
    "medium. Format exactly as:\nNARRATION: <text>\nON-SCREEN: <text>"
)


class ContentAgent(BaseAgent):
    """MINIMAL build (Phase 5): one gated lesson in, one video script out.

    Input is Agent 7's CQI-PASSED lesson — so every chess claim entering this
    agent is already grounded in a committed node. The script transformation is
    S0 semantic distance (Pattern #11: presentation changes, meaning never
    does — P12), which is why the LLM prompt forbids adding chess content and
    why each scene carries forward its section's node_id + evidence_ref
    (Pattern #6: content traceability survives transformation; P13: a claim is
    a claim in any medium).

    Deferred (see README): Topic Opportunity Engine, semantic Claim
    Faithfulness Score (the PQI's faithfulness dimension here is structural —
    provenance intact — not yet an NLP comparison), Series Engine."""

    spec = SPEC
    # PQI: integrity = provenance survives the transformation; quality = the
    # production actually produced usable scenes.
    gate = Gate(
        code='PQI', title='Production Quality Index (PQI)',
        dimensions=(
            # every scene must still carry its node_id + evidence_ref (Pattern #5:
            # composition never destroys provenance) — one orphaned scene blocks
            Dimension("provenance_intact", DimensionKind.INTEGRITY, threshold=1.0),
            # every scene must come from a confirmed-verdict section
            Dimension("verified_source", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("narration_generated", DimensionKind.QUALITY, weight=2.0),
            Dimension("scene_coverage", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api: KnowledgeAPI, llm_client: GroqClient | None = None):
        super().__init__(api)
        self.llm_client = llm_client or GroqClient()
        #: populated by decide()
        self.script: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"lesson": <Agent 7's gated lesson>, "gate_passed": bool}.
        Refusing ungated input is the whole point of layered gates (Pattern #2):
        downstream never consumes what upstream hasn't proven."""
        if not context.get("gate_passed", False):
            raise ValueError(
                "Agent 8: refusing a lesson that has not passed Agent 7's CQI gate "
                "(Pattern #2 — no layer consumes unproven output).")
        return {"lesson": context["lesson"]}

    def interpret(self, observation: dict) -> dict:
        lesson = observation["lesson"]
        return {"topic": lesson["topic"], "graph_version": lesson["graph_version"],
                "sections": lesson["sections"]}

    def decide(self, interpretation: dict) -> dict:
        """Generation last (P10), and only as re-presentation of section text."""
        scenes = []
        for i, s in enumerate(interpretation["sections"], 1):
            user_prompt = (
                f"Lesson section explanation:\n{s['explanation']}\n\n"
                f"Position (FEN): {s['fen']}\n"
                f"Side to move achieves: {s['claimed_result']}\n\n"
                "Write the scene."
            )
            narration, on_screen = "", ""
            try:
                raw = self.llm_client.generate(
                    system=_SCRIPT_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=300,
                )
                narration, on_screen = _parse_scene(raw)
            except Exception as exc:  # one bad call never kills the whole script
                narration = f"(narration unavailable: {exc})"
            scenes.append({
                "scene": i,
                "node_id": s["node_id"],
                "evidence_ref": s["evidence_ref"],
                "verdict_state": s["verdict_state"],
                "fen": s["fen"],
                "narration": narration,
                "on_screen": on_screen,
            })
        script = {"topic": interpretation["topic"],
                  "graph_version": interpretation["graph_version"], "scenes": scenes}
        self.script = script
        return script

    def act(self, decision: dict) -> list[Event]:
        """No EventType models 'video script produced' yet (the L5->staging
        write is a real build item). The script lives on self.script; noted
        honestly rather than inventing an event type mid-slice."""
        return []

    # ---- PQI scoring (pure — no LLM, no I/O) ----

    def score_script(self, script: dict) -> dict[str, float]:
        scenes = script["scenes"]
        if not scenes:
            return {"provenance_intact": 0.0, "verified_source": 0.0,
                    "narration_generated": 0.0, "scene_coverage": 0.0}
        n = len(scenes)
        return {
            "provenance_intact": sum(1 for s in scenes if s.get("node_id") and s.get("evidence_ref")) / n,
            "verified_source": sum(1 for s in scenes if s.get("verdict_state") == "confirmed") / n,
            "narration_generated": sum(
                1 for s in scenes
                if s.get("narration") and not s["narration"].startswith("(narration unavailable")) / n,
            "scene_coverage": 1.0,  # decide() emits one scene per section by construction
        }


def _parse_scene(raw: str) -> tuple[str, str]:
    """Split the model's 'NARRATION: … ON-SCREEN: …' format; tolerate drift."""
    narration, on_screen = raw.strip(), ""
    upper = raw.upper()
    if "NARRATION:" in upper and "ON-SCREEN:" in upper:
        n_start = upper.index("NARRATION:") + len("NARRATION:")
        s_start = upper.index("ON-SCREEN:")
        narration = raw[n_start:s_start].strip()
        on_screen = raw[s_start + len("ON-SCREEN:"):].strip()
    return narration, on_screen
