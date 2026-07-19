"""
ROADMAP Step 3.3 — the proof of life for the entire system.

Runs Agent 5 -> Agent 7 against the real committed graph from Phase 2, producing a
lesson where every explained section traces back to one specific verified node and
its Evidence Ledger entry. --show-provenance prints exactly that mapping for every
section and fetches each evidence blob back off disk to prove it's real, not
asserted.

Usage:
    python scripts/run_lesson.py [--topic "chess endgame study"] [--k 5] [--show-provenance]
"""
from __future__ import annotations

import argparse

from cfaios.agents.agent05_experience.agent import ExperienceAgent
from cfaios.agents.agent07_coaching.agent import CoachingAgent
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a lesson grounded in verified nodes")
    parser.add_argument("--topic", default="chess endgame study",
                        help='topic to retrieve verified nodes for (default: "chess endgame study")')
    parser.add_argument("--k", type=int, default=5, help="how many verified nodes to draw from (default 5)")
    parser.add_argument("--show-provenance", action="store_true",
                        help="print each section's node ID and Evidence Ledger ref, "
                             "and fetch the evidence back to prove it's real")
    parser.add_argument("--ignore-gate", action="store_true",
                        help="show the lesson even if the CQI gate fails (debugging only — "
                             "a failed gate means the lesson must NOT be consumed downstream)")
    args = parser.parse_args()

    api = LocalKnowledgeAPI()
    print(f"[run_lesson] graph  : {api.root.resolve()}  (version {api.current_version()})")
    print(f"[run_lesson] topic  : {args.topic!r}")
    print()

    experience = ExperienceAgent(api)
    experience.run_cycle({"topic": args.topic, "k": args.k})
    blueprint = experience.blueprint
    print(f"[run_lesson] blueprint: {len(blueprint['sections'])} verified node(s) retrieved")
    if not blueprint["sections"]:
        print("[run_lesson] No verified nodes matched this topic — try a different --topic, "
              "or commit more nodes first (scripts/run_truth_slice.py --vision-limit 0).")
        return

    coaching = CoachingAgent(api)
    events = coaching.run_cycle({"blueprint": blueprint})
    lesson = coaching.lesson

    print(f"[run_lesson] lesson   : {len(lesson['sections'])} section(s), "
          f"{len(events)} COACHING_EVENT(s) emitted")

    # CQI gate (Step 4.3): the lesson is not consumable output until this passes.
    gate_result = coaching.evaluate_gate(coaching.score_lesson(lesson))
    verdict = "PASSED" if gate_result.passed else "FAILED"
    print(f"[run_lesson] CQI gate : {verdict}  (quality score {gate_result.score:.2f}, "
          f"phase {gate_result.phase.value})")
    for name, value in gate_result.detail.items():
        print(f"             {name:<22} = {value:.2f}")
    if not gate_result.passed:
        print(f"[run_lesson] blocked integrity dimension(s): {gate_result.failed_integrity}")
        if not args.ignore_gate:
            print("[run_lesson] Lesson withheld — a gated-out lesson must not be consumed "
                  "(re-run with --ignore-gate to inspect it for debugging).")
            raise SystemExit(1)
        print("[run_lesson] --ignore-gate set: showing the lesson for DEBUGGING ONLY.")
    print()

    for i, s in enumerate(lesson["sections"], 1):
        print(f"=== Section {i}: {s['concept']} ===")
        print(s["explanation"])
        if args.show_provenance:
            print()
            print(f"  [provenance] node_id        = {s['node_id']}")
            print(f"  [provenance] fen             = {s['fen']}")
            print(f"  [provenance] verified verdict= {s['verdict_state']}")
            if s["evidence_ref"]:
                fetched = api.object_store.get_evidence(s["evidence_ref"])
                print(f"  [provenance] evidence_ref    = {s['evidence_ref']}")
                print(f"  [provenance]                   ({len(fetched)} bytes fetched back "
                      f"from the Evidence Ledger — not asserted, actually retrieved)")
            else:
                print("  [provenance] no evidence_ref (unexpected for a committed node)")
        print()


if __name__ == "__main__":
    main()
