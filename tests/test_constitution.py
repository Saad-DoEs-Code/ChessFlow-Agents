"""Structural tests for the constitutional skeleton."""
from cfaios.constitution import (ALL_PRINCIPLES, ALL_DOCTRINES, PATTERNS,
                                 by_number, IntegrityLayer, by_layer)
from cfaios.agents_spec import AGENTS
from cfaios.core.knowledge_api import AGENT_KNOWLEDGE_WRITER


def test_eighteen_agents():
    assert len(AGENTS) == 18
    assert [a["number"] for a in AGENTS] == list(range(1, 19))


def test_principle_count():
    # P1-P16 plus Constitutional Execution and External Validation
    assert len(ALL_PRINCIPLES) == 18


def test_four_doctrines():
    assert len(ALL_DOCTRINES) == 4


def test_twenty_two_patterns():
    assert len(PATTERNS) == 22
    assert by_number(1).title == "Candidate Knowledge Queue"


def test_six_integrity_layers_all_populated():
    for layer in IntegrityLayer:
        assert by_layer(layer), f"layer {layer} has no patterns"


def test_single_writer_is_agent_two():
    assert AGENT_KNOWLEDGE_WRITER == 2


def test_every_agent_declares_a_gate_and_p0():
    for a in AGENTS:
        assert a["gate"], a
        assert a["p0"], a
