"""
Escalation — the switchboard from AI to accountable human governance.

Every mechanism in CFAIOS that cannot resolve a conflict WITHOUT relaxing a
constitutional constraint raises an EscalationRecord instead. Agent 16 owns the
record lifecycle (routes, never resolves); humans resolve. This is a first-class
object (P6: versioned, auditable), not a fire-and-forget notification.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


class EscalationState(str, Enum):
    RAISED = "raised"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class EscalationKind(str, Enum):
    CHESS_CONFLICT = "chess_conflict"            # Agent 3: adjudication needs a human
    WELLBEING = "wellbeing"                      # CFCS / CSL: a person may be at risk
    CHILD_SAFETY = "child_safety"                # CSL: overrides everything
    MISSION_MONEY = "mission_money"              # Agent 14: sustainability vs mission
    TRAJECTORY_DRIFT = "trajectory_drift"        # Agent 13 CTA
    CONSTITUTIONAL_CONFLICT = "constitutional"   # values cannot all be satisfied
    AMENDMENT_PROPOSAL = "amendment_proposal"    # Agent 18 proposes; humans enact
    AUDIT_FLOOR = "audit_floor"                  # recursion terminates at humans


@dataclass
class EscalationRecord:
    kind: EscalationKind
    source_agent: int
    evidence: dict
    constitutional_basis: str
    urgency: str = "normal"          # "normal" | "high" | "immediate"
    deadline: datetime | None = None
    required_reviewer: str = "human_governance"
    state: EscalationState = EscalationState.RAISED
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    raised_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def advance(self, to: EscalationState) -> "EscalationRecord":
        # Lifecycle is monotonic and append-only (P6). Agent 16 owns transitions.
        return EscalationRecord(**{**self.__dict__, "state": to})
