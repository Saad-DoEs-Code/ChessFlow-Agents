"""
Agent 5 — Learning Experience Architect (LXA)  (Education layer)

Designs learning experiences by backward design. Owns lesson structure and narrative flow; composes from verified knowledge, never authors explanations.

Gate: Curriculum Quality Score (CQS)
P0 failure: Publishing a course that contradicts verified knowledge or hides conflict.

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event
from cfaios.core.knowledge_api import KnowledgeAPI
from cfaios.constitution.gates import Gate


SPEC = AgentSpec(
    number=5,
    identity='Learning Experience Architect (LXA)',
    layer='Education',
    mandate='Designs learning experiences by backward design. Owns lesson structure and narrative flow; composes from verified knowledge, never authors explanations.',
    gate_code='Curriculum Quality Score (CQS)',
    inherits_principles=['P5', 'P8'],
    inherits_patterns=[2],
    reads=['Learning DNA', 'verified CKG', 'CFDS difficulty'],
    writes=['course/lesson blueprints (references, not copies)'],
    validated_by=['CQS gate', 'Agent 13 (outcomes)'],
    p0_failure='Publishing a course that contradicts verified knowledge or hides conflict.',
    deferred_build=['13-slot lesson ontology', 'Narrative Flow Model', 'Comparative Analysis Lessons'],
)


class ExperienceAgent(BaseAgent):
    """MINIMAL build (ROADMAP Step 3.1). Given a topic, retrieve verified nodes
    via semantic_search and order them into a flat lesson blueprint that
    references node IDs only — never copies their content (P5: Canonical
    Object, one object referenced everywhere, never duplicated). Only committed
    nodes are ever reachable via semantic_search, so "retrieve verified
    knowledge" is enforced by construction, not by an extra check here.

    TODO(build): the 13-slot lesson ontology and Narrative Flow Model are
    deferred — this produces a flat, retrieval-ranked sequence only."""

    spec = SPEC
    # TODO(build): define the concrete gate dimensions for Curriculum Quality Score (CQS).
    gate = Gate(code='Curriculum Quality Score (CQS)', title='Curriculum Quality Score (CQS)', dimensions=())

    def __init__(self, api: KnowledgeAPI):
        super().__init__(api)
        #: populated by decide(), for callers (Agent 7) to inspect after run_cycle()
        self.blueprint: dict | None = None

    def observe(self, context: dict) -> dict:
        """context: {"topic": str, "k": int = 5}"""
        return {"topic": context.get("topic", ""), "k": context.get("k", 5)}

    def interpret(self, observation: dict) -> dict:
        """Reference only: node_id + concept label. Never carries a node's
        payload/raw_text forward — Agent 7 re-retrieves the full node itself
        later, which is what keeps "references, not copies" true end to end,
        not just at this step."""
        nodes = self.api.semantic_search(observation["topic"], k=observation["k"])
        refs = [{"node_id": n.node_id, "concept": n.concept} for n in nodes]
        return {"topic": observation["topic"], "refs": refs}

    def decide(self, interpretation: dict) -> dict:
        blueprint = {
            "topic": interpretation["topic"],
            "graph_version": self.api.current_version(),
            "sections": [
                {"order": i, "node_id": r["node_id"], "concept": r["concept"]}
                for i, r in enumerate(interpretation["refs"], 1)
            ],
        }
        self.blueprint = blueprint
        return blueprint

    def act(self, decision: dict) -> list[Event]:
        """No EventType currently models "lesson blueprint produced" (the
        existing types map to Agents 1/2/3/6/7/12/16/18's writes, not Agent 5's)
        — a real build would add one; noting it here rather than inventing a
        new EventType outside a minimal step. The blueprint itself is on
        self.blueprint for the caller."""
        return []
