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
from cfaios.constitution.gates import Gate


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
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Social Integrity Index (SII).
    gate = Gate(code='Social Integrity Index (SII)', title='Social Integrity Index (SII)', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 9 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 9 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 9 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 9 act() — build me")
