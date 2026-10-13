import numpy as np
import pandas as pd
import pytest

from src import backtest as bt


def _careers(n_per_group=40, seed=3):
    """Made-up careers with seasons: steady improvement that flattens, plus season noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for india in (0, 1):
        for i in range(n_per_group):
            born = int(rng.integers(1996, 2004))
            level = 90.0 - 4.0 * india + rng.normal(0, 2)
            slope = 1.5 + rng.normal(0, 0.3)
            for season in range(born + 16, min(born + 31, 2027)):
                age = season - born
                years = age - 18
                index = level + slope * years - 0.05 * years**2 + rng.normal(0, 0.8)
                rows.append({"wa_id": f"sim-{india}-{i}", "event_key": "lj_m", "season": season,
                             "age": age, "perf_index": index, "india": india})  # fmt: skip
    df = pd.DataFrame(rows)
    return df.assign(years=df["age"] - 18, unit=df["wa_id"] + "|" + df["event_key"])


def _tiny():
    """Three hand-made athlete-events around a 2022 cutoff."""
    return pd.DataFrame({
        "unit": ["a"] * 4 + ["b"] * 2 + ["c"] * 3,
        "wa_id": ["a"] * 4 + ["b"] * 2 + ["c"] * 3,
        "event_key": ["lj_m"] * 9,
        "season": [2020, 2021, 2022, 2023, 2022, 2023, 2016, 2017, 2023],
        "age": [18, 19, 20, 21, 20, 21, 18, 19, 25],
        "perf_index": [88.0, 90.0, 91.0, 92.0, 85.0, 86.0, 80.0, 82.0, 90.0],
        "india": [1] * 4 + [0] * 2 + [0] * 3,
    }).assign(years=lambda d: d["age"] - 18)  # fmt: skip


def test_split_is_by_time_and_needs_enough_history():
    train, test = bt.split_by_season(_tiny())
    assert train["season"].max() <= 2022 and test["season"].min() > 2022
    assert set(test["unit"]) == {"a"}  # b has one training season; c's 2023 is 6 seasons on
    row = test.iloc[0]
    assert (row["last_index"], row["last_age"], row["horizon"]) == (91.0, 20, 1)
    assert row["recent_change"] == pytest.approx(1.0)  # 90 -> 91 over one season
    assert row["best_index"] == 91.0


def test_training_pairs_use_only_training_seasons_and_short_horizons():
    train, _ = bt.split_by_season(_careers())
    pairs = bt.training_pairs(train)
    assert pairs["horizon"].between(1, bt.MAX_HORIZON).all()
    assert pairs["last_season"].max() < 2022  # a pair's origin always has a later training season
    assert set(bt.FEATURES) <= set(pairs.columns)


def test_simple_contenders_on_a_hand_example():
    data = _tiny()
    train, test = bt.split_by_season(data)
    assert bt.predict_last_season(train, test).tolist() == [91.0]
    # back-to-back changes in training: a +2 (age 19), a +1 (age 20), c +2 (age 19)
    # so age 21 has no data (adds 0): prediction stays at 91
    assert bt.predict_age_trend(train, test).tolist() == [pytest.approx(91.0)]


def test_backtest_on_simulated_careers_ranks_contenders_sensibly():
    preds = bt.run_backtest(_careers())
    scores = bt.score(preds).set_index("contender")
    assert list(scores.index) == bt.CONTENDERS
    # athletes keep improving, so following each athlete beats both naive rules
    assert scores.loc["mixed_model", "mae"] < scores.loc["last_season", "mae"]
    assert scores.loc["mixed_model", "mae"] < scores.loc["fixed_curve", "mae"]
    # an honest 80% interval should hold roughly 80% of the real values
    assert 0.65 < scores.loc["mixed_model", "coverage_80"] < 0.95
    assert np.isnan(scores.loc["boosting", "coverage_80"])


def test_score_is_zero_for_perfect_predictions():
    preds = bt.split_by_season(_careers())[1]
    for name in bt.CONTENDERS:
        preds[f"{name}_pred"] = preds["perf_index"]
    preds["mixed_low"], preds["mixed_high"] = preds["perf_index"] - 1, preds["perf_index"] + 1
    scores = bt.score(preds)
    assert (scores["mae"] == 0).all() and (scores["bias"] == 0).all()
    assert scores.set_index("contender").loc["mixed_model", "coverage_80"] == 1.0


def test_every_contender_is_logged_to_mlflow_with_settings_and_errors(tmp_path):
    import mlflow

    preds = bt.run_backtest(_careers(n_per_group=15))
    scores = bt.score(preds)
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    run_ids = bt.log_to_mlflow(preds, scores, {"cutoff": 2022}, tracking_uri=uri,
                               artifact_dir=tmp_path / "artifacts", experiment="test")  # fmt: skip
    assert len(run_ids) == len(bt.CONTENDERS)
    mlflow.set_tracking_uri(uri)
    runs = mlflow.search_runs(experiment_names=["test"])
    assert set(runs["params.contender"]) == set(bt.CONTENDERS)
    assert (runs["params.cutoff"] == "2022").all()
    assert runs["metrics.mae"].notna().all()
    logged = list((tmp_path / "artifacts").rglob("*_predictions.csv"))
    assert len(logged) == len(bt.CONTENDERS)