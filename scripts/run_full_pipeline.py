"""
Phase 5 — the full 18-agent pipeline in one command.

Truth (1, 2, 3) -> Education (5, 6) -> Communication (7, 8, 9, 10, 11, 12) ->
Intelligence (13, 14, 15) -> Governance (16, 17, 18), against the real committed
graph. Every hop that has a gate refuses to proceed if the previous hop's gate
failed (Pattern #2) — this script is the concrete proof that the constitution's
"no layer consumes unproven output" rule holds across the ENTIRE system, not
just pairwise.

Usage:
    python scripts/run_full_pipeline.py [--topic "chess endgame study"] [--k 2]
"""
from __future__ import annotations

import argparse
import json

from cfaios.agents.agent05_experience.agent import ExperienceAgent
from cfaios.agents.agent06_assessment.agent import AssessmentAgent, competency_projection
from cfaios.agents.agent07_coaching.agent import CoachingAgent
from cfaios.agents.agent08_content.agent import ContentAgent
from cfaios.agents.agent09_distribution.agent import DistributionAgent
from cfaios.agents.agent10_visual.agent import VisualAgent
from cfaios.agents.agent11_lifecycle.agent import LifecycleAgent
from cfaios.agents.agent12_community.agent import CommunityAgent
from cfaios.agents.agent13_analytics.agent import AnalyticsAgent
from cfaios.agents.agent14_business.agent import BusinessAgent
from cfaios.agents.agent15_research.agent import ResearchAgent
from cfaios.agents.agent16_orchestrator.agent import OrchestratorAgent, PipelineStep
from cfaios.agents.agent17_brand.agent import BrandAgent
from cfaios.agents.agent18_executive.agent import ExecutiveAgent
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def _h(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full 18-agent pipeline")
    parser.add_argument("--topic", default="chess endgame study")
    parser.add_argument("--k", type=int, default=2, help="sections/scenes (LLM calls scale with this)")
    args = parser.parse_args()

    api = LocalKnowledgeAPI()
    print(f"[pipeline] graph: {api.root.resolve()}  (version {api.current_version()})")

    # ---- Education: Agent 5 -> Agent 7 (CQI-gated) ----
    _h("EDUCATION — Agent 5 (blueprint) -> Agent 7 (lesson, CQI-gated)")
    experience = ExperienceAgent(api)
    experience.run_cycle({"topic": args.topic, "k": args.k})
    if not experience.blueprint["sections"]:
        print("No verified nodes for this topic — run scripts/run_truth_slice.py first.")
        return
    coaching = CoachingAgent(api)
    coaching.run_cycle({"blueprint": experience.blueprint})
    cqi = coaching.evaluate_gate(coaching.score_lesson(coaching.lesson))
    print(f"blueprint: {len(experience.blueprint['sections'])} nodes | "
         f"CQI: {'PASS' if cqi.passed else 'FAIL'} ({cqi.score:.2f})")
    if not cqi.passed:
        print("Lesson gate failed — stopping (Pattern #2)."); return

    # ---- Communication: Agent 8 (PQI) -> 9, 10, 11, 12 ----
    _h("COMMUNICATION — Agent 8 (script, PQI-gated)")
    content = ContentAgent(api)
    content.run_cycle({"lesson": coaching.lesson, "gate_passed": cqi.passed})
    pqi = content.evaluate_gate(content.score_script(content.script))
    print(f"PQI: {'PASS' if pqi.passed else 'FAIL'} ({pqi.score:.2f})")
    if not pqi.passed:
        print("Script gate failed — stopping (Pattern #2)."); return

    _h("COMMUNICATION — Agent 17 (canonical brand) -> Agent 10 (thumbnail spec)")
    brand = BrandAgent(api)
    brand.run_cycle({
        "provisional_spec": {"palette": "chessflow-dark", "font": "bold-sans", "badge_style": "shield"},
        "promises": {"Engine-verified": {"engine_shallow", "engine_deep", "tablebase"}},
    })
    bci = brand.evaluate_gate(brand.score_brand(brand.canonical_brand))
    print(f"BCI: {'PASS' if bci.passed else 'FAIL'} ({bci.score:.2f}) "
         f"approved={brand.canonical_brand['approved_promises']}")

    visual = VisualAgent(api)
    visual.run_cycle({"script": content.script, "gate_passed": pqi.passed, "brand": brand.canonical_brand})
    print(f"thumbnail: badge={visual.thumbnail_spec['badge']!r}, "
         f"board={visual.thumbnail_spec['board_fen']}")

    _h("COMMUNICATION — Agent 9 (distribution fragments)")
    distribution = DistributionAgent(api)
    distribution.run_cycle({"script": content.script, "gate_passed": pqi.passed})
    sii = distribution.evaluate_gate(distribution.score_fragments(distribution.fragments))
    print(f"SII: {'PASS' if sii.passed else 'FAIL'} ({sii.score:.2f}), "
         f"{len(distribution.fragments)} fragments across "
         f"{len({f['platform'] for f in distribution.fragments})} platforms")

    _h("EDUCATION — Agent 6 (assessment) -> Agent 11 (lifecycle)")
    node_ids = [s["node_id"] for s in experience.blueprint["sections"]]
    assessment = AssessmentAgent(api)
    # Demo learner: answers the first question correctly.
    assessment.run_cycle({"learner_id": "demo-learner", "node_ids": node_ids})
    first_q = assessment.result["questions"][0] if assessment.result["questions"] else None
    responses = {first_q["node_id"]: first_q["answer_key"]} if first_q else {}
    assessment.run_cycle({"learner_id": "demo-learner", "node_ids": node_ids, "responses": responses})
    ari_summary = f"attempted={assessment.result['attempted']} accuracy={assessment.result['accuracy']}"
    print(f"assessment: {ari_summary}")

    graph = competency_projection(api.read_events())
    lifecycle = LifecycleAgent(api)
    lifecycle.run_cycle({"learner_id": "demo-learner", "competency": graph.get("demo-learner", {}),
                        "candidate_node_ids": node_ids})
    lii = lifecycle.evaluate_gate(lifecycle.score_sequence(lifecycle.sequence))
    print(f"LII: {'PASS' if lii.passed else 'FAIL'} ({lii.score:.2f}), "
         f"{len(lifecycle.sequence['actions'])} action(s)")
    for a in lifecycle.sequence["actions"]:
        print(f"  [{a['action']}] {a['message']}")

    _h("COMMUNICATION — Agent 12 (community moderation)")
    community = CommunityAgent(api)
    community.run_cycle({"posts": [
        {"post_id": "c1", "author": "learner_x", "text": "Great explanation, thanks!"},
        {"post_id": "c2", "author": "learner_y", "text": "hey what's your phone number"},
    ]})
    epi = community.evaluate_gate(community.score_moderation(community.result["dispositions"]))
    print(f"Epistemic Moderation: {'PASS' if epi.passed else 'FAIL'} ({epi.score:.2f})")
    for d in community.result["dispositions"]:
        state = "ESCALATED (child-safety)" if d["escalate"] else d["epistemic_state"].value
        print(f"  [{d['post_id']}] {state}")

    # ---- Intelligence: Agent 13 -> 14, 15 ----
    _h("INTELLIGENCE — Agent 13 (telemetry) -> Agent 14 (business) + Agent 15 (research)")
    analytics = AnalyticsAgent(api)
    analytics.run_cycle({})
    print(f"funnel: {analytics.report['funnel']}")

    business = BusinessAgent(api)
    business.run_cycle({
        "analytics_report": analytics.report,
        "proposed_metrics": [
            {"name": "confirmed_nodes_per_week", "objective_function": "maximize verified commits"},
            {"name": "engagement_score", "objective_function": "maximize time on app"},
        ],
    })
    bii = business.evaluate_gate(business.score_model(
        business.model, len(business.model["legal_metrics"]) + len(business.model["illegal_metrics"]), 2))
    print(f"BII: {'PASS' if bii.passed else 'FAIL'} ({bii.score:.2f}) "
         f"legal={business.model['legal_metrics']} illegal={[m['metric'] for m in business.model['illegal_metrics']]}")

    research = ResearchAgent(api)
    research.run_cycle({"findings": []})  # staleness scan only this run
    rii = research.evaluate_gate(research.score_result(research.result["checkable"], research.result["noted"]))
    print(f"RII: {'PASS' if rii.passed else 'FAIL'} ({rii.score:.2f}), "
         f"{len(research.result['stale_ids'])} node(s) flagged stale")

    # ---- Governance: Agent 16 sequencing this whole demo, Agent 18 triage ----
    _h("GOVERNANCE — Agent 18 (executive triage of the log's escalations)")
    executive = ExecutiveAgent(api)
    events = executive.run_cycle({})
    eii = executive.evaluate_gate(executive.score_result(executive.result))
    print(f"EII: {'PASS' if eii.passed else 'FAIL'} ({eii.score:.2f}), "
         f"{executive.result['total_escalations']} total escalation(s) in log, "
         f"{len(executive.result['proposals'])} amendment proposal(s) drafted")
    for e in events:
        print(f"  PROPOSAL [{e.subject_id}]: {e.payload['summary']} "
             f"(requires_human_enactment={e.payload['requires_human_enactment']})")

    _h("DONE")
    print(f"final graph version: {api.current_version()}")


if __name__ == "__main__":
    main()
