"""Write the results the API serves: small, versioned files in serving/.

The API never queries BigQuery or refits a model; it serves these files. That keeps it fast,
free to host and reproducible: the files change only when the pipeline is rerun and committed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT

SERVING_DIR = PROJECT_ROOT / "serving"
GAP_COLUMNS = ["event_key", "india_best_athlete", "india_best_mark_raw", "gap_pct",
               "india_world_rank", "tactical_event"]  # fmt: skip
PROJECTION_COLUMNS = ["athlete", "event", "last_season", "last_index", "target_age", "projected",
                      "low", "high", "range_reaches_bronze", "beyond_trained_ages"]  # fmt: skip


def export_serving(gaps: pd.DataFrame, projections: pd.DataFrame, findings: dict,
                   out_dir: Path = SERVING_DIR, now: datetime | None = None,
                   extra: dict[str, pd.DataFrame] | None = None) -> list[Path]:  # fmt: skip
    """Write gaps.csv, projections.csv and findings.json; findings gets a generated_at stamp.

    Only the listed columns are written, so the API's contract does not change by accident when
    a notebook table gains a column. extra holds more tables for the dashboards (for example
    {"curves": ..., "backtest": ...}); each is written as <name>.csv.
    """
    missing = [c for c in GAP_COLUMNS if c not in gaps] + [
        c for c in PROJECTION_COLUMNS if c not in projections]
    if missing:
        raise ValueError(f"missing columns for serving: {missing}")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    paths = [out_dir / "gaps.csv", out_dir / "projections.csv", out_dir / "findings.json"]
    gaps[GAP_COLUMNS].sort_values("event_key").to_csv(paths[0], index=False)
    projections[PROJECTION_COLUMNS].round(2).to_csv(paths[1], index=False)
    paths[2].write_text(json.dumps({"generated_at": stamp, **findings}, indent=2) + "\n")
    for name, table in (extra or {}).items():
        paths.append(out_dir / f"{name}.csv")
        table.round(3).to_csv(paths[-1], index=False)
    return paths