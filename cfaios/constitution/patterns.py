"""
The 22 Architectural Patterns, organized by their six integrity layers.

A pattern is a reusable way to satisfy the constitution. Numbers are stable
discovery-order identifiers for cross-reference; the six layers are the conceptual
grouping. Some patterns serve more than one layer and are filed under their primary.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class IntegrityLayer(str, Enum):
    KNOWLEDGE = "Knowledge Integrity"        # prevent false knowledge
    HUMAN = "Human Integrity"                # protect people
    DECISION = "Decision Integrity"          # prevent unethical decisions
    TEMPORAL = "Temporal Integrity"          # prevent drift
    OPERATIONAL = "Operational Integrity"    # prevent execution failures
    MEASUREMENT = "Measurement Integrity"    # prevent dishonest optimization


@dataclass(frozen=True)
class PatternDef:
    number: int
    title: str
    layer: IntegrityLayer
    purpose: str


L = IntegrityLayer

PATTERNS: tuple[PatternDef, ...] = (
    PatternDef(1, "Candidate Knowledge Queue", L.KNOWLEDGE,
               "All external input enters as candidates; nothing auto-promotes to the graph."),
    PatternDef(2, "Layered Quality Gate", L.KNOWLEDGE,
               "Each layer proves quality before the next consumes it."),
    PatternDef(3, "Verification Router", L.KNOWLEDGE,
               "Routes each claim to the cheapest sufficient check: lookup -> +stats -> +engine."),
    PatternDef(4, "Verified Rendering", L.KNOWLEDGE,
               "Machine-verifiable content is rendered from data, never generated."),
    PatternDef(5, "Verified Visual Composition", L.KNOWLEDGE,
               "Composing provenance-bearing components never destroys provenance."),
    PatternDef(6, "Content Traceability", L.KNOWLEDGE,
               "Every sentence of content traces to a verified object (P3 extended to media)."),
    PatternDef(7, "Respectful Non-Intervention", L.HUMAN,
               "Sometimes the correct action is no action; silence can build more trust."),
    PatternDef(8, "Epistemic Moderation", L.HUMAN,
               "Classify claims by status rather than suppressing speech; teach through correction."),
    PatternDef(9, "Layered Public Trust", L.MEASUREMENT,
               "Validation depth scales with permanence x reach."),
    PatternDef(10, "Adaptive Intelligence Loop", L.OPERATIONAL,
               "Every agent runs Observe -> Interpret -> Decide -> Act -> Measure -> Adapt."),
    PatternDef(11, "Semantic Distance", L.OPERATIONAL,
               "S0 transformation (inherits) -> S1 recombination (partial) -> S2 creation (full)."),
    PatternDef(12, "Validation Conservation", L.OPERATIONAL,
               "Validation is conserved through pure transformation; re-earned only on new meaning."),
    PatternDef(13, "Observation-Decision Separation", L.DECISION,
               "The agent that measures never optimizes; the analyst never decides."),
    PatternDef(14, "Constitutional Trajectory Analysis", L.TEMPORAL,
               "Detect long-term drift invisible in individual decisions."),
    PatternDef(15, "Data Traceability", L.MEASUREMENT,
               "Every dashboard number is explorable to raw events — analytics branch of P3."),
    PatternDef(16, "Incentive-Compatible Metrics", L.HUMAN,
               "Every metric passes the Manipulation Incentive Test."),
    PatternDef(17, "Constitutional Recommendation Filtering", L.DECISION,
               "Unconstitutional proposals never become recommendations."),
    PatternDef(18, "Constitutional Impact Assessment", L.DECISION,
               "Every recommendation carries educational/relational/financial/constitutional impact."),
    PatternDef(19, "Knowledge Freshness Lifecycle", L.TEMPORAL,
               "Knowledge has an expected lifetime; re-verification is scheduled by decay."),
    PatternDef(20, "Persistent Research Watchlists", L.TEMPORAL,
               "Research is continuous surveillance of defined domains, not ad hoc searching."),
    PatternDef(21, "Constitutional Execution", L.OPERATIONAL,
               "Every workflow preserves every constitutional invariant under any condition."),
    PatternDef(22, "Bootstrap Resolution", L.TEMPORAL,
               "Every provisional artifact becomes a governed, versioned canonical one."),
)

# Cross-cutting patterns not numbered above but referenced throughout:
INTEGRITY_FIRST_OPTIMIZATION = (
    "Integrity-First Optimization",
    "Validate -> Constrain -> Optimize. Optimization occurs only inside approved-truthful space.")


def by_number(n: int) -> PatternDef:
    for p in PATTERNS:
        if p.number == n:
            return p
    raise KeyError(f"Unknown pattern #{n}")


def by_layer(layer: IntegrityLayer) -> list[PatternDef]:
    return [p for p in PATTERNS if p.layer is layer]
