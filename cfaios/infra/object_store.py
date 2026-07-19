"""Object store — evidence layer of Agent 2's three-layer store, and home of the
immutable Evidence Ledger (P3). Append-only (P6)."""
from __future__ import annotations
from abc import ABC, abstractmethod
import hashlib
from pathlib import Path


class ObjectStore(ABC):
    @abstractmethod
    def put_evidence(self, blob: bytes, *, content_type: str) -> str: ...

    @abstractmethod
    def get_evidence(self, ref: str) -> bytes: ...


class LocalObjectStore(ObjectStore):
    """Filesystem-backed dev implementation of the Evidence Ledger. Content-
    addressed by SHA-256: identical evidence blobs share a ref, and the ref IS
    the hashed pointer `Verdict.evidence_ref` expects (P3). Append-only in
    practice — writes are idempotent, nothing is ever overwritten or deleted.
    Not for production (no replication/access control) — a real build binds
    S3/GCS/etc. here instead."""

    def __init__(self, root: str | Path = ".cfaios_data/evidence"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_evidence(self, blob: bytes, *, content_type: str) -> str:
        ref = hashlib.sha256(blob).hexdigest()
        path = self.root / ref
        if not path.exists():
            path.write_bytes(blob)
            (self.root / f"{ref}.meta").write_text(content_type, encoding="utf-8")
        return ref

    def get_evidence(self, ref: str) -> bytes:
        path = self.root / ref
        if not path.exists():
            raise KeyError(f"No evidence found for ref {ref!r}")
        return path.read_bytes()
