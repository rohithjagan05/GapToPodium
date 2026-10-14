"""Phase 4 backtest: can the trajectory model predict seasons it has never seen?

Everything up to a cutoff season is used for fitting; every later season is hidden and then
predicted. The split is by time, never at random, so no model ever sees an athlete's future. Five
contenders predict the same hidden seasons:

- last_season: next season equals the athlete's last known season (the simplest guess)
- age_trend: the last known season plus the typical change at each age
- fixed_curve: plain regression, the group's average age curve only (ignores the athlete)
- boosting: gradient boosting on the athlete's history (a flexible machine-learning rival)
- mixed_model: the Phase 4 mixed-effects model (the athlete's own line, continued)

Errors are in performance-index points (1 point is about 1% of the bronze threshold).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import PROJECT_ROOT
from src.trajectory import FORMULA, event_family, fit_trajectory_model

CUTOFF = 2022  # fit on seasons up to here, predict the seasons after it
MIN_HISTORY = 2  # an athlete-event needs this many seasons up to the cutoff to be predicted
MAX_HORIZON = 4  # predict up to four seasons after the athlete's last known season
INTERVAL_Z = 1.2816  # 80% prediction interval (normal quantile)
LOW_Q, HIGH_Q = 0.1, 0.9  # boosting's 80% range: the 10th and 90th percentile of its past misses
CALIBRATION_GAP = 4  # boosting's range is learned from an inner backtest ending this many seasons earlier
TRACKING_URI = f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"  # local, not committed
ARTIFACT_DIR = PROJECT_ROOT / "mlartifacts"  # files logged with each run, not committed
EXPERIMENT = "phase4-backtest"
CONTENDERS = ["last_season", "age_trend", "fixed_curve", "boosting", "mixed_model"]
FEATURES = ["last_index", "last_age", "best_index", "n_seasons", "recent_change", "india",
            "family_code", "target_age", "horizon"]  # fmt: skip
FAMILY_CODES = {"sprints and hurdles": 0, "endurance": 1, "jumps": 2, "throws": 3,
                "combined events": 4}  # fmt: skip


def split_by_season(frame: pd.DataFrame, cutoff: int = CUTOFF,
                    min_history: int = MIN_HISTORY) -> tuple[pd.DataFrame, pd.DataFrame]:  # fmt: skip
    """Training rows (seasons up to the cutoff) and test rows (later seasons).

    Test rows are kept only for athlete-events with at least min_history seasons in training,
    and only up to MAX_HORIZON seasons after that athlete-event's last training season.
    """
    train = frame[frame["season"] <= cutoff]
    counts = train.groupby("unit").size()
    known = counts[counts >= min_history].index
    origins = history_features(train[train["unit"].isin(known)])
    test = frame[(frame["season"] > cutoff) & frame["unit"].isin(known)]
    test = test.merge(origins.drop(columns="india"), on="unit", how="left")
    test = test.assign(horizon=test["season"] - test["last_season"], target_age=test["age"])
    test = test[test["horizon"].between(1, MAX_HORIZON)].reset_index(drop=True)
    return train.reset_index(drop=True), test


def _features_of(rows: pd.DataFrame) -> dict:
    """What is known about one athlete-event at its latest season in rows (sorted by season)."""
    last = rows.iloc[-1]
    recent = np.nan
    if len(rows) >= 2:
        prev = rows.iloc[-2]
        recent = (last["perf_index"] - prev["perf_index"]) / (last["season"] - prev["season"])
    return {"last_season": int(last["season"]), "last_age": int(last["age"]),
            "last_index": float(last["perf_index"]), "best_index": float(rows["perf_index"].max()),
            "n_seasons": len(rows), "recent_change": recent, "india": int(last["india"]),
            "family_code": FAMILY_CODES[event_family(last["event_key"])]}  # fmt: skip


def history_features(train: pd.DataFrame) -> pd.DataFrame:
    """One row per athlete-event: its features at its last training season."""
    rows = [{"unit": unit, **_features_of(grp.sort_values("season"))}
            for unit, grp in train.groupby("unit")]  # fmt: skip
    return pd.DataFrame(rows)


def training_pairs(train: pd.DataFrame) -> pd.DataFrame:
    """Examples for the boosting model, built from training seasons only.

    For every athlete-event and every season in its history, the features known at that season
    are paired with each later training season up to MAX_HORIZON seasons ahead, so the model
    learns the same task it is tested on.
    """
    rows = []
    for unit, grp in train.groupby("unit"):
        grp = grp.sort_values("season").reset_index(drop=True)
        for i in range(len(grp)):
            known = _features_of(grp.iloc[: i + 1])
            for j in range(i + 1, len(grp)):
                horizon = int(grp.loc[j, "season"]) - known["last_season"]
                if horizon > MAX_HORIZON:
                    break
                rows.append({"unit": unit, **known, "target_age": int(grp.loc[j, "age"]),
                             "horizon": horizon, "perf_index": float(grp.loc[j, "perf_index"])})  # fmt: skip
    return pd.DataFrame(rows)


# --- the five contenders -----------------------------------------------------------------------

def predict_last_season(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    return test["last_index"].to_numpy()


def predict_age_trend(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Last known season plus the average change at each age between back-to-back seasons."""
    t = train.sort_values(["unit", "season"])
    step = t.groupby("unit")["season"].diff() == 1
    change = (t["perf_index"] - t.groupby("unit")["perf_index"].shift())[step]
    by_age = change.groupby(t.loc[step, "age"]).mean()
    preds = []
    for last_index, last_age, target_age in zip(test["last_index"], test["last_age"],
                                                test["target_age"]):  # fmt: skip
        gain = sum(by_age.get(a, 0.0) for a in range(int(last_age) + 1, int(target_age) + 1))
        preds.append(last_index + gain)
    return np.array(preds)


