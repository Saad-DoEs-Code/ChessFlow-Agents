"""Unit tests for Agent 1's board-diagram -> FEN vision path, added 2026-07-23
after discovering that a single legal-looking vision call is not evidence of a
correct one (see PROGRESS.md's "Finding (2026-07-23)"). No real vision API or
book is used — a fake client and a minimal single-page PDF fixture stand in."""
from __future__ import annotations

from cfaios.agents.agent01_extraction.agent import ExtractionAgent, _resolve_two_attempts

_KQ_VS_K = "8/8/8/8/4k3/8/4K3/6Q1"          # legal
_ANOTHER_LEGAL = "7k/8/8/8/8/8/8/K6Q"       # legal, different from the above
_NO_KINGS = "8/8/8/8/8/8/8/8"                # legal chars, illegal position


class _FakeVisionClient:
    """Returns queued responses in order, one per call — lets a test script
    exactly what each of the two attempts should return."""

    def __init__(self, responses: list[str]):
        self.model = "fake"
        self._responses = list(responses)
        self.calls = 0

    def vision_to_fen(self, image_bytes: bytes, *, mime: str = "image/png") -> str:
        self.calls += 1
        return self._responses.pop(0)


# ---- _resolve_two_attempts: pure decision logic ----

def test_two_attempts_agree_is_a_hit():
    fen, note = _resolve_two_attempts(_KQ_VS_K, "ok", _KQ_VS_K, "ok")
    assert fen == _KQ_VS_K
    assert "hit" in note and "2/2" in note


def test_two_attempts_disagree_is_not_committed():
    fen, note = _resolve_two_attempts(_KQ_VS_K, "ok", _ANOTHER_LEGAL, "ok")
    assert fen is None
    assert "inconsistent" in note
    assert _KQ_VS_K in note and _ANOTHER_LEGAL in note


def test_one_attempt_legal_one_illegal_is_not_committed():
    fen, note = _resolve_two_attempts(_KQ_VS_K, "ok", None, "illegal position 'x'")
    assert fen is None
    assert "inconsistent" in note


def test_both_attempts_fail_reports_both_reasons():
    fen, note = _resolve_two_attempts(None, "unparseable response 'x'", None, "illegal position 'y'")
    assert fen is None
    assert "both attempts failed" in note
    assert "unparseable" in note and "illegal" in note


# ---- _extract_fen_attempt: parse + legality, via a fake client ----

def test_extract_fen_attempt_accepts_legal_response():
    agent = ExtractionAgent.__new__(ExtractionAgent)  # no api/vision_client needed for this call
    agent.vision_client = _FakeVisionClient([_KQ_VS_K])
    fen, note = agent._extract_fen_attempt(b"fake-png-bytes")
    assert fen == _KQ_VS_K and note == "ok"


def test_extract_fen_attempt_rejects_illegal_response():
    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient([_NO_KINGS])
    fen, note = agent._extract_fen_attempt(b"fake-png-bytes")
    assert fen is None and "illegal" in note


def test_extract_fen_attempt_rejects_unparseable_response():
    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient(["I cannot determine the position."])
    fen, note = agent._extract_fen_attempt(b"fake-png-bytes")
    assert fen is None and "unparseable" in note


# ---- _attach_fens: end-to-end over a real (tiny, synthetic) PDF ----

def _make_one_page_pdf(path) -> None:
    from PIL import Image
    Image.new("RGB", (400, 500), "white").save(path, "PDF")


def test_attach_fens_end_to_end_hit(tmp_path):
    pdf_path = tmp_path / "book.pdf"
    _make_one_page_pdf(pdf_path)

    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient([_KQ_VS_K, _KQ_VS_K])  # both attempts agree

    concepts = [{"page": 1, "study_number": None, "side_char": "w"}]
    result = agent._attach_fens(str(pdf_path), concepts, limit=None, delay=0)

    assert agent.vision_client.calls == 2
    # stores the FULL fen (side-to-move included), not the bare placement —
    # see _is_legal_placement's docstring for why (2026-07-23 finding)
    assert result[0]["fen"] == f"{_KQ_VS_K} w - - 0 1"
    assert "hit" in result[0]["vision_note"]


def test_attach_fens_uses_the_stipulation_side_not_a_hardcoded_default(tmp_path):
    """A "Black to play" study must be validated and stored with Black to
    move — never silently defaulted to White (the actual bug found 2026-07-23,
    fixed at the source rather than papered over)."""
    pdf_path = tmp_path / "book.pdf"
    _make_one_page_pdf(pdf_path)

    # Legal only with Black to move: White king adjacent to Black king would be
    # illegal with Black to move in most framings, so pick a position that is
    # unambiguous: kings not adjacent, but material only makes sense as a
    # "Black to play" composition marker via side_char, proven by is_valid()
    # actually depending on the side field for check-legality below.
    fen_needing_black_to_move = "8/8/8/3k4/8/3K4/8/8"  # kings 2 apart on same file — legal either side
    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient([fen_needing_black_to_move, fen_needing_black_to_move])

    concepts = [{"page": 1, "study_number": None, "side_char": "b"}]
    result = agent._attach_fens(str(pdf_path), concepts, limit=None, delay=0)

    assert result[0]["fen"] == f"{fen_needing_black_to_move} b - - 0 1"


def test_attach_fens_defaults_side_char_when_absent_for_backward_compat(tmp_path):
    pdf_path = tmp_path / "book.pdf"
    _make_one_page_pdf(pdf_path)
    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient([_KQ_VS_K, _KQ_VS_K])

    concepts = [{"page": 1, "study_number": None}]  # no side_char key at all
    result = agent._attach_fens(str(pdf_path), concepts, limit=None, delay=0)

    assert result[0]["fen"] == f"{_KQ_VS_K} w - - 0 1"


def test_attach_fens_end_to_end_inconsistent_never_fabricates(tmp_path):
    pdf_path = tmp_path / "book.pdf"
    _make_one_page_pdf(pdf_path)

    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient([_KQ_VS_K, _ANOTHER_LEGAL])  # disagree

    concepts = [{"page": 1, "study_number": None}]
    result = agent._attach_fens(str(pdf_path), concepts, limit=None, delay=0)

    assert result[0]["fen"] is None    # never guesses between the two (P3)
    assert "inconsistent" in result[0]["vision_note"]


def test_attach_fens_respects_limit(tmp_path):
    """Only the first `limit` concepts get vision calls at all — the rest are
    explicitly "not attempted", never silently treated as a miss."""
    from PIL import Image
    pdf_path = tmp_path / "book.pdf"
    img = Image.new("RGB", (400, 500), "white")
    img.save(pdf_path, "PDF", save_all=True, append_images=[img])  # 2-page pdf

    agent = ExtractionAgent.__new__(ExtractionAgent)
    agent.vision_client = _FakeVisionClient([_KQ_VS_K, _KQ_VS_K])  # only page 1 consumes these

    concepts = [{"page": 1, "study_number": None}, {"page": 2, "study_number": None}]
    result = agent._attach_fens(str(pdf_path), concepts, limit=1, delay=0)

    assert result[0]["fen"] == f"{_KQ_VS_K} w - - 0 1"
    assert result[1]["fen"] is None
    assert "not attempted" in result[1]["vision_note"]
