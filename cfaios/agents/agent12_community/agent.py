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
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


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
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Epistemic Moderation.
    gate = Gate(code='Epistemic Moderation', title='Epistemic Moderation', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 12 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 12 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 12 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 12 act() — build me")
