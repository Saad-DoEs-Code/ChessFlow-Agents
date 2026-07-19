"""
Agent 16 — Automation Orchestrator  (Governance layer)

The conductor: operationally powerful, constitutionally weak. Mechanical authority only — 'determines when work executes, never what work means.'

Gate: Orchestration Integrity Index (OII)
P0 failure: Constitutional Breach — bypassing any constitutional invariant under load.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=16,
    identity='Automation Orchestrator',
    layer='Governance',
    mandate="The conductor: operationally powerful, constitutionally weak. Mechanical authority only — 'determines when work executes, never what work means.'",
    gate_code='Orchestration Integrity Index (OII)',
    inherits_principles=['P4', 'P6'],
    inherits_patterns=[10, 21],
    reads=['execution graph', "every agent's status", 'staging queue', 'escalation triggers'],
    writes=['schedules', 'Escalation Records (routes, never resolves)', 'orchestration events'],
    validated_by=['human override (never autonomous-supreme)', 'Agent 18 (above it)'],
    p0_failure='Constitutional Breach — bypassing any constitutional invariant under load.',
    deferred_build=['Execution-graph engine', 'Atomic-Progress state machine', 'Escalation-Record system', 'Institutional Clock', 'Safe-Halt logic'],
)


@dataclass
class PipelineStep:
    """One scheduled unit of work. The two callables are mechanical glue owned by
    whoever declares the pipeline (a script, eventually the Execution Graph):
    `build_context` assembles the next agent's run_cycle context from shared
    state; `after` folds that agent's outcome back into shared state. Agent 16
    invokes them but never inspects what flows through them — mechanical
    authority only."""
    name: str
    agent_key: str
    build_context: Callable[[dict], dict]
    after: Callable[[dict, BaseAgent, list[Event]], None] | None = None


class OrchestratorAgent(BaseAgent):
    """MINIMAL build (ROADMAP Step 4.2): the AIL loop driver. Runs a declared
    pipeline of other agents' run_cycle()s in order. Never interprets domain
    data ('determines when work executes, never what work means'). On a step
    failure it halts the remaining pipeline (Safe Halt: stop, don't improvise)
    and emits ESCALATION_RAISED — it routes failures, never resolves them.

    Deferred (see README): the real Execution-graph engine, Atomic-Progress
    state machine, Institutional Clock. Scheduling cadence lives in the caller
    (scripts/run_orchestrated_slice.py --every/--times) for now."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Orchestration Integrity Index (OII).
    gate = Gate(code='Orchestration Integrity Index (OII)', title='Orchestration Integrity Index (OII)', dimensions=())

    def __init__(self, api: KnowledgeAPI, registry: dict[str, BaseAgent]):
        super().__init__(api)
        #: agent_key -> constructed agent. Agent 16 runs them; it never builds them.
        self.registry = registry
        #: per-step outcomes of the last run_cycle, for callers to inspect
        self.last_run: list[dict] = []

    def observe(self, context: dict) -> dict:
        """context: {"pipeline": [PipelineStep, ...], "state": dict}"""
        return {"pipeline": context["pipeline"], "state": context.get("state", {})}

    def interpret(self, observation: dict) -> dict:
        """Mechanical validation only: every step's agent must exist in the
        registry. No judgement about whether the pipeline makes domain sense —
        that is precisely not Agent 16's call."""
        missing = [s.agent_key for s in observation["pipeline"] if s.agent_key not in self.registry]
        if missing:
            raise KeyError(f"Agent 16: pipeline references unregistered agents: {missing}")
        return observation

    def decide(self, interpretation: dict) -> dict:
        return {"plan": list(interpretation["pipeline"]), "state": interpretation["state"]}

    def act(self, decision: dict) -> list[Event]:
        """Execute the plan in order. A step failure halts everything after it
        and raises an escalation event — the failure is routed to governance,
        not swallowed, retried, or worked around (Constitutional Execution:
        degradation may change throughput, never integrity)."""
        state = decision["state"]
        escalations: list[Event] = []
        self.last_run = []
        halted = False

        for step in decision["plan"]:
            if halted:
                self.last_run.append({"step": step.name, "status": "skipped (pipeline halted)"})
                continue
            agent = self.registry[step.agent_key]
            try:
                events = agent.run_cycle(step.build_context(state))
                if step.after:
                    step.after(state, agent, events)
                self.last_run.append(
                    {"step": step.name, "status": "ok", "events_emitted": len(events)})
            except Exception as exc:
                halted = True
                self.last_run.append({"step": step.name, "status": f"FAILED: {exc}"})
                escalations.append(Event(
                    type=EventType.ESCALATION_RAISED,
                    actor_agent=self.spec.number,
                    subject_id=step.name,
                    payload={"pipeline_step": step.name, "agent_key": step.agent_key,
                             "error": str(exc), "remaining_steps_halted": True},
                ))
        return escalations
