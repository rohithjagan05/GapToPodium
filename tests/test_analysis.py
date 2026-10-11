import math

import pandas as pd
import pytest

from src import analysis as an

# The real Paris 2024 men's javelin podium (Olympedia) and the top of the real 2024 world toplist.
# Only Neeraj Chopra's World Athletics ID is real; the others are labelled placeholders.
PODIUM = pd.DataFrame({
    "championship_year": [2024] * 3, "event_key": ["jt_m"] * 3,
    "athlete_name": ["Arshad Nadeem", "Neeraj Chopra", "Anderson Peters"],
    "country_code": ["PAK", "IND", "GRN"], "position": [1, 2, 3],
    "mark_value": [92.97, 89.45, 88.54], "higher_is_better": [True] * 3,
})
TOPLIST = pd.DataFrame({
    "season": [2024] * 4, "event_key": ["jt_m"] * 4,
    "athlete_name": ["Arshad NADEEM", "Anderson PETERS", "Max DEHNING", "Neeraj CHOPRA"],
    "country_code": ["PAK", "GRN", "GER", "IND"],
    "wa_id": ["placeholder-1", "placeholder-2", "placeholder-3", "14549089"],
    "mark_value": [92.97, 90.61, 90.20, 89.49], "world_rank": [1, 2, 3, 4],
})


def test_every_medallist_is_matched_to_their_season_best():
    matched = an.match_medallists(PODIUM, TOPLIST)
    assert (matched["match"] == "name+country").all()
    neeraj = matched.set_index("athlete_name").loc["Neeraj Chopra"]
    assert (neeraj["wa_id"], neeraj["season_best"], neeraj["world_rank"]) == ("14549089", 89.49, 4)


def test_tokyo_2020_uses_the_2021_toplist():
    assert an.olympic_season(2020) == 2021 and an.olympic_season(2024) == 2024
    tokyo = PODIUM.assign(championship_year=2020)
    assert (an.match_medallists(tokyo, TOPLIST)["match"] == "not found").all()
    assert (an.match_medallists(tokyo, TOPLIST.assign(season=2021))["season_best"].notna()).all()


def test_two_namesakes_without_a_country_match_are_ambiguous_not_guessed():
    podium = PODIUM.iloc[[1]].assign(athlete_name="Gurpreet Singh", country_code="IND")
    toplist = TOPLIST.iloc[:2].assign(athlete_name=["Gurpreet SINGH", "Gurpreet SINGH"])
    assert an.match_medallists(podium, toplist)["match"].tolist() == ["ambiguous"]


def test_third_best_follows_the_event_direction():
    assert an.third_best([92.97, 89.49, 90.61], higher_is_better=True) == 89.49
    assert an.third_best([100.0, 102.0, 101.0], higher_is_better=False) == 102.0
    assert an.third_best([10.0, 11.0], higher_is_better=False) == 11.0  # two marks: the worse one
    assert an.third_best([], higher_is_better=True) is None


def test_season_best_threshold_uses_the_third_best_podium_season_best():
    per_games = an.season_best_bronze(an.match_medallists(PODIUM, TOPLIST))
    assert per_games[["event_key", "season", "sb_bronze"]].values.tolist() == [["jt_m", 2024, 89.49]]
    averaged = an.average_over_games(per_games)
    assert (averaged["sb_threshold"].iloc[0], averaged["games_used"].iloc[0]) == (89.49, 1)


def test_gap_pct_is_signed_so_positive_means_behind():
    gaps = an.gap_pct([90.23, 13.10, None], [86.45, 13.00, 13.00], [True, False, False])
    assert round(gaps[0], 2) == -4.37  # Neeraj's 90.23 against the 86.45 final-race threshold
    assert round(gaps[1], 2) == 0.77
    assert math.isnan(gaps[2])

def test_short_names_fall_back_to_surname_and_country():
    podium = PODIUM.iloc[[0]].assign(athlete_name="Mondo Duplantis", country_code="SWE",
                                     event_key="pv_m", mark_value=6.25)  # fmt: skip
    toplist = TOPLIST.iloc[:2].assign(event_key="pv_m", athlete_name=["Armand DUPLANTIS", "Sam KENDRICKS"],
                                      country_code=["SWE", "USA"], mark_value=[6.26, 6.00])  # fmt: skip
    hit = an.match_medallists(podium, toplist).iloc[0]
    assert (hit["match"], hit["season_best"], hit["sb_consistent"]) == ("surname+country", 6.26, True)


