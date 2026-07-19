"""
Phase 5 — Agent 6: assess a learner on the verified nodes behind a lesson.

Renders a diagnostic purely from committed nodes (question = the position +
stipulation; answer key = the Agent-3-CONFIRMED result — Verified Rendering, no
LLM), scores the learner's answers, emits COMPETENCY_UPDATED events, and prints
the Competency Graph rebuilt from the event log to prove it's a projection.

Answers come from --answers (comma-separated, aligned with the printed question
order; use "-" to leave one unanswered). --demo simulates a learner who gets the
first question right and the second wrong.

Usage:
    python scripts/run_assessment.py --demo
    python scripts/run_assessment.py --learner alice --answers win,-,draw
"""
from __future__ import annotations

import argparse
import json

from cfaios.agents.agent05_experience.agent import ExperienceAgent
from cfaios.agents.agent06_assessment.agent import AssessmentAgent, competency_projection
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess a learner on verified lesson nodes")
    parser.add_argument("--topic", default="chess endgame study")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--learner", default="demo-learner")
    parser.add_argument("--answers", default=None,
                        help='comma-separated answers in question order ("-" = unanswered)')
    parser.add_argument("--demo", action="store_true",
                        help="simulate: first answer correct, second wrong, rest unanswered")
    args = parser.parse_args()

    api = LocalKnowledgeAPI()

    # Agent 5 picks the nodes (same retrieval the lesson used)
    experience = ExperienceAgent(api)
    experience.run_cycle({"topic": args.topic, "k": args.k})
    node_ids = [s["node_id"] for s in experience.blueprint["sections"]]
    if not node_ids:
        print("[assessment] No verified nodes for this topic.")
        return

    assessment = AssessmentAgent(api)

    # First pass: render the diagnostic (no responses yet) so we know the
    # questions and their keys before constructing demo/CLI answers.
    assessment.run_cycle({"learner_id": args.learner, "node_ids": node_ids})
    questions = assessment.result["questions"]
    print(f"[assessment] learner   : {args.learner}")
    print(f"[assessment] questions : {len(questions)}  "
          f"(excluded: {len(assessment.result['excluded'])})")
    for i, q in enumerate(questions, 1):
        print(f"  Q{i}. {q['prompt']}")

    # Build responses
    responses: dict[str, str] = {}
    if args.demo and questions:
        responses[questions[0]["node_id"]] = questions[0]["answer_key"]          # right
        if len(questions) > 1:
            wrong = {"win": "draw", "draw": "win", "loss": "draw"}[questions[1]["answer_key"]]
            responses[questions[1]["node_id"]] = wrong                            # wrong
    elif args.answers:
        for q, a in zip(questions, args.answers.split(",")):
            if a.strip() != "-":
                responses[q["node_id"]] = a.strip()

    if not responses:
        print("\n[assessment] No answers given (use --demo or --answers) — diagnostic only.")
        return

    # Second pass: score for real
    events = assessment.run_cycle({"learner_id": args.learner, "node_ids": node_ids,
                                   "responses": responses})
    r = assessment.result
    print(f"\n[assessment] attempted : {r['attempted']}   correct: {r['correct']}   "
          f"accuracy: {r['accuracy']}")
    print(f"[assessment] unanswered: {len(r['unanswered'])} (reported, never scored)")
    for s in r["scored"]:
        mark = "RIGHT" if s["correct"] else "WRONG"
        print(f"  {mark}: answered {s['answer']!r}, key {s['answer_key']!r}  "
              f"[node {s['node_id']}]")
    print(f"[assessment] COMPETENCY_UPDATED events emitted: {len(events)}")

    # Prove the Competency Graph is a projection of the log
    graph = competency_projection(api.read_events())
    print(f"\n[assessment] Competency Graph rebuilt from event log:")
    print(json.dumps(graph.get(args.learner, {}), indent=2))


if __name__ == "__main__":
    main()
