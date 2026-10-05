"""Project settings: data folders, Olympedia edition IDs and the scraper's contact details."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = DATA_DIR / "cache"
SEEDS_DIR = DATA_DIR / "seeds"

# Olympedia edition IDs, from https://www.olympedia.org/editions (checked 3 Oct 2026).
# They are not sequential, so the scraper uses this fixed map.
OLYMPEDIA_EDITIONS: dict[int, int] = {
    2000: 25,
    2004: 26,
    2008: 53,
    2012: 54,
    2016: 59,
    2020: 61,
    2024: 63,
}

# Minimum wait between two requests to the same site (NFR-4).
REQUEST_DELAY_SECONDS = 2.0

REPO_URL = "https://github.com/rohithjagan05/GapToPodium"
# BigQuery (Phase 2). Not secrets, so defaults are fine; override in .env if needed.
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gap-to-podium")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")
BQ_RAW_DATASET = os.getenv("BQ_RAW_DATASET", "raw")


def get_contact_email() -> str:
    """Return CONTACT_EMAIL from the environment, or fail with a clear message."""
    email = os.getenv("CONTACT_EMAIL", "").strip()
    if not email or "@" not in email:
        raise RuntimeError(
            "CONTACT_EMAIL is missing or invalid. "
            "Copy .env.example to .env and set CONTACT_EMAIL to your email."
        )
    return email


def user_agent() -> str:
    """The User-Agent header every scraper request sends."""
    return f"GapToPodium/0.1 (+{REPO_URL}; contact: {get_contact_email()})"