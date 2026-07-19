# CFAIOS Build Roadmap

A step-by-step plan for turning the skeleton into a working pipeline, sized for
**one focused Claude Code session per step**. Each step has a **Goal**, a **Prompt**
you can paste (adapt freely), the **Files** it touches, and a **Done when** acceptance
test. Do them in order — later steps assume earlier ones work.

**Golden rule:** depth over breadth. Build 3 agents that work on real data before you
touch the other 15. The constitution was designed to scale *down* (Phase-A before
Phase-B, bootstrap patterns) — lean on that.

---

## How to prompt Claude Code on this repo

- **Always anchor it to the constitution.** Start prompts with: *"Read
  `cfaios/agents/agentNN_x/README.md` and the principles it inherits in
  `cfaios/constitution/principles.py` before writing code."* The agent READMEs carry
  the locked spec; the constitution carries the rules the code must not break.
- **State the acceptance test up front.** Tell it the "Done when" from this file so it
  builds toward a verifiable target, not a vibe.
- **One agent / one slice per session.** Don't ask it to "build the pipeline." Ask it
  to make Agent 1 extract one book. Small scope = reviewable diffs.
- **Guard the invariants explicitly.** Remind it: *"agents write ONLY by emitting
  events / staging candidates through the KnowledgeAPI — never touch the stores
  directly (P4)."* This is the rule most likely to get violated by convenience.
- **Keep the spec in sync.** If a step changes an agent's locked metadata, edit
  `cfaios/agents_spec.py` and re-run `scripts/generate_agents.py` — don't hand-edit
  generated files.
- **Let reality edit the spec.** If real data contradicts a design decision, that's a
  finding, not a failure. Note it, adjust the spec, keep going.

---

## Phase 0 — Make it runnable (infrastructure)

### Step 0.1 — Local environment
- **Goal:** package installs, bootstrap check passes on your machine.
- **Prompt:** "Set up a virtualenv, `pip install -e .[dev]`, and run
  `scripts/bootstrap_check.py` and `pytest`. Fix any environment issues."
- **Files:** `pyproject.toml`, none new.
- **Done when:** `bootstrap_check.py` prints all 18 agents and `pytest` is green locally.

### Step 0.2 — Stand up the stores (Docker)
- **Goal:** Neo4j + a vector store (pgvector) + Stockfish actually running.
- **Prompt:** "Create a `docker-compose.yml` with Neo4j 5, Postgres+pgvector, and a
  Stockfish image (or document installing the binary). Add a `Makefile` with `up`,
  `down`, `logs`. Update `.env` from `.env.example` with the compose credentials."
- **Files:** `docker-compose.yml`, `Makefile`, `.env` (new, gitignored).
- **Done when:** `make up` brings all services healthy; you can open Neo4j Browser.

### Step 0.3 — Bind the infra adapters
- **Goal:** the `infra/` stubs connect to the running services.
- **Prompt:** "Implement `connect()` in `cfaios/infra/neo4j_store.py`, and the
  `VectorStore`/`ObjectStore`/`ChessEngine` interfaces, against the docker services.
  Add `scripts/infra_smoke.py` that connects to each and prints OK."
- **Files:** `cfaios/infra/*.py`, `scripts/infra_smoke.py`.
- **Done when:** `python scripts/infra_smoke.py` connects to Neo4j, the vector store,
  and Stockfish (a legal-move check) with no errors.

---

## Phase 1 — Corpus reality check (DE-RISK THE RISKIEST ASSUMPTION)

> This phase exists because the whole architecture rests on one unproven assumption:
> *you can get clean, verified, structured knowledge out of your actual books.* Your
> corpus is heterogeneous (clean EPUB, OCR-noisy PDFs, mojibake PDFs, diagrams-as-
> images). Prove extraction is feasible **before** building Agent 1 for real.

### Step 1.1 — See what the corpus actually yields
- **Goal:** know, per book, what raw extraction produces.
- **Prompt:** "Write `scripts/corpus_probe.py` that runs each book through text
  extraction (pdfplumber / ebooklib for EPUB) and reports, per file: char count,
  gibberish ratio, and 3 sample paragraphs. Don't build Agent 1 yet — just show me
  what we're working with."
- **Files:** `scripts/corpus_probe.py`, `data/books/` (your PDFs/EPUB).
- **Done when:** you can categorize each book as clean / OCR-noisy / unusable, with
  evidence. **This finding shapes Agent 1's whole design.**

### Step 1.2 — Board-diagram → FEN spike
- **Goal:** find out if vision reliably recovers positions from your diagrams.
- **Prompt:** "Write `scripts/fen_spike.py` that extracts 5 board-diagram images from a
  PDF and sends each to Gemini via `cfaios/infra/llm_google.py` asking for a FEN. Print
  the FEN and validate legality with python-chess. Report the hit rate."
- **Files:** `scripts/fen_spike.py`, `cfaios/infra/llm_google.py`.
- **Done when:** you have a real accuracy number for diagram→FEN. If it's low, Agent 1's
  vision approach needs rethinking now, not after you've built on it.

### Step 1.3 — Lock the extraction strategy
- **Goal:** one decision — how Agent 1 handles each corpus type.
- **Prompt:** "Given the corpus_probe and fen_spike results, propose Agent 1's
  extraction strategy per file type. Update `cfaios/agents/agent01_extraction/README.md`
  with the decision."
- **Done when:** Agent 1's README reflects reality, not hope.

---

## Phase 2 — The Truth vertical slice (Agents 1 → 3 → 2)

> The smallest end-to-end proof that verified knowledge can enter the graph.

