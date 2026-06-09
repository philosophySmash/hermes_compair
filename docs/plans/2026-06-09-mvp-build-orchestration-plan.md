# Construction Project Brain MVP Implementation Plan

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task. Each implementation task must use a fresh subagent, then pass spec-compliance review and code-quality/security review before the next task starts.

**Goal:** Build a small, local-first MVP that can inventory a synthetic project folder, extract cited document facts, store them in a local database, and expose a minimal API/UI for document register, search, graph, timeline, and approval proposals.

**Architecture:** Start with a Python package and CLI/API around deterministic local parsing, provenance-first schemas, SQLite storage, and synthetic fixtures. Do not connect real email, SharePoint, cloud LLMs, or external project systems in the MVP. AI/LLM extraction is represented by a swappable interface and deterministic local extractor first, so the system can later add approved model calls without changing the safety model.

**Tech Stack:** Python 3.12, pytest, FastAPI, SQLite, standard-library parsing where possible, optional lightweight document parsers only after approval, simple HTML/JSON API first, synthetic markdown/text fixtures.

---

## 0. Non-Negotiable Build Rules

1. Do not use real project documents, contracts, emails, drawings, or personal data.
2. Do not upload documents to cloud services or cloud LLMs.
3. Do not add dependencies without explicit approval during execution.
4. Use synthetic fixtures only.
5. Every extracted fact must include source evidence.
6. Timeline, contract, task, payment, scope, safety, and liability changes must become proposed updates, not direct mutations.
7. Every behavior change needs tests.
8. Keep changes small and local.
9. Avoid em dash characters in generated text and UI strings.
10. Do not proceed from one task to the next until the implementer output passes both review gates.

---

## 1. Proposed Subagent Orchestration

Execution should use a controller plus fresh subagents.

### Controller

The main agent will:

1. Read this plan once.
2. Create a todo list for all tasks.
3. Dispatch one implementer subagent per task.
4. Dispatch a spec-compliance reviewer after each task.
5. Dispatch a code-quality/security reviewer after spec compliance passes.
6. If reviewers request changes, dispatch a focused fix subagent and re-review.
7. Run final integration tests itself after all reviews pass.
8. Commit and push only after verification passes.

### Implementer Subagent

Each implementer receives:

- exact task section from this plan;
- current repo path;
- safety rules from AGENTS.md;
- required TDD cycle;
- expected files to create or modify;
- exact test commands.

The implementer must:

1. Write failing tests first.
2. Run the narrow test and capture failure.
3. Implement minimal code.
4. Run the narrow test and capture pass.
5. Run relevant broader tests.
6. Report changed files, tests run, and any risks.

### Spec Reviewer Subagent

The spec reviewer checks only whether the implementation matches this plan.

Review output must be:

- PASS, or
- REQUEST_CHANGES with exact missing or overbuilt items.

### Code Quality and Security Reviewer Subagent

The quality reviewer checks:

- provenance is preserved;
- no direct mutation of high-impact state;
- no confidential-data assumptions;
- no path traversal risks;
- no hardcoded secrets;
- no unapproved dependencies;
- tests cover the behavior;
- code is simple and maintainable.

Review output must be:

- APPROVED, or
- REQUEST_CHANGES with exact issues.

---

## 2. Task Graph

The build should be sequential for the first MVP because tasks share foundations.

1. Task 1: Project scaffold and test harness
2. Task 2: Core schemas and provenance model
3. Task 3: Synthetic sample project fixture
4. Task 4: Local file inventory and document registry
5. Task 5: Text extraction and citation chunking
6. Task 6: Deterministic extraction for meeting actions and dates
7. Task 7: Approval proposal model and rules
8. Task 8: SQLite persistence layer
9. Task 9: Knowledge graph and timeline projection builders
10. Task 10: FastAPI read-only API
11. Task 11: Minimal local dashboard/static UI
12. Task 12: End-to-end smoke test and documentation update
13. Task 13: Final independent integration/security review

