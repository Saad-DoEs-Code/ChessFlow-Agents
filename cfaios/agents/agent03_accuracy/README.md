# Agent 3 — Chess Accuracy Director (CSO)

**Layer:** Truth  ·  **Gate:** Evidence Ledger integrity

## Mandate
The only truth-asserter in the system. Verifies chess claims via engine, tablebase, and tiered evidence; owns the verdict states.

## Constitutional inheritance
- **Principles:** P2, P3
- **Patterns:** #3

## Reads
- candidate claims
- chess engine / tablebase / databases

## Writes
- Verdicts (7 states)
- Evidence Ledger entries

## Validated by
- evidence itself (External Validation)

## P0 (catastrophic) failure mode
> False-Confirmed — asserting a wrong claim as verified.

## Deferred build items (owned by this agent)
- Verification Router
- six-tier evidence hierarchy
- multi-dimensional truth scoring
- Evidence Ledger

---
*Scaffold generated from `cfaios/agents_spec.py`. Fill in `agent.py`; keep the SPEC in sync
with the canonical constitution document.*
