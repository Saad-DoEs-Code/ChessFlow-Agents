"""
Truth states: verification verdicts (Agent 3) and epistemic states (Agent 12).
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class VerdictState(str, Enum):
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    CONTEXT_DEPENDENT = "context_dependent"
    INAPPLICABLE = "inapplicable"          # engine pointed at a non-objective question
    INCONCLUSIVE = "inconclusive"
    STALE = "stale"                        # verification outdated (fired by Agent 15)
    SUPERSEDED = "superseded"              # overturned by newer knowledge (Agent 15)


class TruthDimension(str, Enum):
    OBJECTIVE = "objective"
    PRACTICAL = "practical"
    PEDAGOGICAL = "pedagogical"
    PSYCHOLOGICAL = "psychological"
    HISTORICAL = "historical"


class EvidenceTier(int, Enum):
    TABLEBASE = 6
    ENGINE_DEEP = 5
    ENGINE_SHALLOW = 4
    DATABASE = 3
    AUTHORITY = 2
    COMMUNITY = 1


class EpistemicState(str, Enum):
    VERIFIED = "verified"
    PLAUSIBLE = "plausible"
    OPEN_DISCUSSION = "open_discussion"
    INCORRECT = "incorrect"
    RETRACTED = "retracted"
    EVIDENCE_REQUESTED = "evidence_requested"


@dataclass(frozen=True)
class Verdict:
    dimension_results: dict[TruthDimension, VerdictState]
    tier: EvidenceTier
    evidence_ref: str        # hashed pointer into the Evidence Ledger (P3)
    confidence: float = 0.0
    notes: str = ""


def verdict_to_dict(v: Verdict) -> dict:
    """JSON-safe serialization. Verdicts ride inside events (P6: the event log is
    the authoritative history, so everything an event references must survive a
    round trip through it)."""
    return {
        "dimension_results": {dim.value: state.value for dim, state in v.dimension_results.items()},
        "tier": v.tier.value,
        "evidence_ref": v.evidence_ref,
        "confidence": v.confidence,
        "notes": v.notes,
    }


def verdict_from_dict(d: dict) -> Verdict:
    return Verdict(
        dimension_results={TruthDimension(k): VerdictState(s)
                           for k, s in d["dimension_results"].items()},
        tier=EvidenceTier(d["tier"]),
        evidence_ref=d["evidence_ref"],
        confidence=d["confidence"],
        notes=d["notes"],
    )
