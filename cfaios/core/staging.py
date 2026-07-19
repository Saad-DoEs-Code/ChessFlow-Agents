"""
The Staging Queue — the mediated write buffer in front of Agent 2.

Agents 1, 12, and 15 discover candidate knowledge and place it here. Agent 2 is the
consumer: it verifies (via Agent 3) and commits. This realises the Candidate Knowledge
Queue pattern (#1) and preserves P4 — the queue is the ONLY producer of knowledge
commits, and it never auto-promotes (community/research are sources, not authorities).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from cfaios.core.knowledge_api import Candidate


class StagingQueue(ABC):
    @abstractmethod
    def enqueue(self, candidate: Candidate) -> str:
        """Add a candidate; return staging id. Producers: Agents 1, 12, 15."""

    @abstractmethod
    def dequeue(self, *, _actor: int) -> tuple[str, Candidate] | None:
        """Agent 2 only: pull the next candidate for verification + commit."""

    @abstractmethod
    def size(self) -> int: ...
