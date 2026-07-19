"""
ROADMAP Step 4.1 — prove the event log is authoritative.

Replays .cfaios_data/graph/events.jsonl into a fresh node projection and compares
it, field by field, against the materialized nodes.json. If they match, nodes.json
is demonstrably just a cache and the append-only log is the real source of truth
(P6). Mismatches and unreplayable legacy events are reported honestly, never
patched over.

Usage:
    python scripts/replay_events.py
"""
from __future__ import annotations

from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI, rebuild_nodes_from_events


def main() -> None:
    api = LocalKnowledgeAPI()
    events = api.read_events()
    print(f"[replay] events in log      : {len(events)}")

    rebuilt, warnings = rebuild_nodes_from_events(events)
    print(f"[replay] nodes rebuilt      : {len(rebuilt)}")
    print(f"[replay] warnings           : {len(warnings)}")
    for w in warnings:
        print(f"  ! {w}")
    print()

    current = api._nodes
    print(f"[replay] nodes in nodes.json: {len(current)}")

    matches, mismatches, missing_from_replay = 0, [], []
    for node_id, snap in current.items():
        if node_id not in rebuilt:
            missing_from_replay.append(node_id)
            continue
        r = rebuilt[node_id]
        fields_equal = all(r[k] == snap[k] for k in ("concept", "payload", "graph_version", "verdict"))
        # source_agent may be None in the rebuild when staging bypassed event
        # emission (pre-schema runs) — count as a soft match but say so.
        if fields_equal:
            matches += 1
            if r["source_agent"] != snap.get("source_agent"):
                print(f"  ~ {node_id}: content matches; source_agent unrecoverable from log "
                      f"(snapshot says {snap.get('source_agent')})")
        else:
            diffs = [k for k in ("concept", "payload", "graph_version", "verdict") if r[k] != snap[k]]
            mismatches.append((node_id, diffs))

    print(f"[replay] content matches    : {matches}/{len(current)}")
    if missing_from_replay:
        print(f"[replay] not replayable     : {len(missing_from_replay)} "
              f"(committed before the event schema carried node data)")
        for nid in missing_from_replay:
            print(f"  - {nid}")
    for node_id, diffs in mismatches:
        print(f"  X {node_id}: MISMATCH in {diffs}")

    print()
    if not mismatches and matches + len(missing_from_replay) == len(current):
        replayable = len(current) - len(missing_from_replay)
        print(f"[replay] VERDICT: log is authoritative for all {replayable} node(s) committed "
              f"under the current event schema; {len(missing_from_replay)} legacy node(s) "
              f"predate it (schema added in Step 4.1).")
    else:
        print("[replay] VERDICT: MISMATCH — the log and the snapshot disagree; investigate "
              "before trusting either.")


if __name__ == "__main__":
    main()
