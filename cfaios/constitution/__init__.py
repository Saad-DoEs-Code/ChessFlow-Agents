"""The Constitution — the shared, immutable-by-AI core every agent imports."""
from .principles import Principle, ALL_PRINCIPLES
from .doctrines import Doctrine, ALL_DOCTRINES
from .standards import Standard, ALL_STANDARDS
from .rules import Rule, ALL_RULES
from .patterns import PATTERNS, IntegrityLayer, PatternDef, by_number, by_layer
from .gates import Gate, Dimension, DimensionKind, GateResult, Phase
from .escalation import EscalationRecord, EscalationKind, EscalationState

__all__ = [
    "Principle", "ALL_PRINCIPLES", "Doctrine", "ALL_DOCTRINES",
    "Standard", "ALL_STANDARDS", "Rule", "ALL_RULES",
    "PATTERNS", "IntegrityLayer", "PatternDef", "by_number", "by_layer",
    "Gate", "Dimension", "DimensionKind", "GateResult", "Phase",
    "EscalationRecord", "EscalationKind", "EscalationState",
]
