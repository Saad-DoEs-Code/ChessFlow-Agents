"""
Agent 4 — Learning Science & Cognitive Architecture Director  (Education layer)

Owns how humans learn. Defines the Learning DNA (keystone learner model), cognitive load, and the mastery-stage ladder.

Gate: CFLSS compliance
P0 failure: Deploying a debunked pedagogical heuristic as if evidence-based.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=4,
    identity='Learning Science & Cognitive Architecture Director',
    layer='Education',
    mandate='Owns how humans learn. Defines the Learning DNA (keystone learner model), cognitive load, and the mastery-stage ladder.',
    gate_code='CFLSS compliance',
    inherits_principles=['P8'],
    inherits_patterns=[],
    reads=['verified CKG concepts', 'learning-science research (via A15)'],
    writes=['Learning DNA', 'pedagogical metadata'],
    validated_by=['Agent 3 (pedagogy is evidence-supported)', 'Agent 13 (outcomes)'],
    p0_failure='Deploying a debunked pedagogical heuristic as if evidence-based.',
    deferred_build=['Learning DNA schema', 'CFLSS evidence tiers', 'cognitive-load model', 'spaced-repetition algorithm'],
)


class LearningScienceAgent(BaseAgent):
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for CFLSS compliance.
    gate = Gate(code='CFLSS compliance', title='CFLSS compliance', dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent 4 observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent 4 interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent 4 decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent 4 act() — build me")
