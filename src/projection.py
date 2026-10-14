"""Phase 4 projections: where are India's active athletes likely to be in 2028?

Uses the backtest's winner, gradient boosting, trained on every season we have (both groups). The
80% range comes from boosting's real misses in the backtest (fit to 2022, predict 2023-2026) at
the same number of seasons ahead, so the projections come with measured, not assumed, accuracy.
"""

from __future__ import annotations

import pandas as pd

from src.backtest import (
    CUTOFF,
    FEATURES,
    MAX_HORIZON,
    MIN_HISTORY,
    boosting_misses,
    fit_boosting,
    history_features,
    range_offsets,
    training_pairs,
)
from src.trajectory import MODEL_AGES

TARGET_SEASON = 2028  # the Los Angeles Olympics
ACTIVE_SINCE = 2025  # an athlete-event counts as active if it has a season from here on
BRONZE = 100.0  # performance index at the bronze threshold


def projection_origins(frame: pd.DataFrame, target_season: int = TARGET_SEASON,
                       active_since: int = ACTIVE_SINCE,
                       min_history: int = MIN_HISTORY) -> pd.DataFrame:  # fmt: skip
    """Active Indian athlete-events and what is known at their latest season.

    Kept only if they have at least min_history seasons, a season since active_since, and the
    target season is at most MAX_HORIZON seasons after their latest one (the range the backtest
    tested).
    """
    india = frame[frame["india"] == 1]
    counts = india.groupby("unit").size()
    india = india[india["unit"].isin(counts[counts >= min_history].index)]
    origins = history_features(india)
    birth = (india["season"] - india["age"]).groupby(india["unit"]).first()
    origins = origins.assign(target_age=target_season - origins["unit"].map(birth),
                             horizon=target_season - origins["last_season"])  # fmt: skip
    keep = (origins["last_season"] >= active_since) & (origins["horizon"] <= MAX_HORIZON)
    return origins[keep].reset_index(drop=True)


def project(frame: pd.DataFrame, target_season: int = TARGET_SEASON, seed: int = 0) -> pd.DataFrame:
    """Projected performance index in the target season, with an 80% range, best first."""
    origins = projection_origins(frame, target_season)
    pairs = training_pairs(frame)
    projected = fit_boosting(pairs, seed).predict(origins[FEATURES])
    offsets = range_offsets(boosting_misses(frame, CUTOFF, seed)).loc[origins["horizon"]]
    cols = ["unit", "last_season", "last_age", "last_index", "best_index", "target_age", "horizon"]
    out = origins[cols].assign(projected=projected,
                               low=projected + offsets["low"].to_numpy(),
                               high=projected + offsets["high"].to_numpy())  # fmt: skip
    out["range_reaches_bronze"] = out["high"] >= BRONZE
        # training seasons stop at age 30, so older target ages are extrapolated: flag, don't hide
    out["beyond_trained_ages"] = out["target_age"] > MODEL_AGES[1]
    return out.sort_values("projected", ascending=False).reset_index(drop=True)