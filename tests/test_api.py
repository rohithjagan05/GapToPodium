import json
from datetime import UTC, datetime

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src import api
from src.export import export_serving

# Values shaped like the real outputs; athlete names are labelled placeholders.
GAPS = pd.DataFrame({
    "event_key": ["jt_m", "5000m_m", "hep_w"],
    "india_best_athlete": ["Athlete A", "Athlete B", None],
    "india_best_mark_raw": ["90.23", "13:03.93", None],
    "gap_pct": [-4.37, -0.29, None],
    "india_world_rank": [3, 38, None],
    "tactical_event": [False, True, False],
    "extra_column": [1, 2, 3],  # must not leak into the served file
})  # fmt: skip
PROJ = pd.DataFrame({
    "athlete": ["Athlete A", "Athlete C", "Athlete D"], "event": ["jt_m", "hj_w", "jt_m"],
    "last_season": [2026, 2026, 2025], "last_index": [100.4, 97.3, 89.6], "target_age": [31, 21, 33],
    "projected": [100.5, 97.6, 91.0], "low": [99.4, 96.5, 88.0], "high": [103.8, 101.0, 94.4],
    "range_reaches_bronze": [True, True, False], "beyond_trained_ages": [True, False, True],
})  # fmt: skip
FINDINGS = {"gap_at_18": 4.86, "gap_at_18_ci": [2.97, 6.75]}


@pytest.fixture
def client(tmp_path, monkeypatch):
    export_serving(GAPS, PROJ, FINDINGS, tmp_path, now=datetime(2026, 10, 15, tzinfo=UTC))
    monkeypatch.setenv("SERVING_DIR", str(tmp_path))
    api.load.cache_clear()
    return TestClient(api.app)


def test_export_writes_only_the_contract_columns_and_a_timestamp(tmp_path):
    paths = export_serving(GAPS, PROJ, FINDINGS, tmp_path, now=datetime(2026, 10, 15, tzinfo=UTC))
    assert [p.name for p in paths] == ["gaps.csv", "projections.csv", "findings.json"]
    assert "extra_column" not in pd.read_csv(paths[0]).columns
    assert json.loads(paths[2].read_text())["generated_at"] == "2026-10-15T00:00:00Z"


def test_export_refuses_tables_missing_a_column(tmp_path):
    with pytest.raises(ValueError, match="india_world_rank"):
        export_serving(GAPS.drop(columns="india_world_rank"), PROJ, FINDINGS, tmp_path)


def test_health_and_findings(client):
    assert client.get("/health").json() == {"status": "ok", "generated_at": "2026-10-15T00:00:00Z"}
    assert client.get("/findings").json()["gap_at_18"] == 4.86


def test_events_list_filter_and_missing_values_become_null(client):
    all_events = client.get("/events").json()
    assert len(all_events) == 3
    hep = next(e for e in all_events if e["event_key"] == "hep_w")
    assert hep["gap_pct"] is None and hep["india_world_rank"] is None
    tactical = client.get("/events", params={"tactical": True}).json()
    assert [e["event_key"] for e in tactical] == ["5000m_m"]


def test_one_event_and_unknown_event(client):
    assert client.get("/events/jt_m").json()["india_world_rank"] == 3
    response = client.get("/events/xyz")
    assert response.status_code == 404 and "xyz" in response.json()["detail"]


def test_projections_are_sorted_and_filterable(client):
    rows = client.get("/projections").json()
    assert [r["projected_2028"] for r in rows] == [100.5, 97.6, 91.0]
    assert len(client.get("/projections", params={"event": "jt_m"}).json()) == 2
    assert [r["athlete"] for r in client.get("/projections", params={"athlete": "c"}).json()] == [
        "Athlete C"]
    assert len(client.get("/projections", params={"reaches_bronze": True}).json()) == 2
    assert len(client.get("/projections", params={"limit": 1}).json()) == 1


def test_invalid_limit_is_rejected(client):
    assert client.get("/projections", params={"limit": 0}).status_code == 422

def test_home_page_sends_visitors_to_the_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307 and response.headers["location"] == "/docs"