def predict_fixed_curve(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Plain regression: each group's average age curve, the same for every athlete."""
    import statsmodels.formula.api as smf

    return smf.ols(FORMULA, train).fit().predict(test).to_numpy()


def fit_boosting(pairs: pd.DataFrame, seed: int = 0):
    """Gradient boosting on training pairs: default settings and a fixed seed (nothing is tuned)."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    model = HistGradientBoostingRegressor(random_state=seed, categorical_features=["family_code"])
    return model.fit(pairs[FEATURES], pairs["perf_index"])


def boosting_misses(frame: pd.DataFrame, cutoff: int, seed: int = 0) -> pd.DataFrame:
    """How far boosting's predictions missed (actual minus predicted) for seasons after cutoff.

    The model is fitted only on seasons up to cutoff, exactly as in the backtest.
    """
    train, test = split_by_season(frame, cutoff)
    predicted = fit_boosting(training_pairs(train), seed).predict(test[FEATURES])
    return pd.DataFrame({"horizon": test["horizon"], "miss": test["perf_index"] - predicted})


def range_offsets(misses: pd.DataFrame, min_count: int = 20) -> pd.DataFrame:
    """For each horizon: the 10th and 90th percentile of past misses (split conformal ranges).

    Adding them to a new prediction gives an 80% range whose width is learned from real misses
    rather than assumed. A horizon with fewer than min_count misses uses all horizons together.
    """
    rows = []
    for h in range(1, MAX_HORIZON + 1):
        m = misses.loc[misses["horizon"] == h, "miss"]
        m = m if len(m) >= min_count else misses["miss"]
        rows.append({"horizon": h, "low": m.quantile(LOW_Q), "high": m.quantile(HIGH_Q)})
    return pd.DataFrame(rows).set_index("horizon")


def predict_boosting(train: pd.DataFrame, test: pd.DataFrame, cutoff: int = CUTOFF,
                     seed: int = 0) -> pd.DataFrame:  # fmt: skip
    """Boosting's prediction plus an 80% range.

    The range comes from boosting's own misses in an earlier backtest run inside the training
    seasons (fit to cutoff - CALIBRATION_GAP, predict up to cutoff), so no test season is used.
    """
    point = fit_boosting(training_pairs(train), seed).predict(test[FEATURES])
    offsets = range_offsets(boosting_misses(train, cutoff - CALIBRATION_GAP, seed))
    h = test["horizon"].to_numpy()
    return pd.DataFrame({"boosting": point,
                         "boosting_low": point + offsets.loc[h, "low"].to_numpy(),
                         "boosting_high": point + offsets.loc[h, "high"].to_numpy()})  # fmt: skip


def predict_mixed_model(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """The mixed-effects model: group curve plus the athlete-event's own level and slope.

    Also gives an 80% prediction interval from the uncertainty in the athlete's own line plus
    season-to-season noise (uncertainty in the group curve itself is small and left out).
    """
    result = fit_trajectory_model(train)
    fixed = np.asarray(result.predict(test))
    preds, sds = [], []
    for unit, years, base in zip(test["unit"], test["years"], fixed):
        effect = result.random_effects[unit]
        cov = result.random_effects_cov[unit].to_numpy()
        z = np.array([1.0, years])
        preds.append(base + effect.iloc[0] + effect.iloc[1] * years)
        sds.append(np.sqrt(z @ cov @ z + result.scale))
    preds, sds = np.array(preds), np.array(sds)
    return pd.DataFrame({"mixed_model": preds, "mixed_low": preds - INTERVAL_Z * sds,
                         "mixed_high": preds + INTERVAL_Z * sds})  # fmt: skip


def run_backtest(frame: pd.DataFrame, cutoff: int = CUTOFF) -> pd.DataFrame:
    """The hidden test seasons with every contender's prediction alongside the real value."""
    train, test = split_by_season(frame, cutoff)
    out = test.copy()
    out["last_season_pred"] = predict_last_season(train, test)
    out["age_trend_pred"] = predict_age_trend(train, test)
    out["fixed_curve_pred"] = predict_fixed_curve(train, test)
    boost = predict_boosting(train, test, cutoff)
    out["boosting_pred"] = boost["boosting"].to_numpy()
    out["boosting_low"], out["boosting_high"] = boost["boosting_low"].to_numpy(), boost["boosting_high"].to_numpy()
    mixed = predict_mixed_model(train, test)
    out["mixed_model_pred"] = mixed["mixed_model"].to_numpy()
    out["mixed_low"], out["mixed_high"] = mixed["mixed_low"].to_numpy(), mixed["mixed_high"].to_numpy()
    return out


def score(predictions: pd.DataFrame) -> pd.DataFrame:
    """Errors per contender: overall, by horizon and by group. Lower is better.

    mae = mean absolute error, rmse = root mean squared error (punishes big misses more),
    bias = mean of prediction minus actual (negative = predictions too pessimistic).
    """
    rows = []
    for name in CONTENDERS:
        err = predictions[f"{name}_pred"] - predictions["perf_index"]
        row = {"contender": name, "n": len(err), "mae": err.abs().mean(),
               "rmse": np.sqrt((err**2).mean()), "bias": err.mean()}  # fmt: skip
        for h in range(1, MAX_HORIZON + 1):
            row[f"mae_h{h}"] = err[predictions["horizon"] == h].abs().mean()
        for group, flag in (("india", 1), ("finalists", 0)):
            row[f"mae_{group}"] = err[predictions["india"] == flag].abs().mean()
        rows.append(row)
    out = pd.DataFrame(rows)
    out["coverage_80"] = [coverage(predictions, *RANGES[name]) if name in RANGES else np.nan
                          for name in out["contender"]]  # fmt: skip
    return out


RANGES = {"mixed_model": ("mixed_low", "mixed_high"), "boosting": ("boosting_low", "boosting_high")}


def coverage(predictions: pd.DataFrame, low: str, high: str) -> float:
    """Share of real values inside the 80% range; NaN if this contender gave no range."""
    if low not in predictions or high not in predictions:
        return np.nan
    return float(predictions["perf_index"].between(predictions[low], predictions[high]).mean())


def mae_difference(predictions: pd.DataFrame, a: str, b: str, india: int | None = None,
                   n_boot: int = 2000, seed: int = 0) -> dict:  # fmt: skip
    """Is contender a really worse than b? MAE(a) - MAE(b) with a 95% bootstrap interval.

    Resamples whole athlete-events (not single seasons), because one athlete's seasons are not
    independent. A positive difference means a misses by more than b; if the interval excludes 0,
    the gap is not luck. india=1 or 0 restricts to Indian athletes or finalists.
    """
    p = predictions if india is None else predictions[predictions["india"] == india]
    err_a = (p[f"{a}_pred"] - p["perf_index"]).abs().groupby(p["unit"]).sum()
    err_b = (p[f"{b}_pred"] - p["perf_index"]).abs().groupby(p["unit"]).sum()
    n = p.groupby("unit").size()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(n), size=(n_boot, len(n)))
    sa, sb, sn = err_a.to_numpy(), err_b.to_numpy(), n.to_numpy()
    diffs = (sa[idx].sum(1) - sb[idx].sum(1)) / sn[idx].sum(1)
    return {"a": a, "b": b, "units": len(n), "seasons": int(sn.sum()),
            "difference": float((sa.sum() - sb.sum()) / sn.sum()),
            "ci_low": float(np.percentile(diffs, 2.5)), "ci_high": float(np.percentile(diffs, 97.5))}  # fmt: skip