Only Tasks 3 and 4 may be parallelized after Task 2 if the controller confirms no file conflicts. Default execution should remain sequential to reduce integration risk.

---

## 3. Acceptance Criteria for the MVP

The MVP is acceptable when all of these are true:

1. A synthetic project folder can be scanned from a CLI command.
2. The scan creates a local document register with file path, hash, detected type, modified time, and extraction status.
3. Text is extracted from supported synthetic text/markdown files.
4. Chunks include source file, line range, hash, extraction timestamp, and extraction method.
5. Deterministic extraction identifies simple meeting action items and date mentions from synthetic fixtures.
6. Extracted facts include source_refs, confidence, requires_review, review_status, raw_evidence_text, extracted_at, and extraction_method.
7. Proposed timeline/task updates are stored as proposals, not directly applied to canonical state.
8. Knowledge graph projection returns nodes and edges with source references.
9. Timeline projection returns milestones/tasks/proposals with evidence.
10. FastAPI exposes read-only endpoints for health, documents, chunks/search, graph, timeline, and proposals.
11. Minimal UI can show document register, timeline proposals, and graph JSON or simple graph view.
12. Tests run and pass on synthetic fixtures.
13. No real project files, credentials, cloud calls, or unapproved dependencies are introduced.

---

## 4. Implementation Tasks

### Task 1: Project Scaffold and Test Harness

**Objective:** Create a minimal Python package and test harness without adding unapproved dependencies.

**Files:**
- Create: `src/hermes_compair/__init__.py`
- Create: `src/hermes_compair/cli.py`
- Create: `tests/test_smoke.py`
- Create: `pyproject.toml`
- Modify: `README.md`

**Implementation notes:**

Use standard-library code first. If pytest is unavailable, create the config and tests but report the setup blocker before installing anything.

**Required behavior:**

- `python3 -m hermes_compair.cli --help` works when `PYTHONPATH=src` is set.
- A smoke test imports the package.

**TDD steps:**

1. Write `tests/test_smoke.py` that imports `hermes_compair` and checks a `__version__` string exists.
2. Run: `PYTHONPATH=src python3 -m pytest tests/test_smoke.py -q`
3. Expect failure because package does not exist.
4. Create the package and minimal CLI.
5. Re-run the same test and expect pass.

**Review gates:**

- Spec review: package import, CLI help, no unapproved dependency.
- Quality review: simple structure, no secrets, README does not claim production readiness.

---

### Task 2: Core Schemas and Provenance Model

**Objective:** Define dataclasses or typed dictionaries for documents, source references, chunks, extracted facts, proposals, graph nodes, graph edges, and timeline items.

**Files:**
- Create: `src/hermes_compair/models.py`
- Create: `tests/test_models.py`
- Modify: `schemas/README.md`

**Required behavior:**

- Every extracted fact requires at least one source reference.
- High-impact proposal categories default to `requires_review=True`.
- Models can serialize to JSON-compatible dictionaries.

**TDD steps:**

1. Write tests for source reference serialization.
2. Write tests that creating an extracted fact without source refs fails.
3. Write tests that high-impact proposal types require review by default.
4. Run tests and verify failure.
5. Implement minimal models.
6. Re-run tests and verify pass.

**Review gates:**

- Spec review: source_refs, confidence, requires_review, extraction_method, extracted_at, review_status present where required.
- Quality review: no overbuilt ORM, no external dependencies, clear validation errors.

---

### Task 3: Synthetic Sample Project Fixture

**Objective:** Add safe synthetic sample files for repeatable tests and demos.

**Files:**
- Create: `samples/synthetic_project/meeting_minutes_001.md`
- Create: `samples/synthetic_project/contract_excerpt_001.md`
- Create: `samples/synthetic_project/project_notes_001.md`
- Modify: `samples/README.md`
- Create: `tests/test_samples_are_safe.py`