### Step 2.1 — Agent 1: extract one book → candidates
- **Goal:** one book becomes staged candidate nodes.
- **Prompt:** "Implement `Agent01ExtractionAgent` per its README and the strategy in
  Phase 1. `observe` loads the book; `interpret` decomposes into concept candidates;
  `act` emits `CANDIDATE_STAGED` events via `self.api.stage_candidate`. Do NOT write the
  graph. Add a script to run it on one book and print the candidates."
- **Files:** `cfaios/agents/agent01_extraction/agent.py`, `scripts/run_extraction.py`.
- **Done when:** running it produces N sensible candidate concepts from a real book,
  each with a source reference — and it never calls the graph writer.

### Step 2.2 — Agent 3: verify claims + Evidence Ledger
- **Goal:** a candidate's chess claims get a verdict backed by evidence.
- **Prompt:** "Implement `Agent03AccuracyAgent`. Use the Verification Router idea:
  cheap checks first, Stockfish only when needed. Produce a `Verdict` with the right
  `VerdictState` and write an Evidence Ledger entry (hashed) to the object store.
  Return `INAPPLICABLE` for non-objective claims."
- **Files:** `cfaios/agents/agent03_accuracy/agent.py`, `cfaios/infra/chess_engine.py`.
- **Done when:** given a candidate with a position/eval, Agent 3 returns a verdict whose
  evidence you can fetch back from the ledger.

### Step 2.3 — Agent 2: commit (single-writer)
- **Goal:** verified candidates enter the CKG — and only Agent 2 can do it.
- **Prompt:** "Implement `Agent02IntegrityAgent` and a concrete `KnowledgeAPI` over
  Neo4j + vector + object stores. `commit` MUST assert the actor is Agent 2 and raise
  `SingleWriterViolation` otherwise. Store the node, its embedding, and its verdict
  link. Add a test proving another agent's commit attempt raises."
- **Files:** `cfaios/agents/agent02_integrity/agent.py`, a concrete
  `cfaios/infra/knowledge_api_impl.py`, `tests/test_single_writer.py`.
- **Done when:** verified candidates appear as nodes in Neo4j Browser; the single-writer
  test passes; a non-Agent-2 commit raises.

### Step 2.4 — Truth slice end-to-end
- **Goal:** one command runs book → candidates → verify → commit.
- **Prompt:** "Write `scripts/run_truth_slice.py` chaining Agents 1→3→2 on one book.
  Print how many candidates were extracted, verified, and committed, with a couple of
  Evidence Ledger refs."
- **Done when:** one command turns a real book into verified graph nodes with provenance.
  **This is the moment the architecture's core claim becomes real.**

---

## Phase 3 — Prove the thesis (one verified lesson)

> "We teach truth and can prove it" — demonstrated by a single lesson grounded in
> verified nodes, with the ledger entries to prove it wasn't hallucinated.

### Step 3.1 — Minimal lesson shaping
- **Goal:** enough of Agent 5/6 to select and order a few verified nodes into a lesson
  outline (skip full CFLSS — bootstrap it).
- **Prompt:** "Implement a MINIMAL `Agent05ExperienceAgent.decide` that, given a topic,
  retrieves verified nodes via `semantic_search` and orders them into a simple lesson
  blueprint that references node IDs (never copies content). Skip the 13-slot ontology
  for now — leave a TODO."
- **Done when:** you get a lesson blueprint that is a list of references to verified nodes.

### Step 3.2 — Minimal coach grounded in truth (P10)
- **Goal:** Agent 7 composes a lesson strictly from retrieved verified nodes.
- **Prompt:** "Implement a MINIMAL `Agent07CoachingAgent` that takes the blueprint,
  retrieves the referenced verified nodes, and uses `cfaios/infra/llm_anthropic.py` to
  EXPLAIN them — never to invent chess (P10). Every chess claim in the output must map
  to a node ID it retrieved."
- **Done when:** a generated lesson reads well AND every chess assertion traces to a
  committed node.

### Step 3.3 — Provenance proof
- **Goal:** the lesson can prove its grounding.
- **Prompt:** "Add a `--show-provenance` flag that prints, for each claim in the lesson,
  the node ID and its Evidence Ledger ref. Write `scripts/run_lesson.py`."
- **Done when:** you can point at any sentence in the lesson and show the verified source
  behind it. **This is the proof of life for the entire system.**

---

## Phase 4 — Harden the spine (only after Phase 3 works)

- **4.1** Persist the event log (P6) — a real append-only event store, not in-memory.
- **4.2** Implement the AIL loop driver + a minimal Agent 16 to run cycles on schedule.
- **4.3** Turn one gate real (e.g. Agent 7's CQI) with actual scored dimensions.
- **4.4** Add Agent 13 instrumentation-first — start collecting telemetry even before
  there's anything to validate (it must ship at first publish, per the spec).

---

## Phase 5+ — Expand agent by agent

Only once the truth→lesson spine is solid. Suggested order, each its own mini-project:
1. **Content (8, 10)** — turn one lesson into a video script + thumbnail spec, gated by
   claim-faithfulness. Tests P11/P13.
2. **Distribution (9, 11)** — fragments + lifecycle. Tests P12/P14.
3. **Community (12)** — epistemic moderation + the Candidate Queue back into Agent 1.
4. **Intelligence (13, 14, 15)** — analytics, business, research. Tests the governance
   stack and closes the knowledge loop.
5. **Governance (16, 17, 18)** — full orchestration, brand, executive.

Each new agent: read its README, implement the AIL steps, make its gate real, wire its
reads/writes through the KnowledgeAPI, add a test for its P0 failure mode.

---

## Definition of "the pipeline works"

You have a real pipeline — not a skeleton — the day `scripts/run_lesson.py` produces a
chess lesson where **every claim traces to a verified node with Evidence Ledger
provenance**, on a topic extracted from a real book. Everything after that is scale and
breadth on a proven foundation. Get to that day first.
