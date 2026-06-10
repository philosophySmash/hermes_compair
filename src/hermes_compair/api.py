"""Read-only FastAPI app for the local project brain MVP."""

from __future__ import annotations

import json
import sqlite3
from importlib.resources import files
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from hermes_compair.projections import build_graph_projection, build_timeline_projection
from hermes_compair.storage import ProjectStore


def create_app(db_path: str | Path | None = None) -> FastAPI:
    """Create a read-only API app backed by the local project store."""

    store = ProjectStore(db_path)
    api = FastAPI(
        title="hermes_compair read-only API",
        description="Local read-only API for cited project intelligence data.",
        version="0.1.0",
    )

    @api.get("/", response_class=HTMLResponse)
    def dashboard_root() -> str:
        return _dashboard_html()

    @api.get("/ui", response_class=HTMLResponse)
    def dashboard_ui() -> str:
        return _dashboard_html()

    @api.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "read_only": True}

    @api.get("/documents")
    def documents() -> dict[str, Any]:
        return {"documents": _public_payload(_documents(store))}

    @api.get("/chunks/search")
    def search_chunks(q: str = Query(..., min_length=1)) -> dict[str, Any]:
        matches = [chunk for chunk in _chunks(store) if _matches_query(chunk, q)]
        return {"query": q, "chunks": _public_payload(matches)}

    @api.get("/graph")
    def graph() -> dict[str, Any]:
        projection = build_graph_projection(
            _documents(store),
            _facts(store),
            _proposals(store),
        )
        return _public_payload(projection)

    @api.get("/timeline")
    def timeline() -> dict[str, Any]:
        stored_items = _timeline_items(store)
        if stored_items:
            return {"items": _public_payload(stored_items)}
        return _public_payload(build_timeline_projection(_proposals(store)))

    @api.get("/proposals")
    def proposals() -> dict[str, Any]:
        return {"proposals": _public_payload(_proposals(store))}

    return api


def _dashboard_html() -> str:
    return (
        files("hermes_compair")
        .joinpath("static", "index.html")
        .read_text(encoding="utf-8")
    )


def _documents(store: ProjectStore) -> list[dict[str, Any]]:
    return _read_payloads(store, "documents", "source_path, document_id")


def _chunks(store: ProjectStore) -> list[dict[str, Any]]:
    return _read_payloads(store, "chunks", "chunk_id")


def _facts(store: ProjectStore) -> list[dict[str, Any]]:
    return _read_payloads(store, "facts", "fact_id")


def _proposals(store: ProjectStore) -> list[dict[str, Any]]:
    return _read_payloads(store, "proposals", "proposal_id")


def _timeline_items(store: ProjectStore) -> list[dict[str, Any]]:
    return _read_payloads(store, "timeline_projection", "timeline_item_id")


def _read_payloads(store: ProjectStore, table_name: str, order_by: str) -> list[dict[str, Any]]:
    if not store.db_path.exists():
        return []
    try:
        connection = sqlite3.connect(f"file:{store.db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return []
    connection.row_factory = sqlite3.Row
    with connection:
        try:
            rows = connection.execute(
                f"SELECT payload_json FROM {table_name} ORDER BY {order_by}",
                (),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [json.loads(row["payload_json"]) for row in rows]


def _matches_query(chunk: dict[str, Any], query: str) -> bool:
    normalized_query = query.casefold()
    return normalized_query in str(chunk.get("text", "")).casefold()


def _public_payload(value: Any) -> Any:
    if isinstance(value, list):
        return [_public_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_public_payload(item) for item in value]
    if isinstance(value, dict):
        public: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"source_path", "label"} and isinstance(item, str):
                public[key] = _safe_source_path(item)
            else:
                public[key] = _public_payload(item)
        return public
    return value


def _safe_source_path(source_path: str) -> str:
    """Return a project-safe source identifier without local absolute paths."""

    if _is_absolute_source_path(source_path):
        return PureWindowsPath(source_path).name if "\\" in source_path else PurePosixPath(source_path).name
    return source_path


def _is_absolute_source_path(source_path: str) -> bool:
    return PurePosixPath(source_path).is_absolute() or PureWindowsPath(source_path).is_absolute()


app = create_app()
