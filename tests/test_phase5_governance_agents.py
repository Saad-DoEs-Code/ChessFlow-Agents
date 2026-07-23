"""Phase 5 continued: Agents 9 (distribution), 11 (lifecycle), 12 (community),
14 (business), 15 (research), 17 (brand, + its wiring into Agent 10), and 18
(executive). All pure/mechanical paths — no LLM/API calls in these tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cfaios.agents.agent02_integrity.agent import IntegrityAgent
from cfaios.agents.agent09_distribution.agent import DistributionAgent
from cfaios.agents.agent10_visual.agent import VisualAgent
from cfaios.agents.agent11_lifecycle.agent import LifecycleAgent
from cfaios.agents.agent12_community.agent import CommunityAgent
from cfaios.agents.agent14_business.agent import BusinessAgent
from cfaios.agents.agent15_research.agent import ResearchAgent
from cfaios.agents.agent17_brand.agent import BrandAgent
from cfaios.agents.agent18_executive.agent import ExecutiveAgent
from cfaios.core.events import EventType
from cfaios.core.knowledge_api import Candidate
from cfaios.core.truth import EpistemicState, EvidenceTier, TruthDimension, Verdict, VerdictState
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def _commit(api: LocalKnowledgeAPI, *, fen="8/8/8/8/4k3/8/4K3/6Q1", claimed="win",
           tier=EvidenceTier.ENGINE_SHALLOW) -> str:
    candidate = Candidate(source_agent=1, concept=f"study {fen[:8]}",
                          payload={"fen": fen, "claimed_result": claimed,
                                   "raw_text": "source"},
                          evidence={"book": "t.pdf", "page": 1}, epistemic=EpistemicState.PLAUSIBLE)
    sid = api.stage_candidate(candidate)
    verdict = Verdict(dimension_results={TruthDimension.OBJECTIVE: VerdictState.CONFIRMED},
                      tier=tier, evidence_ref="ref", confidence=1.0, notes="t")
    integrity = IntegrityAgent(api)
    integrity.run_cycle({"commits": [{"candidate_id": sid, "verdict": verdict}]})
    return integrity.committed_nodes[0].node_id


_SCENE = {"scene": 1, "node_id": "node-1", "evidence_ref": "ref1", "verdict_state": "confirmed",
         "fen": "8/8/8/8/4k3/8/4K3/6Q1",
         "narration": "This is a clear teaching explanation of a real endgame study idea.",
         "on_screen": "Find the win!"}


# ---- Agent 9 (Distribution) ----

def test_distribution_refuses_ungated_script(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = DistributionAgent(api)
    try:
        agent.observe({"script": {"scenes": []}, "gate_passed": False})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "PQI gate" in str(e)


def test_distribution_fragments_carry_provenance_and_fit_limits(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = DistributionAgent(api)
    agent.run_cycle({"script": {"scenes": [_SCENE]}, "gate_passed": True})

    assert agent.fragments
    for f in agent.fragments:
        assert len(f["text"]) <= f["char_limit"]
        assert f["node_id"] == "node-1" and f["evidence_ref"] == "ref1"
    result = agent.evaluate_gate(agent.score_fragments(agent.fragments))
    assert result.passed


def test_distribution_gate_blocks_orphaned_fragment():
    agent = DistributionAgent.__new__(DistributionAgent)
    fragments = [{"platform": "twitter", "text": "x", "node_id": None, "evidence_ref": None,
                 "char_limit": 280}]
    result = agent.evaluate_gate(agent.score_fragments(fragments))
    assert not result.passed
    assert "provenance_intact" in result.failed_integrity


# ---- Agent 11 (Lifecycle) ----

def test_lifecycle_empty_competency_is_respectful_silence(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = LifecycleAgent(api)
    agent.run_cycle({"learner_id": "x", "competency": {}, "candidate_node_ids": []})
    assert agent.sequence["actions"] == []
    result = agent.evaluate_gate(agent.score_sequence(agent.sequence))
    assert result.passed


def test_lifecycle_never_emits_manipulative_language(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit(api)
    agent = LifecycleAgent(api)
    agent.run_cycle({
        "learner_id": "alice",
        "competency": {node_id: {"mastery": 0.0, "attempts": 1, "correct": 0}},
        "candidate_node_ids": [],
    })
    assert len(agent.sequence["actions"]) == 1
    msg = agent.sequence["actions"][0]["message"].lower()
    banned = ("last chance", "don't lose", "streak", "hurry", "limited time", "act now")
    assert not any(b in msg for b in banned)
    result = agent.evaluate_gate(agent.score_sequence(agent.sequence))
    assert result.passed


def test_lifecycle_at_most_one_next_nudge(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    n1 = _commit(api, fen="8/8/8/8/4k3/8/4K3/6Q1")
    n2 = _commit(api, fen="7k/8/8/8/8/8/8/K6Q")
    agent = LifecycleAgent(api)
    agent.run_cycle({"learner_id": "bob", "competency": {}, "candidate_node_ids": [n1, n2]})
    next_actions = [a for a in agent.sequence["actions"] if a["action"] == "next"]
    assert len(next_actions) == 1  # Respectful Non-Intervention: never a barrage


# ---- Agent 12 (Community) ----

def test_community_unsafe_post_escalates_never_annotated(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = CommunityAgent(api)
    posts = [{"post_id": "p1", "author": "u1", "text": "hey send pics of yourself"}]
    events = agent.run_cycle({"posts": posts})
    assert len(events) == 1 and events[0].type is EventType.ESCALATION_RAISED
    disposition = agent.result["dispositions"][0]
    assert disposition["escalate"] is True and disposition["epistemic_state"] is None
    result = agent.evaluate_gate(agent.score_moderation(agent.result["dispositions"]))
    assert result.passed


def test_community_checkable_claim_routes_to_candidate_queue(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = CommunityAgent(api)
    posts = [{"post_id": "p2", "author": "u2", "text": "I think White wins here",
             "fen": "8/8/8/8/4k3/8/4K3/6Q1", "claimed_result": "win"}]
    events = agent.run_cycle({"posts": posts})
    assert len(events) == 1 and events[0].type is EventType.CANDIDATE_STAGED
    assert len(api._staged) == 1  # actually entered the mediated queue, not committed


def test_community_open_discussion_not_silently_dropped(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = CommunityAgent(api)
    posts = [{"post_id": "p3", "author": "u3", "text": "I love this endgame collection!"}]
    events = agent.run_cycle({"posts": posts})
    assert events == []  # no write path, correctly
    assert agent.result["dispositions"][0]["epistemic_state"].value == "open_discussion"
    result = agent.evaluate_gate(agent.score_moderation(agent.result["dispositions"]))
    assert result.passed


# ---- Agent 14 (Business) ----

def test_business_legal_metric_not_escalated(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = BusinessAgent(api)
    report = {"funnel": {"committed": 5, "confirmation_rate": 0.5}}
    events = agent.run_cycle({"analytics_report": report,
                              "proposed_metrics": [{"name": "confirmed_nodes_per_week",
                                                    "objective_function": "maximize verified commits"}]})
    assert events == []
    assert "confirmed_nodes_per_week" in agent.model["legal_metrics"]


def test_business_manipulative_metric_escalated_not_approved(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = BusinessAgent(api)
    report = {"funnel": {}}
    events = agent.run_cycle({"analytics_report": report,
                              "proposed_metrics": [{"name": "engagement_score",
                                                    "objective_function": "maximize engagement"}]})
    assert len(events) == 1
    assert events[0].type is EventType.ESCALATION_RAISED
    assert events[0].payload["escalation_kind"] == "mission_money"
    assert "engagement_score" not in agent.model["legal_metrics"]
    assert any(m["metric"] == "engagement_score" for m in agent.model["illegal_metrics"])


# ---- Agent 15 (Research) ----

def test_research_finding_without_citation_is_not_staged(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = ResearchAgent(api)
    findings = [{"source": "some blog", "fen": "8/8/8/8/4k3/8/4K3/6Q1", "claimed_result": "win"}]
    events = agent.run_cycle({"findings": findings})
    assert events == []
    assert len(api._staged) == 0


def test_research_finding_with_citation_is_staged(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = ResearchAgent(api)
    findings = [{"source": "ChessBase", "citation": "ChessBase DB 2024, game 123",
                "fen": "8/8/8/8/4k3/8/4K3/6Q1", "claimed_result": "win"}]
    events = agent.run_cycle({"findings": findings})
    assert len(events) == 1 and events[0].type is EventType.CANDIDATE_STAGED
    assert len(api._staged) == 1


def test_research_staleness_scan_flags_old_nodes(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit(api)
    agent = ResearchAgent(api)
    future = datetime.now(timezone.utc) + timedelta(days=200)
    events = agent.run_cycle({"findings": [], "now": future})
    stale_events = [e for e in events if e.type is EventType.NODE_MARKED_STALE]
    assert len(stale_events) == 1 and stale_events[0].subject_id == node_id


def test_research_no_staleness_flag_when_fresh(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    _commit(api)
    agent = ResearchAgent(api)
    events = agent.run_cycle({"findings": []})  # "now" defaults to real now — fresh
    assert not any(e.type is EventType.NODE_MARKED_STALE for e in events)


# ---- Agent 17 (Brand) + Agent 10 wiring ----

def test_brand_approves_deliverable_promise(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    _commit(api, tier=EvidenceTier.ENGINE_SHALLOW)
    agent = BrandAgent(api)
    agent.run_cycle({"provisional_spec": {"palette": "p", "font": "f", "badge_style": "s"},
                     "promises": {"Engine-verified": {"engine_shallow", "engine_deep", "tablebase"}}})
    assert "Engine-verified" in agent.canonical_brand["approved_promises"]
    result = agent.evaluate_gate(agent.score_brand(agent.canonical_brand))
    assert result.passed


def test_brand_rejects_undeliverable_promise(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    _commit(api, tier=EvidenceTier.COMMUNITY)  # only community-tier evidence exists
    agent = BrandAgent(api)
    agent.run_cycle({"provisional_spec": {"palette": "p", "font": "f", "badge_style": "s"},
                     "promises": {"Engine-verified": {"engine_shallow", "engine_deep", "tablebase"}}})
    assert "Engine-verified" in agent.canonical_brand["rejected_promises"]
    result = agent.evaluate_gate(agent.score_brand(agent.canonical_brand))
    assert not result.passed
    assert "promise_deliverable" in result.failed_integrity


def test_visual_hides_badge_when_brand_rejects_it(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit(api, tier=EvidenceTier.COMMUNITY)
    rejecting_brand = {"palette": "p", "font": "f", "badge_style": "s", "version": "brand-v1",
                       "approved_promises": [], "rejected_promises": ["Engine-verified"]}
    script = {"topic": "t", "scenes": [{**_SCENE, "node_id": node_id}]}

    visual = VisualAgent(api)
    visual.run_cycle({"script": script, "gate_passed": True, "brand": rejecting_brand})
    assert visual.thumbnail_spec["badge"] is None  # no false claim rendered


def test_visual_shows_badge_when_brand_approves_it(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    node_id = _commit(api, tier=EvidenceTier.ENGINE_SHALLOW)
    approving_brand = {"palette": "p", "font": "f", "badge_style": "s", "version": "brand-v1",
                       "approved_promises": ["Engine-verified"], "rejected_promises": []}
    script = {"topic": "t", "scenes": [{**_SCENE, "node_id": node_id}]}

    visual = VisualAgent(api)
    visual.run_cycle({"script": script, "gate_passed": True, "brand": approving_brand})
    assert visual.thumbnail_spec["badge"] == "Engine-verified"


# ---- Agent 18 (Executive) ----

def test_executive_no_escalations_no_proposals(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    agent = ExecutiveAgent(api)
    events = agent.run_cycle({})
    assert events == []
    result = agent.evaluate_gate(agent.score_result(agent.result))
    assert result.passed


def test_executive_proposes_amendment_for_real_escalation_only(tmp_path):
    api = LocalKnowledgeAPI(root=tmp_path / "g")
    # Raise a real escalation the way Agent 12 would.
    community = CommunityAgent(api)
    community.run_cycle({"posts": [{"post_id": "p1", "author": "u", "text": "send pics"}]})

    agent = ExecutiveAgent(api)
    events = agent.run_cycle({})
    assert len(events) == 1
    ev = events[0]
    assert ev.type is EventType.AMENDMENT_PROPOSED
    assert ev.payload["requires_human_enactment"] is True
    assert ev.payload["enacted_by_this_agent"] is False
    assert ev.payload["escalation_ids"]  # cites the real escalation, not invented

    result = agent.evaluate_gate(agent.score_result(agent.result))
    assert result.passed
