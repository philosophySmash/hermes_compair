"""Read-only graph and timeline projection builders.

The functions in this module convert stored documents, facts, and proposals into
JSON-compatible projection shapes. They do not write to storage or mutate input
objects.
"""

from __future__ import annotations

import hashlib
from dataclasses import is_dataclass
from typing import Any, Iterable

GRAPH_EXTRACTION_METHOD = "projection-builder-v1"
TIMELINE_EXTRACTION_METHOD = "projection-builder-v1"
TIMELINE_PROPOSAL_CATEGORIES = frozenset(
    {
        "deliverable_deadline",
        "milestone_date",
        "task_assignment",
        "schedule_change",
    }
)


def build_graph_projection(
    documents: Iterable[Any],
    facts: Iterable[Any],
    proposals: Iterable[Any],
) -> dict[str, list[dict[str, Any]]]:
    """Build a cited, read-only graph projection from explicit inputs."""

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    document_lookup: dict[str, str] = {}
    for document in documents:
        document_id = _string_value(document, "document_id")
        if not document_id:
            continue
        node_id = f"document:{document_id}"
        document_lookup[document_id] = node_id
        source_path = _string_value(document, "source_path")
        if source_path:
            document_lookup[source_path] = node_id
        title = _string_value(document, "title") or source_path or document_id
        nodes[node_id] = _node(
            node_id=node_id,
            node_type="document",
            label=title,
            source_refs=[_document_source_ref(document)],
            confidence=1.0,
            properties={
                "document_id": document_id,
                "source_path": source_path or None,
                "document_type": _optional_string_value(document, "document_type"),
                "revision": _optional_string_value(document, "revision"),
            },
        )

    fact_node_ids: dict[str, str] = {}
    for fact in facts:
        fact_id = _string_value(fact, "fact_id")
        fact_type = _string_value(fact, "fact_type")
        source_refs = _source_refs(fact)
        if not fact_id or not fact_type or not source_refs:
            continue
        if fact_type == "action_item":
            action_node_id = f"fact:{fact_id}"
            fact_node_ids[fact_id] = action_node_id
            nodes[action_node_id] = _node(
                node_id=action_node_id,
                node_type="action_item",
                label=_attribute_string(fact, "task") or _string_value(fact, "text") or fact_id,
                source_refs=source_refs,
                confidence=_confidence(fact),
                raw_evidence_text=_raw_evidence_text(fact),
                extraction_method=_string_value(fact, "extraction_method") or GRAPH_EXTRACTION_METHOD,
                review_status=_string_value(fact, "review_status") or "pending",
                properties={
                    "fact_id": fact_id,
                    "fact_type": fact_type,
                    "text": _string_value(fact, "text") or None,
                },
            )
            document_node_id = _document_node_for_source_refs(source_refs, document_lookup)
            if document_node_id:
                _add_edge(
                    edges,
                    from_node_id=document_node_id,
                    to_node_id=action_node_id,
                    edge_type="document_contains_fact",
                    source_refs=source_refs,
                    confidence=_confidence(fact),
                    raw_evidence_text=_raw_evidence_text(fact),
                    properties={"fact_id": fact_id},
                )

            owner = _attribute_string(fact, "owner")
            if owner:
                stakeholder_node_id = f"stakeholder:{_stable_digest(owner.lower())}"
                nodes.setdefault(
                    stakeholder_node_id,
                    _node(
                        node_id=stakeholder_node_id,
                        node_type="stakeholder",
                        label=owner,
                        source_refs=source_refs,
                        confidence=_confidence(fact),
                        raw_evidence_text=_raw_evidence_text(fact),
                        properties={"name": owner},
                    ),
                )
                _add_edge(
                    edges,
                    from_node_id=action_node_id,
                    to_node_id=stakeholder_node_id,
                    edge_type="action_assigned_to",
                    source_refs=source_refs,
                    confidence=_confidence(fact),
                    raw_evidence_text=_raw_evidence_text(fact),
                    properties={"fact_id": fact_id},
                )

            date_text = _attribute_string(fact, "due_date_text")
            if date_text:
                date_node_id = f"date:{_stable_digest(date_text)}"
                nodes.setdefault(
                    date_node_id,
                    _node(
                        node_id=date_node_id,
                        node_type="date",
                        label=date_text,
                        source_refs=source_refs,
                        confidence=_confidence(fact),
                        raw_evidence_text=_raw_evidence_text(fact),
                        properties={"date_text": date_text},
                    ),
                )
                _add_edge(
                    edges,
                    from_node_id=action_node_id,
                    to_node_id=date_node_id,
                    edge_type="action_due_on",
                    source_refs=source_refs,
                    confidence=_confidence(fact),
                    raw_evidence_text=_raw_evidence_text(fact),
                    properties={"fact_id": fact_id},
                )
        elif fact_type == "date_mention":
            date_text = _attribute_string(fact, "date_text") or _string_value(fact, "text")
            if date_text:
                date_node_id = f"date:{_stable_digest(date_text)}"
                fact_node_ids[fact_id] = date_node_id
                nodes.setdefault(
                    date_node_id,
                    _node(
                        node_id=date_node_id,
                        node_type="date",
                        label=date_text,
                        source_refs=source_refs,
                        confidence=_confidence(fact),
                        raw_evidence_text=_raw_evidence_text(fact),
                        properties={"fact_id": fact_id, "date_text": date_text},
                    ),
                )
                document_node_id = _document_node_for_source_refs(source_refs, document_lookup)
                if document_node_id:
                    _add_edge(
                        edges,
                        from_node_id=document_node_id,
                        to_node_id=date_node_id,
                        edge_type="document_contains_fact",
                        source_refs=source_refs,
                        confidence=_confidence(fact),
                        raw_evidence_text=_raw_evidence_text(fact),
                        properties={"fact_id": fact_id},
                    )

    for proposal in proposals:
        proposal_id = _string_value(proposal, "proposal_id")
        source_refs = _source_refs(proposal)
        if not proposal_id or not source_refs:
            continue
        proposal_node_id = f"proposal:{proposal_id}"
        nodes[proposal_node_id] = _node(
            node_id=proposal_node_id,
            node_type="proposal",
            label=_string_value(proposal, "title") or proposal_id,
            source_refs=source_refs,
            confidence=_confidence(proposal),
            raw_evidence_text=_raw_evidence_text(proposal),
            extraction_method=_string_value(proposal, "extraction_method") or GRAPH_EXTRACTION_METHOD,
            requires_review=bool(_value(proposal, "requires_review", False)),
            review_status=_string_value(proposal, "review_status") or "pending",
            properties={
                "proposal_id": proposal_id,
                "category": _string_value(proposal, "category") or None,
                "proposed_change": _string_value(proposal, "proposed_change") or None,
            },
        )
        source_fact_id = _attribute_string(proposal, "source_fact_id")
        source_fact_node_id = fact_node_ids.get(source_fact_id)
        if source_fact_node_id:
            _add_edge(
                edges,
                from_node_id=source_fact_node_id,
                to_node_id=proposal_node_id,
                edge_type="proposal_from_fact",
                source_refs=source_refs,
                confidence=_confidence(proposal),
                raw_evidence_text=_raw_evidence_text(proposal),
                properties={"proposal_id": proposal_id, "source_fact_id": source_fact_id},
            )

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def build_timeline_projection(proposals: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
    """Build a cited timeline projection from proposed timeline and task updates."""

    items: list[dict[str, Any]] = []
    for proposal in proposals:
        category = _string_value(proposal, "category")
        proposal_id = _string_value(proposal, "proposal_id")
        source_refs = _source_refs(proposal)
        if category not in TIMELINE_PROPOSAL_CATEGORIES or not proposal_id or not source_refs:
            continue
        proposed_value = _attributes(proposal).get("proposed_value", {})
        if not isinstance(proposed_value, dict):
            proposed_value = {}
        date_text = _first_string(
            proposed_value.get("due_date_text"),
            proposed_value.get("date_text"),
            _value(proposal, "date_text"),
        )
        title = _first_string(
            proposed_value.get("task"),
            proposed_value.get("source_text"),
            _value(proposal, "title"),
            _value(proposal, "proposal_id"),
        )
        items.append(
            {
                "timeline_item_id": f"timeline:{proposal_id}",
                "title": title,
                "item_type": category,
                "date_text": date_text,
                "review_status": _string_value(proposal, "review_status") or "pending",
                "requires_review": bool(_value(proposal, "requires_review", True)),
                "source_refs": source_refs,
                "confidence": _confidence(proposal),
                "extraction_method": _string_value(proposal, "extraction_method") or TIMELINE_EXTRACTION_METHOD,
                "raw_evidence_text": _raw_evidence_text(proposal),
                "attributes": {
                    "proposal_id": proposal_id,
                    "proposed_change": _string_value(proposal, "proposed_change") or None,
                    "proposed_value": proposed_value,
                },
            }
        )
    return {"items": items}


def _node(
    *,
    node_id: str,
    node_type: str,
    label: str,
    source_refs: list[dict[str, Any]],
    confidence: float,
    extraction_method: str = GRAPH_EXTRACTION_METHOD,
    requires_review: bool = False,
    review_status: str = "pending",
    raw_evidence_text: str | None = None,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "node_type": node_type,
        "label": label,
        "source_refs": source_refs,
        "confidence": confidence,
        "extraction_method": extraction_method,
        "requires_review": requires_review,
        "review_status": review_status,
        "raw_evidence_text": raw_evidence_text,
        "properties": properties or {},
    }


def _add_edge(
    edges: dict[str, dict[str, Any]],
    *,
    from_node_id: str,
    to_node_id: str,
    edge_type: str,
    source_refs: list[dict[str, Any]],
    confidence: float,
    raw_evidence_text: str | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    edge_id = f"edge:{_stable_digest(from_node_id, to_node_id, edge_type)}"
    edges[edge_id] = {
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "edge_type": edge_type,
        "source_refs": source_refs,
        "confidence": confidence,
        "extraction_method": GRAPH_EXTRACTION_METHOD,
        "requires_review": False,
        "review_status": "pending",
        "raw_evidence_text": raw_evidence_text,
        "properties": properties or {},
    }


def _document_node_for_source_refs(source_refs: list[dict[str, Any]], lookup: dict[str, str]) -> str:
    for source_ref in source_refs:
        for key in (source_ref.get("source_id"), source_ref.get("source_path")):
            if key in lookup:
                return lookup[key]
    return ""


def _document_source_ref(document: Any) -> dict[str, Any]:
    return {
        "source_id": _string_value(document, "document_id"),
        "source_path": _string_value(document, "source_path"),
        "source_system": _string_value(document, "source_system") or "local_file",
        "document_title": _optional_string_value(document, "title"),
        "location": None,
        "raw_evidence_text": None,
        "content_hash": _optional_string_value(document, "content_hash"),
        "metadata": _dict_value(document, "metadata"),
    }


def _source_refs(item: Any) -> list[dict[str, Any]]:
    refs = _value(item, "source_refs", [])
    if refs is None:
        return []
    return [_to_dict(ref) for ref in refs]


def _attributes(item: Any) -> dict[str, Any]:
    return _dict_value(item, "attributes")


def _raw_evidence_text(item: Any) -> str | None:
    return _optional_string_value(item, "raw_evidence_text")


def _attribute_string(item: Any, key: str) -> str:
    value = _attributes(item).get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def _confidence(item: Any) -> float:
    value = _value(item, "confidence", 1.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 1.0


def _string_value(item: Any, key: str) -> str:
    value = _value(item, key, "")
    if value is None:
        return ""
    return str(value).strip()


def _optional_string_value(item: Any, key: str) -> str | None:
    value = _string_value(item, key)
    return value or None


def _dict_value(item: Any, key: str) -> dict[str, Any]:
    value = _value(item, key, {})
    if isinstance(value, dict):
        return _json_value(value)
    return {}


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _first_string(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if is_dataclass(value) and hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value)


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _stable_digest(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]
