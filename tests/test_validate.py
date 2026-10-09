from datetime import date

import pandas as pd
import pytest

from src import validate as v
from src.events import DISCIPLINES


def olympedia_rows(rows):
    columns = ["edition_year", "event_key", "athlete_name", "noc", "position", "medal",
               "mark_raw", "olympedia_athlete_id"]  # fmt: skip
    return v.with_values(pd.DataFrame(rows, columns=columns))


JAVELIN_2024 = [  # real 2024 podium marks
    (2024, "jt_m", "Arshad Nadeem", "PAK", 1, "Gold", "92.97 (1)", 145843),
    (2024, "jt_m", "Neeraj Chopra", "IND", 2, "Silver", "89.45 (2)", 143754),
    (2024, "jt_m", "Anderson Peters", "GRN", 3, "Bronze", "88.54 (3)", 793),
]


def test_with_values_parses_marks():
    assert olympedia_rows(JAVELIN_2024)["mark_value"].tolist() == [92.97, 89.45, 88.54]


def test_required_flags_missing_and_blank_values():
    df = pd.DataFrame({"a": ["x", "", None], "b": [1, 2, 3]})
    result = v.check_required(df, ["a", "b"], "test")
    assert result.status == v.FAIL
    assert len(result.examples) == 2


def test_required_passes_complete_rows():
    assert v.check_required(olympedia_rows(JAVELIN_2024), ["athlete_name"], "test").status == v.PASS


def test_medallist_without_mark_fails():
    rows = [*JAVELIN_2024[:2], (2024, "jt_m", "No Mark", "GRN", 3, "Bronze", "NM", 1)]
    assert v.check_medallists_have_marks(olympedia_rows(rows), "test").status == v.FAIL


def test_medal_counts_other_than_three_are_info():
    rows = [*JAVELIN_2024, (2024, "jt_m", "Tied Bronze", "KEN", 3, "Bronze", "88.54", 2)]
    result = v.check_medal_counts(olympedia_rows(rows), ["edition_year", "event_key"], "test")
    assert result.status == v.INFO
    assert result.examples["medals"].tolist() == [4]


def test_gold_shorter_than_bronze_fails_for_distances():
    rows = [(2024, "jt_m", "A", "X", 1, "Gold", "80.00", 1),
            (2024, "jt_m", "B", "Y", 3, "Bronze", "85.00", 2)]  # fmt: skip
    assert v.check_gold_beats_bronze(olympedia_rows(rows), ["edition_year", "event_key"],
                                     "test").status == v.FAIL  # fmt: skip


def test_gold_slower_than_bronze_fails_for_times():
    rows = [(2024, "100m_m", "A", "X", 1, "Gold", "10.20", 1),
            (2024, "100m_m", "B", "Y", 3, "Bronze", "9.90", 2)]  # fmt: skip
    assert v.check_gold_beats_bronze(olympedia_rows(rows), ["edition_year", "event_key"],
                                     "test").status == v.FAIL  # fmt: skip


def test_real_podium_and_vacant_bronze_pass():
    rows = [*JAVELIN_2024, (2012, "hj_m", "A", "X", 1, "Gold", "2.33", 5),
            (2012, "hj_m", "B", "Y", 2, "Silver", "2.29", 6)]  # no bronze, like 2012  # fmt: skip
    result = v.check_gold_beats_bronze(olympedia_rows(rows), ["edition_year", "event_key"], "test")
    assert result.status == v.PASS
    assert result.detail.startswith("1 events")  # only the javelin had both gold and bronze


def test_better_than_plausible_fails_and_worse_is_info_for_distances():
    rows = [*JAVELIN_2024, (2024, "jt_m", "Typo", "X", 9, None, "109.29", 9),
            (2024, "jt_m", "Injured", "Y", 30, None, "9.29", 10)]  # fmt: skip
    better, worse = v.check_ranges(olympedia_rows(rows), "test")
    assert (better.status, better.examples["athlete_name"].tolist()) == (v.FAIL, ["Typo"])
    assert (worse.status, worse.examples["athlete_name"].tolist()) == (v.INFO, ["Injured"])


def test_range_direction_for_times():
    rows = [(2000, "100m_m", "Too Fast", "X", 1, None, "8.50", 1),
            (2000, "100m_m", "Injured", "Y", 8, None, "16.40", 2)]  # fmt: skip
    better, worse = v.check_ranges(olympedia_rows(rows), "test")
    assert better.examples["athlete_name"].tolist() == ["Too Fast"]
    assert worse.examples["athlete_name"].tolist() == ["Injured"]


def test_road_times_written_with_a_dot_are_read_as_hours():
    rows = [(2019, "20kmw_m", "Walker", "JPN", 1, "Gold", "1:26.34", 1)]
    assert olympedia_rows(rows)["mark_value"].tolist() == [5194.0]


def test_duplicates_ignore_rows_without_an_id():
    rows = [*JAVELIN_2024, JAVELIN_2024[0],
            (2024, "jt_m", "No Link 1", "X", 20, None, "70.00", None),
            (2024, "jt_m", "No Link 2", "Y", 21, None, "69.00", None)]  # fmt: skip
    result = v.check_no_duplicates(olympedia_rows(rows), ["edition_year", "event_key",
                                                          "olympedia_athlete_id"], "test")  # fmt: skip
    assert result.status == v.FAIL
    assert set(result.examples["athlete_name"]) == {"Arshad Nadeem"}