def test_a_season_best_worse_than_the_olympic_mark_is_flagged_and_left_out():
    toplist = TOPLIST.assign(mark_value=[92.97, 90.61, 90.20, 85.00])  # Neeraj's SB below his 89.45
    matched = an.match_medallists(PODIUM, toplist)
        # podium order: Nadeem, Chopra, Peters; only Neeraj's impossible season best is flagged
    assert matched["sb_consistent"].tolist() == [True, False, True]
    per_games = an.season_best_bronze(matched)
    assert per_games["medallists_matched"].iloc[0] == 2  # only the two consistent matches count

def test_rank_test_detects_worse_ranks_in_tactical_events():
    matched = pd.DataFrame({
        "discipline_group": ["long_distance"] * 6 + ["throws"] * 6 + ["throws"],
        "world_rank": [14, 41, 93, 62, 13, 8] + [1, 2, 3, 4, 2, 5] + [500],
        "sb_consistent": [True] * 12 + [False],  # the inconsistent match must be ignored
    })
    out = an.medallist_rank_test(matched)
    assert (out["n_tactical"], out["n_all_out"]) == (6, 6)
    assert out["median_rank_tactical"] > out["median_rank_all_out"]
    assert out["p_value"] < 0.05


def test_rank_test_finds_nothing_when_groups_are_alike():
    ranks = [1, 5, 9, 3, 7, 2]
    matched = pd.DataFrame({"discipline_group": ["road"] * 6 + ["jumps"] * 6,
                            "world_rank": ranks + ranks, "sb_consistent": [True] * 12})  # fmt: skip
    assert an.medallist_rank_test(matched)["p_value"] > 0.4

# --- bootstrap confidence intervals ---------------------------------------------------------------


def test_repeatable_level_is_the_mean_of_the_best_three():
    best_three_throws = (88.05 + 85.83 + 85.69) / 3
    best_three_times = (13.03 + 13.05 + 13.10) / 3
    assert an.repeatable_level([85.69, 79.61, 85.83, 88.05], True) == pytest.approx(best_three_throws)
    assert an.repeatable_level([13.10, 13.03, 13.40, 13.05], False) == pytest.approx(best_three_times)
    assert math.isnan(an.repeatable_level([88.05, 85.83], higher_is_better=True))


def test_bootstrap_interval_contains_the_level_and_is_reproducible():
    marks = [85.69, 79.61, 85.83, 88.05, 84.10, 86.40]
    first = an.bootstrap_level(marks, higher_is_better=True, n_boot=2000)
    assert first == an.bootstrap_level(marks, higher_is_better=True, n_boot=2000)
    level, low, high = first
    assert low <= level <= high
    assert high <= max(marks)


def test_one_great_race_widens_the_interval():
    steady = [85.0, 85.1, 84.9, 85.2, 85.0, 84.8]
    one_off = [85.0, 85.1, 84.9, 85.2, 85.0, 91.0]
    _, lo_s, hi_s = an.bootstrap_level(steady, higher_is_better=True)
    _, lo_o, hi_o = an.bootstrap_level(one_off, higher_is_better=True)
    assert (hi_o - lo_o) > (hi_s - lo_s)


def test_gap_intervals_use_the_best_athletes_races_and_need_three():
    races = pd.DataFrame({
        "wa_id": ["14549089"] * 4 + ["other"] * 2,
        "event_key": ["jt_m"] * 4 + ["lj_m"] * 2,
        "mark_value": [85.69, 79.61, 85.83, 88.05, 8.20, 8.10],
    })
    best = pd.DataFrame({
        "event_key": ["jt_m", "lj_m"], "best_wa_id": ["14549089", "other"],
        "best_mark": [90.23, 8.38], "higher_is_better": [True, True],
        "bronze_threshold": [86.45, 8.28],
    })
    out = an.gap_intervals(races, best, n_boot=1000).set_index("event_key")
    jt = out.loc["jt_m"]
    assert (jt["races"], round(jt["gap_best"], 2)) == (4, -4.37)
    assert jt["gap_level"] > jt["gap_best"]  # the repeatable level is below the single best
    assert jt["gap_low"] <= jt["gap_level"] <= jt["gap_high"]
    assert out.loc["lj_m", "races"] == 2 and math.isnan(out.loc["lj_m", "gap_low"])

