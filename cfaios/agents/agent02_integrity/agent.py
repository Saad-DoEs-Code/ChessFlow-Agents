"""
Agent 2 — Chief Knowledge Integrity Officer  (Truth layer)

The sole writer to the canonical knowledge graph (P4). Owns the three-layer store, schema, ontology, and event-sourced history.

Gate: Graph-Health KPIs
P0 failure: Evidence Loss — committing knowledge whose provenance cannot be reconstructed.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import KnowledgeAPI, KnowledgeNode
from cfaios.core.truth import VerdictState, verdict_to_dict
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=2,
    identity='Chief Knowledge Integrity Officer',
    layer='Truth',
    mandate='The sole writer to the canonical knowledge graph (P4). Owns the three-layer store, schema, ontology, and event-sourced history.',
    gate_code='Graph-Health KPIs',
    inherits_principles=['P1', 'P4', 'P5', 'P6'],
    inherits_patterns=[1, 2],
    reads=['staging queue', 'Agent 3 verdicts'],
    writes=['CKG commits (SOLE WRITER)', 'ontology/schema versions'],
    validated_by=['Ontology Review Board (human+AI)'],
    p0_failure='Evidence Loss — committing knowledge whose provenance cannot be reconstructed.',
    deferred_build=['three-layer store (Neo4j+vector+object)', 'Knowledge Identity Score', 'ontology governance / Review Board', 'confidence propagation'],
)


class IntegrityAgent(BaseAgent):
    """The sole writer to the canonical knowledge graph (P4). Agent 2 does not
    re-verify anything itself (External Validation — no agent is its own final
    validator): it gates strictly on what Agent 3 already decided. Only a
    CONFIRMED verdict clears the bar to commit; REFUTED/INCONCLUSIVE/INAPPLICABLE
    candidates are never written — committing an unconfirmed claim as knowledge
    is exactly this agent's P0 failure mode (Evidence Loss) in spirit, even
    though the literal P0 is about provenance loss on what IS committed."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Graph-Health KPIs.
    gate = Gate(code='Graph-Health KPIs', title='Graph-Health KPIs', dimensions=())

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        #: populated by act(), for callers to inspect after run_cycle()
        self.committed_nodes: list[KnowledgeNode] = []
        self.skipped: list[dict] = []

    def observe(self, context: dict) -> dict:
        """context: {"commits": [{"candidate_id": str, "verdict": Verdict}, ...]}
        (typically: candidate_ids Agent 1 staged, paired with the Verdict Agent 3
        returned for each)."""
        return {"commits": context.get("commits", [])}

    def interpret(self, observation: dict) -> dict:
        """Gate on Agent 3's verdict — the only judgement Agent 2 makes."""
        eligible, rejected = [], []
        for item in observation["commits"]:
            state = next(iter(item["verdict"].dimension_results.values()))
            (eligible if state is VerdictState.CONFIRMED else rejected).append(item)
        return {"eligible": eligible, "rejected": rejected}

    def decide(self, interpretation: dict) -> dict:
        self.skipped = interpretation["rejected"]
        return {"to_commit": interpretation["eligible"]}

    def act(self, decision: dict) -> list[Event]:
        """Commit each eligible candidate — never touches the graph any other
        way (P4) — and emit one KNOWLEDGE_COMMITTED event per node for the
        audit log. `self.api.commit()` independently asserts the actor is
        Agent 2 (SingleWriterViolation otherwise); `self.api.emit()` (called by
        run_cycle after this returns) asserts it again on the event itself."""
        events: list[Event] = []
        for item in decision["to_commit"]:
            node = self.api.commit(item["candidate_id"], item["verdict"], _actor=self.spec.number)
            self.committed_nodes.append(node)
            # The event carries the FULL node record: the append-only log must be
            # able to rebuild the graph projection on its own (P6 — the log is the
            # source of truth, nodes.json is a cache). candidate_id lets replay
            # join back to the CANDIDATE_STAGED event to recover provenance.
            events.append(Event(
                type=EventType.KNOWLEDGE_COMMITTED,
                actor_agent=self.spec.number,
                subject_id=node.node_id,
                payload={"concept": node.concept, "graph_version": node.graph_version,
                         "evidence_ref": item["verdict"].evidence_ref,
                         "candidate_id": item["candidate_id"],
                         "node_payload": node.payload,
                         "verdict": verdict_to_dict(item["verdict"])},
            ))
        return events