def test_early_season_track_pb_is_info_but_field_pb_is_not():
    marks = pd.DataFrame({
        "wa_id": ["1", "2"], "event_key": ["5000m_m", "jt_m"], "kind": ["personal_best"] * 2,
        "mark_raw": ["12:59.77", "90.23"], "date": [date(2025, 2, 21), date(2025, 3, 1)],
        "indoor": [False, False], "not_legal": [False, False],
    })  # fmt: skip
    result = v.check_early_season_pbs(marks)
    assert result.status == v.INFO
    assert result.examples["event_key"].tolist() == ["5000m_m"]


def test_seed_ids_duplicates_fail_and_missing_are_info():
    seeds = pd.DataFrame({"athlete_name": ["A", "B", "C"], "wa_id": ["1", "1", ""],
                          "notes": ["", "", "not found on WA"]})  # fmt: skip
    duplicates, missing = v.check_seed_ids(seeds)
    assert duplicates.status == v.FAIL
    assert missing.status == v.INFO
    assert missing.examples["athlete_name"].tolist() == ["C"]


def test_seed_link_to_unknown_olympedia_id_fails():
    seeds = pd.DataFrame({"athlete_name": ["Neeraj Chopra", "Typo"],
                          "olympedia_athlete_id": ["143754", "999999"]})  # fmt: skip
    result = v.check_seed_links(seeds, olympedia_rows(JAVELIN_2024))
    assert result.status == v.FAIL
    assert result.examples["athlete_name"].tolist() == ["Typo"]


def test_every_individual_discipline_has_a_plausible_range():
    individual = {d for d, (group, _) in DISCIPLINES.items() if group != "relays"}
    assert set(v.PLAUSIBLE) == individual


def test_report_returns_exit_codes(capsys):
    assert v.report([v.CheckResult("s", "ok", v.PASS, "fine")]) == 0
    assert "All checks passed." in capsys.readouterr().out
    assert v.report([v.CheckResult("s", "broken", v.FAIL, "bad")]) == 1
    assert "1 check(s) failed" in capsys.readouterr().out


def test_missing_inputs_fail():
    results = v.run_checks({})
    assert {r.source for r in results if r.status == v.FAIL} == {
        "olympedia", "worlds", "wa_toplists", "wa_athletes", "wa_marks", "seeds"}  # fmt: skip


@pytest.mark.parametrize("status", [v.PASS, v.INFO])
def test_info_never_causes_failure(status):
    assert v.report([v.CheckResult("s", "x", status, "d")]) == 0

def test_run_checks_on_small_valid_inputs_gives_only_passing_results():
    olympedia_columns = ["edition_year", "event_key", "athlete_name", "noc", "position",
                         "medal", "mark_raw", "olympedia_athlete_id"]
    inputs = {
        "olympedia": pd.DataFrame(JAVELIN_2024, columns=olympedia_columns),
        "worlds": pd.DataFrame(
            [(2023, "jt_m", "Gold", "Neeraj Chopra", "India", "88.17 m"),
             (2023, "jt_m", "Silver", "Arshad Nadeem", "Pakistan", "87.82 m SB"),
             (2023, "jt_m", "Bronze", "Jakub Vadlejch", "Czech Republic", "86.67 m")],
            columns=["championship_year", "event_key", "medal", "athlete_name",
                     "country_name", "mark_raw"],
        ),
        "wa_toplists": pd.DataFrame({"season": [2024], "event_key": ["jt_m"],
                                     "athlete_name": ["Neeraj CHOPRA"], "wa_id": ["14549089"],
                                     "mark_raw": ["89.49"]}),
        "wa_athletes": pd.DataFrame({"wa_id": ["14549089"], "country_code": ["IND"],
                                     "birth_date": [date(1997, 12, 24)]}),
        "wa_marks": pd.DataFrame({"wa_id": ["14549089"], "event_key": ["jt_m"],
                                  "kind": ["personal_best"], "mark_raw": ["90.23"],
                                  "date": [date(2025, 5, 16)], "indoor": [False],
                                  "not_legal": [False]}),
        "seeds": pd.DataFrame({"athlete_name": ["Neeraj Chopra"], "wa_id": ["14549089"],
                               "olympedia_athlete_id": ["143754"], "notes": [""]}),
    }
    results = v.run_checks(inputs)
    assert all(isinstance(r, v.CheckResult) for r in results)
    assert [r.name for r in results if r.status != v.PASS] == []

    assert any(r.source == "toplists" for r in results)  # the toplist checks actually ran

def test_world_record_level_marks_are_not_flagged():
    rows = [(2023, "sp_m", "Ryan Crouser", "USA", 1, "Gold", "23.56", 1),
            (1996, "jt_m", "Jan Zelezny", "CZE", 1, "Gold", "98.48", 2),
            (1988, "dt_w", "Gabriele Reinsch", "GDR", 1, "Gold", "76.80", 3),
            (2025, "pv_m", "Mondo Duplantis", "SWE", 1, "Gold", "6.30", 4)]
    better, _ = v.check_ranges(olympedia_rows(rows), "test")
    assert better.status == v.PASS