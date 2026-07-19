"""
The Four Doctrines — the highest constitutional tier.

A doctrine is a *property of the institution itself* that the principles exist to
serve. Doctrines are what make CFAIOS trustworthy as a whole; principles are the
rules that realize them.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class DoctrineDef:
    code: str
    title: str
    statement: str


class Doctrine(DoctrineDef, Enum):
    CONSTITUTIONAL_SUPREMACY = (
        "D1", "Constitutional Supremacy",
        "No AI authority possesses constitutional exemption authority. Three authority "
        "classes: Constitutional (defines what is permissible — humans only), Executive "
        "(chooses among permissible options — Agent 18), Operational (executes them — "
        "Agent 16). No layer may perform the layer above it.")
    EXTERNAL_VALIDATION = (
        "D2", "External Validation",
        "No critical institutional function may be its own final validator. Knowledge is "
        "validated by evidence; measurement by a human recursion floor; execution by human "
        "override; strategy by analytics plus human governance.")
    STRATEGIC_EPISTEMIC_HUMILITY = (
        "D3", "Strategic Epistemic Humility",
        "Strategy consumes reality; it never edits reality. The Decision Graph may read the "
        "Knowledge Graph but never write it.")
    INSTITUTIONAL_LEGITIMACY = (
        "D4", "Institutional Legitimacy",
        "Authority is legitimate only because every exercise of it is constrained by "
        "publicly defined rules, independently validated evidence, and accountable human "
        "governance. This is why users may trust decisions they cannot personally inspect.")


ALL_DOCTRINES = tuple(Doctrine)
