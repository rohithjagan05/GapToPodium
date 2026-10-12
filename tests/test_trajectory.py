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



def test_season_best_threshold_is_preferred_and_the_source_is_recorded():
    fair = pd.DataFrame({"event_key": ["1500m_m", "lj_m", "hj_w"],
                         "sb_threshold": [210.0, None, None],
                         "bronze_threshold": [213.0, 8.25, None]})  # fmt: skip
    out = tr.pick_thresholds(fair).set_index("event_key")
    assert out.loc["1500m_m", "threshold"] == 210.0
    assert out.loc["1500m_m", "source"] == "medallists' season bests"
    assert out.loc["lj_m", "source"] == "final's bronze mark"
    assert "hj_w" not in out.index  # no threshold at all: left out, not guessed


def _write_run(run_dir, athletes, marks):
    run_dir.mkdir(parents=True)
    pd.DataFrame(athletes).to_parquet(run_dir / "athletes.parquet")
    pd.DataFrame(marks).to_parquet(run_dir / "marks.parquet")


def test_load_group_uses_the_newest_run_own_events_and_excludes_a_country(tmp_path):
    athletes = {"wa_id": ["1", "2"], "country_code": ["KEN", "IND"],
                "birth_date": pd.to_datetime(["2000-05-01", "2001-01-01"])}  # fmt: skip
    marks = {"wa_id": ["1", "1", "2"], "event_key": ["1500m_m", "800m_m", "1500m_m"],
             "kind": "season_progression", "season": [2019, 2019, 2019],
             "mark_raw": ["3:40.00", "1:50.00", "3:45.00"], "indoor": False, "not_legal": False}
    _write_run(tmp_path / "wa_finalists" / "20261001T000000Z", athletes, marks)
    _write_run(tmp_path / "wa_finalists" / "20261011T000000Z", athletes, marks)
    (tmp_path / "wa_finalists" / "20261012T000000Z").mkdir()  # an unfinished run: no marks yet
    seeds = tmp_path / "seeds.csv"
    seeds.write_text("athlete_name,sex,events,wa_id,country_code\n"
                     "Runner One,m,1500m_m,1,KEN\nRunner Two,m,1500m_m,2,IND\n")  # fmt: skip

    run = tr.latest_run(tmp_path / "wa_finalists")
    assert run.name == "20261011T000000Z"
    sbs, births = tr.load_group(run, seeds, exclude_country="IND")
    assert births == {"1": 2000}
    assert sbs["event_key"].tolist() == ["1500m_m"]  # the 800 m is not one of the seeded events
    assert sbs["mark_value"].tolist() == [220.0]


def test_latest_run_fails_clearly_when_nothing_was_scraped(tmp_path):
    with pytest.raises(FileNotFoundError):
        tr.latest_run(tmp_path)


def test_level_by_age_counts_each_athlete_once_per_age():
    traj = pd.DataFrame({"wa_id": ["a", "a", "b", "c"], "age": [18, 18, 18, 19],
                         "perf_index": [90.0, 94.0, 92.0, 96.0]})  # fmt: skip
    out = tr.level_by_age(traj).set_index("age")
    assert out.loc[18, "athletes"] == 2  # athlete a's two events count once, at 94
    assert out.loc[18, "median"] == pytest.approx(93.0)
    assert out.loc[19, "athletes"] == 1