"""
Standards — versioned measurement, conduct, and rights rules.

Unlike principles (immutable), standards EVOLVE with evidence (technical) or remain
near-immutable for ethical reasons (conduct/rights). Governance differs per category:
technical standards are amended by the Ontology / Standards Review Board; conduct and
rights standards by human ethical/legal review.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class StandardDef:
    code: str
    title: str
    category: str  # "technical" | "conduct" | "rights"
    governs: str


class Standard(StandardDef, Enum):
    CFDS = ("CFDS", "Chess Flow Difficulty Standard", "technical",
            "Deterministic difficulty: conceptual depth, plies, tactical/strategic load, rating band.")
    CFLSS = ("CFLSS", "Chess Flow Learning Science Standard", "technical",
             "Evidence-tiered pedagogy (tiers A/B/C/D); every recommendation cites its evidence.")
    CFCS = ("CFCS", "Chess Flow Human Interaction Standard", "conduct",
            "Every direct interaction with an identifiable person: truthful, calm, respectful, "
            "encouraging, intellectually honest, non-condescending; never shame, never manipulate; "
            "respect autonomy and age; protect wellbeing; escalate when appropriate.")
    CFRS = ("CFRS", "Chess Flow Rights Standard", "rights",
            "Copyright, licensing, likeness, marks; originality preferred over licensing.")


ALL_STANDARDS = tuple(Standard)