def test_clean_races_drops_indoor_illegal_and_combined_event_parts():
    d = pd.to_datetime(["2026-05-25", "2026-06-28", "2026-05-24", "2026-05-03", "2026-06-25"]).date
    races = pd.DataFrame({
        "wa_id": ["14921137"] * 3 + ["14859017"] * 2,
        "event_key": ["hep_w", "hep_w", "100mh_w", "pv_w", "pv_w"],
        "season": [2026] * 5, "date": d,
        "mark_raw": ["5632", "5619", "14.49", "4.23", "4.20"],
        "competition": [""] * 5, "race": ["F", "F", "CE2", "F", "F"], "place": [""] * 5,
        "indoor": [False, False, False, True, False], "not_legal": [False] * 5,
    })
    # the illegal 5632 appears twice (season best and progression), as in the real marks table
    marks = pd.DataFrame({"wa_id": ["14921137"] * 2, "event_key": ["hep_w"] * 2,
                          "date": pd.to_datetime(["2026-05-25"] * 2), "mark_raw": ["5632"] * 2,
                          "not_legal": [True] * 2})  # fmt: skip
    kept = an.clean_races(races, marks)
    assert kept["mark_raw"].tolist() == ["5619", "4.20"]


# --- H2: improvement rates ----------------------------------------------------------------------


def _progression(wa_id, event_key, seasons, marks):
    return pd.DataFrame({"wa_id": wa_id, "event_key": event_key, "kind": "season_progression",
                         "season": seasons, "mark_raw": marks, "indoor": False,
                         "not_legal": False})  # fmt: skip


def test_season_bests_keep_the_athletes_own_events_and_the_best_per_season():
    marks = pd.concat([
        _progression("1", "jt_m", [2015, 2016, 2016], ["70.00", "79.00", "82.23"]),
        _progression("1", "dt_m", [2016], ["40.00"]),  # not one of the athlete's events
    ])
    sbs = an.season_bests(marks, {"1": {"jt_m"}})
    assert sbs[["season", "mark_value"]].sort_values("season").values.tolist() == [
        [2015, 70.0], [2016, 82.23]]


def test_improvement_is_positive_when_better_for_both_directions():
    sbs = pd.DataFrame({"wa_id": ["1", "1", "2", "2"], "event_key": ["jt_m", "jt_m", "400m_m", "400m_m"],
                        "season": [2016, 2017, 2016, 2017], "mark_value": [80.0, 88.0, 46.0, 45.54],
                        "higher_is_better": [True, True, False, False]})  # fmt: skip
    out = an.annual_improvements(sbs, {"1": 1997, "2": 1997}).set_index("wa_id")
    assert out.loc["1", "improvement_pct"] == pytest.approx(10.0)
    assert out.loc["2", "improvement_pct"] == pytest.approx(1.0)


def test_only_back_to_back_seasons_inside_the_age_window_count():
    sbs = pd.DataFrame({"wa_id": ["1"] * 4, "event_key": ["jt_m"] * 4,
                        "season": [2014, 2015, 2017, 2018], "mark_value": [60.0, 66.0, 80.0, 84.0],
                        "higher_is_better": [True] * 4})  # fmt: skip
    out = an.annual_improvements(sbs, {"1": 1997}, age_window=(18, 21))
    assert out["season"].tolist() == [2015, 2018]  # 2015-17 is a gap; 2018 is age 21
    assert an.annual_improvements(sbs, {"1": 1997}, age_window=(18, 20))["season"].tolist() == [2015]


def test_improvement_test_counts_each_athlete_once():
    india = pd.DataFrame({"wa_id": ["a", "a", "a", "b", "c"], "improvement_pct": [1, 1, 9, 0.5, 1.5]})
    finalists = pd.DataFrame({"wa_id": list("defgh"), "improvement_pct": [4, 5, 6, 3, 4.5]})
    out = an.improvement_test(india, finalists)
    assert (out["n_india"], out["n_finalists"]) == (3, 5)
    assert out["median_improvement_india"] == 1.0
    assert out["p_value"] < 0.05