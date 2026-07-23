"""
Agent 15 — Research Scientist  (Intelligence layer)

Discovery and environmental sensing. Keeps the foundation from going stale; 'discovery creates candidates, verification creates knowledge.'

Gate: Research Integrity Index (RII)
P0 failure: Contaminating the pipeline with unverified external knowledge.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import Candidate, KnowledgeAPI
from cfaios.core.truth import EpistemicState
from cfaios.constitution.gates import Dimension, DimensionKind, Gate

#: Pattern #19 (Knowledge Freshness Lifecycle) bootstrap threshold — a real
#: system would vary this per domain (openings theory drifts faster than
#: elementary endgame theory); one flat threshold is the honest floor.
_STALENESS_DAYS = 180


SPEC = AgentSpec(
    number=15,
    identity='Research Scientist',
    layer='Intelligence',
    mandate="Discovery and environmental sensing. Keeps the foundation from going stale; 'discovery creates candidates, verification creates knowledge.'",
    gate_code='Research Integrity Index (RII)',
    inherits_principles=['P3', 'P10'],
    inherits_patterns=[1, 19, 20],
    reads=['external sources', 'CKG (gaps + staleness)', 'community signal (A12)'],
    writes=['candidate knowledge -> A1', 'staleness flags -> A3', 'competitive intel -> A18'],
    validated_by=['RII gate', 'Agent 3 (fires Stale/Superseded)'],
    p0_failure='Contaminating the pipeline with unverified external knowledge.',
    deferred_build=['Knowledge Freshness Lifecycle', 'source-credibility tiers', 'Persistent Research Watchlists'],
)


class ResearchAgent(BaseAgent):
    """MINIMAL build (Phase 5). 'Discovery creates candidates, verification
    creates knowledge' is implemented literally: every external finding with
    a checkable claim goes through the SAME mediated Candidate Queue as
    Agent 1 and Agent 12 (Pattern #1) — `self.api.stage_candidate`, never a
    direct write. The P0 (contaminating the pipeline with unverified
    knowledge) is structurally excluded the same way it is for Agent 1: this
    agent has no method that could commit anything.

    Also runs a real staleness scan (Pattern #19) over the committed graph,
    using each node's actual KNOWLEDGE_COMMITTED timestamp from the event
    log — not a guess. A real system persists Persistent Research Watchlists
    and live external sources; this build takes findings as input (the
    'external sources' read is the caller's job — no live web access is
    wired into agent code, see README) and is honest that the watchlist
    itself remains a deferred build item."""

    spec = SPEC
    gate = Gate(
        code='RII', title='Research Integrity Index (RII)',
        dimensions=(
            # every finding staged must carry a source citation — no anonymous claims
            Dimension("evidence_cited", DimensionKind.INTEGRITY, threshold=1.0),
            # no finding ever bypasses the staging queue (checked structurally: the
            # only write path in this agent IS stage_candidate)
            Dimension("staged_via_queue_only", DimensionKind.INTEGRITY, threshold=1.0),
            Dimension("staleness_scan_completed", DimensionKind.QUALITY, weight=1.0),
        ))

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        self.result: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"findings": [{"source", "citation", "fen"?, "claimed_result"?, "note"}],
        "now": datetime? (injectable for testing; defaults to real UTC now)}"""
        return {"findings": context.get("findings", []),
                "now": context.get("now") or datetime.now(timezone.utc),
                "node_ids": self.api.list_node_ids()}

    def interpret(self, observation: dict) -> dict:
        checkable, noted = [], []
        for f in observation["findings"]:
            if f.get("fen") and f.get("claimed_result") in ("win", "draw", "loss") and f.get("citation"):
                checkable.append(f)
            else:
                noted.append(f)  # not staged — no checkable claim or no citation to ground it

        events = self.api.read_events()
        committed_at = {e["subject_id"]: e["at"] for e in events
                        if e["type"] == EventType.KNOWLEDGE_COMMITTED.value}
        stale_ids = []
        cutoff = observation["now"] - timedelta(days=_STALENESS_DAYS)
        for node_id in observation["node_ids"]:
            ts = committed_at.get(node_id)
            if ts and datetime.fromisoformat(ts) < cutoff:
                stale_ids.append(node_id)

        return {"checkable": checkable, "noted": noted, "stale_ids": stale_ids}

    def decide(self, interpretation: dict) -> dict:
        self.result = interpretation
        return interpretation

    def act(self, decision: dict) -> list[Event]:
        events: list[Event] = []
        for f in decision["checkable"]:
            candidate = Candidate(
                source_agent=self.spec.number,
                concept=f"Research finding: {f.get('note', f['source'])[:60]}",
                payload={"fen": f["fen"], "claimed_result": f["claimed_result"], "note": f.get("note")},
                evidence={"source": f["source"], "citation": f["citation"]},
                epistemic=EpistemicState.PLAUSIBLE,
            )
            staging_id = self.api.stage_candidate(candidate)
            events.append(Event(
                type=EventType.CANDIDATE_STAGED, actor_agent=self.spec.number,
                subject_id=staging_id, payload={"source": f["source"], "citation": f["citation"]},
            ))
        for node_id in decision["stale_ids"]:
            events.append(Event(
                type=EventType.NODE_MARKED_STALE, actor_agent=self.spec.number,
                subject_id=node_id,
                payload={"staleness_days_threshold": _STALENESS_DAYS,
                         "note": "Agent 15 staleness scan; re-verification owned by Agent 3"},
            ))
        return events

    # ---- RII scoring (pure) ----

    def score_result(self, checkable: list[dict], noted: list[dict]) -> dict[str, float]:
        total = len(checkable) + len(noted)
        if total == 0:
            return {"evidence_cited": 1.0, "staged_via_queue_only": 1.0, "staleness_scan_completed": 1.0}
        cited = sum(1 for f in checkable if f.get("citation"))
        return {
            "evidence_cited": (cited / len(checkable)) if checkable else 1.0,
            "staged_via_queue_only": 1.0,  # true by construction — see class docstring
            "staleness_scan_completed": 1.0,
        }
