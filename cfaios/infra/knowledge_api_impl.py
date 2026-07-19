"""
Concrete KnowledgeAPI binding — ROADMAP.md Step 2.3.

Real Neo4j (Step 0.2) isn't available in this environment (no Docker on this
machine — see PROGRESS.md), so the graph layer here is a persistent, JSON-backed
local store rather than Neo4j. Everything else is real, not mocked: the P4
single-writer contract is enforced at two independent points (`commit()` and
`emit()`), the event log is append-only on disk (P6), and the vector/object
stores are injected collaborators, not hardcoded.

This is exactly the seam KnowledgeAPI was designed for (see its module docstring):
swapping in real Neo4j later means writing a new KnowledgeAPI subclass that backs
`get_node`/`commit`/etc. with Cypher instead of a JSON file — no agent code changes,
because every agent only ever talks to the abstract `KnowledgeAPI` interface.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import (
    AGENT_KNOWLEDGE_WRITER, Candidate, KnowledgeAPI, KnowledgeNode, SingleWriterViolation)
from cfaios.core.truth import Verdict, verdict_from_dict, verdict_to_dict
from cfaios.infra.object_store import LocalObjectStore, ObjectStore
from cfaios.infra.vector_store import LocalVectorStore, VectorStore

_EMBED_DIM = 128


def _local_embedding(text: str) -> list[float]:
    """Deterministic, dependency-free hashing-trick bag-of-words vector.

    NOT a real semantic embedding — a placeholder (Pattern #22: Bootstrap
    Resolution) that lets upsert/query/cosine-similarity be exercised for real
    while a proper embedding model isn't reliably available (Google's project
    has zero API quota — see PROGRESS.md). Swap this function for a real model
    call without touching KnowledgeAPI or any agent — VectorStore is the seam.
    """
    vec = [0.0] * _EMBED_DIM
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % _EMBED_DIM
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm else vec


class LocalKnowledgeAPI(KnowledgeAPI):
    """Local dev binding. `nodes.json` is a materialized current-state view
    (a rebuildable projection, not the source of truth); `events.jsonl` is the
    real append-only event log (P6) — nothing is ever rewritten, only appended.
    """

    def __init__(self, root: str | Path = ".cfaios_data/graph",
                 vector_store: VectorStore | None = None,
                 object_store: ObjectStore | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._nodes_path = self.root / "nodes.json"
        self._events_path = self.root / "events.jsonl"

        self._nodes: dict[str, dict] = (
            json.loads(self._nodes_path.read_text(encoding="utf-8"))
            if self._nodes_path.exists() else {})
        #: in-memory staging queue — transient by design (Agent 2 drains it within a run)
        self._staged: dict[str, Candidate] = {}

        self.vector_store = vector_store or LocalVectorStore(self.root.parent / "vectors")
        self.object_store = object_store or LocalObjectStore(self.root.parent / "evidence")

    # ---- persistence ----

    def _save_nodes(self) -> None:
        self._nodes_path.write_text(json.dumps(self._nodes, indent=2), encoding="utf-8")

    def _append_event(self, event: Event) -> None:
        record = {
            "id": event.id, "type": event.type.value, "actor_agent": event.actor_agent,
            "subject_id": event.subject_id, "payload": event.payload,
            "at": event.at.isoformat(), "graph_version": event.graph_version,
        }
        with self._events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    # ---- reads (open to all agents) ----

    def get_node(self, node_id: str, *, version: str | None = None) -> KnowledgeNode | None:
        # Version pinning (courses/videos pin a version) is a deferred concern —
        # this binding only ever holds one current snapshot per node.
        raw = self._nodes.get(node_id)
        return _to_knowledge_node(node_id, raw) if raw else None

    def semantic_search(self, query: str, *, k: int = 10) -> list[KnowledgeNode]:
        hits = self.vector_store.query(_local_embedding(query), k=k)
        return [_to_knowledge_node(node_id, self._nodes[node_id])
                for node_id, _score in hits if node_id in self._nodes]

    def get_verdict(self, node_id: str) -> Verdict | None:
        raw = self._nodes.get(node_id)
        return verdict_from_dict(raw["verdict"]) if raw and raw.get("verdict") else None

    def current_version(self) -> str:
        return f"local-v{len(self._nodes)}"

    def read_events(self) -> list[dict]:
        """The full append-only history, oldest first (P6 read; Pattern #15)."""
        if not self._events_path.exists():
            return []
        with self._events_path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    # ---- write path (mediated; P4) ----

    def stage_candidate(self, candidate: Candidate) -> str:
        staging_id = f"stg-{uuid.uuid4().hex[:12]}"
        self._staged[staging_id] = candidate
        return staging_id

    def emit(self, event: Event) -> None:
        if event.type is EventType.KNOWLEDGE_COMMITTED and event.actor_agent != AGENT_KNOWLEDGE_WRITER:
            raise SingleWriterViolation(
                f"actor {event.actor_agent} attempted to emit KNOWLEDGE_COMMITTED; "
                f"only Agent {AGENT_KNOWLEDGE_WRITER} may (P4).")
        self._append_event(event)

    # ---- Agent 2 only ----

    def commit(self, candidate_id: str, verdict: Verdict, *, _actor: int) -> KnowledgeNode:
        if _actor != AGENT_KNOWLEDGE_WRITER:
            raise SingleWriterViolation(
                f"actor {_actor} attempted to commit; only Agent {AGENT_KNOWLEDGE_WRITER} may (P4).")
        if candidate_id not in self._staged:
            raise KeyError(
                f"No staged candidate {candidate_id!r} (already committed, or never staged).")

        candidate = self._staged.pop(candidate_id)
        node_id = f"node-{uuid.uuid4().hex[:12]}"
        embedding = _local_embedding(f"{candidate.concept} {json.dumps(candidate.payload)}")
        self.vector_store.upsert(node_id, embedding, metadata={"concept": candidate.concept})

        self._nodes[node_id] = {
            "concept": candidate.concept,
            "payload": candidate.payload,
            "graph_version": f"local-v{len(self._nodes) + 1}",
            "verdict": verdict_to_dict(verdict),
            "source_agent": candidate.source_agent,
        }
        self._save_nodes()
        return _to_knowledge_node(node_id, self._nodes[node_id])


def _to_knowledge_node(node_id: str, raw: dict) -> KnowledgeNode:
    return KnowledgeNode(
        node_id=node_id,
        concept=raw["concept"],
        payload=raw["payload"],
        graph_version=raw["graph_version"],
        verdict=verdict_from_dict(raw["verdict"]) if raw.get("verdict") else None,
    )


def rebuild_nodes_from_events(events: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """Replay the event log into a fresh node projection (P6: the log is the
    source of truth; nodes.json is a rebuildable cache).

    Returns (nodes, warnings). A KNOWLEDGE_COMMITTED event must carry the full
    node record in its payload to be replayable; `source_agent` is recovered by
    joining the commit's `candidate_id` back to the CANDIDATE_STAGED event for
    that staging id — the log joining to itself, which only works when staging
    went through the evented path. Events from before this schema (or commits
    whose staging bypassed event emission) are reported as warnings, never
    silently guessed at (P3)."""
    stager_by_candidate: dict[str, int] = {}
    nodes: dict[str, dict] = {}
    warnings: list[str] = []

    for ev in events:
        if ev["type"] == EventType.CANDIDATE_STAGED.value:
            stager_by_candidate[ev["subject_id"]] = ev["actor_agent"]
        elif ev["type"] == EventType.KNOWLEDGE_COMMITTED.value:
            p = ev["payload"]
            if "node_payload" not in p:
                warnings.append(
                    f"event {ev['id']} (node {ev['subject_id']}): legacy payload without "
                    f"node data — not replayable")
                continue
            source_agent = stager_by_candidate.get(p.get("candidate_id"))
            if source_agent is None:
                warnings.append(
                    f"event {ev['id']} (node {ev['subject_id']}): no CANDIDATE_STAGED event "
                    f"for candidate {p.get('candidate_id')!r} — source_agent unrecoverable")
            nodes[ev["subject_id"]] = {
                "concept": p["concept"],
                "payload": p["node_payload"],
                "graph_version": p["graph_version"],
                "verdict": p["verdict"],
                "source_agent": source_agent,
            }
    return nodes, warnings
