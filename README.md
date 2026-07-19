# CFAIOS — Chess Flow AI Operating System (v1.0)

An 18-agent **constitutional architecture** for verified chess education. This
repository is the **skeleton**: the shared constitution, the Knowledge-API spine, the
base-agent contract, and all 18 agent packages carrying their locked specifications.
The agents' internal logic is scaffolded (raises `NotImplementedError`) and filled in
per the deferred-build registry.

> Most AI architectures ask *how do we make the model smarter?* CFAIOS asks a different
> question: *how do we build an institution whose intelligence remains trustworthy as
> it grows?*

## Proof of life

```bash
pip install -e ".[dev]"
PYTHONPATH=. python scripts/bootstrap_check.py   # imports everything, lists all 18 agents
PYTHONPATH=. pytest -q                            # structural invariants
```

If those run clean, the skeleton is wired correctly.

## Layout

```
cfaios/
  constitution/        # THE SHARED CORE — imported by every agent
    principles.py      #   P1–P16 + Constitutional Execution + External Validation
    doctrines.py       #   the 4 doctrines (highest tier)
    patterns.py        #   the 22 patterns, in six integrity layers
    standards.py       #   CFDS · CFLSS · CFCS · CFRS
    rules.py           #   CSL · Safe Halt · Equipoise · Pricing Ethics · Mission Hierarchy · Reserved Human
    gates.py           #   the Quality Gate base (integrity dims block; quality dims score)
    governance.py      #   the stack: MIT → CRF → CIA → CTA → Constitutional Execution
    escalation.py      #   EscalationRecord — the AI→human switchboard
  core/                # THE SPINE
    knowledge_api.py   #   P4 single-writer contract — the ONLY doorway to shared state
    agent_base.py      #   BaseAgent: the AIL loop, gate ownership, event-only writes
    events.py          #   event sourcing (P6)
    truth.py           #   verdict states (Agent 3) + epistemic states (Agent 12)
    graphs.py          #   the three orthogonal graphs, with read/write discipline
    staging.py         #   the Candidate Knowledge Queue in front of Agent 2
  infra/               # adapters (interfaces + stubs; bind real backends at build time)
    neo4j_store.py · vector_store.py · object_store.py
    llm_anthropic.py · llm_google.py · chess_engine.py
  agents/              # the 18 agent packages (generated from agents_spec.py)
    agent01_extraction/ … agent18_executive/
  agents_spec.py       # single source of truth for all 18 agents' locked metadata
config/                # settings (env-driven; no secrets in code)
scripts/               # generate_agents.py · bootstrap_check.py
tests/                 # structural invariants
```

## The invariants this skeleton enforces by construction

| Invariant | Where |
|---|---|
| **Single-Writer (P4)** — only Agent 2 commits knowledge | `core/knowledge_api.py`, `AGENT_KNOWLEDGE_WRITER` |
| **Agents write only via events** | `core/agent_base.py` `run_cycle()` emits, never writes |
| **Every agent owns one gate** | `AgentSpec.gate_code`, `Gate` base |
| **No function self-certifies** (External Validation) | `AgentSpec.validated_by` on all 18 |
| **Three graphs never collapse** | `core/graphs.py` read-only edges |
| **Nothing overwritten (P6)** | `core/events.py` append-only `Event` |
| **Governance stack contracts** | `constitution/governance.py` |

## Regenerating the agents

The 18 agent packages are generated from `cfaios/agents_spec.py`:

```bash
PYTHONPATH=. python scripts/generate_agents.py
```

Edit the **spec** (not the generated files) to change an agent's locked metadata; the
spec is the machine-readable mirror of the canonical constitution document.

## Building it out — suggested order

The constitution is deliberately **scale-down-able** (Layered Public Trust, Phase-A
before Phase-B, bootstrap patterns). Don't build 18 at once. The recommended first
vertical slice:

1. **Agent 1 → Agent 3 → Agent 2** on ONE real book (the riskiest assumption is getting
   clean, verified structured knowledge out of messy PDFs — prove it first).
2. Bind `infra/` to real Neo4j + a vector store + Stockfish.
3. Surface a single verified lesson via a minimal **Agent 7** with an Evidence-Ledger
   entry proving it wasn't hallucinated. That is the smallest proof the core claim —
   *we teach truth and can prove it* — is real.

Each agent's `README.md` lists its **deferred build items** — the concrete engineering
that turns its scaffold into a working bot.

## Status

Specification complete and locked (18/18 agents). This skeleton imports cleanly and
passes structural tests; agent internals and `infra/` backends are the build phase.
