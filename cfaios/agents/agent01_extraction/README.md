# Agent 1 — Chief Knowledge Extraction Officer

**Layer:** Truth  ·  **Gate:** 5-Gate Completion

## Mandate
Extract knowledge from source material into candidate nodes. Owns triage and board-to-FEN vision; produces staging packages only — never writes the graph.

## Constitutional inheritance
- **Principles:** P3, P10
- **Patterns:** #1, #6

## Reads
- source corpus (books)
- Candidate Knowledge Queue (from A12, A15)

## Writes
- Extraction Packages -> staging (candidates)

## Validated by
- Agent 3 (verification)

## P0 (catastrophic) failure mode
> Fabricated node presented as extracted (evidence-free knowledge).

## Deferred build items (owned by this agent)
- heterogeneous-corpus triage
- synthesized-canonical de-duplication
- 5-gate completion checks

## Status (updated 2026-07-18, reality not hope — see PROGRESS.md)
Implemented against one real corpus: `data/books/200 Brilliant Endgames (gnv64).pdf`
(236pp, OCR'd PDF). Study-page detection keys off the `"<side> to play and
<win/draw/mate/lose>"` stipulation line (proved far more reliable than the
letter-spaced "ENDING" heading OCR frequently mangles). 201 candidates staged from
201 detected study pages (1 known false positive: the book's own back-cover blurb).

Board-diagram -> FEN vision is wired for real (opt-in via `context["use_vision"]`),
not just spiked: renders the study's page to PNG, calls `GoogleClient.vision_to_fen`
(`gemini-3.1-flash-lite` — earlier default `gemini-2.0-flash` had zero free-tier
quota on this project), validates the result with python-chess, and attaches the FEN
to the candidate payload (or `None` + a `vision_note` explaining why, never a guessed
position — P3). Real measured hit rate on this corpus: **60%** (3/5 sample). Vision
failures degrade gracefully per-page; one bad call never aborts the whole extraction.

**Not yet done:** heterogeneous-corpus triage (this is tuned to one book's exact
formatting, not EPUB/other layouts).

## Finding (2026-07-23): legality is not correctness — fixed with a consistency check

Running the truth slice at real scale (40 pages) surfaced a real problem: the
book's actual REFUTED rate looked suspiciously high (10 of 17 vision hits). Traced
one case (p.12) back to its evidence: Stockfish scored the extracted position at
**-5.70**, decisively contradicting the book's claimed draw. Rendered the actual
page and called Gemini vision **three times on the identical image** — it returned
**three different piece placements** on the contested rank each time, one attempt
even hallucinating an extra pawn. Every one of the three was independently a
*legal* chess position. **A single legal FEN was never evidence of a correct FEN**
— python-chess's legality check has no way to know whether a position matches the
diagram it was supposedly read from, only whether it's a coherent chess position at
all. That gap had been invisible until real scale (and a page-by-page audit) exposed
it: the earlier 45-60% "hit rate" numbers from Phase 1.2 only ever measured
legality, never diagram-fidelity.

Fixed in `_attach_fens`: every page now gets **two independent vision calls**,
accepted only on **exact placement agreement**. Disagreement — which is common,
not rare — degrades to `fen: None` with a `vision: inconsistent across 2 attempts`
note, exactly like any other extraction failure (P3: report unknown, never guess).
This roughly doubles vision API cost and latency per page but directly targets the
P0 failure mode (fabricated/misattributed extraction presented as real). Corrected,
honest yield on this corpus: roughly 3-9% net two-call-agreement hit rate across
several real runs — see PROGRESS.md for the exact before/after numbers.

## Second finding, same audit (2026-07-23): side-to-move was silently assumed

`chess.Board()` defaults to White-to-move when given a bare piece-placement
string — no error, just a guess. Every extracted FEN was stored and validated
this way. Checked directly whether that's actually safe for this book: swept all
201 detected stipulations, and **100% say "White to play"** — so the assumption
was harmless here, but it was a latent bug for any future corpus with "Black to
play" studies (a real, common composition convention this book just doesn't use).
**Fixed**: `interpret()` now captures the stipulation's actual side (`side_char`),
and `_attach_fens` validates against it and stores the FULL fen (with the correct
side field) instead of a bare placement. Nothing downstream needed to change —
`chess.Board()` already respects an explicit side field correctly; the bug was
only ever in what Agent 1 handed it.

---
*Scaffold generated from `cfaios/agents_spec.py`. Fill in `agent.py`; keep the SPEC in sync
with the canonical constitution document.*
