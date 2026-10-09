import math

import pandas as pd

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