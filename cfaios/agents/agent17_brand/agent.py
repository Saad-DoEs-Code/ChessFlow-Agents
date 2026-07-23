"""
Agent 17 — Brand Identity Director  (Governance layer)

Owns the Declared Brand — the observable manifestation of institutional character. Defines identity; Agent 10 expresses it.

Gate: Brand Consistency Index (BCI)
P0 failure: A brand promise the institution cannot deliver (misrepresenting the whole company).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.core.truth import EvidenceTier
from cfaios.constitution.gates import Dimension, DimensionKind, Gate

#: Tiers that back a genuine "engine-verified" claim; COMMUNITY-tier evidence
#: does not (see truth.py's EvidenceTier — COMMUNITY is the weakest rung).
_ENGINE_BACKED_TIERS = {EvidenceTier.ENGINE_SHALLOW, EvidenceTier.ENGINE_DEEP, EvidenceTier.TABLEBASE}


SPEC = AgentSpec(
    number=17,
    identity='Brand Identity Director',
    layer='Governance',
    mandate='Owns the Declared Brand — the observable manifestation of institutional character. Defines identity; Agent 10 expresses it.',
    gate_code='Brand Consistency Index (BCI)',
    inherits_principles=['P11', 'P12', 'P13'],
    inherits_patterns=[22],
    reads=['provisional brand spec', 'brand-perception data (A13)', 'constitutional reality'],
    writes=['canonical Brand Standard', 'voice spec', 'brand versions -> A2'],
    validated_by=['BCI gate', 'Brand Constitution Test', 'Agent 13 (Brand Debt)'],
    p0_failure='A brand promise the institution cannot deliver (misrepresenting the whole company).',
    deferred_build=['Brand Standard', 'Identity Continuity Score', 'Brand Constitution Test', 'Brand Debt model'],
)


class BrandAgent(BaseAgent):
    """MINIMAL build (Phase 5): Pattern #22 (Bootstrap Resolution) in direct
    action. Agent 10 ships with a hardcoded, provisional `_BRAND` dict and an
    "Engine-verified" badge it cannot itself justify — that provisional
    artifact is exactly what this agent canonicalizes into a versioned Brand
    Standard, checked against 'constitutional reality' before approval.

    The P0 (a brand promise the institution cannot deliver) is checked
    literally: 'Engine-verified' is only approved if the graph actually
    contains engine/tablebase-tier verdicts (not just community-tier). A
    provisional spec that promises more than the graph can back is REJECTED,
    not rubber-stamped — this is the one place in the whole system that
    checks the brand's own honesty against the data, rather than trusting it."""

    spec = SPEC
    gate = Gate(
        code='BCI', title='Brand Consistency Index (BCI)',
        dimensions=(
            # every promise in the canonical standard is checked against real data
            Dimension("promise_deliverable", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("required_fields_present", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("versioned", DimensionKind.QUALITY, weight=1.0),
        ))

    _REQUIRED_FIELDS = ("palette", "font", "badge_style")

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        self.canonical_brand: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"provisional_spec": dict, "promises": {claim_text: required_tier_set}}
        e.g. {"Engine-verified": {"engine_shallow", "engine_deep", "tablebase"}}"""
        return {"provisional_spec": context["provisional_spec"],
                "promises": context.get("promises", {}),
                "node_ids": self.api.list_node_ids()}

    def interpret(self, observation: dict) -> dict:
        """Check each promise against real committed verdicts — 'constitutional
        reality', not the provisional spec's own say-so."""
        tiers_present = set()
        for node_id in observation["node_ids"]:
            verdict = self.api.get_verdict(node_id)
            if verdict is not None:
                tiers_present.add(verdict.tier.name.lower())

        checked = {claim: bool(required_tiers & tiers_present)
                  for claim, required_tiers in observation["promises"].items()}
        return {"provisional_spec": observation["provisional_spec"], "checked_promises": checked}

    def decide(self, interpretation: dict) -> dict:
        spec = interpretation["provisional_spec"]
        deliverable = interpretation["checked_promises"]
        approved_promises = [c for c, ok in deliverable.items() if ok]
        rejected_promises = [c for c, ok in deliverable.items() if not ok]

        canonical = {
            **spec,
            "version": "brand-v1",
            "approved_promises": approved_promises,
            "rejected_promises": rejected_promises,
        }
        self.canonical_brand = canonical
        return canonical

    def act(self, decision: dict) -> list[Event]:
        """No EventType models 'brand version published'; the canonical
        standard lives on self.canonical_brand for Agent 10 to consume."""
        return []

    # ---- BCI scoring (pure) ----

    def score_brand(self, canonical: dict) -> dict[str, float]:
        promises = canonical["approved_promises"] + canonical["rejected_promises"]
        promise_deliverable = (
            len(canonical["approved_promises"]) / len(promises) if promises else 1.0)
        fields_present = sum(1 for f in self._REQUIRED_FIELDS if canonical.get(f)) / len(self._REQUIRED_FIELDS)
        return {
            "promise_deliverable": promise_deliverable,
            "required_fields_present": fields_present,
            "versioned": 1.0 if canonical.get("version") else 0.0,
        }
