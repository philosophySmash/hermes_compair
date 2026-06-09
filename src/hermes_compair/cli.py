"""Command line interface for hermes_compair."""

from __future__ import annotations

import argparse

from hermes_compair import __version__


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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface."""
    parser = build_parser()
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
