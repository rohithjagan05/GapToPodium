from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
from google.cloud import bigquery

from src import load_bigquery as lb
from src.events import DISCIPLINES


def marks_frame(mark: str = "89.45 (2)") -> pd.DataFrame:
    return pd.DataFrame({"event_key": ["jt_m"], "mark_raw": [mark]})


def make_raw(tmp_path):
    """A small raw folder: two Olympedia files, one Worlds file, one complete and one partial run."""
    (tmp_path / "olympedia").mkdir()
    (tmp_path / "worlds").mkdir()
    for name in ("olympedia_results_20261003T000000Z", "olympedia_results_20261004T111259Z"):
        marks_frame().to_parquet(tmp_path / "olympedia" / f"{name}.parquet")
    marks_frame("88.17 m").to_parquet(tmp_path / "worlds" / "worlds_podium_20261004T155605Z.parquet")
    run = tmp_path / "wa" / "20261004T204401Z"
    run.mkdir(parents=True)
    pd.DataFrame({"wa_id": ["14549089"]}).to_parquet(run / "athletes.parquet")
    marks_frame("90.23").to_parquet(run / "marks.parquet")
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
        self.loads: dict[str, tuple] = {}

    def create_dataset(self, dataset, exists_ok=False):
        self.datasets.append((dataset.dataset_id, dataset.location, exists_ok))

    def load_table_from_dataframe(self, df, table_id, job_config=None):
        self.loads[table_id] = (df, job_config)
        return FakeJob()

    def get_table(self, table_id):
        return SimpleNamespace(num_rows=len(self.loads[table_id][0]))


def test_plan_picks_the_newest_file_from_each_source(tmp_path):
    run = make_raw(tmp_path)
    plans = {p.table: p.path for p in lb.plan_loads(tmp_path)}
    assert plans["raw_olympedia_results"].name == "olympedia_results_20261004T111259Z.parquet"
    assert plans["raw_worlds_podium"].name.startswith("worlds_podium_")
    assert plans["raw_wa_marks"] == run / "marks.parquet"  # the partial newer run is skipped
    assert plans["raw_wa_profiles"] == run
    assert plans["raw_disciplines"] is None


def test_plan_is_empty_without_raw_files(tmp_path):
    assert lb.plan_loads(tmp_path) == []


def test_profiles_frame_has_one_row_per_profile(tmp_path):
    run = make_raw(tmp_path)
    frame = lb.profiles_frame(run)
    assert list(frame.columns) == lb.PROFILE_COLUMNS
    assert frame["wa_id"].tolist() == ["14549089", "14734731"]
    assert (frame["scraped_at"] == datetime(2026, 10, 4, 20, 44, 1, tzinfo=UTC)).all()


def test_disciplines_frame_comes_from_events_py():
    frame = lb.disciplines_frame()
    assert len(frame) == len(DISCIPLINES)
    javelin = frame.set_index("discipline").loc["jt"]
    assert (javelin["discipline_group"], bool(javelin["higher_is_better"])) == ("throws", True)


def test_load_all_adds_mark_values_and_replaces_each_table(tmp_path):
    make_raw(tmp_path)
    client = FakeClient()
    loaded = lb.load_all(client, lb.plan_loads(tmp_path), project="p", dataset="raw",
                         location="US")
    assert client.datasets == [("raw", "US", True)]
    assert set(loaded) == {"raw_olympedia_results", "raw_worlds_podium", "raw_wa_athletes",
                           "raw_wa_marks", "raw_wa_profiles", "raw_disciplines"}
    for df, config in client.loads.values():
        assert config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert client.loads["p.raw.raw_olympedia_results"][0]["mark_value"].tolist() == [89.45]
    assert client.loads["p.raw.raw_worlds_podium"][0]["mark_value"].tolist() == [88.17]
    assert client.loads["p.raw.raw_wa_marks"][0]["mark_value"].tolist() == [90.23]
    assert "mark_value" not in client.loads["p.raw.raw_wa_athletes"][0].columns