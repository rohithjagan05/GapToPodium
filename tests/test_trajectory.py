import pandas as pd
import pytest

from src import trajectory as tr

# Made-up season bests for labelled placeholder athletes; thresholds are round test numbers.
SBS = pd.DataFrame({
    "wa_id": ["sprinter-1"] * 3 + ["jumper-1"] * 2 + ["no-birth-year"] + ["thrower-1"],
    "event_key": ["100m_m"] * 3 + ["lj_m"] * 2 + ["lj_m"] + ["jt_m"],
    "season": [2019, 2020, 2021, 2023, 2022, 2023, 2024],
    "mark_value": [10.50, 10.30, 10.10, 8.00, 7.80, 7.50, 80.00],
    "higher_is_better": [False] * 3 + [True] * 4,
})
BIRTH_YEARS = {"sprinter-1": 2001, "jumper-1": 2004, "thrower-1": 2000}
THRESHOLDS = {"100m_m": 9.90, "lj_m": 8.25}  # no javelin threshold on purpose


def test_index_is_100_at_bronze_level_and_higher_is_always_better():
    idx = tr.performance_index([8.25, 8.00, 9.90, 10.00], [8.25, 8.25, 9.90, 9.90],
                               [True, True, False, False])  # fmt: skip
    assert idx[0] == pytest.approx(100) and idx[2] == pytest.approx(100)
    assert idx[1] == pytest.approx(96.97, abs=0.01)  # 8.00 m is about 3% short of 8.25 m
    assert idx[3] == pytest.approx(99.0)  # 10.00 s against 9.90 s


def test_ages_and_index_are_added_per_season():
    traj = tr.age_aligned(SBS, BIRTH_YEARS, THRESHOLDS)
    assert list(traj.columns) == tr.TRAJECTORY_COLUMNS
    sprinter = traj[traj["wa_id"] == "sprinter-1"]
    assert sprinter["age"].tolist() == [18, 19, 20]
    assert sprinter["perf_index"].is_monotonic_increasing  # times got faster, so the index rises


def test_rows_without_birth_year_or_threshold_are_dropped():
    traj = tr.age_aligned(SBS, BIRTH_YEARS, THRESHOLDS)
    assert "no-birth-year" not in set(traj["wa_id"])
    assert "jt_m" not in set(traj["event_key"])
    missing = tr.age_aligned(SBS, BIRTH_YEARS, {**THRESHOLDS, "100m_m": float("nan")})
    assert "100m_m" not in set(missing["event_key"])


def test_impossible_ages_are_dropped_and_rows_are_sorted():
    traj = tr.age_aligned(SBS, {**BIRTH_YEARS, "jumper-1": 2010}, THRESHOLDS)
    assert "jumper-1" not in set(traj["wa_id"])  # ages 12 and 13 are outside 15-40
    jumper = tr.age_aligned(SBS, BIRTH_YEARS, THRESHOLDS)
    assert jumper[jumper["wa_id"] == "jumper-1"]["season"].tolist() == [2022, 2023]