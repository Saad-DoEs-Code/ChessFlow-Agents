"""Chess engine + tablebase adapter — Agent 3's verification muscle. Wraps Stockfish
(evaluation) and Syzygy (proven endgames). Invoked via the Verification Router (#3):
cheap lookups/stats first, engine only when a claim requires it."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from config.settings import settings


class ChessEngine(ABC):
    @abstractmethod
    def evaluate(self, fen: str, *, depth: int = 20) -> float: ...

    @abstractmethod
    def legal(self, fen: str) -> bool: ...

    @abstractmethod
    def tablebase(self, fen: str) -> str | None: ...


class StockfishEngine(ChessEngine):
    """Real adapter: talks UCI to a local Stockfish binary via python-chess, and
    (optionally) probes Syzygy tablebases when CFAIOS_SYZYGY_PATH is set.

    `legal()` never needs the binary (pure python-chess). `evaluate()` lazily
    launches the engine process on first use and reuses it; call `close()` when
    done. `tablebase()` returns None (not "unknown") whenever no tablebase is
    configured or the position falls outside it — callers fall back to the
    engine, never invent a result."""

    def __init__(self, path: str | None = None):
        self.path = path or settings.stockfish_path
        self._engine = None
        self._tb = None

    def _ensure_engine(self):
        if self._engine is None:
            if not self.path or not Path(self.path).exists():
                raise RuntimeError(
                    f"Stockfish binary not found at {self.path!r}. "
                    "Set CFAIOS_STOCKFISH_PATH in .env to a real Stockfish executable."
                )
            import chess.engine
            self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self._engine

    def legal(self, fen: str) -> bool:
        import chess
        try:
            board = chess.Board(fen)
        except ValueError:
            return False
        return board.is_valid()

    def evaluate(self, fen: str, *, depth: int = 20) -> float:
        """White-relative score in pawns. Mate scores map to a sentinel magnitude
        (just under 100, sign = who mates) so callers can threshold on magnitude
        without special-casing mate separately from a large material advantage."""
        import chess
        import chess.engine

        engine = self._ensure_engine()
        board = chess.Board(fen)
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"].white()
        if score.is_mate():
            mate_in = score.mate()
            magnitude = 100.0 - min(abs(mate_in), 99)
            return magnitude if mate_in > 0 else -magnitude
        return score.score() / 100.0

    def tablebase(self, fen: str) -> str | None:
        """Returns "win" | "draw" | "loss" from the perspective of the side to
        move, per Syzygy WDL convention — or None if unavailable/out of range."""
        if not settings.syzygy_path:
            return None
        import chess
        import chess.syzygy

        if self._tb is None:
            self._tb = chess.syzygy.open_tablebase(settings.syzygy_path)
        board = chess.Board(fen)
        try:
            wdl = self._tb.probe_wdl(board)
        except (KeyError, chess.syzygy.MissingTableError):
            return None
        if wdl > 0:
            return "win"
        if wdl < 0:
            return "loss"
        return "draw"

    def close(self) -> None:
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
