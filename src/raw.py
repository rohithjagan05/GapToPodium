"""Write raw scrape output: one timestamped Parquet file per run, never overwritten."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def save_raw(df: pd.DataFrame, out_dir: Path, prefix: str, now: datetime | None = None) -> Path:
    """Write df to out_dir/<prefix>_<UTC timestamp>.parquet with a scraped_at column."""
    now = now or datetime.now(UTC)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prefix}_{now:%Y%m%dT%H%M%SZ}.parquet"
    if path.exists():
        raise FileExistsError(f"{path} already exists; raw files are never overwritten")
    df.assign(scraped_at=now).to_parquet(path, index=False)
    return path