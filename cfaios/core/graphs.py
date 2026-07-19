"""
The Three Orthogonal Graphs (conceptual model, enforced structurally).

They must never collapse into one another; that separation is what makes CFAIOS
auditable. Each has one authority and a strict read/write discipline:

    Knowledge Graph   "what is true?"    owner: Agent 3 (verification) / Agent 2 (writer)
    Decision Graph    "what to do?"      owner: Agents 13-18 (apex: 18)
    Execution Graph   "what runs?"       owner: Agent 16

Rules (Strategic Epistemic Humility doctrine):
  * Decision may READ Knowledge, never WRITE it.
  * Execution may READ Decision, never redefine truth or meaning.
"""
from __future__ import annotations
from enum import Enum


class Graph(str, Enum):
    KNOWLEDGE = "knowledge"
    DECISION = "decision"
    EXECUTION = "execution"


#: Allowed read edges. Absence of a write edge is intentional: no graph writes another.
CAN_READ: dict[Graph, set[Graph]] = {
    Graph.KNOWLEDGE: set(),
    Graph.DECISION: {Graph.KNOWLEDGE},
    Graph.EXECUTION: {Graph.DECISION},
}


def assert_read_allowed(reader: Graph, target: Graph) -> None:
    if target is reader:
        return
    if target not in CAN_READ[reader]:
        raise PermissionError(
            f"{reader.value} graph may not read {target.value} graph "
            f"(violates orthogonal-graph separation)")
