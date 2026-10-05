"""Load the latest raw files into BigQuery's raw dataset (Phase 2, step 1).

Each raw table is replaced by the newest local snapshot; the full history of runs stays in
data/raw/. `make load` runs validation first, so unvalidated data never reaches the warehouse.
Credentials come from Application Default Credentials (gcloud auth application-default login).
Usage: python -m src.load_bigquery
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from src.config import BQ_LOCATION, BQ_RAW_DATASET, GCP_PROJECT_ID, RAW_DIR

PROFILE_COLUMNS = ["wa_id", "scraped_at", "payload"]


@dataclass(frozen=True)
class LoadPlan:
    table: str
    path: Path  # a Parquet file, or a World Athletics run folder for the profile JSON


def plan_loads(raw_dir: Path = RAW_DIR) -> list[LoadPlan]:
    """The newest file from each source (file and folder names carry UTC timestamps)."""
    olympedia = max((raw_dir / "olympedia").glob("*.parquet"), default=None)
    worlds = max((raw_dir / "worlds").glob("*.parquet"), default=None)
    wa_run = max((p for p in (raw_dir / "wa").glob("*") if (p / "marks.parquet").exists()),
                 default=None)
    plans = []
    if olympedia:
        plans.append(LoadPlan("raw_olympedia_results", olympedia))
    if worlds:
        plans.append(LoadPlan("raw_worlds_podium", worlds))
    if wa_run:
        plans += [
            LoadPlan("raw_wa_athletes", wa_run / "athletes.parquet"),
            LoadPlan("raw_wa_marks", wa_run / "marks.parquet"),
            LoadPlan("raw_wa_profiles", wa_run),
        ]
    return plans


def profiles_frame(run_dir: Path) -> pd.DataFrame:
    """One row per saved profile: wa_id, the run's UTC time, and the full JSON as text."""
    scraped_at = datetime.strptime(run_dir.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    rows = [
        {"wa_id": p.stem, "scraped_at": scraped_at, "payload": p.read_text(encoding="utf-8")}
        for p in sorted(run_dir.glob("*.json"))
    ]
    return pd.DataFrame(rows, columns=PROFILE_COLUMNS)


def load_all(client, plans: list[LoadPlan], project: str = GCP_PROJECT_ID,
             dataset: str = BQ_RAW_DATASET, location: str = BQ_LOCATION) -> dict[str, int]:
    """Create the dataset if needed, replace each planned table, return rows per table."""
    target = bigquery.Dataset(f"{project}.{dataset}")
    target.location = location
    client.create_dataset(target, exists_ok=True)
    replace = bigquery.WriteDisposition.WRITE_TRUNCATE
    loaded: dict[str, int] = {}
    for plan in plans:
        table_id = f"{project}.{dataset}.{plan.table}"
        if plan.path.is_dir():
            config = bigquery.LoadJobConfig(write_disposition=replace)
            job = client.load_table_from_dataframe(profiles_frame(plan.path), table_id,
                                                   job_config=config)
        else:
            config = bigquery.LoadJobConfig(write_disposition=replace,
                                            source_format=bigquery.SourceFormat.PARQUET)
            with plan.path.open("rb") as handle:
                job = client.load_table_from_file(handle, table_id, job_config=config)
        job.result()  # waits for the load to finish; raises if BigQuery rejected it
        loaded[plan.table] = client.get_table(table_id).num_rows
    return loaded


def main() -> int:
    plans = plan_loads()
    if not plans:
        print("No raw files found; run the scrapers first.")
        return 1
    client = bigquery.Client(project=GCP_PROJECT_ID, location=BQ_LOCATION)
    loaded = load_all(client, plans)
    for plan in plans:
        print(f"{plan.table:<24} {loaded[plan.table]:>6} rows  from {plan.path.name}")
    print(f"\nLoaded {len(plans)} tables into {GCP_PROJECT_ID}.{BQ_RAW_DATASET} ({BQ_LOCATION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())