"""
ROADMAP Step 4.4 — Agent 13 telemetry, instrumentation-first.

Prints Agent 13's report over the real event log: every number is a pure
aggregation over events.jsonl (Data Traceability — re-derive any figure by
filtering the log yourself). Findings only, no recommendations.

Usage:
    python scripts/run_analytics.py
"""
from __future__ import annotations

import json

from cfaios.agents.agent13_analytics.agent import AnalyticsAgent
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def main() -> None:
    api = LocalKnowledgeAPI()
    agent = AnalyticsAgent(api)
    agent.run_cycle({})

    print(f"[analytics] event log: {api._events_path.resolve()}")
    print(json.dumps(agent.report, indent=2))


if __name__ == "__main__":
    main()
