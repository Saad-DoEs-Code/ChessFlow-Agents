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
formatting, not EPUB/other layouts), and mapping the `stipulation` string to Agent
3's `claimed_result` vocabulary (`"win"`/`"draw"`/`"loss"` — the stipulation regex
also matches `"mate"`/`"lose"`, not yet normalized) — needed before Step 2.4 can run
the real 201 candidates through Agent 3 end-to-end.

---
*Scaffold generated from `cfaios/agents_spec.py`. Fill in `agent.py`; keep the SPEC in sync
with the canonical constitution document.*
