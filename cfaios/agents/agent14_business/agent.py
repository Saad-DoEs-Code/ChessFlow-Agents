"""
Agent 14 — Business Intelligence Officer (BIO)  (Intelligence layer)

Revenue is infrastructure, not objective. Models the business; never sets strategy.

Gate: Business Integrity Index (BII)
P0 failure: A manipulative growth directive laundered through a metric.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=14,
    identity='Business Intelligence Officer (BIO)',
    layer='Intelligence',
    mandate='Revenue is infrastructure, not objective. Models the business; never sets strategy.',
    gate_code='Business Integrity Index (BII)',
    inherits_principles=['P14', 'P16'],
    inherits_patterns=[13, 17, 18],
    reads=['Agent 13 (ONLY measurement source)', 'Trust Signals', 'cost/ops data'],
    writes=['business models', 'CIAs', 'MIT-screened metrics', 'escalated conflicts -> A18'],
    validated_by=['BII gate', 'Agent 13', 'human governance (escalation)'],
    p0_failure='A manipulative growth directive laundered through a metric.',
    deferred_build=['Mission Hierarchy model', 'CRF filter', 'CIA generator', 'pricing-ethics checker'],
)


class BusinessAgent(BaseAgent):
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Business Integrity Index (BII).
    gate = Gate(code='Business Integrity Index (BII)', title='Business Integrity Index (BII)', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 14 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 14 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 14 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 14 act() — build me")
