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
    files = [sd.SITE_ROOT / "site" / "app.py", *(sd.SITE_ROOT / "site" / "ui").glob("*.py")]
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        pairs = {(node.module, alias.name) for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) for alias in node.names}  # fmt: skip
        assert not any(module == "src" and name != "site_data" for module, name in pairs), path
        assert not any(module and module.startswith("src.") for module, _ in pairs), path
        assert not any(isinstance(node, ast.Import) and any(a.name.startswith("src") for a in node.names)
                       for node in ast.walk(tree)), path  # fmt: skip


# Phase 6b: the dashboard and Mission control helpers


def test_closest_to_bronze_puts_the_highest_index_first(data):
    top = sd.closest_to_bronze(data["projections"])
    assert list(top["athlete"]) == ["Neeraj Chopra", "Murali Sreeshankar", "Gulveer Singh"]
    assert top["last_index"].is_monotonic_decreasing
    assert top.loc[0, "event"] == "Javelin (M)"


def test_ladder_keeps_every_event_once(data):
    rows = sd.ladder_rows(data["gaps"])
    assert len(rows) == len(data["gaps"]) == 42
    assert rows["event"].is_unique


def test_ladder_kinds_and_order(data):
    rows = sd.ladder_rows(data["gaps"])
    kinds = list(rows["kind"])
    assert kinds[:2] == ["ahead", "ahead"]  # javelin and long jump (men) are past bronze
    assert set(rows.loc[rows["kind"] == "tactical", "event"]) >= {"5000 m (M)", "10,000 m (M)"}
    first = {k: kinds.index(k) for k in ("behind", "tactical", "none")}
    last_behind = max(i for i, k in enumerate(kinds) if k in ("ahead", "behind"))
    assert last_behind < first["tactical"] < first["none"]
    assert rows.loc[rows["kind"].isin(["ahead", "behind"]), "gap"].is_monotonic_increasing
    tactical = rows[rows["kind"] == "tactical"]["rank"].dropna()
    assert tactical.is_monotonic_increasing


def test_a_tactical_event_ahead_of_bronze_is_still_tactical(data):
    rows = sd.ladder_rows(data["gaps"]).set_index("event")
    assert rows.loc["10,000 m (M)", "kind"] == "tactical"  # gap is -0.67, but read the rank


def test_data_age_and_freshness():
    from datetime import UTC, datetime
    now = datetime(2026, 10, 16, 18, 13, 42, tzinfo=UTC)
    assert sd.data_age_days("2026-10-15T18:13:42Z", now) == pytest.approx(1.0)
    assert [sd.freshness_status(d) for d in (1, 13.9, 14, 60, 61)] == ["ok", "ok", "warn", "warn",
                                                                      "down"]


def test_coverage_status_bands():
    assert sd.coverage_status(0.82) == "ok"
    assert sd.coverage_status(0.85) == "ok"
    assert sd.coverage_status(0.71) == "warn"
    assert sd.coverage_status(0.65) == "down"


def test_api_status():
    assert sd.api_status(0.3, True) == "ok"
    assert sd.api_status(2.0, True) == "warn"  # answered, but slow
    assert sd.api_status(None, False) == "warn"  # timed out: the free host is waking up
    assert sd.api_status(0.1, False) == "down"  # refused or an error


def test_roadmap_reads_the_readme_table():
    phases = sd.roadmap((sd.SITE_ROOT / "README.md").read_text(encoding="utf-8"))
    assert [p["phase"] for p in phases] == [str(i) for i in range(8)]
    assert phases[0]["status"] == "Done"
    assert all(p["what"] and p["status"] for p in phases)


def test_api_version_is_read_from_the_source():
    assert sd.api_version((sd.SITE_ROOT / "src" / "api.py").read_text(encoding="utf-8")) == "1.0.0"
    assert sd.api_version("no version here") is None


def test_head_commit_reads_loose_and_packed_refs(tmp_path):
    (tmp_path / "HEAD").write_text("ref: refs/heads/main\n")
    assert sd.head_commit(tmp_path) is None
    (tmp_path / "packed-refs").write_text("# pack-refs\nabc123 refs/heads/main\n")
    assert sd.head_commit(tmp_path) == "abc123"
    (tmp_path / "refs" / "heads").mkdir(parents=True)
    (tmp_path / "refs" / "heads" / "main").write_text("def456\n")
    assert sd.head_commit(tmp_path) == "def456"
    (tmp_path / "HEAD").write_text("0123abcd\n")  # detached
    assert sd.head_commit(tmp_path) == "0123abcd"
    assert sd.head_commit(tmp_path / "missing") is None


def test_parse_shortlog_and_names():
    people = sd.parse_shortlog("     1\tRohith Jagan <r@example.com>\n     4\tAda L <a@example.com>\n")
    assert [p["name"] for p in people] == ["Ada L", "Rohith Jagan"]
    assert people[0]["commits"] == 4
    assert sd.initials("Rohith Jagan") == "RJ"
    tools = sd.parse_shortlog("     3\tClaude <noreply@anthropic.com>\n     2\tdependabot[bot] <x@y.z>\n"
                             "     1\tRohith Jagan <r@example.com>\n")
    assert [p["name"] for p in tools] == ["Rohith Jagan"]
    assert sd.initials("Claude") == "C"
    assert sd.tidy_name("Neeraj CHOPRA") == "Neeraj Chopra"
    assert sd.tidy_name("I. ASHA") == "I. Asha"
    assert sd.tidy_name("POOJA") == "Pooja"
