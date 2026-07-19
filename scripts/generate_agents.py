"""
Generate the 18 agent packages from cfaios/agents_spec.py.

Each agent gets a package `cfaios/agents/agentNN_<key>/` containing:
  * agent.py    — a BaseAgent subclass with the locked AgentSpec baked in and the AIL
                  loop stubbed (NotImplementedError) so it is unmistakably a scaffold.
  * README.md   — the agent's locked specification, human-readable.
  * __init__.py — exports the agent class.

Re-runnable: it overwrites the generated files but never invents spec — the spec lives
in agents_spec.py, the single source of truth.
"""
from __future__ import annotations

import pathlib

from cfaios.agents_spec import AGENTS

ROOT = pathlib.Path(__file__).resolve().parents[1] / "cfaios" / "agents"


AGENT_TEMPLATE = '''"""
Agent {number} — {identity}  ({layer} layer)

{mandate}

Gate: {gate}
P0 failure: {p0}

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number={number},
    identity={identity!r},
    layer={layer!r},
    mandate={mandate!r},
    gate_code={gate!r},
    inherits_principles={principles!r},
    inherits_patterns={patterns!r},
    reads={reads!r},
    writes={writes!r},
    validated_by={validated_by!r},
    p0_failure={p0!r},
    deferred_build={deferred!r},
)


class {cls}(BaseAgent):
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for {gate}.
    gate = Gate(code={gate!r}, title={gate!r}, dimensions=())

    def observe(self, context: dict) -> dict:
        raise NotImplementedError("Agent {number} observe() — build me")

    def interpret(self, observation: dict) -> dict:
        raise NotImplementedError("Agent {number} interpret() — build me")

    def decide(self, interpretation: dict) -> dict:
        raise NotImplementedError("Agent {number} decide() — build me")

    def act(self, decision: dict) -> list[Event]:
        raise NotImplementedError("Agent {number} act() — build me")
'''

README_TEMPLATE = """# Agent {number} — {identity}

**Layer:** {layer}  ·  **Gate:** {gate}

## Mandate
{mandate}

## Constitutional inheritance
- **Principles:** {principles_str}
- **Patterns:** {patterns_str}

## Reads
{reads_md}

## Writes
{writes_md}

## Validated by
{validated_md}

## P0 (catastrophic) failure mode
> {p0}

## Deferred build items (owned by this agent)
{deferred_md}

---
*Scaffold generated from `cfaios/agents_spec.py`. Fill in `agent.py`; keep the SPEC in sync
with the canonical constitution document.*
"""


def _md_list(items) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "- _(none)_"


def class_name(key: str) -> str:
    return "".join(part.capitalize() for part in key.split("_")) + "Agent"


def generate() -> list[str]:
    written = []
    for a in AGENTS:
        pkg = ROOT / f"agent{a['number']:02d}_{a['key']}"
        pkg.mkdir(parents=True, exist_ok=True)
        cls = class_name(a["key"])

        (pkg / "agent.py").write_text(AGENT_TEMPLATE.format(cls=cls, **a), encoding="utf-8")
        (pkg / "__init__.py").write_text(
            f"from .agent import {cls}, SPEC\n\n__all__ = [{cls!r}, 'SPEC']\n", encoding="utf-8")
        (pkg / "README.md").write_text(README_TEMPLATE.format(
            principles_str=", ".join(a["principles"]) or "—",
            patterns_str=", ".join(f"#{n}" for n in a["patterns"]) or "—",
            reads_md=_md_list(a["reads"]),
            writes_md=_md_list(a["writes"]),
            validated_md=_md_list(a["validated_by"]),
            deferred_md=_md_list(a["deferred"]),
            **a), encoding="utf-8")
        written.append(str(pkg))
    return written


if __name__ == "__main__":
    for path in generate():
        print("wrote", path)
