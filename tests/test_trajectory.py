import numpy as np
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



def _simulated(n_per_group=60, gap=-3.0, slope_diff=0.0, seed=1):
    """Made-up careers with a known gap at 18 and a known difference in yearly improvement."""
    rng = np.random.default_rng(seed)
    rows = []
    for india in (0, 1):
        for i in range(n_per_group):
            level = 91.0 + india * gap + rng.normal(0, 2)
            slope = 1.5 + india * slope_diff + rng.normal(0, 0.3)
            start = int(rng.integers(16, 21))
            for age in range(start, start + 8):
                years = age - 18
                index = level + slope * years - 0.05 * years**2 + rng.normal(0, 0.8)
                rows.append({"wa_id": f"sim-{india}-{i}", "event_key": "lj_m", "age": age,
                             "perf_index": index, "india": india})  # fmt: skip
    frame = pd.DataFrame(rows)
    return tr.model_frame(frame[frame["india"] == 1].drop(columns="india"),
                          frame[frame["india"] == 0].drop(columns="india"))


def test_model_frame_measures_age_from_18_and_keeps_the_model_ages():
    india = pd.DataFrame({"wa_id": ["1", "1"], "event_key": ["lj_m", "lj_m"], "age": [18, 33],
                          "perf_index": [90.0, 95.0]})  # fmt: skip
    finalists = pd.DataFrame({"wa_id": ["2"], "event_key": ["lj_m"], "age": [21],
                              "perf_index": [96.0]})  # fmt: skip
    frame = tr.model_frame(india, finalists)
    assert frame["age"].tolist() == [18, 21]  # 33 is outside 16-30
    assert frame["years"].tolist() == [0, 3]
    assert frame["india"].tolist() == [1, 0]
    assert frame["unit"].tolist() == ["1|lj_m", "2|lj_m"]


def test_model_recovers_a_known_gap_at_18_and_equal_improvement():
    result = tr.fit_trajectory_model(_simulated(gap=-3.0, slope_diff=0.0))
    effects = tr.group_effects(result).set_index("term")
    gap = effects.loc["india"]
    assert gap["ci_low"] < -3.0 < gap["ci_high"]
    assert gap["ci_high"] < 0  # clearly behind at 18
    slope = effects.loc["india:years"]
    assert slope["ci_low"] < 0 < slope["ci_high"]  # no real difference in improvement


def test_model_detects_slower_improvement_when_there_is_one():
    result = tr.fit_trajectory_model(_simulated(gap=0.0, slope_diff=-0.6, seed=2))
    slope = tr.group_effects(result).set_index("term").loc["india:years"]
    assert slope["ci_high"] < 0


def test_mean_curves_give_both_groups_at_every_model_age():
    result = tr.fit_trajectory_model(_simulated())
    curves = tr.mean_curves(result)
    assert len(curves) == 2 * 15  # ages 16-30
    at18 = curves[curves["age"] == 18].set_index("group")["perf_index"]
    assert at18["India"] < at18["Finalists"]



def test_event_families_group_similar_events():
    assert tr.event_family("110mh_m") == tr.event_family("100m_w") == "sprints and hurdles"
    assert tr.event_family("marathon_w") == tr.event_family("1500m_m") == "endurance"
    assert tr.event_family("jt_m") == "throws"


def test_robustness_refits_each_subset_and_skips_ones_too_small_to_fit():
    out = tr.robustness(_simulated(gap=-3.0)).set_index("subset")
    assert list(out.index) == ["all events", "jumps", "men", "women", "ages 16-28",
                               "cubic age curve"]
    assert out.loc["women", "note"] == "too few lines to fit"  # the made-up careers are all men
    assert out.loc["all events", "gap_low"] < 3.0 < out.loc["all events", "gap_high"]
    assert out.loc["jumps", "gap_at_18"] == pytest.approx(out.loc["all events", "gap_at_18"])
    assert out.loc["ages 16-28", "converged"]
    assert out.loc["all events", "optimizer"] in {"lbfgs", "powell"}
    # the simulated curve is quadratic, so a cubic term changes the gap at 18 very little
    assert out.loc["cubic age curve", "gap_at_18"] == pytest.approx(
        out.loc["all events", "gap_at_18"], abs=0.5)


def test_variance_parts_and_residuals_look_like_the_simulation():
    frame = _simulated()
    result = tr.fit_trajectory_model(frame)
    parts = tr.variance_parts(result)
    assert parts["sd_level_at_18"] == pytest.approx(2.0, abs=0.6)  # simulated with sd 2
    assert parts["sd_season_noise"] == pytest.approx(0.8, abs=0.2)  # simulated with sd 0.8
    check = tr.residual_check(result, frame)
    assert set(check["group"]) == {"India", "Finalists"}
    assert check["mean"].abs().max() < 0.6  # the right curve shape leaves no pattern by age