"""Read BigQuery tables and views into pandas for analysis (Phase 3 onwards).

Uses the same Application Default Credentials as the loader and dbt.
"""

from __future__ import annotations

import pandas as pd
from google.cloud import bigquery

from src.config import BQ_LOCATION, GCP_PROJECT_ID


def query(sql: str, client=None) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""
    client = client or bigquery.Client(project=GCP_PROJECT_ID, location=BQ_LOCATION)
    return client.query(sql).to_dataframe(create_bqstorage_client=False)


def table(name: str, client=None) -> pd.DataFrame:
    """A whole table or view by dataset and name, e.g. table("marts.mart_gap_to_podium")."""
    return query(f"SELECT * FROM `{GCP_PROJECT_ID}.{name}`", client)