# Agent 16 — Automation Orchestrator

**Layer:** Governance  ·  **Gate:** Orchestration Integrity Index (OII)

## Mandate
The conductor: operationally powerful, constitutionally weak. Mechanical authority only — 'determines when work executes, never what work means.'

## Constitutional inheritance
- **Principles:** P4, P6
- **Patterns:** #10, #21

## Reads
- execution graph
- every agent's status
- staging queue
- escalation triggers

## Writes
- schedules
- Escalation Records (routes, never resolves)
- orchestration events

## Validated by
- human override (never autonomous-supreme)
- Agent 18 (above it)

## P0 (catastrophic) failure mode
> Constitutional Breach — bypassing any constitutional invariant under load.

## Deferred build items (owned by this agent)
- Execution-graph engine
- Atomic-Progress state machine
- Escalation-Record system
- Institutional Clock
- Safe-Halt logic

---
*Scaffold generated from `cfaios/agents_spec.py`. Fill in `agent.py`; keep the SPEC in sync
with the canonical constitution document.*
