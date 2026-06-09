"""Core data models for cited project knowledge.

The models in this module are intentionally small stdlib dataclasses. They
preserve provenance for extracted project facts and proposed project updates
without adding runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _json_value(value: Any) -> Any:
    """Convert dataclass values into JSON-compatible Python objects."""

    if is_dataclass(value):
        return _dataclass_to_dict(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(instance: Any) -> dict[str, Any]:
    return {item.name: _json_value(getattr(instance, item.name)) for item in fields(instance)}


@dataclass
class JsonModel:
    """Mixin for JSON-compatible serialization."""

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SourceReference(JsonModel):
    """Reference to the source evidence behind an extraction."""

    source_id: str
    source_path: str
    source_system: str = "local_file"
    document_title: str | None = None
    location: str | None = None
    raw_evidence_text: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document(JsonModel):
    """Metadata for an ingested document."""

    document_id: str
    source_path: str
    title: str | None = None
    source_system: str = "local_file"
    content_hash: str | None = None
    modified_at: datetime | None = None
    document_type: str | None = None
    revision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk(JsonModel):
    """A text chunk with source provenance."""

    chunk_id: str
    document_id: str
    text: str
    source_refs: list[SourceReference]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("Chunk requires at least one source reference.")


@dataclass
class ExtractedFact(JsonModel):
    """A cited fact extracted from project source material."""

    fact_id: str
    fact_type: str
    text: str
    source_refs: list[SourceReference]
    confidence: float
    extraction_method: str
    requires_review: bool = False
    extraction_notes: str = ""
    raw_evidence_text: str | None = None
    extracted_at: datetime = field(default_factory=utc_now)
    review_status: str = "pending"
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("ExtractedFact requires at least one source reference.")
        _validate_evidence("ExtractedFact", self.raw_evidence_text, self.source_refs)
        _validate_confidence(self.confidence)


HIGH_IMPACT_PROPOSAL_CATEGORIES = frozenset(
    {
        "contract_obligation",
        "milestone_date",
        "deliverable_deadline",
        "payment_terms",
        "scope_change",
        "legal_notice",
        "liability_clause",
        "penalty_clause",
        "safety_decision",
        "task_assignment",
        "schedule_change",
        "cost_change",
        "project_state_change",
    }
)


@dataclass
class Proposal(JsonModel):
    """A proposed project update that may require human review."""

    proposal_id: str
    category: str
    title: str
    proposed_change: str
    source_refs: list[SourceReference]
    confidence: float
    extraction_method: str
    requires_review: bool | None = None
    extraction_notes: str = ""
    raw_evidence_text: str | None = None
    extracted_at: datetime = field(default_factory=utc_now)
    review_status: str = "pending"
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("Proposal requires at least one source reference.")
        _validate_confidence(self.confidence)
        if self.requires_review is None:
            self.requires_review = self.category in HIGH_IMPACT_PROPOSAL_CATEGORIES


@dataclass
class GraphNode(JsonModel):
    """A graph node derived from cited project knowledge."""

    node_id: str
    node_type: str
    label: str
    source_refs: list[SourceReference]
    confidence: float
    extraction_method: str
    requires_review: bool = False
    extraction_notes: str = ""
    raw_evidence_text: str | None = None
    extracted_at: datetime = field(default_factory=utc_now)
    review_status: str = "pending"
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("GraphNode requires at least one source reference.")
        _validate_confidence(self.confidence)


@dataclass
class GraphEdge(JsonModel):
    """A graph relationship derived from cited project knowledge."""

    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    source_refs: list[SourceReference]
    confidence: float
    extraction_method: str
    requires_review: bool = False
    extraction_notes: str = ""
    raw_evidence_text: str | None = None
    extracted_at: datetime = field(default_factory=utc_now)
    review_status: str = "pending"
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("GraphEdge requires at least one source reference.")
        _validate_confidence(self.confidence)


@dataclass
class TimelineItem(JsonModel):
    """A cited project timeline item."""

    timeline_item_id: str
    title: str
    item_type: str
    source_refs: list[SourceReference]
    confidence: float
    extraction_method: str
    date_text: str | None = None
    requires_review: bool = True
    extraction_notes: str = ""
    raw_evidence_text: str | None = None
    extracted_at: datetime = field(default_factory=utc_now)
    review_status: str = "pending"
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_refs:
            raise ValueError("TimelineItem requires at least one source reference.")
        _validate_confidence(self.confidence)


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _validate_evidence(
    model_name: str,
    raw_evidence_text: str | None,
    source_refs: list[SourceReference],
) -> None:
    if _has_text(raw_evidence_text):
        return
    for ref in source_refs:
        if _has_text(ref.location) or _has_text(ref.raw_evidence_text):
            return
    raise ValueError(
        f"{model_name} requires raw evidence text or at least one source reference "
        "with a location or raw evidence text."
    )


def _validate_confidence(confidence: float) -> None:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0.")
