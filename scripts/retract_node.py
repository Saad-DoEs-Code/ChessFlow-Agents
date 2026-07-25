"""
Manual node retraction — emits a NODE_SUPERSEDED event for a committed node.

Not tied to any agent's automatic loop: this is the governance-adjacent, human-
directed correction path for a node found wrong by investigation (as opposed to
Agent 15's automatic time-based staleness scan, which fires NODE_MARKED_STALE
instead). Retraction hides the node from get_node/semantic_search from this
point forward; the original commit is never erased from events.jsonl (P6).

Usage:
    python scripts/retract_node.py <node_id> "<reason>"
"""
from __future__ import annotations

import sys

from cfaios.core.events import Event, EventType
from cfaios.infra.knowledge_api_impl import LocalKnowledgeAPI


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python scripts/retract_node.py <node_id> \"<reason>\"")
        sys.exit(1)
    node_id, reason = sys.argv[1], sys.argv[2]

    api = LocalKnowledgeAPI()
    before = api.get_node(node_id)
    if before is None:
        print(f"[retract] {node_id!r} is not currently visible (already retracted, "
              f"or never committed) — nothing to do.")
        sys.exit(1)

    print(f"[retract] retracting {node_id}: {before.concept!r}")
    print(f"[retract] reason: {reason}")

    # actor_agent=3: framed as Agent 3 (Accuracy, owns verdict states) revising
    # an earlier verdict on new evidence — see the docstring on
    # LocalKnowledgeAPI._retract for why no actor check is enforced here.
    api.emit(Event(type=EventType.NODE_SUPERSEDED, actor_agent=3, subject_id=node_id,
                   payload={"reason": reason}))

    after = api.get_node(node_id)
    print(f"[retract] get_node now returns: {after}")
    print(f"[retract] graph version: {api.current_version()}")


if __name__ == "__main__":
    main()
