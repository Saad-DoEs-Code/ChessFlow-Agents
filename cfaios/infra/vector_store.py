"""Vector/embedding store — semantic layer of Agent 2's three-layer store. Powers P10
retrieval. Swap backend (pgvector/Qdrant/Pinecone) behind this interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
import json
import math
from pathlib import Path


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, node_id: str, embedding: list[float], metadata: dict) -> None: ...

    @abstractmethod
    def query(self, embedding: list[float], k: int = 10) -> list[tuple[str, float]]: ...


class LocalVectorStore(VectorStore):
    """File-backed, brute-force cosine-similarity store. Fine at this corpus's scale
    (hundreds, not millions, of nodes) and proves upsert/query works end-to-end
    without pgvector/Qdrant running — swap the backend behind this interface later,
    no caller changes needed."""

    def __init__(self, root: str | Path = ".cfaios_data/vectors"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "vectors.json"
        self._data: dict[str, dict] = (
            json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {})

    def upsert(self, node_id: str, embedding: list[float], metadata: dict) -> None:
        self._data[node_id] = {"embedding": embedding, "metadata": metadata}
        self._path.write_text(json.dumps(self._data), encoding="utf-8")

    def query(self, embedding: list[float], k: int = 10) -> list[tuple[str, float]]:
        scored = [(node_id, _cosine(embedding, v["embedding"])) for node_id, v in self._data.items()]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0
