"""Deterministic local extractors for synthetic meeting facts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from hermes_compair.models import Chunk, ExtractedFact, SourceReference

EXTRACTION_METHOD = "deterministic-pattern-v1"

_ACTION_RE = re.compile(r"^\s*ACTION:\s*(?P<owner>.*?)\s*-\s*(?P<body>.+?)\s*$", re.IGNORECASE)
_BY_RE = re.compile(r"^(?P<task>.+?)\s+by\s+(?P<date>.+?)\s*$", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_RE = "|".join(_MONTHS)
_WRITTEN_DATE_RES = (
    re.compile(rf"\b(?:{_MONTH_RE})\s+\d{{1,2}},\s+\d{{4}}\b"),
    re.compile(rf"\b\d{{1,2}}\s+(?:{_MONTH_RE})\s+\d{{4}}\b"),
)
_REVIEW_DATE_TOKENS = {"", "tbd", "unknown", "to be confirmed", "to be determined"}
_REVIEW_OWNER_TOKENS = {"", "tbd", "unknown", "to be confirmed", "to be determined"}


def extract_facts_from_chunks(chunks: list[Chunk]) -> list[ExtractedFact]:
    """Extract cited action items and date mentions from text chunks."""

    facts: list[ExtractedFact] = []
    for chunk in chunks:
        for line_number, line in _iter_chunk_lines(chunk):
            if not line.strip():
                continue
            facts.extend(_extract_action_fact(chunk, line, line_number))
            facts.extend(_extract_date_facts(chunk, line, line_number))
    return facts


def extract_facts_from_text(
    text: str,
    source_id: str = "synthetic-text",
    source_path: str = "synthetic-text",
) -> list[ExtractedFact]:
    """Convenience wrapper for synthetic text without pre-built chunks."""

    ref = SourceReference(
        source_id=source_id,
        source_path=source_path,
        location=f"lines 1-{len(text.splitlines()) or 1}",
        raw_evidence_text=text,
        metadata={"line_start": 1, "line_end": len(text.splitlines()) or 1},
    )
    chunk = Chunk(
        chunk_id=_stable_id("chunk", source_id, source_path, text),
        document_id=source_id,
        text=text,
        source_refs=[ref],
        metadata={"line_start": 1, "line_end": len(text.splitlines()) or 1},
    )
    return extract_facts_from_chunks([chunk])


def _extract_action_fact(chunk: Chunk, line: str, line_number: int) -> list[ExtractedFact]:
    match = _ACTION_RE.match(line)
    if not match:
        return []

    owner = match.group("owner").strip()
    body = match.group("body").strip()
    task = body
    due_date_text = ""

    by_match = _BY_RE.match(body)
    if by_match:
        task = by_match.group("task").strip()
        due_date_text = by_match.group("date").strip()

    has_review_date = _is_review_date(due_date_text)
    has_recognized_date = bool(due_date_text and _is_recognized_date(due_date_text))
    missing_or_ambiguous_owner = _is_review_owner(owner)
    missing_or_ambiguous_date = not due_date_text or has_review_date or not has_recognized_date
    requires_review = missing_or_ambiguous_owner or missing_or_ambiguous_date
    confidence = 0.35 if requires_review else 0.82

    attributes = {
        "owner": owner,
        "task": task,
    }
    if due_date_text:
        attributes["due_date_text"] = due_date_text

    evidence = line.strip()
    return [
        ExtractedFact(
            fact_id=_stable_id("fact", chunk.chunk_id, str(line_number), "action_item", evidence),
            fact_type="action_item",
            text=_action_text(owner, task, due_date_text),
            source_refs=[_line_source_ref(chunk, line_number, evidence)],
            confidence=confidence,
            extraction_method=EXTRACTION_METHOD,
            requires_review=requires_review,
            extraction_notes="explicit ACTION pattern" if not requires_review else "explicit ACTION pattern with ambiguous owner or date",
            raw_evidence_text=evidence,
            attributes=attributes,
        )
    ]


def _extract_date_facts(chunk: Chunk, line: str, line_number: int) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    seen_spans: set[tuple[int, int]] = set()
    for pattern in (_ISO_DATE_RE, *_WRITTEN_DATE_RES):
        for match in pattern.finditer(line):
            span = match.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)
            date_text = match.group(0)
            evidence = line.strip()
            facts.append(
                ExtractedFact(
                    fact_id=_stable_id("fact", chunk.chunk_id, str(line_number), "date_mention", date_text, evidence),
                    fact_type="date_mention",
                    text=f"Date mentioned: {date_text}",
                    source_refs=[_line_source_ref(chunk, line_number, evidence)],
                    confidence=0.76,
                    extraction_method=EXTRACTION_METHOD,
                    requires_review=False,
                    extraction_notes="deterministic date pattern",
                    raw_evidence_text=evidence,
                    attributes={"date_text": date_text},
                )
            )
    return facts


def _iter_chunk_lines(chunk: Chunk) -> list[tuple[int, str]]:
    start = int(chunk.metadata.get("line_start", 1))
    return [(start + index, line) for index, line in enumerate(chunk.text.splitlines())]


def _line_source_ref(chunk: Chunk, line_number: int, evidence: str) -> SourceReference:
    base = chunk.source_refs[0]
    ref = replace(base)
    ref.location = f"lines {line_number}-{line_number}"
    ref.raw_evidence_text = evidence
    ref.metadata = dict(base.metadata)
    ref.metadata["line_start"] = line_number
    ref.metadata["line_end"] = line_number
    return ref


def _is_recognized_date(value: str) -> bool:
    value = value.strip()
    return bool(
        _ISO_DATE_RE.fullmatch(value)
        or any(pattern.fullmatch(value) for pattern in _WRITTEN_DATE_RES)
    )


def _is_review_date(value: str) -> bool:
    return value.strip().lower() in _REVIEW_DATE_TOKENS


def _is_review_owner(value: str) -> bool:
    return value.strip().lower() in _REVIEW_OWNER_TOKENS


def _action_text(owner: str, task: str, due_date_text: str) -> str:
    parts = ["Action item"]
    if owner:
        parts.append(f"for {owner}")
    if task:
        parts.append(f"to {task}")
    if due_date_text:
        parts.append(f"by {due_date_text}")
    return " ".join(parts) + "."


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return f"{prefix}:{digest.hexdigest()}"