**Required behavior:**

- Fixtures are clearly marked synthetic.
- Fixtures contain no real client names, credentials, emails, phone numbers, or private project identifiers.
- Tests scan fixture text for obvious unsafe markers like `password`, `api_key`, `secret`, and real-looking email addresses.

**TDD steps:**

1. Write safety test before creating sample files.
2. Run test and verify failure because files are missing.
3. Add synthetic files.
4. Re-run test and verify pass.

**Review gates:**

- Spec review: all files are synthetic and cover minutes, contract, and notes.
- Quality review: no sensitive data, no real companies, useful extraction cases.

---

### Task 4: Local File Inventory and Document Registry

**Objective:** Implement a read-only crawler that inventories files under a given folder and creates document records.

**Files:**
- Create: `src/hermes_compair/inventory.py`
- Create: `tests/test_inventory.py`
- Modify: `src/hermes_compair/cli.py`

**Required behavior:**

- Recursively scan a folder.
- Skip hidden folders, `.git`, cache folders, and local database files.
- Compute SHA-256 hash.
- Detect file extension and basic document type.
- Never modify source files.
- CLI command: `python3 -m hermes_compair.cli inventory samples/synthetic_project --json`

**TDD steps:**

1. Write tests using temporary files.
2. Verify crawler skips `.git` and hidden/cache paths.
3. Verify hash and detected type are present.
4. Verify missing folder returns a clear error.
5. Run tests and verify failure.
6. Implement inventory.
7. Re-run tests and CLI smoke check.

**Review gates:**

- Spec review: recursive inventory, skip rules, hashes, JSON CLI.
- Quality review: path handling safe, no file mutation, clear errors.

---

### Task 5: Text Extraction and Citation Chunking

**Objective:** Extract text from supported local text-like files and create citation-preserving chunks.

**Files:**
- Create: `src/hermes_compair/extract_text.py`
- Create: `src/hermes_compair/chunking.py`
- Create: `tests/test_extract_text.py`
- Create: `tests/test_chunking.py`
- Modify: `src/hermes_compair/cli.py`

**Required behavior:**

- Support `.md`, `.txt`, and `.csv` in MVP.
- Unsupported files are marked unsupported without failure.
- Chunks include source file, line_start, line_end, content hash, extraction timestamp, and extraction method.
- CLI command: `extract samples/synthetic_project --json` outputs documents and chunks.

**TDD steps:**

1. Write failing tests for markdown extraction with line numbers.
2. Write failing tests for unsupported file handling.
3. Write failing tests for chunk source references.
4. Implement minimal extraction and chunking.
5. Re-run tests and CLI smoke check.

**Review gates:**

- Spec review: source citations retained per chunk.
- Quality review: no OCR claims, unsupported files handled honestly, no model calls.

---

### Task 6: Deterministic Extraction for Meeting Actions and Dates

**Objective:** Create a deterministic, local extractor for simple synthetic meeting action items and date mentions.

**Files:**
- Create: `src/hermes_compair/deterministic_extractors.py`
- Create: `tests/test_deterministic_extractors.py`

**Required behavior:**

- Extract action items from synthetic patterns such as `ACTION: Owner - task by date`.
- Extract simple ISO dates and common written dates from synthetic text.
- Every extracted fact has source_refs and raw evidence text.
- Confidence is conservative.
- Ambiguous owners or dates set `requires_review=True`.

**TDD steps:**

1. Write failing tests for action item extraction with cited line range.
2. Write failing tests for date extraction.
3. Write failing tests for ambiguous item requiring review.
4. Implement minimal deterministic extractor.
5. Re-run tests.

**Review gates:**

- Spec review: cited facts only, no hallucinated owners or dates.
- Quality review: simple pattern matching, no false production claims.

---

### Task 7: Approval Proposal Model and Rules

