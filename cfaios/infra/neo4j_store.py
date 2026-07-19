"""Neo4j adapter — the graph layer of Agent 2's three-layer store. Holds the Knowledge
Graph (cyclic) and Learning Dependency Graph (DAG) as distinct labelled subgraphs (P1).
Only place Cypher lives; agents reach it via the KnowledgeAPI, never directly."""
from __future__ import annotations
from config.settings import settings


class Neo4jStore:
    def __init__(self, uri: str | None = None):
        self.uri = uri or settings.neo4j_uri
        self._driver = None

    def connect(self) -> None:
        # TODO(build): from neo4j import GraphDatabase; self._driver = GraphDatabase.driver(...)
        raise NotImplementedError("Bind neo4j.GraphDatabase using settings.neo4j_* values")

    def close(self) -> None:
        if self._driver:
            self._driver.close()
