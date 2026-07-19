"""
Rules, Safety Layers, and Ethical Constraints.

These are operational obligations that bind specific agents. Several are hard blocks
(CSL, Safe Halt); others are governing policies (Mission Hierarchy, Pricing Ethics).
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class RuleDef:
    code: str
    title: str
    statement: str
    hard_block: bool  # True => violation halts/blocks; False => governing policy


class Rule(RuleDef, Enum):
    CSL = ("CSL", "Community Safety Layer",
           "Dedicated, proactive, human-escalated child-safety layer. Independent of and "
           "stricter than ordinary moderation; reputation grants no exemption. Safety outranks "
           "growth.", True)
    SAFE_HALT = ("SAFE_HALT", "Safe Halt Principle",
                 "When constitutional execution cannot be guaranteed, halt and escalate rather "
                 "than improvise.", True)
    EDUCATIONAL_EQUIPOISE = ("EQUIPOISE", "Educational Equipoise",
                             "Learners may be randomized across conditions only under genuine "
                             "uncertainty about which is better. Known superiority forbids "
                             "experimentation.", True)
    PRICING_ETHICS = ("PRICING", "Pricing Ethics",
                      "Transparent, understandable, educationally coherent, reversible. No dark "
                      "patterns, no hostage economics, strong minor protections.", False)
    MISSION_HIERARCHY = ("MISSION", "Mission Hierarchy",
                         "Mission -> Financial Sustainability -> Operational Efficiency. The "
                         "purpose of revenue is to increase educational capacity, not replace "
                         "educational purpose.", False)
    RESERVED_HUMAN = ("RESERVED", "Reserved Human Decisions",
                      "Constitutional amendment, institutional dissolution, mission change, "
                      "unresolvable ethical conflict, legal accountability, high-irreversibility "
                      "actions — humans only.", True)


ALL_RULES = tuple(Rule)