def log_to_mlflow(predictions: pd.DataFrame, scores: pd.DataFrame, params: dict,
                  tracking_uri: str = TRACKING_URI, artifact_dir: Path = ARTIFACT_DIR,
                  experiment: str = EXPERIMENT) -> list[str]:  # fmt: skip
    """Record one MLflow run per contender: settings, errors and its predictions as a CSV.

    Returns the run IDs. Runs are stored in a local SQLite file; compare them in the browser with
    `mlflow ui --backend-store-uri sqlite:///mlflow.db` from the project root.
    """
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    found = mlflow.get_experiment_by_name(experiment)
    experiment_id = found.experiment_id if found else mlflow.create_experiment(
        experiment, artifact_location=Path(artifact_dir).resolve().as_uri())
    keep = ["unit", "season", "age", "horizon", "india", "perf_index"]
    run_ids = []
    for row in scores.to_dict("records"):
        name = row.pop("contender")
        with mlflow.start_run(experiment_id=experiment_id, run_name=name) as run:
            mlflow.log_params({**params, "contender": name})
            mlflow.log_metrics({k: float(v) for k, v in row.items() if pd.notna(v)})
            cols = keep + [f"{name}_pred"] + list(RANGES.get(name, ()))
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / f"{name}_predictions.csv"
                predictions[cols].to_csv(path, index=False)
                mlflow.log_artifact(str(path))
            run_ids.append(run.info.run_id)
    return run_ids