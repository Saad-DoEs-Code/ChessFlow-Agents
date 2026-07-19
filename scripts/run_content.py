"""
Phase 5 — the content chain: lesson (A5+A7, CQI-gated) -> video script (A8,
PQI-gated) -> thumbnail spec (A10, rendered from data).

Each hop only consumes the previous hop's output if its gate PASSED (Pattern #2);
Agents 8 and 10 refuse ungated input outright. Provenance (node_id +
evidence_ref) survives every transformation — printable at the end from the
thumbnail spec alone.

Usage:
    python scripts/run_content.py [--topic "chess endgame study"] [--k 3]
"""
from __future__ import annotations

import argparse
import json

from cfaios.agents.agent05_experience.agent import ExperienceAgent
from cfaios.agents.agent07_coaching.agent import CoachingAgent
from cfaios.agents.agent08_content.agent import ContentAgent
from cfaios.agents.agent10_visual.agent import VisualAgent
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def main() -> None:
    parser = argparse.ArgumentParser(description="Lesson -> video script -> thumbnail spec")
    parser.add_argument("--topic", default="chess endgame study")
    parser.add_argument("--k", type=int, default=3,
                        help="sections/scenes to produce (default 3 — each costs LLM calls)")
    args = parser.parse_args()

    api = LocalKnowledgeAPI()

    # ---- Agent 5: blueprint ----
    experience = ExperienceAgent(api)
    experience.run_cycle({"topic": args.topic, "k": args.k})
    if not experience.blueprint["sections"]:
        print("[content] No verified nodes for this topic.")
        return
    print(f"[content] blueprint : {len(experience.blueprint['sections'])} node refs")

    # ---- Agent 7: lesson + CQI gate ----
    coaching = CoachingAgent(api)
    coaching.run_cycle({"blueprint": experience.blueprint})
    cqi = coaching.evaluate_gate(coaching.score_lesson(coaching.lesson))
    print(f"[content] CQI gate  : {'PASSED' if cqi.passed else 'FAILED'} "
          f"(quality {cqi.score:.2f})")
    if not cqi.passed:
        print(f"[content] blocked: {cqi.failed_integrity} — stopping (Pattern #2).")
        raise SystemExit(1)

    # ---- Agent 8: video script + PQI gate ----
    content = ContentAgent(api)
    content.run_cycle({"lesson": coaching.lesson, "gate_passed": cqi.passed})
    pqi = content.evaluate_gate(content.score_script(content.script))
    print(f"[content] PQI gate  : {'PASSED' if pqi.passed else 'FAILED'} "
          f"(quality {pqi.score:.2f})")
    if not pqi.passed:
        print(f"[content] blocked: {pqi.failed_integrity} — stopping (Pattern #2).")
        raise SystemExit(1)

    print()
    for s in content.script["scenes"]:
        print(f"--- Scene {s['scene']}  [node {s['node_id']}] ---")
        print(f"  NARRATION: {s['narration']}")
        print(f"  ON-SCREEN: {s['on_screen']}")
        print()

    # ---- Agent 10: thumbnail spec (rendered from data, no LLM) ----
    visual = VisualAgent(api)
    visual.run_cycle({"script": content.script, "gate_passed": pqi.passed})
    print("[content] thumbnail spec (Agent 10, rendered from verified data):")
    print(json.dumps(visual.thumbnail_spec, indent=2))


if __name__ == "__main__":
    main()
