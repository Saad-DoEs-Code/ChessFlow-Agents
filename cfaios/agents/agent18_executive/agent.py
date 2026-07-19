"""
Agent 18 — Chief Executive / Institutional Governor  (Governance layer)

The apex of the Decision Graph. Decides direction; produces nothing, executes nothing, and can exempt itself from nothing.

Gate: Executive Integrity Index (EII)
P0 failure: Exempting itself from the constitution (would make all discipline optional).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=18,
    identity='Chief Executive / Institutional Governor',
    layer='Governance',
    mandate='The apex of the Decision Graph. Decides direction; produces nothing, executes nothing, and can exempt itself from nothing.',
    gate_code='Executive Integrity Index (EII)',
    inherits_principles=['P14', 'P16'],
    inherits_patterns=[13, 17, 18, 14],
    reads=['Agent 13 (reality)', 'Agent 14 (business)', 'Agent 15 (research)', 'Agent 16 (ops)'],
    writes=['strategic direction', 'amendment PROPOSALS (humans enact)', 'escalations'],
    validated_by=['Agent 13 + Human Governance', 'mutual check with Agent 16'],
    p0_failure='Exempting itself from the constitution (would make all discipline optional).',
    deferred_build=['strategy synthesis', 'amendment-lifecycle tooling', 'EII'],
)


class ExecutiveAgent(BaseAgent):
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Executive Integrity Index (EII).
    gate = Gate(code='Executive Integrity Index (EII)', title='Executive Integrity Index (EII)', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 18 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 18 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 18 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 18 act() — build me")
