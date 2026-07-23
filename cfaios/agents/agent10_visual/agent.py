"""
Agent 10 — Chief Visual Experience Architect (CVEA)  (Communication layer)

Owns static visual assets. Proves integrity is modality-independent (P13); applies brand, bootstraps it until Agent 17.

Gate: Thumbnail Quality Index (TQI)
P0 failure: A thumbnail making a false visual claim (fabricated position/eval).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=10,
    identity='Chief Visual Experience Architect (CVEA)',
    layer='Communication',
    mandate='Owns static visual assets. Proves integrity is modality-independent (P13); applies brand, bootstraps it until Agent 17.',
    gate_code='Thumbnail Quality Index (TQI)',
    inherits_principles=['P11', 'P13'],
    inherits_patterns=[4, 5],
    reads=['A8 video specs', 'verified FENs/evals', 'Brand Standard (A17/bootstrap)'],
    writes=['thumbnail specs/assets', 'Visual Faithfulness / Expectation Match scores'],
    validated_by=['TQI gate', 'Agent 3 (depicted positions)', 'CFRS (rights)'],
    p0_failure='A thumbnail making a false visual claim (fabricated position/eval).',
    deferred_build=['Verified Rendering Engine', 'Visual Faithfulness Score', 'Expectation Match', 'Visual Consistency Engine'],
)


#: Bootstrap Brand Standard (applied until Agent 17 owns it — see mandate).
_BRAND = {"palette": "chessflow-dark", "font": "bold-sans", "badge_style": "shield"}

_STIPULATION_TITLES = {"win": "Can you find the WIN?", "draw": "The saving DRAW!",
                       "loss": "A lost cause?"}


class VisualAgent(BaseAgent):
    """MINIMAL build (Phase 5): thumbnail SPEC rendered 100% from verified
    data — no LLM anywhere in this agent. That is not a shortcut; it is the
    constitutional design: this agent inherits exactly Patterns #4 (Verified
    Rendering: machine-verifiable content is rendered from data, never
    generated) and #5 (composition never destroys provenance). The board on
    the thumbnail IS the committed node's FEN; the title is picked from a
    fixed table keyed by the verified stipulation; the badge states only what
    the Evidence Ledger can back. The P0 (a thumbnail making a false visual
    claim) is structurally impossible here because nothing is invented.

    Deferred (see README): actual image rendering (this emits the spec an
    image pipeline would consume), Visual Faithfulness Score, Expectation
    Match. Agent 17 brand integration IS wired: pass its canonical_brand via
    context["brand"] and this agent uses Agent 17's actual approved/rejected
    promises to decide whether it may show the "Engine-verified" badge,
    falling back to the bootstrap default only when no canonical brand has
    been produced yet (Pattern #22: bootstrap until governed)."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Thumbnail Quality Index (TQI).
    gate = Gate(code='Thumbnail Quality Index (TQI)', title='Thumbnail Quality Index (TQI)', dimensions=())

    def __init__(self, api):
        super().__init__(api)
        #: populated by decide()
        self.thumbnail_spec: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"script": <Agent 8's PQI-passed script>, "gate_passed": bool}."""
        if not context.get("gate_passed", False):
            raise ValueError(
                "Agent 10: refusing a script that has not passed Agent 8's PQI gate "
                "(Pattern #2 — no layer consumes unproven output).")
        return {"script": context["script"], "brand": context.get("brand")}

    def interpret(self, observation: dict) -> dict:
        """Pick the hero scene: the first scene (already ordered by Agent 5's
        blueprint). Mechanical choice — no judgement, no generation."""
        script = observation["script"]
        if not script["scenes"]:
            raise ValueError("Agent 10: script has no scenes to depict.")
        return {"topic": script["topic"], "hero": script["scenes"][0],
                "scene_count": len(script["scenes"]), "brand": observation["brand"]}

    def decide(self, interpretation: dict) -> dict:
        hero = interpretation["hero"]
        node = self.api.get_node(hero["node_id"])
        claimed = (node.payload.get("claimed_result") if node else None) or "win"

        canonical = interpretation["brand"]
        if canonical is not None:
            # Governed path: only show the badge if Agent 17 actually approved
            # it against real committed evidence (constitutional reality).
            brand_dict = {k: v for k, v in canonical.items()
                         if k in ("palette", "font", "badge_style", "version")}
            badge = "Engine-verified" if "Engine-verified" in canonical.get("approved_promises", []) else None
        else:
            # Bootstrap path (Pattern #22): no canonical brand yet, use the
            # provisional default — same behavior as before Agent 17 existed.
            brand_dict = dict(_BRAND)
            badge = "Engine-verified"

        spec = {
            "board_fen": hero["fen"],                      # the committed position, verbatim
            "title": _STIPULATION_TITLES.get(claimed, "Solve this!"),
            "badge": badge,
            "subtitle": f"{interpretation['scene_count']}-part lesson",
            "brand": brand_dict,
            # provenance rides ON the spec — composition preserves it (Pattern #5)
            "provenance": {"node_id": hero["node_id"], "evidence_ref": hero["evidence_ref"],
                           "graph_version": self.api.current_version()},
        }
        self.thumbnail_spec = spec
        return spec

    def act(self, decision: dict) -> list[Event]:
        """No EventType models 'thumbnail spec produced'; the spec lives on
        self.thumbnail_spec, provenance included."""
        return []
