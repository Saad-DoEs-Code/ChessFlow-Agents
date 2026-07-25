"""Unit tests for Agent 3's Verification Router, added 2026-07-23 alongside a
real fix: a shallow-depth REFUTATION now escalates to deep search before being
finalized (composed studies can be invisible to shallow search — see
PROGRESS.md's "Finding (2026-07-23)"). Uses a fake, deterministic ChessEngine
so the router's branches are tested precisely and fast, without depending on a
real Stockfish binary being installed."""
from __future__ import annotations

import json
import types

from cfaios.agents.agent03_accuracy.agent import AccuracyAgent
from cfaios.core.truth import EvidenceTier, TruthDimension, VerdictState
from cfaios.infra.chess_engine import ChessEngine
from cfaios.infra.object_store import LocalObjectStore

_LEGAL_FEN = "8/8/8/8/4k3/8/4K3/6Q1"  # white to move by construction (see agent01 convention)
_ILLEGAL_FEN = "8/8/8/8/8/8/8/8"


class _FakeChessEngine(ChessEngine):
    def __init__(self, *, legal=True, tablebase=None, eval_sequence=None, raises=None):
        self._legal = legal
        self._tablebase = tablebase
        self._eval_sequence = list(eval_sequence or [])
        self._raises = raises
        self.evaluate_depths: list[int] = []

    def legal(self, fen: str) -> bool:
        return self._legal

    def tablebase(self, fen: str) -> str | None:
        return self._tablebase

    def evaluate(self, fen: str, *, depth: int = 20) -> float:
        self.evaluate_depths.append(depth)
        if self._raises:
            raise self._raises
        return self._eval_sequence.pop(0)


def _null_api():
    """Agent 3 never reads/writes the knowledge graph — only run_cycle()'s
    generic event-emission loop needs an `emit`, so a stub suffices."""
    return types.SimpleNamespace(emit=lambda event: None)


def _agent(engine: _FakeChessEngine, tmp_path) -> AccuracyAgent:
    return AccuracyAgent(api=_null_api(), engine=engine,
                         object_store=LocalObjectStore(tmp_path / "evidence"))


def _claim(claim_id="c1", fen=_LEGAL_FEN, claimed_result="win") -> dict:
    return {"claim_id": claim_id, "fen": fen, "claimed_result": claimed_result}


# ---- non-objective / illegal (no engine call) ----

def test_non_objective_claim_never_touches_engine(tmp_path):
    engine = _FakeChessEngine()
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [{"claim_id": "c1", "note": "prose only"}]})
    assert agent.verdicts["c1"].dimension_results[TruthDimension.OBJECTIVE] is VerdictState.INAPPLICABLE
    assert engine.evaluate_depths == []


def test_illegal_fen_never_touches_engine(tmp_path):
    engine = _FakeChessEngine(legal=False)
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(fen=_ILLEGAL_FEN)]})
    assert agent.verdicts["c1"].dimension_results[TruthDimension.OBJECTIVE] is VerdictState.INCONCLUSIVE
    assert engine.evaluate_depths == []


# ---- tablebase short-circuits the engine entirely ----

def test_tablebase_hit_confirms_without_calling_engine(tmp_path):
    engine = _FakeChessEngine(tablebase="win")
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.CONFIRMED
    assert v.tier is EvidenceTier.TABLEBASE
    assert engine.evaluate_depths == []


def test_tablebase_mismatch_refutes(tmp_path):
    engine = _FakeChessEngine(tablebase="draw")
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    assert agent.verdicts["c1"].dimension_results[TruthDimension.OBJECTIVE] is VerdictState.REFUTED


# ---- shallow decisive + matching: no escalation needed ----

def test_shallow_confirmed_does_not_escalate(tmp_path):
    engine = _FakeChessEngine(eval_sequence=[5.0])  # decisive win, matches claim
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.CONFIRMED
    assert v.tier is EvidenceTier.ENGINE_SHALLOW
    assert engine.evaluate_depths == [12]  # only ONE call — no wasted deep search


# ---- the actual fix: shallow refutation escalates before finalizing ----

def test_shallow_refutation_escalates_and_gets_rescued_by_deep_search(tmp_path):
    """The real-world case this fix targets: a composed study's point is
    invisible at depth 12 but resolves correctly at depth 20."""
    engine = _FakeChessEngine(eval_sequence=[-3.0, 5.0])  # shallow: loss: deep: win (rescued)
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.CONFIRMED
    assert v.tier is EvidenceTier.ENGINE_DEEP
    assert engine.evaluate_depths == [12, 20]  # both calls made — deep search WAS consulted


def test_shallow_refutation_confirmed_by_deep_search_finalizes_refuted(tmp_path):
    """If deep search agrees with shallow that the claim is false, REFUTED is
    finalized on the STRONGER (deep) evidence, not the shallow read."""
    engine = _FakeChessEngine(eval_sequence=[-3.0, -4.0])  # both say loss; claim was win
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.REFUTED
    assert v.tier is EvidenceTier.ENGINE_DEEP  # not ENGINE_SHALLOW — used the deeper evidence
    assert engine.evaluate_depths == [12, 20]


# ---- ambiguous escalation path (pre-existing behavior, unchanged) ----

def test_ambiguous_shallow_escalates_to_deep(tmp_path):
    engine = _FakeChessEngine(eval_sequence=[1.0, 5.0])  # 1.0 is ambiguous; 5.0 is decisive win
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.CONFIRMED
    assert v.tier is EvidenceTier.ENGINE_DEEP
    assert engine.evaluate_depths == [12, 20]


def test_ambiguous_at_both_depths_is_inconclusive(tmp_path):
    engine = _FakeChessEngine(eval_sequence=[1.0, 1.2])  # ambiguous at both
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.INCONCLUSIVE
    assert v.tier is EvidenceTier.ENGINE_DEEP
    assert engine.evaluate_depths == [12, 20]


def test_engine_unavailable_is_inconclusive_not_a_crash(tmp_path):
    engine = _FakeChessEngine(raises=RuntimeError("Stockfish binary not found"))
    agent = _agent(engine, tmp_path)
    agent.run_cycle({"claims": [_claim()]})
    v = agent.verdicts["c1"]
    assert v.dimension_results[TruthDimension.OBJECTIVE] is VerdictState.INCONCLUSIVE
    assert v.tier is EvidenceTier.COMMUNITY


# ---- evidence really round-trips, for every state ----

def test_every_verdict_evidence_is_fetchable(tmp_path):
    engine = _FakeChessEngine(eval_sequence=[5.0])
    store = LocalObjectStore(tmp_path / "evidence")
    agent = AccuracyAgent(api=_null_api(), engine=engine, object_store=store)
    agent.run_cycle({"claims": [_claim(claimed_result="win")]})
    ref = agent.verdicts["c1"].evidence_ref
    blob = json.loads(store.get_evidence(ref))
    assert blob["verdict_state"] == "confirmed"
    assert blob["claim_id"] == "c1"
