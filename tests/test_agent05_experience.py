"""Unit tests for Agent 5 (Experience) — added 2026-07-23 to close a coverage
gap: this agent had zero dedicated tests despite being used live throughout
Phase 3-5 (only ever exercised indirectly via run_lesson.py / run_content.py /
run_full_pipeline.py). Uses a fake KnowledgeAPI so retrieval order and node
count are fully controlled and deterministic."""
from __future__ import annotations

import types

from cfaios.agents.agent05_experience.agent import ExperienceAgent
from cfaios.core.knowledge_api import KnowledgeNode


def _node(node_id: str, concept: str) -> KnowledgeNode:
    return KnowledgeNode(node_id=node_id, concept=concept,
                         payload={"raw_text": "should never leak into the blueprint"},
                         graph_version="v1", verdict=None)


def _fake_api(search_results: list[KnowledgeNode], version="local-v3"):
    calls = {"topic": None, "k": None}

    def semantic_search(topic, *, k=10):
        calls["topic"], calls["k"] = topic, k
        return search_results

    return types.SimpleNamespace(
        semantic_search=semantic_search, current_version=lambda: version, emit=lambda e: None,
    ), calls


def test_blueprint_orders_and_references_only_never_copies_content():
    results = [_node("n1", "Study A"), _node("n2", "Study B")]
    api, _ = _fake_api(results)
    agent = ExperienceAgent(api)

    agent.run_cycle({"topic": "endgames", "k": 5})

    bp = agent.blueprint
    assert bp["graph_version"] == "local-v3"
    assert bp["sections"] == [
        {"order": 1, "node_id": "n1", "concept": "Study A"},
        {"order": 2, "node_id": "n2", "concept": "Study B"},
    ]
    # never carries payload/raw_text forward — "references, not copies" (P5)
    for section in bp["sections"]:
        assert "payload" not in section and "raw_text" not in section


def test_topic_and_k_pass_through_to_search():
    api, calls = _fake_api([])
    agent = ExperienceAgent(api)
    agent.run_cycle({"topic": "rook endings", "k": 7})
    assert calls == {"topic": "rook endings", "k": 7}


def test_default_k_is_five_when_omitted():
    api, calls = _fake_api([])
    agent = ExperienceAgent(api)
    agent.run_cycle({"topic": "x"})
    assert calls["k"] == 5


def test_no_results_yields_empty_blueprint_not_a_crash():
    api, _ = _fake_api([])
    agent = ExperienceAgent(api)
    events = agent.run_cycle({"topic": "nonexistent topic"})
    assert agent.blueprint["sections"] == []
    assert events == []


def test_act_emits_nothing_blueprint_lives_on_the_agent():
    api, _ = _fake_api([_node("n1", "Study A")])
    agent = ExperienceAgent(api)
    events = agent.run_cycle({"topic": "x"})
    assert events == []
    assert agent.blueprint is not None
