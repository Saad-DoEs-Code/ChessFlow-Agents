"""
BaseAgent — the universal agent contract.

Every one of the 18 agents subclasses this. It encodes the invariants that hold for
*all* agents, so no agent has to re-implement (or accidentally violate) them:

  * Adaptive Intelligence Loop (Pattern #10): observe -> interpret -> decide -> act ->
    measure -> adapt. Subclasses implement the steps; the loop is orchestrated by
    Agent 16, not called ad hoc.
  * Single-Writer (P4): agents write ONLY by emitting events / staging candidates
    through the Knowledge API. `self.api` is the sole doorway.
  * Gate ownership (Pattern #2): every agent declares one gate; output is not consumed
    downstream until the gate passes.
  * External Validation (Doctrine): no agent certifies itself. `validated_by` records
    who validates this agent's output (another agent and/or human governance).
  * Constitutional inheritance: `inherits` lists the principles/patterns this agent is
    bound by, making inheritance explicit and auditable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cfaios.constitution.gates import Gate, GateResult, Phase
from cfaios.constitution.principles import Principle
from cfaios.core.events import Event
from cfaios.core.knowledge_api import KnowledgeAPI


@dataclass
class AgentSpec:
    """Static, locked metadata for an agent (mirrors the constitution document)."""
    number: int
    identity: str
    layer: str
    mandate: str
    gate_code: str
    inherits_principles: tuple[str, ...]
    inherits_patterns: tuple[int, ...]
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    validated_by: tuple[str, ...]
    p0_failure: str                       # the catastrophic failure mode for this agent
    deferred_build: tuple[str, ...] = ()


class BaseAgent(ABC):
    """Abstract base every CFAIOS agent extends."""

    spec: AgentSpec
    gate: Gate

    def __init__(self, api: KnowledgeAPI):
        #: the ONLY doorway to shared state (P4). Agents never touch stores directly.
        self.api = api

    # ---- Adaptive Intelligence Loop (Pattern #10) ----
    @abstractmethod
    def observe(self, context: dict) -> dict:
        """Gather inputs from the agent's domain (reads via self.api, sensors, etc.)."""

    @abstractmethod
    def interpret(self, observation: dict) -> dict:
        """Turn raw observation into meaning within the agent's remit."""

    @abstractmethod
    def decide(self, interpretation: dict) -> dict:
        """Choose an action. For generative agents this obeys P10: retrieve+verify
        BEFORE any generation; generation is always the last step."""

    @abstractmethod
    def act(self, decision: dict) -> list[Event]:
        """Produce outputs strictly as events / staged candidates. Returns the events
        this agent emits — it does NOT write the graph directly (P4)."""

    def measure(self, events: list[Event]) -> dict:
        """Structural (Phase A) self-measurement. Outcome (Phase B) measurement is
        performed by Agent 13, not the agent itself (Observation-Decision Separation)."""
        return {"events_emitted": len(events)}

    def adapt(self, measurement: dict) -> None:
        """Update the agent's internal policy from measurement. Bounded by
        Integrity-First Optimization: only within the constitution-compliant space."""

    # ---- Loop driver (invoked by Agent 16, the orchestrator) ----
    def run_cycle(self, context: dict) -> list[Event]:
        obs = self.observe(context)
        interp = self.interpret(obs)
        decision = self.decide(interp)
        events = self.act(decision)
        for e in events:
            self.api.emit(e)
        self.adapt(self.measure(events))
        return events

    # ---- Gate ----
    def evaluate_gate(self, scores: dict[str, float], phase: Phase = Phase.A) -> GateResult:
        return self.gate.evaluate(scores, phase)

    def bound_principles(self) -> list[Principle]:
        return [Principle[p] if p in Principle.__members__ else _by_code(p)
                for p in self.spec.inherits_principles]


def _by_code(code: str) -> Principle:
    for p in Principle:
        if p.code == code:
            return p
    raise KeyError(code)
