"""
The Knowledge API — the spine of CFAIOS.

This is the ONLY interface through which agents touch the canonical knowledge graph.
It enforces the Single-Writer Invariant (P4): reads are open to all agents; writes are
NOT direct — an agent submits candidates / emits events, and only Agent 2 commits them.
Even Agents 16 and 18 (the most powerful) write through here, never around it.

The class below is an abstract contract. Concrete implementations bind it to Neo4j +
the vector store + the object store (see cfaios.infra). Business logic is deferred; the
*contract* — who may do what — is fixed here and is not a build-time decision.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from cfaios.core.events import Event
from cfaios.core.truth import EpistemicState, Verdict


AGENT_KNOWLEDGE_WRITER = 2  # P4: only Agent 2 may commit to the graph


@dataclass(frozen=True)
class KnowledgeNode:
    """A projection of a committed knowledge object (read-only to consumers)."""
    node_id: str
    concept: str
    payload: dict
    graph_version: str
    verdict: Verdict | None = None


@dataclass(frozen=True)
class Candidate:
    """Something that MIGHT become knowledge. Produced by Agents 1, 12, 15.
    Never authoritative until it passes Agent 1 extraction + Agent 3 verification."""
    source_agent: int
    concept: str
    payload: dict
    evidence: dict
    epistemic: EpistemicState = EpistemicState.PLAUSIBLE


class KnowledgeAPI(ABC):
    """The single doorway to the CKG. Reads are universal; writes are mediated."""

    # ---- READS (open to all agents) ----
    @abstractmethod
    def get_node(self, node_id: str, *, version: str | None = None) -> KnowledgeNode | None:
        """Fetch a committed knowledge node (optionally at a pinned version)."""

    @abstractmethod
    def semantic_search(self, query: str, *, k: int = 10) -> list[KnowledgeNode]:
        """Vector-store retrieval. Supports P10 (retrieve before reasoning)."""

    @abstractmethod
    def get_verdict(self, node_id: str) -> Verdict | None:
        """Fetch Agent 3's verification verdict for a node."""

    @abstractmethod
    def current_version(self) -> str:
        """The current CKG snapshot tag (courses/videos pin a version)."""

    def read_events(self) -> list[dict]:
        """Read the append-only event history as plain dicts (P6). A read like any
        other — open to all agents; Agent 13 (analytics) is the primary consumer
        (Pattern #15: every dashboard number explorable to raw events). Default is
        empty for bindings without a persistent log; persistent bindings override."""
        return []

    def list_node_ids(self) -> list[str]:
        """All committed node ids. A read like any other — Agent 15 uses this for
        staleness scanning (Pattern #19). Default empty; persistent bindings override."""
        return []

    # ---- WRITE PATH (mediated; P4) ----
    @abstractmethod
    def stage_candidate(self, candidate: Candidate) -> str:
        """Submit a candidate to the staging queue. Returns a staging id.
        This is how Agents 1/12/15 propose knowledge. It does NOT enter the graph."""

    @abstractmethod
    def emit(self, event: Event) -> None:
        """Append an event to the log. For KNOWLEDGE_COMMITTED events this MUST reject
        any actor_agent != AGENT_KNOWLEDGE_WRITER (enforces P4)."""

    # ---- Agent 2 only ----
    @abstractmethod
    def commit(self, candidate_id: str, verdict: Verdict, *, _actor: int) -> KnowledgeNode:
        """Commit a verified candidate into the graph. Implementations MUST assert
        `_actor == AGENT_KNOWLEDGE_WRITER` and raise otherwise."""


class SingleWriterViolation(RuntimeError):
    """Raised when any agent other than Agent 2 attempts a knowledge commit."""
