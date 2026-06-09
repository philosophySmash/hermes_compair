"""Read-only local file inventory for document registry records."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from hermes_compair.models import Document

SKIPPED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        ".cache",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "cache",
        "node_modules",
    }
)

LOCAL_DATABASE_SUFFIXES = frozenset(
    {
        ".db",
        ".db-shm",
        ".db-wal",
        ".db-journal",
        ".sqlite",
        ".sqlite-shm",
        ".sqlite-wal",
        ".sqlite-journal",
        ".sqlite3",
        ".sqlite3-shm",
        ".sqlite3-wal",
        ".sqlite3-journal",
    }
)

DOCUMENT_TYPES_BY_EXTENSION = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".text": "text",
    ".csv": "spreadsheet",
    ".tsv": "spreadsheet",
    ".xls": "spreadsheet",
    ".xlsx": "spreadsheet",
    ".pdf": "pdf",
    ".doc": "word",
    ".docx": "word",
    ".eml": "email",
    ".msg": "email",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".html": "html",
    ".htm": "html",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".tif": "image",
    ".tiff": "image",
    ".dwg": "drawing",
    ".dxf": "drawing",
}


def inventory_folder(folder: str | Path) -> list[Document]:
    """Recursively inventory files under a folder without modifying them."""

    root = Path(folder)
    if root.is_symlink():
        raise ValueError(f"Inventory folder must not be a symlink: {root}")
    if not root.exists():
        raise FileNotFoundError(f"Inventory folder not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Inventory path is not a folder: {root}")

    documents: list[Document] = []
    for file_path in _iter_inventory_files(root):
        documents.append(_document_from_file(file_path))
    return documents


def _iter_inventory_files(root: Path):
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if path.is_dir():
            continue
        if _should_skip_path(path, root):
            continue
        if path.is_file():
            yield path


def _should_skip_path(path: Path, root: Path) -> bool:
    if path.is_symlink():
        return True

    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path

    parent_parts = relative.parts[:-1]
    for part in parent_parts:
        if part.startswith(".") or part in SKIPPED_DIRECTORY_NAMES:
            return True

    return path.name.startswith(".") or _is_local_database_file(path)


def _is_local_database_file(path: Path) -> bool:
    name = path.name.lower()
    suffix = path.suffix.lower()
    return suffix in LOCAL_DATABASE_SUFFIXES or any(
        name.endswith(database_suffix) for database_suffix in LOCAL_DATABASE_SUFFIXES
    )


def _document_from_file(path: Path) -> Document:
    content_hash = _sha256_file(path)
    extension = path.suffix.lower()
    stat = path.stat()
    return Document(
        document_id=f"sha256:{content_hash}",
        source_path=str(path),
        title=path.name,
        content_hash=content_hash,
        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
        document_type=detect_document_type(path),
        metadata={
            "extension": extension,
            "size_bytes": stat.st_size,
        },
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def detect_document_type(path: str | Path) -> str:
    """Detect a basic document type from a file extension."""

    extension = Path(path).suffix.lower()
    return DOCUMENT_TYPES_BY_EXTENSION.get(extension, "unknown")
