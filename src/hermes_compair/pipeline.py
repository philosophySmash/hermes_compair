"""Local end-to-end pipeline helpers for synthetic or approved project folders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_compair.chunking import chunk_extracted_documents
from hermes_compair.deterministic_extractors import extract_facts_from_chunks
from hermes_compair.extract_text import extract_folder
from hermes_compair.inventory import inventory_folder
from hermes_compair.models import GraphEdge, GraphNode, SourceReference, TimelineItem
from hermes_compair.projections import build_graph_projection, build_timeline_projection
from hermes_compair.proposals import create_proposals_from_facts
from hermes_compair.storage import ProjectStore

PIPELINE_EXTRACTED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class PipelineResult:
    """Counts and database path from a completed local pipeline run."""

    db_path: Path
    document_count: int
    chunk_count: int
    fact_count: int
    proposal_count: int
    graph_node_count: int
    graph_edge_count: int
    timeline_item_count: int


def run_local_pipeline(folder: str | Path, db_path: str | Path | None = None) -> PipelineResult:
    """Run the local MVP pipeline and persist cited outputs.

    The helper performs only local deterministic work: inventory, text extraction,
    chunking, deterministic fact extraction, proposal creation, graph projection,
    timeline projection, and SQLite persistence. It does not call external
    services or apply proposed updates to canonical project state.
    """

    source_folder = Path(folder)
    _validate_source_folder(source_folder)
    store = ProjectStore(db_path)
    _reject_database_inside_source(source_folder, store.db_path)

    documents = inventory_folder(source_folder)
    extracted_documents = extract_folder(source_folder)
    for document in extracted_documents:
        document.extracted_at = PIPELINE_EXTRACTED_AT
    chunks = chunk_extracted_documents(extracted_documents)
    facts = extract_facts_from_chunks(chunks)
    for fact in facts:
        fact.extracted_at = PIPELINE_EXTRACTED_AT
    proposals = create_proposals_from_facts(facts)
    for proposal in proposals:
        proposal.extracted_at = PIPELINE_EXTRACTED_AT
    graph = build_graph_projection(documents, facts, proposals)
    timeline = build_timeline_projection(proposals)

    store.init_db()
    store.clear_pipeline_outputs()

    for document in documents:
        store.upsert_document(document)
    for chunk in chunks:
        store.upsert_chunk(chunk)
    for fact in facts:
        store.upsert_fact(fact)
    for proposal in proposals:
        store.upsert_proposal(proposal)
    for node in graph["nodes"]:
        store.upsert_graph_node(_graph_node_from_dict(node))
    for edge in graph["edges"]:
        store.upsert_graph_edge(_graph_edge_from_dict(edge))
    for item in timeline["items"]:
        store.upsert_timeline_item(_timeline_item_from_dict(item))

    return PipelineResult(
        db_path=store.db_path,
        document_count=len(documents),
        chunk_count=len(chunks),
        fact_count=len(facts),
        proposal_count=len(proposals),
        graph_node_count=len(graph["nodes"]),
        graph_edge_count=len(graph["edges"]),
        timeline_item_count=len(timeline["items"]),
    )


def _validate_source_folder(source_folder: Path) -> None:
    if not source_folder.exists():
        raise FileNotFoundError(f"Folder not found: {source_folder}")
    if not source_folder.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {source_folder}")


def _reject_database_inside_source(source_folder: Path, db_path: Path) -> None:
    resolved_source = source_folder.resolve()
    resolved_db = db_path.resolve()
    if resolved_db == resolved_source or resolved_source in resolved_db.parents:
        raise ValueError("Pipeline database path must be outside the source folder.")


def _graph_node_from_dict(payload: dict[str, Any]) -> GraphNode:
    node = GraphNode(
        node_id=str(payload["node_id"]),
        node_type=str(payload["node_type"]),
        label=str(payload["label"]),
        source_refs=_source_refs_from_dicts(payload.get("source_refs", [])),
        confidence=float(payload.get("confidence", 1.0)),
        extraction_method=str(payload.get("extraction_method") or "pipeline"),
        requires_review=bool(payload.get("requires_review", False)),
        raw_evidence_text=payload.get("raw_evidence_text"),
        review_status=str(payload.get("review_status") or "pending"),
        properties=_dict_value(payload.get("properties", {})),
    )
    node.extracted_at = PIPELINE_EXTRACTED_AT
    return node


def _graph_edge_from_dict(payload: dict[str, Any]) -> GraphEdge:
    edge = GraphEdge(
        edge_id=str(payload["edge_id"]),
        from_node_id=str(payload["from_node_id"]),
        to_node_id=str(payload["to_node_id"]),
        edge_type=str(payload["edge_type"]),
        source_refs=_source_refs_from_dicts(payload.get("source_refs", [])),
        confidence=float(payload.get("confidence", 1.0)),
        extraction_method=str(payload.get("extraction_method") or "pipeline"),
        requires_review=bool(payload.get("requires_review", False)),
        raw_evidence_text=payload.get("raw_evidence_text"),
        review_status=str(payload.get("review_status") or "pending"),
        properties=_dict_value(payload.get("properties", {})),
    )
    edge.extracted_at = PIPELINE_EXTRACTED_AT
    return edge


def _timeline_item_from_dict(payload: dict[str, Any]) -> TimelineItem:
    item = TimelineItem(
        timeline_item_id=str(payload["timeline_item_id"]),
        title=str(payload["title"]),
        item_type=str(payload["item_type"]),
        source_refs=_source_refs_from_dicts(payload.get("source_refs", [])),
        confidence=float(payload.get("confidence", 1.0)),
        extraction_method=str(payload.get("extraction_method") or "pipeline"),
        date_text=payload.get("date_text"),
        requires_review=bool(payload.get("requires_review", True)),
        raw_evidence_text=payload.get("raw_evidence_text"),
        review_status=str(payload.get("review_status") or "pending"),
        attributes=_dict_value(payload.get("attributes", {})),
    )
    item.extracted_at = PIPELINE_EXTRACTED_AT
    return item


def _source_refs_from_dicts(payloads: list[dict[str, Any]]) -> list[SourceReference]:
    return [
        SourceReference(
            source_id=str(payload.get("source_id") or ""),
            source_path=str(payload.get("source_path") or ""),
            source_system=str(payload.get("source_system") or "local_file"),
            document_title=payload.get("document_title"),
            location=payload.get("location"),
            raw_evidence_text=payload.get("raw_evidence_text"),
            content_hash=payload.get("content_hash"),
            metadata=_dict_value(payload.get("metadata", {})),
        )
        for payload in payloads
    ]


def _dict_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
