import pandas as pd

from src import warehouse


class FakeJob:
    def __init__(self, frame):
        self.frame = frame

    def to_dataframe(self, **kwargs):
        return self.frame


class FakeClient:
    def __init__(self):
        self.sql = None

    def query(self, sql):
        self.sql = sql
        return FakeJob(pd.DataFrame({"ok": [1]}))


def test_query_returns_the_dataframe():
    assert warehouse.query("SELECT 1 AS ok", FakeClient())["ok"].tolist() == [1]


def test_table_selects_everything_from_the_project_dataset():
    client = FakeClient()
    warehouse.table("marts.mart_gap_to_podium", client)
    assert client.sql == "SELECT * FROM `gap-to-podium.marts.mart_gap_to_podium`"