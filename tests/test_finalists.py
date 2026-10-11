import pandas as pd

from src.finalists import SEED_COLUMNS, finalists_seed

# Real names and countries; only Neeraj Chopra's World Athletics ID is real.
FINALISTS = pd.DataFrame({
    "championship_year": [2024] * 4,
    "event_key": ["jt_m", "jt_m", "5000m_m", "10000m_m"],
    "athlete_name": ["Neeraj Chopra", "Nobody Known", "Grant Fisher", "Grant Fisher"],
    "country_code": ["IND", "XYZ", "USA", "USA"],
    "position": [2, 8, 3, 3],
    "mark_value": [89.45, 80.0, 795.13, None],  # the 10000 m mark is missing on purpose
    "higher_is_better": [True, True, False, False],
    "olympedia_athlete_id": [143754, 1, 2, 2],
})
TOPLIST = pd.DataFrame({
    "season": [2024] * 3,
    "event_key": ["jt_m", "5000m_m", "10000m_m"],
    "athlete_name": ["Neeraj CHOPRA", "Grant FISHER", "Grant FISHER"],
    "country_code": ["IND", "USA", "USA"],
    "wa_id": ["14549089", "placeholder-fisher", "placeholder-fisher"],
    "mark_value": [89.49, 771.84, 1603.46],
    "world_rank": [4, 14, 7],
})


def test_matched_finalists_become_seed_rows_and_unmatched_are_dropped():
    seeds = finalists_seed(FINALISTS, TOPLIST)
    assert list(seeds.columns) == SEED_COLUMNS
    assert set(seeds["wa_id"]) == {"14549089", "placeholder-fisher"}
    neeraj = seeds.set_index("wa_id").loc["14549089"]
    assert (neeraj["athlete_name"], neeraj["sex"], neeraj["country_code"]) == (
        "Neeraj CHOPRA", "m", "IND")


def test_an_athlete_in_two_finals_gets_one_row_with_both_events():
    fisher = finalists_seed(FINALISTS, TOPLIST).set_index("wa_id").loc["placeholder-fisher"]
    assert fisher["events"] == "10000m_m;5000m_m"