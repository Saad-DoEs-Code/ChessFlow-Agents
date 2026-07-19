"""
The Governance Stack: MIT -> CRF -> CIA -> CTA -> Constitutional Execution.

Five mechanisms defend the constitution from erosion at ascending scope. Each governs
the next; nothing skips a layer. These are Protocols/base classes — the concrete
scoring and detection logic are deferred build items, but the *contracts* here fix how
each mechanism must behave (notably: none may resolve a conflict by relaxing a
constraint; unresolved conflicts escalate — see escalation.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# ---- Layer 1: Manipulation Incentive Test (a metric) ----
@dataclass
class MITResult:
    metric: str
    legal: bool
    #: which constitutional item the sole-optimization of this metric would violate
    violated: list[str] = field(default_factory=list)
    rationale: str = ""


class ManipulationIncentiveTest(Protocol):
    """Screen a metric by simulating its sole-optimization.

    'If this metric became the company's only optimization target, what behavior
    emerges — and does that behavior violate P11 / P14 / CFCS / CSL?' If so, the
    metric is illegal and may not be tracked or targeted.
    """
    def screen(self, metric_name: str, objective_function: str) -> MITResult: ...


# ---- Layer 2: Constitutional Recommendation Filtering (a recommendation) ----
@dataclass
class Recommendation:
    summary: str
    origin_agent: int
    payload: dict = field(default_factory=dict)


class ConstitutionalRecommendationFilter(Protocol):
    """Filter recommendations BEFORE they are emitted. Unconstitutional proposals
    never become recommendations — only rejected candidates. Returns None on reject."""
    def filter(self, candidate: Recommendation) -> Recommendation | None: ...


# ---- Layer 3: Constitutional Impact Assessment (a decision) ----
@dataclass
class ConstitutionalImpactAssessment:
    recommendation: Recommendation
    educational_impact: str
    relational_impact: str
    financial_impact: str
    trust_impact: str
    principle_checks: dict[str, bool]     # e.g. {"P11": True, "P14": True}
    forecast_confidence: float
    human_approval_required: bool


# ---- Layer 4: Constitutional Trajectory Analysis (the org over time) ----
@dataclass
class TrajectoryReading:
    metric: str
    quarters: list[float]
    drifting: bool
    direction: str  # "up" | "down" | "flat"


class ConstitutionalTrajectoryAnalysis(Protocol):
    """Longitudinal drift detection. Detects the case where every individual decision
    passed review yet the *direction* over quarters is unconstitutional (e.g. declining
    Relationship Equity, widening Educational-vs-Financial LTV gap, rising Brand Debt).
    Significant drift produces a Constitutional Conflict Escalation — never an automatic
    strategy change."""
    def analyze(self, metric: str, series: list[float]) -> TrajectoryReading: ...


# ---- Layer 5: Constitutional Execution (every operation) ----
class ConstitutionalExecutionGuard(Protocol):
    """No operational state may weaken constitutional constraints. Degradation may
    change speed/throughput/availability — never integrity/safety/truth/verification.
    Returns True only if the planned operation preserves every invariant; otherwise the
    caller must Safe-Halt and escalate (see rules.Rule.SAFE_HALT)."""
    def permits(self, operation: str, context: dict) -> bool: ...


GOVERNANCE_STACK = ("MIT", "CRF", "CIA", "CTA", "Constitutional Execution")
