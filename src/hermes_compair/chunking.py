"""Citation-preserving chunking for extracted text documents."""

from __future__ import annotations

import hashlib

from hermes_compair.extract_text import ExtractedLine, ExtractedTextDocument
from hermes_compair.models import Chunk, SourceReference

DEFAULT_MAX_LINES = 40
CHUNKING_METHOD = "line-window-v1"


def chunk_extracted_documents(
    documents: list[ExtractedTextDocument],
    max_lines: int = DEFAULT_MAX_LINES,
) -> list[Chunk]:
    """Create citation-preserving chunks for multiple extracted documents."""

    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_extracted_document(document, max_lines=max_lines))
    return chunks


def chunk_extracted_document(
    document: ExtractedTextDocument,
    max_lines: int = DEFAULT_MAX_LINES,
) -> list[Chunk]:
    """Create citation-preserving chunks for one extracted document."""

    if max_lines < 1:
        raise ValueError("max_lines must be at least 1")
    if not document.supported:
        return []

    chunks: list[Chunk] = []
    for group in _line_groups(document.lines, max_lines):
        if not group:
            continue
        line_start = group[0].line_number
        line_end = group[-1].line_number
        text = "\n".join(line.text for line in group)
        if not text.strip():
            continue
        extracted_at = document.extracted_at.isoformat()
        metadata = {
            "source_file": document.source_path,
            "line_start": line_start,
            "line_end": line_end,
            "content_hash": document.content_hash,
            "extracted_at": extracted_at,
            "extraction_method": document.extraction_method,
            "chunking_method": CHUNKING_METHOD,
        }
        ref = SourceReference(
            source_id=document.document_id,
            source_path=document.source_path,
            document_title=document.title,
            location=f"lines {line_start}-{line_end}",
            raw_evidence_text=text,
            content_hash=document.content_hash,
            metadata=metadata.copy(),
        )
        chunks.append(
            Chunk(
                chunk_id=_chunk_id(document.document_id, line_start, line_end, text),
                document_id=document.document_id,
                text=text,
                source_refs=[ref],
                metadata=metadata,
            )
        )
    return chunks


def _line_groups(lines: list[ExtractedLine], max_lines: int) -> list[list[ExtractedLine]]:
    groups: list[list[ExtractedLine]] = []
    current: list[ExtractedLine] = []
    for line in lines:
        if not line.text.strip():
            if current:
                groups.append(current)
                current = []
            continue
        current.append(line)
        if len(current) >= max_lines:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _chunk_id(document_id: str, line_start: int, line_end: int, text: str) -> str:
    digest = hashlib.sha256()
    digest.update(document_id.encode("utf-8"))
    digest.update(str(line_start).encode("ascii"))
    digest.update(str(line_end).encode("ascii"))
    digest.update(text.encode("utf-8"))
    return f"chunk:{digest.hexdigest()}"
