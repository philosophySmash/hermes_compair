"""Command line interface for hermes_compair."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from hermes_compair import __version__
from hermes_compair.chunking import chunk_extracted_documents
from hermes_compair.extract_text import extract_folder
from hermes_compair.inventory import inventory_folder
from hermes_compair.pipeline import run_local_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(
        prog="hermes_compair",
        description="Local project intelligence prototype for construction documents.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"hermes_compair {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    inventory_parser = subparsers.add_parser(
        "inventory",
        help="Create read-only local document inventory records.",
    )
    inventory_parser.add_argument("folder", help="Folder to scan.")
    inventory_parser.add_argument(
        "--json",
        action="store_true",
        help="Output inventory records as JSON.",
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract supported text and create cited chunks.",
    )
    extract_parser.add_argument("folder", help="Folder to extract from.")
    extract_parser.add_argument(
        "--json",
        action="store_true",
        help="Output extracted documents and chunks as JSON.",
    )

    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run the local deterministic pipeline into a SQLite database.",
    )
    pipeline_parser.add_argument("folder", help="Folder to process.")
    pipeline_parser.add_argument(
        "--db",
        default=None,
        help="SQLite database path. Defaults to .hermes_compair/project_brain.db.",
    )
    pipeline_parser.add_argument(
        "--json",
        action="store_true",
        help="Output pipeline counts as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inventory":
        try:
            documents = inventory_folder(args.folder)
        except (FileNotFoundError, NotADirectoryError, OSError, sqlite3.Error, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

        payload = {"documents": [document.to_dict() for document in documents]}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for document in documents:
                print(f"{document.source_path}\t{document.document_type}\t{document.content_hash}")
        return 0

    if args.command == "extract":
        try:
            documents = extract_folder(args.folder)
        except (FileNotFoundError, NotADirectoryError, OSError, sqlite3.Error, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

        chunks = chunk_extracted_documents(documents)
        payload = {
            "documents": [document.to_dict() for document in documents],
            "chunks": [chunk.to_dict() for chunk in chunks],
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"documents\t{len(documents)}")
            print(f"chunks\t{len(chunks)}")
        return 0

    if args.command == "pipeline":
        try:
            result = run_local_pipeline(args.folder, args.db)
        except (FileNotFoundError, NotADirectoryError, OSError, sqlite3.Error, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

        payload = {
            "db_path": str(result.db_path),
            "documents": result.document_count,
            "chunks": result.chunk_count,
            "facts": result.fact_count,
            "proposals": result.proposal_count,
            "graph_nodes": result.graph_node_count,
            "graph_edges": result.graph_edge_count,
            "timeline_items": result.timeline_item_count,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for key, value in payload.items():
                print(f"{key}\t{value}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
