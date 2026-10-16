"""Offline tests for src/site_data.py. Most read the committed files in serving/."""

import ast
import json

import pandas as pd
import pytest

from src import charts
from src import site_data as sd


@pytest.fixture(scope="module")
def data():
    return sd.load_serving()


def test_loads_every_file_the_site_uses(data):
    assert set(data) == {"gaps", "projections", "curves", "backtest", "findings"}
    assert "tactical_event" in data["gaps"].columns
    assert data["findings"]["gap_at_18_points"] == pytest.approx(4.86)


def test_marks_stay_as_text_so_they_show_as_written(data):
    marks = set(data["gaps"]["india_best_mark_raw"].dropna())
    assert {"10.09", "27:00.22"} <= marks
    assert all(isinstance(m, str) for m in marks)


def test_event_labels_match_the_notebook_charts(data):
    for key in data["gaps"]["event_key"]:
        assert sd.event_label(key) == charts.event_label(key)


def test_gap_table_keeps_every_event(data):
    assert len(sd.gap_table(data["gaps"])) == len(data["gaps"])


def test_events_without_an_india_mark_are_labelled(data):
    gaps = data["gaps"]
    blank = gaps[gaps["india_best_athlete"].isna()]
    assert len(blank) > 0
    labels = [sd.event_label(k) for k in blank["event_key"]]
    shown = sd.gap_table(gaps)
    shown = shown[shown["Event"].isin(labels)]
    assert len(shown) == len(blank)
    assert (shown["Best Indian athlete"] == sd.NO_MARK).all()
    assert shown["Gap to bronze (%)"].isna().all()


def test_tactical_split_adds_up(data):
    gaps = data["gaps"]
    yes = sd.gap_table(gaps, tactical=True)
    no = sd.gap_table(gaps, tactical=False)
    assert len(yes) + len(no) == len(gaps)
    assert yes["Tactical event"].all()
    assert not no["Tactical event"].any()


def test_empty_selection_gives_an_empty_table_with_all_columns():
    gaps = pd.DataFrame({
        "event_key": ["100m_m"], "india_best_athlete": ["A"], "india_best_mark_raw": ["10.09"],
        "gap_pct": [2.2], "india_world_rank": [106], "tactical_event": [False],
    })  # fmt: skip
    empty = sd.gap_table(gaps, tactical=True)
    assert empty.empty
    assert list(empty.columns) == ["Event", "Best Indian athlete", "Best mark", "Gap to bronze (%)",
                                   "World rank", "Tactical event"]  # fmt: skip


def test_gap_chart_leaves_out_tactical_and_blank_events(data):
    chart = sd.gap_chart_data(data["gaps"])
    tactical_labels = set(sd.gap_table(data["gaps"], tactical=True)["Event"])
    assert not tactical_labels & set(chart["Event"])
    assert chart["Gap"].notna().all()
    assert list(chart["Gap"]) == sorted(chart["Gap"])


def test_gap_at_18_matches_the_findings(data):
    gap = sd.gap_at_age(data["curves"], 18)
    assert gap == pytest.approx(data["findings"]["gap_at_18_points"], abs=0.01)
    lo, hi = data["findings"]["gap_at_18_ci_95"]
    assert lo <= gap <= hi


def test_backtest_table_puts_the_lowest_error_first(data):
    table = sd.backtest_table(data["backtest"])
    assert table.iloc[0]["Model"] == "Gradient boosting"
    assert list(table["MAE (points)"]) == sorted(table["MAE (points)"])
    assert "Mixed-effects model" in set(table["Model"])


def test_unknown_model_name_is_shown_as_it_is():
    backtest = pd.DataFrame({"contender": ["new_model"], "mae": [1.0], "rmse": [1.2],
                             "bias": [0.0], "coverage_80": [None]})  # fmt: skip
    assert sd.backtest_table(backtest)["Model"].tolist() == ["new_model"]


def test_findings_agree_with_the_backtest_file(data):
    assert sd.check_findings(data["findings"], data["backtest"]) == []


def test_check_findings_reports_a_wrong_or_missing_model(data):
    broken = json.loads(json.dumps(data["findings"]))
    broken["backtest_mae_points"]["boosting"] = 2.5
    broken["backtest_mae_points"]["ghost"] = 1.0
    problems = sd.check_findings(broken, data["backtest"])
    assert any("boosting" in p for p in problems)
    assert any("ghost" in p for p in problems)


def test_projections_are_listed_highest_first(data):
    table = sd.projection_table(data["projections"])
    values = list(table["Projected index"])
    assert values == sorted(values, reverse=True)


def test_every_projection_range_contains_its_projection(data):
    p = data["projections"]
    assert ((p["low"] <= p["projected"]) & (p["projected"] <= p["high"])).all()


def test_event_filter_keeps_only_that_event(data):
    p = data["projections"]
    table = sd.projection_table(p, event="jt_m")
    assert len(table) == (p["event"] == "jt_m").sum()
    assert (table["Event"] == sd.event_label("jt_m")).all()


def test_athlete_filter_ignores_case(data):
    table = sd.projection_table(data["projections"], athlete="neeraj")
    assert "Neeraj Chopra" in set(table["Athlete"])


def test_neeraj_chopra_is_flagged_as_beyond_the_trained_ages(data):
    table = sd.projection_table(data["projections"], athlete="Neeraj Chopra")
    assert table["Beyond trained ages"].all()


def test_bronze_filter_splits_the_projections(data):
    p = data["projections"]
    yes = sd.projection_table(p, reaches_bronze=True)
    no = sd.projection_table(p, reaches_bronze=False)
    assert len(yes) + len(no) == len(p)
    assert yes["Range reaches bronze"].all()
    assert not no["Range reaches bronze"].any()


def test_load_reads_a_different_folder(tmp_path, data):
    copy = tmp_path / "serving"
    copy.mkdir()
    for name in ("gaps.csv", "projections.csv", "curves.csv", "backtest.csv", "findings.json"):
        (copy / name).write_bytes((sd.SERVING_DIR / name).read_bytes())
    loaded = sd.load_serving(copy)
    assert loaded["findings"] == data["findings"]
    assert len(loaded["gaps"]) == len(data["gaps"])


def test_the_page_draws_only_from_site_data():
    tree = ast.parse((sd.SITE_ROOT / "site" / "app.py").read_text(encoding="utf-8"))
    pairs = {(node.module, alias.name) for node in ast.walk(tree)
             if isinstance(node, ast.ImportFrom) for alias in node.names}  # fmt: skip
    assert ("src", "site_data") in pairs
    assert not any(module == "src" and name != "site_data" for module, name in pairs)
    assert not any(module and module.startswith("src.") for module, _ in pairs)