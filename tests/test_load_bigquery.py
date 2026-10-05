from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
from google.cloud import bigquery

from src import load_bigquery as lb


def make_raw(tmp_path):
    """A small raw folder: two Olympedia files, one Worlds file, one complete and one partial run."""
    (tmp_path / "olympedia").mkdir()
    (tmp_path / "worlds").mkdir()
    for name in ("olympedia_results_20261003T000000Z", "olympedia_results_20261004T111259Z"):
        pd.DataFrame({"a": [1]}).to_parquet(tmp_path / "olympedia" / f"{name}.parquet")
    pd.DataFrame({"a": [1]}).to_parquet(tmp_path / "worlds" / "worlds_podium_20261004T155605Z.parquet")
    run = tmp_path / "wa" / "20261004T204401Z"
    run.mkdir(parents=True)
    pd.DataFrame({"a": [1]}).to_parquet(run / "athletes.parquet")
    pd.DataFrame({"a": [1]}).to_parquet(run / "marks.parquet")
    (run / "14549089.json").write_text('{"props": {}}', encoding="utf-8")
    (run / "14734731.json").write_text('{"props": {}}', encoding="utf-8")
    (tmp_path / "wa" / "20261005T000000Z").mkdir()  # newer, but no extracted tables
    return run


class FakeJob:
    def result(self):
        return self


class FakeClient:
    def __init__(self) -> None:
        self.datasets: list = []
        self.loads: list = []

    def create_dataset(self, dataset, exists_ok=False):
        self.datasets.append((dataset.dataset_id, dataset.location, exists_ok))

    def load_table_from_file(self, handle, table_id, job_config=None):
        self.loads.append(("file", table_id, job_config, handle.read(4)))
        return FakeJob()

    def load_table_from_dataframe(self, df, table_id, job_config=None):
        self.loads.append(("frame", table_id, job_config, len(df)))
        return FakeJob()

    def get_table(self, table_id):
        return SimpleNamespace(num_rows=42)


def test_plan_picks_the_newest_file_from_each_source(tmp_path):
    run = make_raw(tmp_path)
    plans = {p.table: p.path for p in lb.plan_loads(tmp_path)}
    assert plans["raw_olympedia_results"].name == "olympedia_results_20261004T111259Z.parquet"
    assert plans["raw_worlds_podium"].name.startswith("worlds_podium_")
    assert plans["raw_wa_marks"] == run / "marks.parquet"  # the partial newer run is skipped
    assert plans["raw_wa_profiles"] == run


def test_plan_is_empty_without_raw_files(tmp_path):
    assert lb.plan_loads(tmp_path) == []


def test_profiles_frame_has_one_row_per_profile(tmp_path):
    run = make_raw(tmp_path)
    frame = lb.profiles_frame(run)
    assert list(frame.columns) == lb.PROFILE_COLUMNS
    assert frame["wa_id"].tolist() == ["14549089", "14734731"]
    assert (frame["scraped_at"] == datetime(2026, 10, 4, 20, 44, 1, tzinfo=UTC)).all()


def test_load_all_replaces_each_table_in_the_raw_dataset(tmp_path):
    make_raw(tmp_path)
    client = FakeClient()
    loaded = lb.load_all(client, lb.plan_loads(tmp_path), project="p", dataset="raw",
                         location="US")
    assert client.datasets == [("raw", "US", True)]
    assert set(loaded) == {"raw_olympedia_results", "raw_worlds_podium", "raw_wa_athletes",
                           "raw_wa_marks", "raw_wa_profiles"}
    file_loads = [load for load in client.loads if load[0] == "file"]
    assert all(load[3] == b"PAR1" for load in file_loads)  # real Parquet files were sent
    for _, table_id, config, _ in client.loads:
        assert table_id.startswith("p.raw.raw_")
        assert config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert all(load[2].source_format == bigquery.SourceFormat.PARQUET for load in file_loads)