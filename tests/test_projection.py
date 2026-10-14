import numpy as np

from src import projection as pj
from tests.test_backtest import _careers


def test_only_active_indian_athletes_within_the_tested_horizon_are_projected():
    frame = _careers()
    origins = pj.projection_origins(frame)
    assert set(origins["india"]) == {1}
    assert (origins["last_season"] >= pj.ACTIVE_SINCE).all()
    assert origins["horizon"].between(1, 4).all()
    row = origins.iloc[0]
    unit = frame[frame["unit"] == row["unit"]]
    born = int((unit["season"] - unit["age"]).iloc[0])
    assert row["target_age"] == 2028 - born


def test_projections_come_with_a_range_and_are_sorted_best_first():
    out = pj.project(_careers())
    assert len(out) > 0
    assert out["projected"].is_monotonic_decreasing
    assert (out["low"] < out["projected"]).all() and (out["projected"] < out["high"]).all()
    assert out["range_reaches_bronze"].dtype == bool
    assert (out["beyond_trained_ages"] == (out["target_age"] > 30)).all()
    assert np.isfinite(out[["projected", "low", "high"]]).all().all()