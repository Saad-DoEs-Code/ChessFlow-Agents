"""Proof-of-life: import the whole system and print the constitution + all 18 agents.
Run:  PYTHONPATH=. python scripts/bootstrap_check.py
If this runs clean, the skeleton is wired correctly."""
from __future__ import annotations
import importlib

from cfaios.constitution import (ALL_PRINCIPLES, ALL_DOCTRINES, ALL_STANDARDS,
                                 ALL_RULES, PATTERNS)
from cfaios.agents_spec import AGENTS


def main() -> None:
    print("=" * 70)
    print("CFAIOS v1.0 — bootstrap check")
    print("=" * 70)
    print(f"Doctrines : {len(ALL_DOCTRINES)}")
    print(f"Principles: {len(ALL_PRINCIPLES)}")
    print(f"Standards : {len(ALL_STANDARDS)}")
    print(f"Rules     : {len(ALL_RULES)}")
    print(f"Patterns  : {len(PATTERNS)}")
    print("-" * 70)
    print("Agents:")
    for a in AGENTS:
        mod = importlib.import_module(
            f"cfaios.agents.agent{a['number']:02d}_{a['key']}")
        cls = getattr(mod, [n for n in dir(mod) if n.endswith('Agent')][0])
        assert cls.spec.number == a["number"]
        print(f"  {a['number']:>2}. {a['identity']:<48} [{a['layer']}]  gate={a['gate']}")
    print("-" * 70)
    print(f"All {len(AGENTS)} agents import and carry their locked spec. OK.")


if __name__ == "__main__":
    main()
