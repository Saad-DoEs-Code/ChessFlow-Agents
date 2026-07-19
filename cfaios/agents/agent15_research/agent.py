"""
Agent 15 — Research Scientist  (Intelligence layer)

Discovery and environmental sensing. Keeps the foundation from going stale; 'discovery creates candidates, verification creates knowledge.'

Gate: Research Integrity Index (RII)
P0 failure: Contaminating the pipeline with unverified external knowledge.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=15,
    identity='Research Scientist',
    layer='Intelligence',
    mandate="Discovery and environmental sensing. Keeps the foundation from going stale; 'discovery creates candidates, verification creates knowledge.'",
    gate_code='Research Integrity Index (RII)',
    inherits_principles=['P3', 'P10'],
    inherits_patterns=[1, 19, 20],
    reads=['external sources', 'CKG (gaps + staleness)', 'community signal (A12)'],
    writes=['candidate knowledge -> A1', 'staleness flags -> A3', 'competitive intel -> A18'],
    validated_by=['RII gate', 'Agent 3 (fires Stale/Superseded)'],
    p0_failure='Contaminating the pipeline with unverified external knowledge.',
    deferred_build=['Knowledge Freshness Lifecycle', 'source-credibility tiers', 'Persistent Research Watchlists'],
)


class ResearchAgent(BaseAgent):
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Research Integrity Index (RII).
    gate = Gate(code='Research Integrity Index (RII)', title='Research Integrity Index (RII)', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 15 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 15 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 15 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 15 act() — build me")
