# Schemas

This directory documents extraction and storage schema expectations for the local project brain MVP.

Core schema categories:

- document metadata
- source citation references
- document chunks
- extracted facts
- proposed updates
- graph nodes and relationships
- timeline items
- meeting action items
- contract obligations
- deliverables
- milestones
- risks/issues

The stdlib dataclass implementations live in `src/hermes_compair/models.py`.

## Provenance requirements

Important extracted project knowledge must include provenance fields so it can be audited before use in graph, timeline, task, contract, or reporting views:

- `source_refs`
- `confidence`
- `requires_review`
- `extraction_notes`
- `raw_evidence_text` or another evidence location
- `extracted_at`
- `extraction_method`
- `review_status`

Every extracted fact must have at least one source reference. High-impact proposal categories, such as contract obligations, milestone dates, deliverable deadlines, payment terms, scope changes, legal notices, liability clauses, penalty clauses, safety decisions, task assignments, schedule changes, cost changes, and project state changes, default to `requires_review=True`.

Models expose `to_dict()` for JSON-compatible serialization.
