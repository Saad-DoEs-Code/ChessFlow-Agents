"""
Event sourcing (P6: Universal Versioning).

Nothing in CFAIOS is overwritten. Every change is an appended, immutable event.
Agents EMIT events; only Agent 2 (Single-Writer Invariant, P4) commits knowledge
events to the canonical graph. The current state of any object is the projection of
its event stream.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


class EventType(str, Enum):
    CANDIDATE_STAGED = "candidate_staged"        # Agent 1/12/15 -> staging
    KNOWLEDGE_COMMITTED = "knowledge_committed"  # Agent 2 only
    VERDICT_RECORDED = "verdict_recorded"        # Agent 3
    NODE_SUPERSEDED = "node_superseded"          # Agent 3, fired by Agent 15
    NODE_MARKED_STALE = "node_marked_stale"      # Agent 3, fired by Agent 15
    COACHING_EVENT = "coaching_event"            # Agent 7
    COMPETENCY_UPDATED = "competency_updated"    # Agent 6 (projection)
    ESCALATION_RAISED = "escalation_raised"
    ESCALATION_ADVANCED = "escalation_advanced"
    AMENDMENT_PROPOSED = "amendment_proposed"    # Agent 18 -> humans


@dataclass(frozen=True)
class Event:
    """An immutable, appended fact. `actor_agent` records provenance for audit."""
    type: EventType
    actor_agent: int
    subject_id: str
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    #: the CKG snapshot version this event was produced against
    graph_version: str | None = None
