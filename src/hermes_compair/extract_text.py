"""Local text extraction for supported text-like files."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hermes_compair.inventory import inventory_folder
from hermes_compair.models import JsonModel, utc_now

SUPPORTED_TEXT_SUFFIXES = frozenset({".md", ".txt", ".csv"})
TEXT_EXTRACTION_METHOD = "text-like-utf-8"
UNSUPPORTED_EXTRACTION_METHOD = "unsupported"


@dataclass
class ExtractedLine(JsonModel):
    """One extracted line of source text with its original line number."""

    line_number: int
    text: str


@dataclass
class ExtractedTextDocument(JsonModel):
    """Text extracted from one local file with provenance metadata."""

    document_id: str
    source_path: str
    title: str
    supported: bool
    content_hash: str
    extracted_at: datetime
    extraction_method: str
    lines: list[ExtractedLine] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def line_count(self) -> int:
        """Return the number of extracted source lines."""

        return len(self.lines)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["line_count"] = self.line_count
        return data


def extract_folder(folder: str | Path) -> list[ExtractedTextDocument]:
    """Extract supported text from inventoried files under a folder."""

    documents = inventory_folder(folder)
    return [extract_file(document.source_path) for document in documents]


def extract_file(path: str | Path) -> ExtractedTextDocument:
    """Extract text from a supported local file or mark it unsupported."""

    file_path = Path(path)
    if file_path.is_symlink():
        raise ValueError(f"Extraction file must not be a symlink: {file_path}")
    if not file_path.exists():
        raise FileNotFoundError(f"Extraction file not found: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Extraction path is not a file: {file_path}")

    content_hash = _sha256_file(file_path)
    suffix = file_path.suffix.lower()
    extracted_at = utc_now()
    base_metadata: dict[str, Any] = {
        "extension": suffix,
        "size_bytes": file_path.stat().st_size,
    }

    if suffix not in SUPPORTED_TEXT_SUFFIXES:
        metadata = dict(base_metadata)
        metadata["status"] = "unsupported file type"
        return ExtractedTextDocument(
            document_id=f"sha256:{content_hash}",
            source_path=str(file_path),
            title=file_path.name,
            supported=False,
            content_hash=content_hash,
            extracted_at=extracted_at,
            extraction_method=UNSUPPORTED_EXTRACTION_METHOD,
            lines=[],
            metadata=metadata,
        )

    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        metadata = dict(base_metadata)
        metadata["status"] = "decode failed: unsupported encoding"
        return ExtractedTextDocument(
            document_id=f"sha256:{content_hash}",
            source_path=str(file_path),
            title=file_path.name,
            supported=False,
            content_hash=content_hash,
            extracted_at=extracted_at,
            extraction_method=UNSUPPORTED_EXTRACTION_METHOD,
            lines=[],
            metadata=metadata,
        )
    lines = [
        ExtractedLine(line_number=index, text=line)
        for index, line in enumerate(text.splitlines(), start=1)
    ]
    metadata = dict(base_metadata)
    metadata["status"] = "extracted"
    return ExtractedTextDocument(
        document_id=f"sha256:{content_hash}",
        source_path=str(file_path),
        title=file_path.name,
        supported=True,
        content_hash=content_hash,
        extracted_at=extracted_at,
        extraction_method=TEXT_EXTRACTION_METHOD,
        lines=lines,
        metadata=metadata,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
