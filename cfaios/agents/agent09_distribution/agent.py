"""
Agent 9 — Chief Social Distribution Intelligence (CSDI)  (Communication layer)

Distribution, not creation. Maximizes reach of validated content without altering its truth (P12).

Gate: Social Integrity Index (SII)
P0 failure: A fragment that misleads out of context (Audience Inference failure).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Dimension, DimensionKind, Gate

#: character budgets per platform — mechanical constraints, not editorial choices
_PLATFORMS = {"twitter": 280, "tiktok_caption": 150, "instagram_caption": 2200}


SPEC = AgentSpec(
    number=9,
    identity='Chief Social Distribution Intelligence (CSDI)',
    layer='Communication',
    mandate='Distribution, not creation. Maximizes reach of validated content without altering its truth (P12).',
    gate_code='Social Integrity Index (SII)',
    inherits_principles=['P11', 'P12'],
    inherits_patterns=[9, 11, 12],
    reads=['validated A8 content (parents)', 'CKG (for reactive R1)', 'platform data'],
    writes=['platform-native fragments (L6)', 'trend signal -> A8'],
    validated_by=['SII gate', 'post-publication monitoring'],
    p0_failure='A fragment that misleads out of context (Audience Inference failure).',
    deferred_build=['Audience Inference Risk scorer', 'Semantic Distance classifier', 'reactive R1/R2/R3 gate', 'scheduling engine'],
)


class DistributionAgent(BaseAgent):
    """MINIMAL build (Phase 5): platform-native fragments via S0 transformation
    ONLY (Pattern #11: presentation changes, meaning never does). No LLM is
    involved — truncation and templating are the entire transformation, which
    is what makes Validation Conservation (Pattern #12) hold by construction
    rather than by post-hoc checking: nothing gets reworded, so nothing can
    drift from what Agent 8 already had PQI-gated.

    The P0 (a fragment that misleads out of context) is addressed structurally:
    every fragment carries a verified-provenance tag inline, so it never stands
    alone without its grounding, however far it travels from the source lesson.
    A real Audience Inference Risk scorer (probabilistic, platform-specific) is
    still deferred — this is the S0-only floor under it."""

    spec = SPEC
    gate = Gate(
        code='SII', title='Social Integrity Index (SII)',
        dimensions=(
            # every fragment must still carry its node_id + evidence_ref
            Dimension("provenance_intact", DimensionKind.INTEGRITY, threshold=1.0),
            # mechanical: a fragment that doesn't fit its platform is not "distributed", it's broken
            Dimension("within_platform_limit", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("platform_coverage", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api):
        super().__init__(api)
        self.fragments: list[dict] | None = None

    def observe(self, context: dict) -> dict:
        """context: {"script": <Agent 8's PQI-passed script>, "gate_passed": bool}"""
        if not context.get("gate_passed", False):
            raise ValueError(
                "Agent 9: refusing a script that has not passed Agent 8's PQI gate "
                "(Pattern #2 — no layer consumes unproven output).")
        return {"script": context["script"]}

    def interpret(self, observation: dict) -> dict:
        return {"scenes": observation["script"]["scenes"]}

    def decide(self, interpretation: dict) -> dict:
        """The transformation: truncate, never rewrite. `_fit()` cuts on a word
        boundary and always leaves room for the provenance tag — the tag is
        never the part that gets cut."""
        fragments = []
        for s in interpretation["scenes"]:
            tag = f" [Verified — node {s['node_id']}]"
            for platform, limit in _PLATFORMS.items():
                body = _fit(s.get("on_screen") or s["narration"], limit - len(tag))
                fragments.append({
                    "platform": platform,
                    "text": body + tag,
                    "node_id": s["node_id"],
                    "evidence_ref": s["evidence_ref"],
                    "char_limit": limit,
                })
        return {"fragments": fragments}

    def act(self, decision: dict) -> list[Event]:
        """No EventType models 'fragment published' yet; fragments live on
        self.fragments. 'trend signal -> A8' needs real platform engagement
        data this build has no source for — left deferred rather than faked
        (P16: no fabricated telemetry)."""
        self.fragments = decision["fragments"]
        return []

    # ---- SII scoring (pure) ----

    def score_fragments(self, fragments: list[dict]) -> dict[str, float]:
        if not fragments:
            return {"provenance_intact": 0.0, "within_platform_limit": 0.0, "platform_coverage": 0.0}
        n = len(fragments)
        return {
            "provenance_intact": sum(1 for f in fragments if f.get("node_id") and f.get("evidence_ref")) / n,
            "within_platform_limit": sum(1 for f in fragments if len(f["text"]) <= f["char_limit"]) / n,
            "platform_coverage": len({f["platform"] for f in fragments}) / len(_PLATFORMS),
        }


def _fit(text: str, budget: int) -> str:
    text = " ".join(text.split())
    if len(text) <= budget:
        return text
    cut = text[:max(budget - 1, 0)].rsplit(" ", 1)[0]
    return cut + "…"
