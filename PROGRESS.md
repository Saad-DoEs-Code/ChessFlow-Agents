# CFAIOS Build Progress

Tracks actual status against [`ROADMAP.md`](ROADMAP.md), step by step. Re-verified
against the live repo on 2026-07-18 (all commands below were actually run, not
assumed). Update this file at the end of each roadmap step.

Legend: ✅ done & verified · ⚠️ partial / skipped intentionally · ⬜ not started

---

## Phase 0 — Make it runnable (infrastructure)

| Step | Status | Notes |
|---|---|---|
| 0.1 Local environment | ✅ | `.venv` set up, `pip install -e ".[dev]"` done. `bootstrap_check.py` lists all 18 agents; `pytest` 7/7 green. |
| 0.2 Stand up the stores (Docker) | ⬜ | No `docker-compose.yml`. Neo4j / pgvector not running. Skipped deliberately — see "Deviations from strict order" below. |
| 0.3 Bind the infra adapters | ⚠️ | **Bound for real:** `llm_google.py` (Gemini), `llm_groq.py` (Groq, added outside the original roadmap), `chess_engine.py` (`StockfishEngine`, real UCI binary confirmed working). **Still abstract stubs:** `neo4j_store.py`, `vector_store.py`, `llm_anthropic.py`. No `scripts/infra_smoke.py` yet. |

## Phase 1 — Corpus reality check

| Step | Status | Notes |
|---|---|---|
| 1.1 Corpus probe | ✅ (with a caveat) | `scripts/corpus_probe.py` classified the one book (`200 Brilliant Endgames (gnv64).pdf`, 236pp) as **CLEAN** (0.04% gibberish). **Caveat on record:** the heuristic misses letter-substitution OCR noise ("Alekhhw" for Alekhine, etc.) visible in the sample paragraphs — don't fully trust the CLEAN label without spot-checking. |
| 1.2 Board-diagram → FEN spike | ✅ resolved 2026-07-18 | Root cause of the earlier 0/5 found: `gemini-2.0-flash`'s free tier is `limit: 0` for this Google project specifically (confirmed by testing `gemini-2.0-flash-lite` too — also `limit: 0`; `gemini-2.5-flash-lite` — `404`, retired for new users). `gemini-3.1-flash-lite` has real free quota and works. Groq was checked as an alternative first (`client.models.list()`) — no vision-capable model available on this key (text/audio only: Llama, GPT-OSS, Whisper, Orpheus). Real 5-sample run against `gemini-3.1-flash-lite`: **3/5 (60%) hit rate — "ACCEPTABLE"**. `config/settings.py`, `.env`, `.env.example` default `google_model` updated to `gemini-3.1-flash-lite`. |
| 1.3 Lock the extraction strategy | ⬜ | Never formally done — Agent 1's README was not updated with a documented per-file-type strategy. |

## Phase 2 — The Truth vertical slice (Agents 1 → 3 → 2)

