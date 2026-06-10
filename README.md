# hermes_compair

Local-first construction project intelligence prototype for synthetic or explicitly approved project files.

The project concept is a project brain that can ingest construction project documentation and communications, extract structured knowledge with citations, maintain draft graph and timeline views, and create proposed updates for human review. The current code is an MVP prototype, not a production system.

## Current Contents

- `docs/construction_project_brain_plan.md` - research and implementation plan.
- `AGENTS.md` - safety and behavior rules for AI agents working in this repo.
- `samples/synthetic_project/` - safe synthetic sample files for local tests and demos.
- `schemas/` - reserved for extraction and data schemas.
- `src/hermes_compair/` - Python package, local pipeline, read-only API, and CLI entry point.
- `tests/` - stdlib unittest coverage, including an end-to-end synthetic project smoke test.
- `pyproject.toml` - Python project metadata.

## Core Principles

1. Do not invent project facts.
2. Preserve citations and source evidence for extracted facts.
3. Treat real construction project documents as confidential by default.
4. Prefer local-first parsing and least-data model calls.
5. Use human approval for high-impact timeline, contract, and task updates.
6. Use synthetic or sanitized data for examples and tests.

## Implemented MVP Scope

The current local MVP can:

- scan a local folder and build document inventory records;
- extract text from UTF-8 `.md`, `.txt`, and `.csv` files;
- split extracted text into cited chunks;
- run deterministic extraction for date mentions, explicit `ACTION:` lines, and role-based synthetic action bullets;
- convert extracted facts into reviewable proposals;
- persist documents, chunks, facts, proposals, graph projection items, and timeline projection items to local SQLite;
- expose read-only FastAPI endpoints for stored data;
- serve a minimal local dashboard at `/ui`.

## Setup

Use a local virtual environment. With uv:

```bash
uv sync
```

Commands below assume you run them from the repository root. If FastAPI or uvicorn is needed, use the project virtual environment Python at `.venv/bin/python` after `uv sync`.

## Test Commands

Run the full unittest suite:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q
```

Run only the synthetic end-to-end smoke test:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_e2e_synthetic_project -q
```

Show CLI help:

```bash
PYTHONPATH=src .venv/bin/python -m hermes_compair.cli --help
```

## Local Pipeline Commands

Inventory the synthetic project:

```bash
PYTHONPATH=src .venv/bin/python -m hermes_compair.cli inventory samples/synthetic_project
```

Extract text and chunks from the synthetic project:

```bash
PYTHONPATH=src .venv/bin/python -m hermes_compair.cli extract samples/synthetic_project
```

Run the complete deterministic local pipeline into a SQLite database:

```bash
PYTHONPATH=src .venv/bin/python -m hermes_compair.cli pipeline samples/synthetic_project --db .hermes_compair/synthetic_project.db
```

The pipeline performs inventory, text extraction, chunking, deterministic fact extraction, proposal creation, graph projection, timeline projection, and persistence. It does not call external services and does not apply proposals to canonical project state. Put the SQLite database outside the source folder being processed so the database is never inventoried as input.

## Read-Only Local API and Dashboard

The MVP exposes a local FastAPI app for read-only access to stored project brain data. It does not ingest files through API endpoints, apply proposals, call external services, or mutate canonical project state.

First load synthetic data into a local database:

```bash
PYTHONPATH=src .venv/bin/python -m hermes_compair.cli pipeline samples/synthetic_project --db .hermes_compair/synthetic_project.db
```

Run the API against that database:

```bash
HERMES_COMPAIR_DB_PATH=.hermes_compair/synthetic_project.db PYTHONPATH=src .venv/bin/python -m uvicorn hermes_compair.api:app --host 127.0.0.1 --port 8000
```

Then visit `http://127.0.0.1:8000/ui` in a local browser.

Available read-only endpoints:

- `GET /health` - health check with read-only status.
- `GET /documents` - list stored document metadata.
- `GET /chunks/search?q=term` - search stored chunks by text.
- `GET /graph` - return stored graph projection items or build a cited graph projection from stored documents, facts, and proposals.
- `GET /timeline` - list stored timeline projection items or build them from stored proposals.
- `GET /proposals` - list reviewable proposed updates.

API responses preserve stored citations and evidence fields. Absolute local source paths are reduced to file-name source identifiers before being returned by API responses.

## Safety Limits

- Use `samples/synthetic_project/` for demos and tests.
- Treat real project documents as confidential by default.
- Do not upload real project files to external services without explicit approval.
- Do not commit local databases, `.env` files, credentials, private emails, or real client documents.
- Proposed task, deadline, contract, payment, safety, scope, and liability changes require human review.
- The local pipeline is deterministic and offline. It does not use cloud LLMs, email, SharePoint, OneDrive, Teams, or other external integrations.

## Not Implemented

The current MVP does not include:

- OCR or scanned PDF extraction;
- DOCX, XLSX, PDF, `.eml`, or `.msg` parsing beyond inventory metadata;
- vector embeddings or semantic RAG chat;
- cloud LLM extraction;
- SharePoint, email, Teams, cloud storage, or task-system integrations;
- authentication or multi-user permissions;
- automatic approval or application of proposed updates;
- legal-grade contract interpretation;
- production deployment hardening.

## Repository Publishing Safety

If this repository is connected to a remote Git host, verify before pushing that no confidential project documents, credentials, `.env` files, private emails, or local database files have been added.

Example remote setup, if needed:

```bash
git remote add origin git@github.com:<owner>/<repo>.git
git branch -M main
git push -u origin main
```
