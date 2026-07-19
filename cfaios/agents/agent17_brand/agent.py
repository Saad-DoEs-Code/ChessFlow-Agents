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
from cfaios.constitution.gates import Gate


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
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Brand Consistency Index (BCI).
    gate = Gate(code='Brand Consistency Index (BCI)', title='Brand Consistency Index (BCI)', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 17 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 17 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 17 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 17 act() — build me")