**Objective:** Implement proposal creation rules that prevent high-impact direct mutation.

**Files:**
- Create: `src/hermes_compair/proposals.py`
- Create: `tests/test_proposals.py`

**Required behavior:**

- Convert extracted action/date/obligation facts into proposed updates.
- High-impact categories always require review.
- Proposals include previous_value, proposed_value, rationale, source_refs, confidence, status.
- No function applies a proposal to canonical state in this MVP.

**TDD steps:**

1. Write failing test that deadline proposal requires review.
2. Write failing test that contract obligation proposal requires review.
3. Write failing test that direct apply function does not exist or raises NotImplementedError with safe message.
4. Implement proposal logic.
5. Re-run tests.

**Review gates:**

- Spec review: no silent mutation path.
- Quality review: safe defaults, clear status transitions.

---

### Task 8: SQLite Persistence Layer

**Objective:** Persist document register, chunks, facts, proposals, graph projection, and timeline projection locally.

**Files:**
- Create: `src/hermes_compair/storage.py`
- Create: `tests/test_storage.py`
- Modify: `.gitignore`

**Required behavior:**

- SQLite database path must be user-provided or default to ignored local path.
- Tables store documents, chunks, facts, and proposals.
- Insert operations are idempotent by content hash or stable IDs.
- Queries return JSON-compatible dictionaries.
- Local `.db` files are ignored by git.

**TDD steps:**

1. Write failing tests using temporary SQLite DB.
2. Test document insert and re-insert idempotency.
3. Test chunk/fact/proposal persistence with source refs.
4. Test parameterized queries and no string-formatted SQL.
5. Implement storage.
6. Re-run tests.

**Review gates:**

- Spec review: tables cover MVP objects and preserve evidence.
- Quality review: parameterized SQL, safe paths, no committed DB.

---

### Task 9: Knowledge Graph and Timeline Projection Builders

**Objective:** Build read-only projections from stored facts/proposals into graph and timeline JSON.

**Files:**
- Create: `src/hermes_compair/projections.py`
- Create: `tests/test_projections.py`

**Required behavior:**

- Graph contains nodes for documents, action items, stakeholders, dates, and proposals where available.
- Edges include relationship type and source_refs.
- Timeline contains proposed milestones/tasks/dates with review status.
- Projection functions do not mutate storage.

**TDD steps:**

1. Write failing graph projection test from synthetic facts.
2. Write failing timeline projection test from proposals.
3. Verify source refs are present on edges/items.
4. Implement projection builders.
5. Re-run tests.

**Review gates:**

- Spec review: graph and timeline include evidence.
- Quality review: no graph over-extraction, readable JSON shape.

---

### Task 10: FastAPI Read-Only API

**Objective:** Expose read-only API endpoints for the local MVP.

**Files:**
- Create: `src/hermes_compair/api.py`
- Create: `tests/test_api.py`
- Modify: `README.md`

**Dependency note:**

FastAPI is a new dependency. Before executing this task, the controller must ask for approval to add FastAPI and any test client dependency if they are not already available. If approval is not granted, replace this task with a standard-library HTTP server or CLI-only API plan.

**Required endpoints:**

- `GET /health`
- `GET /documents`
- `GET /chunks/search?q=...`
- `GET /graph`
- `GET /timeline`
- `GET /proposals`

**TDD steps:**

1. Write failing tests for `/health` and one data endpoint.
2. Run tests and verify failure.
3. Implement minimal API app.
4. Re-run tests.

**Review gates:**

- Spec review: endpoints are read-only.
- Quality review: no external calls, no unsafe file path exposure, clear errors.

---

### Task 11: Minimal Local Dashboard or Static UI

**Objective:** Provide a simple local interface for document register, proposals, timeline, and graph JSON.

**Files:**
- Create: `src/hermes_compair/static/index.html` or `src/hermes_compair/ui.py`
- Create: `tests/test_ui_artifact.py`
- Modify: `README.md`

