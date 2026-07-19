"""
Quality Gates (Layered Quality Gate Pattern #2).

Every agent owns exactly one gate that must pass before its output is consumed
downstream. A gate is a weighted composite of *integrity* dimensions and *quality*
dimensions; per Integrity-First Optimization, a failed integrity dimension blocks
regardless of how high the quality dimensions score.

Phase A/B (P9): each dimension is a structural prediction until outcome data exists,
then it is recalibrated by Agent 13. `phase` records which regime a score is in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Phase(str, Enum):
    A = "A"  # structural prediction (cold start)
    B = "B"  # outcome-validated


class DimensionKind(str, Enum):
    INTEGRITY = "integrity"   # failure blocks unconditionally
    QUALITY = "quality"       # contributes to weighted score


@dataclass(frozen=True)
class Dimension:
    name: str
    kind: DimensionKind
    weight: float = 1.0
    #: minimum score in [0,1] required for an integrity dimension to pass
    threshold: float = 0.0


@dataclass
class GateResult:
    passed: bool
    score: float
    phase: Phase
    failed_integrity: list[str] = field(default_factory=list)
    detail: dict[str, float] = field(default_factory=dict)


@dataclass
class Gate:
    """A named quality gate. Subclass or instantiate per agent.

    Concrete scoring is deferred (a build-time item): `evaluate` here enforces the
    *contract* — integrity dimensions gate unconditionally, quality dimensions form a
    weighted average — while the per-dimension scoring functions are supplied later.
    """
    code: str
    title: str
    dimensions: tuple[Dimension, ...]

    def evaluate(self, scores: dict[str, float], phase: Phase = Phase.A) -> GateResult:
        failed: list[str] = []
        weighted_sum = 0.0
        weight_total = 0.0
        for dim in self.dimensions:
            s = scores.get(dim.name, 0.0)
            if dim.kind is DimensionKind.INTEGRITY and s < dim.threshold:
                failed.append(dim.name)
            if dim.kind is DimensionKind.QUALITY:
                weighted_sum += s * dim.weight
                weight_total += dim.weight
        score = (weighted_sum / weight_total) if weight_total else 0.0
        return GateResult(
            passed=(not failed),
            score=score,
            phase=phase,
            failed_integrity=failed,
            detail=dict(scores),
        )
