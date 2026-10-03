"""Olympedia scraper: Olympic athletics final standings, 2000-2024.

Phase 0 stub: the command-line interface is in place; the scraping itself is added in Phase 1.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from src.config import OLYMPEDIA_EDITIONS


def build_parser() -> argparse.ArgumentParser:
    """Define the command-line options."""
    parser = argparse.ArgumentParser(
        prog="python -m src.scrapers.olympedia",
        description="Scrape Olympic athletics final standings from Olympedia into data/raw/.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        choices=sorted(OLYMPEDIA_EDITIONS),
        default=sorted(OLYMPEDIA_EDITIONS),
        metavar="YEAR",
        help="Olympic years to scrape (default: all of %(default)s).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scraper. Returns a process exit code (0 means success)."""
    args = build_parser().parse_args(argv)
    editions = {year: OLYMPEDIA_EDITIONS[year] for year in args.years}
    print(f"Would scrape {len(editions)} Games: {editions}")
    print("Scraping is not implemented yet; it arrives in Phase 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())