**Required behavior:**

- UI is explicitly labeled local prototype.
- Shows document register, proposal list, timeline data, and graph data from API or generated JSON.
- Does not imply legal/contract authority.
- Uses no external CDN unless approved.

**TDD steps:**

1. Write tests that UI artifact exists and includes required warning text.
2. Run tests and verify failure.
3. Implement minimal UI.
4. Re-run tests.

**Review gates:**

- Spec review: all required sections present.
- Quality review: no external data leakage, no misleading production claims.

---

### Task 12: End-to-End Smoke Test and Documentation Update

**Objective:** Add a repeatable smoke test that runs the synthetic project through the pipeline and updates user docs.

**Files:**
- Create: `tests/test_e2e_synthetic_project.py`
- Modify: `README.md`
- Modify: `docs/construction_project_brain_plan.md` if the implemented MVP differs from the plan

**Required behavior:**

- A test runs inventory, extraction, deterministic extraction, proposal creation, persistence, and projection on synthetic files.
- README explains setup, commands, safety limits, and what is not implemented.
- README no longer says GitHub upload is still future-only if that section remains stale.

**TDD steps:**

1. Write failing E2E test for synthetic pipeline.
2. Run and verify failure.
3. Wire pipeline command or helper.
4. Re-run E2E test.
5. Update README.

**Review gates:**

- Spec review: E2E covers complete MVP path.
- Quality review: docs are honest, no production claims.

---

### Task 13: Final Independent Integration and Security Review

**Objective:** Verify the entire implementation before commit/push.

**Files:**
- No planned edits unless issues are found.

**Required checks:**

1. `git status --short`
2. `git diff --stat`
3. Search for secrets and unsafe fixture content.
4. Run all tests.
5. Run API smoke check if API exists.
6. Verify no `.db`, `.env`, real documents, or private data are staged.
7. Verify no em dash or en dash characters were introduced in generated user-facing text where avoidable.
8. Independent reviewer checks full diff for security, privacy, direct mutation, and provenance issues.

**Review gates:**

- Final reviewer must approve before commit/push.
- If issues are found, dispatch a fix subagent, then re-run final review.

---

## 5. Execution Commands Expected During Build

Use these commands as the baseline. Adjust only if the implementation creates documented alternatives.

```bash
cd /mnt/c/Users/Bruger/Documents/code/hermes_compair
PYTHONPATH=src python3 -m pytest tests -q
PYTHONPATH=src python3 -m hermes_compair.cli --help
PYTHONPATH=src python3 -m hermes_compair.cli inventory samples/synthetic_project --json
PYTHONPATH=src python3 -m hermes_compair.cli extract samples/synthetic_project --json
```

If FastAPI is approved and added:

```bash
PYTHONPATH=src python3 -m hermes_compair.api
```

---

## 6. Commit Strategy

Use small commits after reviewed task groups, not after unreviewed work.

Suggested commits:

1. `chore: add python scaffold and synthetic fixtures`
2. `feat: add cited local ingestion pipeline`
3. `feat: add proposals and project projections`
4. `feat: add read-only local API and UI`
5. `docs: document mvp usage and safety limits`

Do not push until final tests and review pass unless the user asks for intermediate pushes.

---

## 7. Questions Before Execution

Execution can start with safe default assumptions, but these choices affect scope:

1. Do you approve adding FastAPI later for the local read-only API, or should the first MVP stay CLI-only until the core pipeline works?
2. Should I create a feature branch before implementation instead of committing directly on `main`?
3. Should the first UI be a simple static HTML page, or should we delay UI and focus on CLI/API plus JSON outputs first?

Recommended defaults if you want me to proceed efficiently:

- Create a feature branch: `feat/mvp-local-project-brain`.
- Build CLI/core pipeline first.
- Ask again before adding FastAPI.
- Use static local HTML only after API/core tests pass.
