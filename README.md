# hermes_compair

Research and planning repository for a construction-sector project intelligence system.

The project concept is a “project brain” that can ingest construction project documentation and communications, extract structured knowledge, maintain a knowledge graph, show deliverable timelines, and propose task/timeline updates as new information arrives.

## Current Contents

- `docs/construction_project_brain_plan.md` - research and implementation plan.
- `AGENTS.md` - safety and behavior rules for AI agents working in this repo.
- `samples/` - reserved for synthetic or sanitized sample data only.
- `schemas/` - reserved for extraction/data schemas.
- `src/hermes_compair/` - minimal Python package and CLI entry point.
- `tests/test_smoke.py` - smoke test for package import and version metadata.
- `pyproject.toml` - Python project metadata and pytest test path configuration.

## Core Principles

1. Do not invent project facts.
2. Preserve citations and source evidence for extracted facts.
3. Treat real construction project documents as confidential by default.
4. Prefer local-first parsing and least-data model calls.
5. Use human approval for high-impact timeline, contract, and task updates.
6. Use synthetic or sanitized data for examples and tests.

## Recommended MVP

Start with one project folder and build a read-only prototype that can:

- scan files;
- classify document types;
- extract searchable text and metadata;
- support document Q&A with citations;
- extract meeting action items;
- extract contract obligations;
- extract deliverables and dates;
- show a draft knowledge graph;
- show a draft timeline;
- propose updates for human approval.

## Test and CLI Smoke Checks

Run the unittest suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Show CLI help with:

```bash
PYTHONPATH=src python3 -m hermes_compair.cli --help
```

## Read-Only Local API

The MVP exposes a local FastAPI app for read-only access to stored project brain data. It does not ingest files, apply proposals, call external services, or mutate canonical project state through API endpoints.

Install the project dependencies in a local virtual environment, for example with uv:

```bash
uv sync
```

Run the API from the repository root with:

```bash
PYTHONPATH=src uvicorn hermes_compair.api:app --host 127.0.0.1 --port 8000
```

Available read-only endpoints:

- `GET /health` - health check with read-only status.
- `GET /documents` - list stored document metadata.
- `GET /chunks/search?q=term` - search stored chunks by text.
- `GET /graph` - build a cited graph projection from stored documents, facts, and proposals.
- `GET /timeline` - list stored timeline projection items or build them from stored proposals.
- `GET /proposals` - list reviewable proposed updates.

API responses preserve stored citations and evidence fields. Absolute local source paths are reduced to file-name source identifiers before being returned.

## GitHub Upload Later

This repo is initialized locally with Git and can be connected to GitHub later:

```bash
git remote add origin git@github.com:<owner>/<repo>.git
git branch -M main
git push -u origin main
```

Before pushing, verify that no confidential project documents, credentials, `.env` files, or private emails have been added.
