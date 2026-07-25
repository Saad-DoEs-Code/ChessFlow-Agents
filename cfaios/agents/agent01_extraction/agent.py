"""
Agent 1 — Chief Knowledge Extraction Officer  (Truth layer)

Extract knowledge from source material into candidate nodes. Owns triage and board-to-FEN vision; produces staging packages only — never writes the graph.

Gate: 5-Gate Completion
P0 failure: Fabricated node presented as extracted (evidence-free knowledge).

This is a SCAFFOLD. The AgentSpec below is locked; the AIL steps raise
NotImplementedError until built. See README.md in this package for the full spec.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from cfaios.core.agent_base import AgentSpec, BaseAgent
from cfaios.core.events import Event, EventType
from cfaios.core.knowledge_api import Candidate, KnowledgeAPI
from cfaios.core.truth import EpistemicState
from cfaios.constitution.gates import Gate
from cfaios.infra.llm_google import GoogleClient


SPEC = AgentSpec(
    number=1,
    identity='Chief Knowledge Extraction Officer',
    layer='Truth',
    mandate='Extract knowledge from source material into candidate nodes. Owns triage and board-to-FEN vision; produces staging packages only — never writes the graph.',
    gate_code='5-Gate Completion',
    inherits_principles=['P3', 'P10'],
    inherits_patterns=[1, 6],
    reads=['source corpus (books)', 'Candidate Knowledge Queue (from A12, A15)'],
    writes=['Extraction Packages -> staging (candidates)'],
    validated_by=['Agent 3 (verification)'],
    p0_failure='Fabricated node presented as extracted (evidence-free knowledge).',
    deferred_build=['heterogeneous-corpus triage', 'synthesized-canonical de-duplication', '5-gate completion checks'],
)


# This corpus (Dover-style endgame-study collections) marks each study with a
# "<side> to play and <win/draw/mate/lose>" stipulation line. Empirically (see
# scripts/run_extraction.py probe notes) that anchor is far more reliable than the
# study-number heading, which PDF text extraction frequently mangles (letter-spaced
# "ENDING" headings, digits fused with diagram rank labels). We key study boundaries
# off the stipulation and treat the number/author as optional, best-effort fields —
# never fabricated when they can't be confidently parsed (P3: No Knowledge Without
# Evidence — an unparseable number must be reported as unknown, not guessed).
_STIPULATION_RE = re.compile(
    r"(White|Black)\s+to\s+play\s+and\s+(win|draw|mate|lose)", re.IGNORECASE)
# Agent 3's claim vocabulary is exactly {"win", "draw", "loss"}, always relative to
# the side to move — which is exactly what these stipulations already state ("<side>
# to play and <outcome>"). "mate" is a winning method, not a distinct outcome, so it
# maps to "win"; "lose" (rare — a losing side-to-move stipulation) maps to "loss".
_OUTCOME_TO_CLAIMED_RESULT = {"win": "win", "mate": "win", "draw": "draw", "lose": "loss"}
_HEADING_NUMBER_RE = re.compile(r"((?:\d\s*){1,3})E\s*N\s*D\s*I\s*N\s*G", re.IGNORECASE)
_AUTHOR_YEAR_RE = re.compile(r"([A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]+){0,3}),\s*(\d{4})")

# Below this many characters a stipulation match is more likely a fluke (running
# header, index entry) than a genuine study page.
_MIN_STUDY_CHARS = 120

# Board-diagram -> FEN vision (see GoogleClient.vision_to_fen). Rendering DPI and
# FEN-parsing regex match scripts/fen_spike.py, which proved this feasible (Phase
# 1.2: 3/5, 60%, "ACCEPTABLE" on this corpus with gemini-3.1-flash-lite) before
# this agent ever called it for real.
_VISION_RENDER_DPI = 120
_FEN_PLACEMENT_RE = re.compile(r"[rnbqkpRNBQKP1-8]{1,8}(?:/[rnbqkpRNBQKP1-8]{1,8}){7}")


def _parse_fen(raw: str) -> str | None:
    raw = raw.strip()
    m = _FEN_PLACEMENT_RE.search(raw)
    if m:
        return m.group(0)
    line = raw.splitlines()[0].strip() if raw else ""
    return line if line.count("/") == 7 else None


def _is_legal_placement(placement: str, side_char: str = "w") -> bool:
    """Finding, 2026-07-23: `chess.Board()` silently defaults to White-to-move
    when given a bare piece-placement string — it never raises, it just
    guesses. This corpus happens to be 100% "White to play" (verified against
    all 201 detected stipulations), so the old hardcoded " w " was harmless
    HERE, but it was a latent bug: a future corpus with "Black to play"
    studies would have every such position silently evaluated from the wrong
    side. `side_char` is now threaded through from the actual stipulation
    (see interpret()) instead of assumed."""
    import chess
    try:
        return chess.Board(f"{placement} {side_char} - - 0 1").is_valid()
    except ValueError:
        return False


def _render_page_png(page) -> bytes:
    import io
    buf = io.BytesIO()
    page.to_image(resolution=_VISION_RENDER_DPI).original.save(buf, format="PNG")
    return buf.getvalue()


def _resolve_two_attempts(first: str | None, first_note: str,
                          second: str | None, second_note: str) -> tuple[str | None, str]:
    """Pure decision logic, separated from the I/O (vision calls, PDF rendering)
    so it's testable without a real vision client or book — see
    _extract_fen_attempt for what produces each (placement_or_None, note) pair."""
    if first is not None and first == second:
        return first, "vision: hit (2/2 attempts agreed)"
    if first or second:
        return None, (f"vision: inconsistent across 2 attempts "
                      f"({first or first_note} vs {second or second_note}) — "
                      f"not committed without agreement")
    return None, f"vision: both attempts failed ({first_note}; {second_note})"


class ExtractionAgent(BaseAgent):
    spec = SPEC
    # TODO(build): define the concrete gate dimensions for 5-Gate Completion.
    gate = Gate(code='5-Gate Completion', title='5-Gate Completion', dimensions=())

    def __init__(self, api: KnowledgeAPI, vision_client: GoogleClient | None = None):
        super().__init__(api)
        #: not connected until a vision call actually happens (lazy, like GoogleClient
        #: itself) — extraction works fine with vision left off, no key required.
        self.vision_client = vision_client or GoogleClient()

    def observe(self, context: dict) -> dict:
        """Load the source book and return its raw per-page text.

        context: {"book_path": str | Path, "use_vision": bool = False,
        "vision_limit": int | None = None, "vision_delay": float = 1.0}. Text
        extraction always happens; vision (board-diagram -> FEN) is opt-in and
        happens later, in decide() — only for pages interpret() actually flags
        as studies, never speculatively on all 236 pages.
        """
        book_path = Path(context["book_path"])
        if not book_path.exists():
            raise FileNotFoundError(f"Agent 1: source book not found: {book_path}")

        import pdfplumber

        pages: list[dict] = []
        with pdfplumber.open(book_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages.append({"page": i, "text": page.extract_text() or ""})

        return {
            "book_path": str(book_path), "book_name": book_path.name, "pages": pages,
            "use_vision": bool(context.get("use_vision", False)),
            "vision_limit": context.get("vision_limit"),
            "vision_delay": context.get("vision_delay", 1.0),
        }

    def interpret(self, observation: dict) -> dict:
        """Find endgame-study page boundaries and package each as a structural
        concept candidate carrying its page-level source evidence (P3). This is
        purely mechanical text matching — no generation, so there is nothing here
        that could originate an unverified chess claim (P10)."""
        concepts = []
        for pg in observation["pages"]:
            text = pg["text"]
            if len(text) < _MIN_STUDY_CHARS:
                continue
            stip_m = _STIPULATION_RE.search(text)
            if not stip_m:
                continue

            heading_m = _HEADING_NUMBER_RE.search(text)
            study_number = None
            if heading_m:
                digits = re.sub(r"\s+", "", heading_m.group(1))
                # Reject obviously-mangled captures (fused diagram rank labels etc.)
                if digits.isdigit() and 1 <= int(digits) <= 300:
                    study_number = int(digits)

            author_m = _AUTHOR_YEAR_RE.search(text[stip_m.end():stip_m.end() + 200])

            concepts.append({
                "page": pg["page"],
                "study_number": study_number,
                "stipulation": f"{stip_m.group(1).title()} to play and {stip_m.group(2).lower()}",
                "claimed_result": _OUTCOME_TO_CLAIMED_RESULT[stip_m.group(2).lower()],
                # the side the stipulation actually names — never assumed (see
                # _is_legal_placement's docstring for why this matters)
                "side_char": stip_m.group(1)[0].lower(),
                "source_label": f"{author_m.group(1)}, {author_m.group(2)}" if author_m else None,
                "raw_text": text.strip(),
            })

        return {"book_name": observation["book_name"], "book_path": observation["book_path"],
                "concepts": concepts, "use_vision": observation["use_vision"],
                "vision_limit": observation["vision_limit"], "vision_delay": observation["vision_delay"]}

    def decide(self, interpretation: dict) -> dict:
        """Every concept interpret() produced already passed the study-page
        filter; decide() is also where the (opt-in) board-diagram -> FEN vision
        retrieval happens — P10 puts retrieval before any generation, and this
        agent never generates chess content, so there's nothing downstream of
        this that could originate an unverified claim. Vision failures (API
        error, illegal FEN) degrade to `fen: None`, never a guessed position
        (P3) — Agent 3 correctly reports those as INAPPLICABLE later."""
        concepts = interpretation["concepts"]
        if interpretation["use_vision"] and concepts:
            concepts = self._attach_fens(
                interpretation["book_path"], concepts,
                interpretation["vision_limit"], interpretation["vision_delay"])
        return {"book_name": interpretation["book_name"], "book_path": interpretation["book_path"],
                "candidates": concepts}

    def _extract_fen_attempt(self, png: bytes, side_char: str = "w") -> tuple[str | None, str]:
        """One vision call + parse + legality check, validated against the
        side the study's own stipulation names. NOT the full acceptance
        decision — see _attach_fens for why a single legal-looking attempt is
        not treated as sufficient."""
        raw = self.vision_client.vision_to_fen(png)
        placement = _parse_fen(raw)
        if placement is None:
            return None, f"unparseable response {raw[:60]!r}"
        if not _is_legal_placement(placement, side_char):
            return None, f"illegal position {placement!r}"
        return placement, "ok"

    def _attach_fens(self, book_path: str, concepts: list[dict],
                      limit: int | None, delay: float) -> list[dict]:
        """Two independent vision calls per page, accepted ONLY on exact
        agreement. Discovered empirically (not theoretically): a single
        "legal FEN" is not evidence of a CORRECT FEN — repeated calls on the
        identical image can each return a different, individually-legal
        position (verified directly: 3 calls on the same page produced 3
        different piece placements on the contested rank, one even
        hallucinating an extra pawn). Legality is necessary, not sufficient.
        Committing on single-call legality would let Agent 3 verify a
        position that isn't the one in the book — evidence-free knowledge by
        a different name (P0: Fabricated node presented as extracted). Two-
        call exact agreement is cheap insurance against that: an inconsistent
        page is reported, not guessed at (P3)."""
        import pdfplumber

        targets = concepts if limit is None else concepts[:limit]
        fen_by_page: dict[int, str | None] = {}
        note_by_page: dict[int, str] = {}
        with pdfplumber.open(book_path) as pdf:
            for i, c in enumerate(targets):
                page_num = c["page"]
                side_char = c.get("side_char", "w")
                try:
                    png = _render_page_png(pdf.pages[page_num - 1])
                    first, first_note = self._extract_fen_attempt(png, side_char)
                    if delay:
                        time.sleep(delay)
                    second, second_note = self._extract_fen_attempt(png, side_char)
                    placement, note_by_page[page_num] = _resolve_two_attempts(
                        first, first_note, second, second_note)
                    # Store the FULL fen (correct side-to-move included) — never
                    # let a downstream reader silently default to White again.
                    fen_by_page[page_num] = f"{placement} {side_char} - - 0 1" if placement else None
                except Exception as exc:  # a bad page/API error must not kill the run
                    fen_by_page[page_num] = None
                    note_by_page[page_num] = f"vision: error {exc}"
                if delay and i < len(targets) - 1:
                    time.sleep(delay)

        for c in concepts:
            c["fen"] = fen_by_page.get(c["page"])
            c["vision_note"] = note_by_page.get(c["page"], "vision: not attempted (limit/disabled)")
        return concepts

    def act(self, decision: dict) -> list[Event]:
        """Stage each concept as a Candidate — never write the graph (P4) — and
        return one CANDIDATE_STAGED event per staged candidate for provenance.
        run_cycle() is responsible for actually emitting these via self.api.emit()."""
        events: list[Event] = []
        for c in decision["candidates"]:
            label = f"Endgame study #{c['study_number']}" if c["study_number"] else "Endgame study"
            concept_name = f"{label} (p.{c['page']}, {decision['book_name']})"

            candidate = Candidate(
                source_agent=self.spec.number,
                concept=concept_name,
                payload={
                    "study_number": c["study_number"],
                    "stipulation": c["stipulation"],
                    "claimed_result": c["claimed_result"],
                    "source_label": c["source_label"],
                    "raw_text": c["raw_text"],
                    "fen": c.get("fen"),
                    "vision_note": c.get("vision_note"),
                },
                evidence={
                    "book": decision["book_name"],
                    "book_path": decision["book_path"],
                    "page": c["page"],
                },
                epistemic=EpistemicState.PLAUSIBLE,
            )
            staging_id = self.api.stage_candidate(candidate)
            events.append(Event(
                type=EventType.CANDIDATE_STAGED,
                actor_agent=self.spec.number,
                subject_id=staging_id,
                payload={"concept": concept_name, "page": c["page"]},
            ))
        return events