| Step | Status | Notes |
|---|---|---|
| 2.1 Agent 1 — extract one book → candidates | ✅ | `cfaios/agents/agent01_extraction/agent.py` implemented. Detects study pages via the `"<side> to play and <win/draw/mate/lose>"` stipulation line (proved more reliable than the "ENDING" heading: 201/236 hits vs. 109). `scripts/run_extraction.py` staged **201 candidates**, each with page-number evidence, **zero graph-writer calls**. 1 known false positive (the book's own back-cover blurb happens to contain the stipulation phrase) — effectively 200/200 real studies caught. |
| 2.2 Agent 3 — verify claims + Evidence Ledger | ✅ | `cfaios/agents/agent03_accuracy/agent.py` implements the Verification Router (Pattern #3): legality (free) → Syzygy tablebase (not yet exercised — no tablebase files) → Stockfish shallow (depth 12) → deep (depth 20) if ambiguous. `LocalObjectStore` (new, in `cfaios/infra/object_store.py`) is a real SHA-256 content-addressed filesystem ledger. `scripts/run_verification.py` proved all 5 branches with a **real Stockfish binary**: non-objective→`INAPPLICABLE`, illegal FEN→`INCONCLUSIVE`, true "win" claim→`CONFIRMED` (+5.38 pawns), the **same position falsely claimed "draw"→`REFUTED`** (+5.42 pawns — the P0 failure mode, False-Confirmed, actively caught), bare-kings "draw"→`CONFIRMED` (-0.16 pawns). Every verdict's evidence round-trips from disk. |
| 2.3 Agent 2 — commit (single-writer) | ✅ | Real Neo4j (0.2) wasn't available (no Docker on this machine), so by explicit user choice this binds a **persistent local substitute** instead: `cfaios/infra/knowledge_api_impl.py` (`LocalKnowledgeAPI`) — JSON-backed node store + append-only `events.jsonl` (P6) + a new `LocalVectorStore` (brute-force cosine similarity over a placeholder hashing-trick embedding, since no embedding API is reliably available either) + the `LocalObjectStore` from Step 2.2. `cfaios/agents/agent02_integrity/agent.py` implemented: gates strictly on Agent 3's verdict (only `CONFIRMED` commits), `commit()` and `emit()` independently assert `_actor == AGENT_KNOWLEDGE_WRITER` and raise `SingleWriterViolation` otherwise. `tests/test_single_writer.py` (4 new tests, 11/11 total) proves this against the real binding, including that a committed node survives a fresh `LocalKnowledgeAPI` instance pointed at the same directory (genuinely persistent, not in-memory-only). `scripts/run_commit.py` ran a true claim and a false claim through Agent 3 → Agent 2 for real: the true one committed (`node-3fbb2bf309f9`, real Stockfish evidence attached), the false one was correctly refused (never committed), and a spoofed Agent-7 commit attempt raised `SingleWriterViolation`. Inspected `.cfaios_data/graph/nodes.json` and `events.jsonl` directly — real files, real audit trail. **Swappable later:** replacing `LocalKnowledgeAPI` with a real Neo4j-backed implementation requires no agent code changes — `KnowledgeAPI` is exactly the seam designed for that. |
| 2.4 Truth slice end-to-end | ✅ | Real book → 5 real committed nodes with fetchable Evidence Ledger provenance. See below. |

## Phase 3 — Prove the thesis (one verified lesson)

| Step | Status | Notes |
|---|---|---|
| 3.1 Minimal lesson shaping | ✅ | `cfaios/agents/agent05_experience/agent.py` implemented: given a topic, `semantic_search`s the real graph and orders hits into a flat blueprint of `{node_id, concept}` references — never copies content. 13-slot ontology / Narrative Flow Model left as an explicit TODO, per the roadmap's own instruction. No `EventType` currently models "blueprint produced," so `act()` emits nothing — noted honestly rather than inventing a new event type mid-step. |
| 3.2 Minimal coach grounded in truth (P10) | ✅ | `cfaios/agents/agent07_coaching/agent.py` implemented: retrieves each blueprint node via `get_node` (real retrieval, not copied from the blueprint), then generates **one explanation per node**, each explicitly grounded in that node's FEN/claimed-result/verdict/source-excerpt — so "every claim maps to a node ID" holds by construction, not by scanning free text after the fact. **Deviation:** ROADMAP names `llm_anthropic.py`, but `CFAIOS_ANTHROPIC_API_KEY` is still an unfilled placeholder — used the already-proven `llm_groq.py` instead (noted in-code, swappable). Emits a real `COACHING_EVENT` per section. |
| 3.3 Provenance proof | ✅ | `scripts/run_lesson.py` (new), `--show-provenance` flag. |

**Real run** (`python scripts/run_lesson.py --show-provenance`, topic `"chess endgame study"`, k=5):
5 verified nodes retrieved → 5 generated sections → 5 `COACHING_EVENT`s in the real
append-only log. Every section's provenance block fetched real bytes back from the
Evidence Ledger (287-303 bytes each, all confirmed verdicts). **Notably**, for the
page-6 false-positive node (the book's back-cover blurb — see Step 2.1/2.4 notes),
the model correctly said *"the source text doesn't provide a clear explanation of the
specific moves"* rather than inventing a plausible-sounding solution — the grounding
constraint held exactly where it mattered most. This is ROADMAP.md's stated
**"proof of life for the entire system"**: a real book → real verified nodes → a real
generated lesson → every sentence traceable to a specific node and a fetchable,
real Evidence Ledger entry.

**Known non-determinism, not a bug:** the FEN committed for the page-6 node differs
across the several separate demo/dry runs performed this session (each called Gemini
vision fresh) — expected LLM sampling variance in the *extraction* step. Once
committed, a node's data is fixed (P6, append-only) regardless of what a later,
separate extraction run might produce for the same page.

## Phase 4 — Harden the spine

| Step | Status | Notes |
|---|---|---|
| 4.1 Persist + replay the event log | ✅ | The log already persisted (`events.jsonl`, since 2.3), but couldn't rebuild the graph — `KNOWLEDGE_COMMITTED` payloads lacked node data. Fixed: Agent 2's commit events now carry the **full node record** (payload + verdict + candidate_id); `rebuild_nodes_from_events()` (in `knowledge_api_impl.py`) replays the log into a fresh projection, recovering `source_agent` by joining commits back to their `CANDIDATE_STAGED` events — the log joining to itself. `scripts/replay_events.py` compares replay vs. `nodes.json` field-by-field; `verdict_to_dict/from_dict` moved into `core/truth.py` as shared helpers; `read_events()` added to the `KnowledgeAPI` contract (a universal read, default `[]`). **Proven live:** a fresh commit through the evented path replays exactly; the 8 pre-schema nodes are honestly flagged "legacy, not replayable" rather than patched over. 3 new tests, incl. one proving un-evented staging is reported as provenance loss, never guessed at. |
| 4.2 AIL loop driver + minimal Agent 16 | ✅ | `agent16_orchestrator/agent.py` implemented: runs a declared list of `PipelineStep`s (name + agent key + mechanical context-builder/after-hook glue owned by the caller) through each agent's `run_cycle`, in order. Never interprets domain data ("determines when work executes, never what work means"). On step failure: **halts all remaining steps** (Safe Halt) and emits `ESCALATION_RAISED` — routes failures, never resolves them. `scripts/run_orchestrated_slice.py` runs the truth slice under Agent 16 (with `--every/--times` as a minimal scheduler; Institutional Clock deferred). **Proven live both ways:** clean run (extract→verify→commit, all ok) and failure run (missing book → extract FAILED → verify/commit skipped → 1 escalation raised and persisted to the log). |
| 4.3 Turn one gate real | ✅ | Agent 7's CQI is the system's first real gate: integrity dims `grounding` and `verified_only` (threshold 1.0 — one ungrounded or unverified section blocks the whole lesson, regardless of quality) + quality dims `explanation_generated` (w2) and `explanation_length` (w1). `score_lesson()` is pure (testable without an LLM); `run_lesson.py` now evaluates the gate and **withholds the lesson entirely on failure** (exit 1; `--ignore-gate` for debugging only). 5 new tests including: integrity blocks even when quality is perfect, and an empty lesson fails rather than vacuously passing 0/0. **Live lesson passed 4/4 dims, quality 1.00, Phase A.** |
| 4.4 Agent 13 instrumentation-first | ✅ | `agent13_analytics/agent.py` implemented minimal: pure aggregation over `api.read_events()` — every reported number re-derivable by filtering the log (Data Traceability #15). Produces **Findings, never Recommendations** (Observation-Decision Separation #13). Rates report `None`, never a fabricated number, when the denominator is 0 (P16). `scripts/run_analytics.py` over the real log: 1,630 events — 804 staged / 806 verdicts (9 confirmed, 5 refuted, 790 inapplicable, 2 inconclusive) / 9 committed (commit rate of confirmed = 1.0) / 10 coaching sections / 1 escalation (the deliberate 4.2 failure test). The funnel numbers match every earlier run's printed output — the log and reality agree. |

Suite after Phase 4: **19 tests passing** (11 + 3 replay + 5 CQI gate), bootstrap clean.

## Phase 5+ — Expand agent by agent

| Agent | Status | Notes |
|---|---|---|
| 6 Assessment | ✅ minimal (2026-07-18) | Diagnostic questions **rendered from verified data, no LLM** (Pattern #4): question = committed FEN + stipulation, answer key = the Agent-3-CONFIRMED `claimed_result` — a hallucinated question/key is structurally impossible. Only confirmed-verdict nodes are assessable; others excluded and reported. Scoring emits `COMPETENCY_UPDATED` events; the **Competency Graph is a projection of those events** (`competency_projection()` rebuilds it from the log — same event-sourcing discipline as 4.1). P0 guard: unanswered questions reported, never scored; accuracy is `None`, never fabricated, at 0 attempts. `scripts/run_assessment.py` proven live: 5 questions from real nodes, demo learner 1 right / 1 wrong / 3 unanswered, graph rebuilt from log. |
| 8 Content | ✅ minimal (2026-07-18) | Lesson → video script, one scene per lesson section, S0 transformation only (P12 — the LLM prompt forbids adding chess content). **Refuses ungated input** (`ValueError` if the lesson didn't pass CQI — Pattern #2 enforced in code, not convention). PQI gate real: integrity dims `provenance_intact` + `verified_source` at 1.0, quality dims for narration/coverage. Full semantic Claim Faithfulness Score deferred (the faithfulness check today is structural provenance, not NLP comparison). |
| 10 Visual | ✅ minimal (2026-07-18) | Thumbnail **spec** rendered 100% from committed data — no LLM anywhere in the agent, which is exactly its locked inheritance (Patterns #4/#5): board = the node's FEN verbatim, title from a fixed stipulation-keyed table, "Engine-verified" badge backed by the ledger ref riding on the spec. P0 (false visual claim) structurally impossible. Refuses scripts that didn't pass PQI. Actual image rendering deferred (emits the spec an image pipeline consumes). |
| 4, 9, 11, 12, 14, 15, 17, 18 | ⬜ | Still `NotImplementedError` scaffolds. |

**Live chain proven** (`scripts/run_content.py`): blueprint → CQI-gated lesson → PQI-gated
script → thumbnail spec, provenance intact end to end — the final thumbnail spec alone
still names its node_id, evidence_ref, and graph version. And Agent 13's telemetry picked
up the new `competency_updated` events with **zero code changes** — pure log aggregation.

Suite after this slice: **26 tests passing**.

---

## Deviations from strict roadmap order

The roadmap says "do them in order." We didn't, on purpose, by explicit user choice:

- **Skipped 0.2 (Docker stores) and jumped to 2.1/2.2.** Rationale at the time: Agent 1
  only stages candidates (never touches Neo4j) and Agent 3 only needs the chess engine +
  a local evidence store — neither actually needs Neo4j/pgvector running. This holds up:
  both steps completed and verified without Docker. **It will stop holding at Step 2.3**,
  which explicitly requires a real `KnowledgeAPI` over Neo4j + vector + object stores.
- **1.2 (FEN spike) never got a real result** — blocked by Google API quota, not retried
  with Groq (Groq's free tier is text-only for the model currently configured;
  vision would need a different Groq model or fixing Google's quota).
- **1.3 (lock extraction strategy) never formally written up** — the strategy that
  emerged (stipulation-line anchoring) lives in code comments in `agent01_extraction/agent.py`
  and in agent memory, not in the README as the roadmap prescribes.

None of this blocked 2.1/2.2. For 2.3, Docker turned out to not be installed on this
machine at all (checked directly — no `docker` command in Bash or PowerShell, no Docker
Desktop at its default path); by explicit user choice we proceeded with a persistent
local substitute rather than installing Docker Desktop (which typically needs WSL2/
Hyper-V + admin rights + a reboot on Windows). **Real Neo4j is still not bound anywhere**
— `cfaios/infra/neo4j_store.py`'s `connect()` still raises `NotImplementedError`.

---

## Verification commands (all green as of 2026-07-18)

```bash
PYTHONPATH=. python scripts/bootstrap_check.py   # all 18 agents import
PYTHONPATH=. pytest -q                            # 11 passed
PYTHONPATH=. python scripts/run_extraction.py     # 201 candidates staged, 0 graph writes
PYTHONPATH=. python scripts/run_verification.py   # 5/5 verdicts correct, incl. catching a false claim
PYTHONPATH=. python scripts/run_commit.py         # true claim committed, false claim refused, spoofed commit raises
PYTHONPATH=. python scripts/run_truth_slice.py     # 201 extracted, 5 committed, real Evidence Ledger provenance
```

---

## Vision wired into Agent 1 (2026-07-18) — no longer just a spike

`cfaios/agents/agent01_extraction/agent.py`: `decide()` now optionally (opt-in via
`context["use_vision"]`) renders each detected study page to PNG, calls
`GoogleClient.vision_to_fen`, validates the result with python-chess, and attaches
`fen` (+ a `vision_note` explaining hit/miss/error) to the candidate payload. Never
guesses a position on failure (P3) — degrades to `fen: None` and keeps going; one bad
page/API error never aborts the run. `scripts/run_extraction.py` got `--vision`,
`--vision-limit` (default 10, protects against silently burning the full 201-page
quota), and `--vision-delay` flags.

**Real test, 8 real study pages, `--vision --vision-limit 8`: 4/8 hits (50%)** —
consistent with the 60% spike number within small-sample noise. Regression-checked:
extraction without `--vision` is unchanged (still 201 candidates, 0 graph writes).
`agents_spec.py` and the README were updated to move "board-diagram -> FEN vision" out
of Agent 1's deferred-build list (by hand, not via `generate_agents.py`, which would
have wiped this implementation) — `synthesized-canonical de-duplication` and
`5-gate completion checks` remain deferred, as does mapping the `stipulation` string to
Agent 3's `"win"/"draw"/"loss"` vocabulary (the regex also matches `"mate"`/`"lose"`,
not yet normalized — needed before Step 2.4).

The full 201-page vision run (`--vision --vision-limit 0`) hasn't been done yet — at
~1-2s/call with the delay, that's several minutes and real API quota. Worth doing
deliberately, not as a side effect.

## Step 2.4 done 2026-07-18 — the truth slice is real

Both gaps closed: `agent01_extraction/agent.py` now maps `stipulation` -> `claimed_result`
(`win`/`mate`->`"win"`, `draw`->`"draw"`, `lose`->`"loss"` — Agent 3's exact vocabulary),
and `scripts/run_truth_slice.py` (new) chains Agents 1 → 3 → 2 on the real book in one
command, against the real persistent `LocalKnowledgeAPI` from Step 2.3.

**Real result (`--vision-limit 20`, the default):**

| | |
|---|---|
| candidates extracted | 201 |
| vision attempted | 20 |
| FEN hits | 9 (45%) |
| verdicts | 192 inapplicable · 2 refuted · 5 confirmed · 2 inconclusive |
| **committed to the graph** | **5** |
| skipped (not committed) | 196 |

Every committed node carries a real Stockfish-backed verdict and a fetchable Evidence
Ledger entry (spot-checked all 5 — real bytes, real evaluations, e.g. `+3.89 -> win`,
`-0.07 -> draw`). The 2 `refuted` claims were correctly never committed — real false
claims caught and rejected, not hidden. Persistence confirmed: `.cfaios_data/graph/nodes.json`
has 8 nodes total (5 from this run + 3 from earlier smaller demo/dry runs, all in the
same canonical local graph, correctly cumulative across runs — `local-v8`).

**One nuance surfaced by running on real data:** one committed node (`p.6`) is the same
page flagged back in Step 2.1 as a false positive (the book's own back-cover blurb, not
a numbered study). It evidently also contains a real board diagram vision read correctly,
and the verdict itself is honestly correct — Stockfish genuinely confirms that position.
The caveat is only that Agent 1's page-level detection isn't perfectly precise about
*what* it's extracting, not that the truth-verification chain is wrong.

The full 201-page vision pass (`--vision-limit 0`) still hasn't been run — the 20-page
default was a deliberate cost/time tradeoff, not a limitation of the pipeline itself.

**This is ROADMAP.md's stated moment the architecture's core claim becomes real**:
a real book → real candidates → real verified verdicts → real committed graph nodes,
with provenance you can fetch back. Phase 2 (the Truth vertical slice) is complete.

---

## Phase 3 complete — the roadmap's stated proof of life is real

`scripts/run_lesson.py --show-provenance` produces a lesson where every section traces
to a specific committed node and a fetchable Evidence Ledger entry. Per ROADMAP.md's own
"Definition of 'the pipeline works'": this is that day. Everything after this is scale
and breadth on a proven foundation, not proving the core claim itself.

## Phase 4 complete (2026-07-18) — the spine is hardened

Event log proven authoritative (replayable), pipeline runs under a real orchestrator
with Safe Halt + escalation, the first gate blocks for real, and telemetry over raw
events is live. New scripts: `replay_events.py`, `run_orchestrated_slice.py`,
`run_analytics.py`.

## Phase 5 opened (2026-07-18): Agents 6, 8, 10 built minimal and proven live

The learning loop closed (extract → verify → commit → teach → **assess**) and the
content chain runs gated end to end (lesson → script → thumbnail spec, provenance
surviving every hop). New scripts: `run_assessment.py`, `run_content.py`.

## Next step: continue Phase 5

Remaining per ROADMAP.md's order: **Distribution (9, 11)** — platform fragments +
lifecycle, testing P12/P14 — then Community (12), Intelligence (14, 15), Governance
(17, 18). Agent 4 (Learning Science) is also still a scaffold and would deepen
Agents 5/6 (Learning DNA, cognitive-load model) when it comes up.

Also still open from earlier phases (unchanged): the full 201-page vision pass,
Step 1.3's README write-up, real Neo4j (needs Docker or a native install), Syzygy
tablebases, binding `llm_anthropic.py` (needs a real key), and the corpus-probe
gibberish heuristic's blindness to letter-substitution OCR noise.
