"""
Agent 3 — Chess Accuracy Director (CSO)  (Truth layer)

The only truth-asserter in the system. Verifies chess claims via engine, tablebase, and tiered evidence; owns the verdict states.

Gate: Evidence Ledger integrity
P0 failure: False-Confirmed — asserting a wrong claim as verified.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

import json

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.core.truth import EvidenceTier, TruthDimension, Verdict, VerdictState
from cfaios.constitution.gates import Gate
from cfaios.infra.chess_engine import ChessEngine
from cfaios.infra.object_store import ObjectStore


SPEC = AgentSpec(
    number=3,
    identity='Chess Accuracy Director (CSO)',
    layer='Truth',
    mandate='The only truth-asserter in the system. Verifies chess claims via engine, tablebase, and tiered evidence; owns the verdict states.',
    gate_code='Evidence Ledger integrity',
    inherits_principles=['P2', 'P3'],
    inherits_patterns=[3],
    reads=['candidate claims', 'chess engine / tablebase / databases'],
    writes=['Verdicts (7 states)', 'Evidence Ledger entries'],
    validated_by=['evidence itself (External Validation)'],
    p0_failure='False-Confirmed — asserting a wrong claim as verified.',
    deferred_build=['Verification Router', 'six-tier evidence hierarchy', 'multi-dimensional truth scoring', 'Evidence Ledger'],
)


def _side_to_move(fen: str) -> str:
    import chess
    return "white" if chess.Board(fen).turn else "black"


class AccuracyAgent(BaseAgent):
    """A claim this agent understands: {"claim_id": str, "fen": str, "claimed_result":
    "win"|"draw"|"loss"}. `claimed_result` is always relative to the side to move in
    `fen` — matching how these claims naturally read ("White to play and win" = the
    side to move wins). Anything missing a fen/claimed_result is non-objective and
    gets INAPPLICABLE (ROADMAP Step 2.2) rather than silently skipped, so the audit
    trail still records that Agent 3 looked at it.

    Verification Router (Pattern #3): legality (free) -> tablebase (exact, if in
    range) -> engine shallow -> engine deep only if shallow is ambiguous. Never
    skips straight to the expensive check."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Evidence Ledger integrity.
    gate = Gate(code='Evidence Ledger integrity', title='Evidence Ledger integrity', dimensions=())

    SHALLOW_DEPTH = 12
    DEEP_DEPTH = 20
    DECISIVE_THRESHOLD = 2.5   # pawns, side-to-move relative: |score| >= this => win/loss
    DRAW_THRESHOLD = 0.5       # pawns, side-to-move relative: |score| <= this => draw

    def __init__(self, api: KnowledgeAPI, engine: ChessEngine, object_store: ObjectStore):
        super().__init__(api)
        self.engine = engine
        self.object_store = object_store
        #: claim_id -> Verdict, for callers to fetch evidence back after a run_cycle.
        self.verdicts: dict[str, Verdict] = {}

    # ---- AIL steps ----

    def observe(self, context: dict) -> dict:
        """context: {"claims": [{"claim_id", "fen"?, "claimed_result"?}, ...]}"""
        return {"claims": context.get("claims", [])}

    def interpret(self, observation: dict) -> dict:
        """Classify each claim: does it even have a checkable objective shape
        (a FEN + a concrete win/draw/loss claim), and if so, is the FEN legal?
        Purely structural — no verdict is reached here."""
        classified = []
        for claim in observation["claims"]:
            fen = claim.get("fen")
            claimed_result = claim.get("claimed_result")
            objective = bool(fen) and claimed_result in ("win", "draw", "loss")
            legal = self.engine.legal(fen) if objective else False
            classified.append({**claim, "objective": objective, "legal": legal})
        return {"claims": classified}

    def decide(self, interpretation: dict) -> dict:
        """Run the Verification Router per claim (P10: verify BEFORE any output
        is produced — act() only ever packages what decide() already determined,
        it never re-decides or generates)."""
        return {"results": [self._verify_one(c) for c in interpretation["claims"]]}

    def act(self, decision: dict) -> list[Event]:
        """Hash each verdict's evidence into the Evidence Ledger (P3) and emit
        one VERDICT_RECORDED event per claim. Never touches the knowledge graph
        (P4) — Agent 3 asserts truth, Agent 2 alone commits it."""
        events: list[Event] = []
        for r in decision["results"]:
            evidence_blob = json.dumps({
                "claim_id": r["claim_id"],
                "fen": r.get("fen"),
                "claimed_result": r.get("claimed_result"),
                "check": r["check"],
                "raw_result": r["raw_result"],
                "verdict_state": r["state"].value,
                "note": r["note"],
            }, sort_keys=True).encode("utf-8")
            evidence_ref = self.object_store.put_evidence(evidence_blob, content_type="application/json")

            verdict = Verdict(
                dimension_results={TruthDimension.OBJECTIVE: r["state"]},
                tier=r["tier"],
                evidence_ref=evidence_ref,
                confidence=1.0 if r["state"] in (VerdictState.CONFIRMED, VerdictState.REFUTED) else 0.0,
                notes=r["note"],
            )
            self.verdicts[r["claim_id"]] = verdict

            events.append(Event(
                type=EventType.VERDICT_RECORDED,
                actor_agent=self.spec.number,
                subject_id=r["claim_id"],
                payload={"verdict_state": r["state"].value, "tier": r["tier"].value,
                         "evidence_ref": evidence_ref},
            ))
        return events

    # ---- Verification Router (Pattern #3) ----

    def _verify_one(self, claim: dict) -> dict:
        claim_id = claim.get("claim_id", "unknown")
        base = {"claim_id": claim_id, "fen": claim.get("fen"),
                "claimed_result": claim.get("claimed_result")}

        if not claim["objective"]:
            return {**base, "state": VerdictState.INAPPLICABLE, "tier": EvidenceTier.COMMUNITY,
                    "check": "non_objective", "raw_result": None,
                    "note": "No FEN + concrete win/draw/loss claim to verify — not an "
                            "objective chess claim (P2: only some truth is a single boolean)."}

        fen, claimed = claim["fen"], claim["claimed_result"]

        if not claim["legal"]:
            return {**base, "state": VerdictState.INCONCLUSIVE, "tier": EvidenceTier.COMMUNITY,
                    "check": "illegal_fen", "raw_result": None,
                    "note": f"FEN does not describe a legal position: {fen!r}"}

        # Cheapest sufficient check first: an exact tablebase hit ends the search.
        tb = self.engine.tablebase(fen)
        if tb is not None:
            state = VerdictState.CONFIRMED if tb == claimed else VerdictState.REFUTED
            return {**base, "state": state, "tier": EvidenceTier.TABLEBASE,
                    "check": "tablebase", "raw_result": tb,
                    "note": f"Syzygy tablebase says {tb} for the side to move; claim was {claimed}."}

        # Engine fallback: shallow first, escalate to deep only if ambiguous.
        last_score, last_depth = None, None
        for depth, tier in ((self.SHALLOW_DEPTH, EvidenceTier.ENGINE_SHALLOW),
                             (self.DEEP_DEPTH, EvidenceTier.ENGINE_DEEP)):
            try:
                white_score = self.engine.evaluate(fen, depth=depth)
            except RuntimeError as exc:
                return {**base, "state": VerdictState.INCONCLUSIVE, "tier": EvidenceTier.COMMUNITY,
                        "check": "engine_unavailable", "raw_result": str(exc),
                        "note": f"Engine unavailable: {exc}"}

            side_relative = white_score if _side_to_move(fen) == "white" else -white_score
            last_score, last_depth = side_relative, depth
            engine_result = self._classify_score(side_relative)
            if engine_result is not None:
                state = VerdictState.CONFIRMED if engine_result == claimed else VerdictState.REFUTED
                return {**base, "state": state, "tier": tier, "check": f"engine_depth_{depth}",
                        "raw_result": {"score_pawns": side_relative, "depth": depth},
                        "note": f"Engine (depth {depth}) evaluates {side_relative:+.2f} for the "
                                f"side to move -> {engine_result}; claim was {claimed}."}

        return {**base, "state": VerdictState.INCONCLUSIVE, "tier": EvidenceTier.ENGINE_DEEP,
                "check": "engine_ambiguous",
                "raw_result": {"score_pawns": last_score, "depth": last_depth},
                "note": "Engine evaluation too close to call even at deep search."}

    def _classify_score(self, score_pawns: float) -> str | None:
        """Side-to-move-relative pawn score -> "win"/"draw"/"loss", or None if
        it falls in the ambiguous middle ground (caller should escalate depth)."""
        if score_pawns >= self.DECISIVE_THRESHOLD:
            return "win"
        if score_pawns <= -self.DECISIVE_THRESHOLD:
            return "loss"
        if abs(score_pawns) <= self.DRAW_THRESHOLD:
            return "draw"
        return None
