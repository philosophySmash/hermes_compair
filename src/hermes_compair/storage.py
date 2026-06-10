"""SQLite persistence for local project brain data.

The store keeps JSON payloads for the MVP dataclasses while adding stable
columns for idempotent inserts and simple filters. It uses only stdlib sqlite3
and local filesystem paths.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from hermes_compair.models import Chunk, Document, ExtractedFact, GraphEdge, GraphNode, Proposal, TimelineItem

DEFAULT_DB_PATH = Path(".hermes_compair/project_brain.db")


class ProjectStore:
    """Small SQLite-backed store for cited MVP project knowledge."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH

    def init_db(self) -> None:
        """Create the local SQLite database schema if it does not exist."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    content_hash TEXT UNIQUE,
                    source_path TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    title TEXT,
                    document_type TEXT,
                    revision TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content_hash TEXT UNIQUE,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(document_id)
                );

                CREATE TABLE IF NOT EXISTS facts (
                    fact_id TEXT PRIMARY KEY,
                    fact_type TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    requires_review INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graph_projection (
                    projection_id TEXT PRIMARY KEY,
                    projection_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS timeline_projection (
                    timeline_item_id TEXT PRIMARY KEY,
                    item_type TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def clear_pipeline_outputs(self) -> None:
        """Clear pipeline-owned MVP tables before replacing a run."""

        self.init_db()
        with self._connect() as connection:
            connection.executescript(
                """
                DELETE FROM timeline_projection;
                DELETE FROM graph_projection;
                DELETE FROM proposals;
                DELETE FROM facts;
                DELETE FROM chunks;
                DELETE FROM documents;
                """
            )

    def upsert_document(self, document: Document) -> str:
        """Insert or update a document, deduplicating by content hash when present."""

        self.init_db()
        payload = document.to_dict()
        payload_json = _json_dumps(payload)
        with self._connect() as connection:
            if document.content_hash:
                row = connection.execute(
                    "SELECT document_id FROM documents WHERE content_hash = ?",
                    (document.content_hash,),
                ).fetchone()
                if row is not None:
                    existing_id = row["document_id"]
                    connection.execute(
                        """
                        UPDATE documents
                        SET source_path = ?, source_system = ?, title = ?, document_type = ?, revision = ?, payload_json = ?
                        WHERE document_id = ?
                        """,
                        (
                            document.source_path,
                            document.source_system,
                            document.title,
                            document.document_type,
                            document.revision,
                            payload_json,
                            existing_id,
                        ),
                    )
                    return str(existing_id)
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, content_hash, source_path, source_system, title, document_type, revision, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    source_path = excluded.source_path,
                    source_system = excluded.source_system,
                    title = excluded.title,
                    document_type = excluded.document_type,
                    revision = excluded.revision,
                    payload_json = excluded.payload_json
                """,
                (
                    document.document_id,
                    document.content_hash,
                    document.source_path,
                    document.source_system,
                    document.title,
                    document.document_type,
                    document.revision,
                    payload_json,
                ),
            )
        return document.document_id

    def upsert_chunk(self, chunk: Chunk) -> str:
        """Insert or update a cited chunk by stable chunk id."""

        self.init_db()
        payload = chunk.to_dict()
        content_hash = _content_hash(payload)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chunks (chunk_id, document_id, content_hash, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    document_id = excluded.document_id,
                    content_hash = excluded.content_hash,
                    payload_json = excluded.payload_json
                """,
                (chunk.chunk_id, chunk.document_id, content_hash, _json_dumps(payload)),
            )
        return chunk.chunk_id

    def upsert_fact(self, fact: ExtractedFact) -> str:
        """Insert or update a cited extracted fact by stable fact id."""

        self.init_db()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO facts (fact_id, fact_type, review_status, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(fact_id) DO UPDATE SET
                    fact_type = excluded.fact_type,
                    review_status = excluded.review_status,
                    payload_json = excluded.payload_json
                """,
                (fact.fact_id, fact.fact_type, fact.review_status, _json_dumps(fact.to_dict())),
            )
        return fact.fact_id

    def upsert_proposal(self, proposal: Proposal) -> str:
        """Insert or update a cited proposal by stable proposal id."""

        self.init_db()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO proposals (proposal_id, category, review_status, requires_review, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(proposal_id) DO UPDATE SET
                    category = excluded.category,
                    review_status = excluded.review_status,
                    requires_review = excluded.requires_review,
                    payload_json = excluded.payload_json
                """,
                (
                    proposal.proposal_id,
                    proposal.category,
                    proposal.review_status,
                    int(bool(proposal.requires_review)),
                    _json_dumps(proposal.to_dict()),
                ),
            )
        return proposal.proposal_id

    def upsert_graph_node(self, node: GraphNode) -> str:
        """Insert or update a graph node projection by stable node id."""

        return self._upsert_graph_projection(node.node_id, "node", node.to_dict())

    def upsert_graph_edge(self, edge: GraphEdge) -> str:
        """Insert or update a graph edge projection by stable edge id."""

        return self._upsert_graph_projection(edge.edge_id, "edge", edge.to_dict())

    def upsert_timeline_item(self, item: TimelineItem) -> str:
        """Insert or update a timeline projection item by stable item id."""

        self.init_db()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO timeline_projection (timeline_item_id, item_type, review_status, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(timeline_item_id) DO UPDATE SET
                    item_type = excluded.item_type,
                    review_status = excluded.review_status,
                    payload_json = excluded.payload_json
                """,
                (item.timeline_item_id, item.item_type, item.review_status, _json_dumps(item.to_dict())),
            )
        return item.timeline_item_id

    def list_documents(self) -> list[dict[str, Any]]:
        self.init_db()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM documents ORDER BY source_path, document_id",
                (),
            ).fetchall()
        return [_decode_payload(row) for row in rows]

    def list_chunks(self, document_id: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        with self._connect() as connection:
            if document_id is None:
                rows = connection.execute(
                    "SELECT payload_json FROM chunks ORDER BY chunk_id",
                    (),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM chunks WHERE document_id = ? ORDER BY chunk_id",
                    (document_id,),
                ).fetchall()
        return [_decode_payload(row) for row in rows]

    def list_facts(self, fact_type: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        with self._connect() as connection:
            if fact_type is None:
                rows = connection.execute(
                    "SELECT payload_json FROM facts ORDER BY fact_id",
                    (),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM facts WHERE fact_type = ? ORDER BY fact_id",
                    (fact_type,),
                ).fetchall()
        return [_decode_payload(row) for row in rows]

    def list_proposals(self, review_status: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        with self._connect() as connection:
            if review_status is None:
                rows = connection.execute(
                    "SELECT payload_json FROM proposals ORDER BY proposal_id",
                    (),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM proposals WHERE review_status = ? ORDER BY proposal_id",
                    (review_status,),
                ).fetchall()
        return [_decode_payload(row) for row in rows]

    def list_graph_projection(self, projection_type: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        with self._connect() as connection:
            if projection_type is None:
                rows = connection.execute(
                    "SELECT payload_json FROM graph_projection ORDER BY projection_id",
                    (),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM graph_projection WHERE projection_type = ? ORDER BY projection_id",
                    (projection_type,),
                ).fetchall()
        return [_decode_payload(row) for row in rows]

    def list_timeline_projection(self, review_status: str | None = None) -> list[dict[str, Any]]:
        self.init_db()
        with self._connect() as connection:
            if review_status is None:
                rows = connection.execute(
                    "SELECT payload_json FROM timeline_projection ORDER BY timeline_item_id",
                    (),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM timeline_projection WHERE review_status = ? ORDER BY timeline_item_id",
                    (review_status,),
                ).fetchall()
        return [_decode_payload(row) for row in rows]

    def _upsert_graph_projection(self, projection_id: str, projection_type: str, payload: dict[str, Any]) -> str:
        self.init_db()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO graph_projection (projection_id, projection_type, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(projection_id) DO UPDATE SET
                    projection_type = excluded.projection_type,
                    payload_json = excluded.payload_json
                """,
                (projection_id, projection_type, _json_dumps(payload)),
            )
        return projection_id

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _decode_payload(row: sqlite3.Row) -> dict[str, Any]:
    return json.loads(row["payload_json"])


def _content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()
