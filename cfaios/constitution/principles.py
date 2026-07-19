"""
The Constitutional Principles (P1–P16 + two governing principles).

Principles are IMMUTABLE architectural law. Only Human Governance may amend them,
through the Constitutional Amendment Lifecycle (see governance.py). This module is
the single source of truth for the constitution's principle tier; agents import
`Principle` and declare which principles they inherit so that inheritance is
explicit and auditable rather than implicit.

Design note: a principle is a *rule the system follows*. A doctrine (see
doctrines.py) is a *property of the institution* the principles serve, and sits
above them.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PrincipleDef:
    code: str
    title: str
    statement: str
    #: The constitutional question this principle answers.
    question: str


class Principle(PrincipleDef, Enum):
    P1 = ("P1", "Two-Graph Separation",
          "Knowledge is a cyclic graph; Learning is a DAG. They are never collapsed.",
          "How is knowledge structured vs. how is it taught?")
    P2 = ("P2", "Multi-Dimensional Truth",
          "Chess truth is asserted across multiple dimensions, not as a single boolean.",
          "What does 'true' mean here?")
    P3 = ("P3", "No Knowledge Without Evidence",
          "Nothing enters the knowledge graph without grounding evidence.",
          "Why should this be believed?")
    P4 = ("P4", "Single-Writer Invariant",
          "Agent 2 is the sole writer to the canonical graph; all others emit events.",
          "Who may change what is true?")
    P5 = ("P5", "Canonical Object",
          "One object, many references, system-wide. Never duplicated, only referenced.",
          "How is redundancy prevented?")
    P6 = ("P6", "Universal Versioning",
          "Everything is event-sourced; history is appended, never destroyed.",
          "How does the system change over time?")
    P7 = ("P7", "Adaptive Trust-Based Review",
          "Review depth scales with an agent's demonstrated trustworthiness.",
          "How much should this be checked?")
    P8 = ("P8", "Evidence-Grounded Pedagogy",
          "Teaching rests on cited evidence; unsupported folk theory is demoted.",
          "Why teach it this way?")
    P9 = ("P9", "Progressive Validation",
          "Every metric is Phase-A structural prediction maturing to Phase-B outcome validation.",
          "Is this metric actually true yet?")
    P10 = ("P10", "Retrieval Before Reasoning",
           "No agent originates domain knowledge. Retrieve, verify, personalize, then generate. "
           "Generation is always the last stage.",
           "Where does truth originate?")
    P11 = ("P11", "Educational Integrity Before Engagement",
           "Engagement may amplify truth; never replace it. Retrieve -> Verify -> Teach -> Engage.",
           "Which wins when engagement conflicts with truth?")
    P12 = ("P12", "Semantic Integrity Through Transformation",
           "Derivative content may change presentation, never meaning.",
           "Can truth survive transformation?")
    P13 = ("P13", "Integrity is Modality Independent",
           "A claim is a claim in any medium. Every modality inherits the full integrity stack.",
           "Does truth depend on modality?")
    P14 = ("P14", "Respect Human Agency",
           "CFAIOS may persuade but never manipulate — binding communication directly and "
           "strategy/analytics/growth indirectly.",
           "May influence override autonomy?")
    P15 = ("P15", "Conversation Permitted, Authority Earned",
           "People may speak freely; claims receive epistemic status, never automatic truth. "
           "Authority is earned only through evidence.",
           "How is user-generated content handled?")
    P16 = ("P16", "Measurement Integrity Before Optimization",
           "Measurements must faithfully represent reality before they optimize decisions.",
           "Is the measurement itself honest?")
    CONSTITUTIONAL_EXECUTION = (
        "CE", "Constitutional Execution",
        "No operational state may weaken constitutional constraints. Degradation may change "
        "speed, throughput, availability — never integrity, safety, truth, verification.",
        "Can operational pressure bypass the constitution?")
    EXTERNAL_VALIDATION = (
        "EV", "External Validation",
        "No critical institutional function may be its own final validator.",
        "Who validates the validator?")


#: The canonical ordered list, for documentation / bootstrap checks.
ALL_PRINCIPLES: tuple[Principle, ...] = tuple(Principle)


def get(code: str) -> Principle:
    for p in Principle:
        if p.code == code:
            return p
    raise KeyError(f"Unknown principle: {code!r}")
