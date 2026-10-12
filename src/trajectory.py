"""Phase 4 trajectory helpers: line up athletes' season bests by age on one common scale.

The question from Phase 3: Indian athletes improve as fast as eventual Olympic finalists and peak
at the same age, so is the gap already there at 18? To compare athletes across events, every
season best becomes a performance index: the mark as a percentage of the event's bronze
threshold, where 100 means bronze level and a higher number is always better.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis import season_bests
from src.events import DISCIPLINES
from src.scrapers.world_athletics import read_seeds
from src.validate import discipline_of

AGE_RANGE = (15, 40)  # ages outside this are almost certainly wrong birth dates or seasons
TRAJECTORY_COLUMNS = ["wa_id", "event_key", "season", "age", "mark_value", "higher_is_better",
                      "perf_index"]  # fmt: skip


def performance_index(mark, threshold, higher_is_better) -> np.ndarray:
    """Mark as a percentage of the bronze threshold: 100 = bronze level, higher is always better.

    Jumps and throws: 100 * mark / threshold. Running and walking: 100 * threshold / mark, so a
    faster time gives a bigger number. An index of 97 means about 3% short of bronze level.
    """
    mark = np.asarray(mark, dtype=float)
    threshold = np.asarray(threshold, dtype=float)
    higher = np.asarray(higher_is_better, dtype=bool)
    return np.where(higher, 100 * mark / threshold, 100 * threshold / mark)


def age_aligned(sbs: pd.DataFrame, birth_years: dict[str, int], thresholds: dict[str, float],
                age_range: tuple[int, int] = AGE_RANGE) -> pd.DataFrame:  # fmt: skip
    """One row per athlete, event and season, with the athlete's age and performance index.

    sbs is the output of analysis.season_bests; birth_years maps wa_id to birth year; thresholds
    maps event_key to that event's bronze threshold. Age is season minus birth year (the age the
    athlete turns during the season), as in Phase 3. Rows without a birth year or a threshold are
    dropped, and so are ages outside age_range.
    """
    thresholds = {k: v for k, v in thresholds.items() if pd.notna(v)}
    df = sbs[sbs["wa_id"].isin(birth_years.keys()) & sbs["event_key"].isin(thresholds.keys())]
    df = df.assign(age=df["season"].astype(int) - df["wa_id"].map(birth_years).astype(int))
    df = df[df["age"].between(*age_range)]
    df = df.assign(perf_index=performance_index(df["mark_value"], df["event_key"].map(thresholds),
                                                df["higher_is_better"]))  # fmt: skip
    df = df.sort_values(["wa_id", "event_key", "season"]).reset_index(drop=True)
    return df[TRAJECTORY_COLUMNS]


def pick_thresholds(fair: pd.DataFrame) -> pd.DataFrame:
    """One bronze threshold per event: the medallists' season-best threshold where Phase 3 has one.

    Trajectories are made of season bests, so the like-for-like threshold is the medallists'
    season bests (sb_threshold). Events without one fall back to the final's bronze mark
    (bronze_threshold); the source column says which was used.
    """
    use_sb = fair["sb_threshold"].notna()
    return pd.DataFrame({
        "event_key": fair["event_key"],
        "threshold": fair["sb_threshold"].where(use_sb, fair["bronze_threshold"]),
        "source": np.where(use_sb, "medallists' season bests", "final's bronze mark"),
    }).dropna(subset=["threshold"]).reset_index(drop=True)  # fmt: skip


def latest_run(raw_subdir: Path) -> Path:
    """The newest World Athletics run folder (timestamped names sort by time) with marks in it."""
    runs = [p for p in raw_subdir.glob("*") if (p / "marks.parquet").exists()]
    if not runs:
        raise FileNotFoundError(f"no run with marks.parquet in {raw_subdir}")
    return max(runs)


def load_group(run_dir: Path, seed_file: Path,
               exclude_country: str | None = None) -> tuple[pd.DataFrame, dict[str, int]]:  # fmt: skip
    """Season bests in each athlete's own seeded events, and birth years, from one scrape run.

    exclude_country drops athletes of that country (Indian athletes are kept out of the
    finalists group, as in Phase 3).
    """
    athletes = pd.read_parquet(run_dir / "athletes.parquet")
    if exclude_country:
        athletes = athletes[athletes["country_code"] != exclude_country]
    keep = set(athletes["wa_id"])
    events = {s.wa_id: set(s.events) for s in read_seeds(seed_file) if s.wa_id in keep}
    births = {w: pd.Timestamp(d).year for w, d in zip(athletes["wa_id"], athletes["birth_date"])
              if pd.notna(d)}  # fmt: skip
    sbs = season_bests(pd.read_parquet(run_dir / "marks.parquet"), events)
    return sbs, births


def level_by_age(traj: pd.DataFrame) -> pd.DataFrame:
    """Per age: how many athletes, and the median and middle half of their performance index.

    An athlete seeded in two events counts once per age, at their better index that season, so
    the summary describes athletes, not athlete-events.
    """
    per_athlete = traj.groupby(["wa_id", "age"])["perf_index"].max().reset_index()
    out = per_athlete.groupby("age")["perf_index"].agg(
        athletes="count", median="median",
        q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75))
    return out.reset_index()



# --- mixed-effects trajectory model ------------------------------------------------------------

BASE_AGE = 18  # ages are measured from 18, so the group difference in the model is the gap at 18
MODEL_AGES = (16, 30)  # development and peak years; later seasons add decline, not development
FORMULA = "perf_index ~ india * (years + I(years ** 2))"
CUBIC_FORMULA = "perf_index ~ india * (years + I(years ** 2) + I(years ** 3))"  # robustness only
EFFECT_NAMES = {"india": "gap at 18 (points)",
                "india:years": "difference in improvement per year at 18 (points)",
                "india:I(years ** 2)": "difference in curvature (points per year squared)"}


def model_frame(india: pd.DataFrame, finalists: pd.DataFrame,
                ages: tuple[int, int] = MODEL_AGES) -> pd.DataFrame:  # fmt: skip
    """Both groups' trajectories in one table for the model.

    india is 1 for Indian athletes and 0 for finalists; years is age minus 18; unit is one
    athlete in one event (an athlete's 5000 m and 10,000 m are separate lines).
    """
    both = pd.concat([india.assign(india=1), finalists.assign(india=0)], ignore_index=True)
    both = both[both["age"].between(*ages)]
    return both.assign(years=both["age"] - BASE_AGE,
                       unit=both["wa_id"].astype(str) + "|" + both["event_key"])  # fmt: skip


def fit_trajectory_model(frame: pd.DataFrame, formula: str = FORMULA):
    """Mixed-effects model of performance index on age, Indian athletes against finalists.

    Fixed part: each group's average curve (a level at 18, a yearly improvement and a bend, so the
    curve can flatten at the peak). Random part: every athlete-event gets its own level and its
    own improvement rate, so the model compares athletes with their own earlier seasons rather
    than whichever athletes happen to have a mark at each age. Fitted by REML. The optimizer that
    produced the result is kept as result.optimizer.
    """
    import statsmodels.formula.api as smf

    model = smf.mixedlm(formula, frame, groups=frame["unit"], re_formula="~years")
    for method in ("lbfgs", "powell"):  # powell is slower but steadier if lbfgs does not converge
        result = model.fit(reml=True, method=method)
        result.optimizer = method
        if result.converged:
            return result
    return result


def group_effects(result) -> pd.DataFrame:
    """The three India-vs-finalists terms with 95% confidence intervals and p-values."""
    ci = result.conf_int()
    rows = [{"term": term, "meaning": meaning, "estimate": result.params[term],
             "ci_low": ci.loc[term, 0], "ci_high": ci.loc[term, 1], "p_value": result.pvalues[term]}
            for term, meaning in EFFECT_NAMES.items()]  # fmt: skip
    return pd.DataFrame(rows)


def mean_curves(result, ages: tuple[int, int] = MODEL_AGES) -> pd.DataFrame:
    """Each group's average performance index at every age, from the model's fixed part."""
    grid = pd.DataFrame([(a, g) for g in (0, 1) for a in range(ages[0], ages[1] + 1)],
                        columns=["age", "india"])  # fmt: skip
    grid["years"] = grid["age"] - BASE_AGE
    grid["perf_index"] = result.predict(grid)
    grid["group"] = np.where(grid["india"] == 1, "India", "Finalists")
    return grid[["group", "age", "perf_index"]]



# --- robustness and diagnostics ----------------------------------------------------------------

FAMILIES = {"sprints": "sprints and hurdles", "hurdles": "sprints and hurdles",
            "middle_distance": "endurance", "long_distance": "endurance", "road": "endurance",
            "jumps": "jumps", "throws": "throws", "combined": "combined events"}  # fmt: skip
MIN_LINES = 8  # fewer athlete-event lines than this in either group: too few to fit, not reported


def event_family(event_key: str) -> str:
    """Broad event family, so each subset still has enough Indian athletes to fit."""
    return FAMILIES[DISCIPLINES[discipline_of(event_key)][0]]


def robustness(frame: pd.DataFrame, min_lines: int = MIN_LINES) -> pd.DataFrame:
    """Refit the model on subsets (each event family, each sex, ages 16-28) and with a cubic curve.

    If the gap at 18 has the same sign and a similar size in every row, it is not an artefact of
    one event group, the age window or the curve's shape. Warnings from a fit (for example a
    random-effects variance at its boundary, or a first optimizer that failed before the second
    succeeded) are kept in the note column, and the optimizer that produced the result is shown.
    """
    from statsmodels.tools.sm_exceptions import ConvergenceWarning

    family = frame["event_key"].map(event_family)
    sex = frame["event_key"].str.rsplit("_", n=1).str[1]
    subsets = {"all events": frame}
    subsets.update({name: frame[family == name] for name in sorted(family.unique())})
    subsets.update({"men": frame[sex == "m"], "women": frame[sex == "w"],
                    "ages 16-28": frame[frame["age"] <= 28], "cubic age curve": frame})  # fmt: skip
    rows = []
    for name, sub in subsets.items():
        formula = CUBIC_FORMULA if name == "cubic age curve" else FORMULA
        lines = sub.groupby("india")["unit"].nunique()
        row = {"subset": name, "indian_lines": int(lines.get(1, 0)),
               "finalist_lines": int(lines.get(0, 0))}  # fmt: skip
        if min(row["indian_lines"], row["finalist_lines"]) < min_lines:
            rows.append({**row, "note": "too few lines to fit"})
            continue
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            result = fit_trajectory_model(sub, formula)
        effects = group_effects(result).set_index("term")
        notes = sorted({str(w.message).split(".")[0] for w in caught})
        rows.append({**row,
                     "gap_at_18": -effects.loc["india", "estimate"],
                     "gap_low": -effects.loc["india", "ci_high"],
                     "gap_high": -effects.loc["india", "ci_low"],
                     "slope_diff": effects.loc["india:years", "estimate"],
                     "slope_low": effects.loc["india:years", "ci_low"],
                     "slope_high": effects.loc["india:years", "ci_high"],
                     "converged": bool(result.converged), "optimizer": result.optimizer,
                     "note": "; ".join(notes)})  # fmt: skip
    return pd.DataFrame(rows)


def variance_parts(result) -> dict:
    """How much athletes differ from each other, and how noisy single seasons are (in points)."""
    cov = result.cov_re
    return {"sd_level_at_18": float(np.sqrt(cov.iloc[0, 0])),
            "sd_yearly_improvement": float(np.sqrt(cov.iloc[1, 1])),
            "corr_level_improvement": float(cov.iloc[0, 1] / np.sqrt(cov.iloc[0, 0] * cov.iloc[1, 1])),
            "sd_season_noise": float(np.sqrt(result.scale))}  # fmt: skip


def residual_check(result, frame: pd.DataFrame) -> pd.DataFrame:
    """The model's leftover errors by group and age.

    A mean near 0 at every age means the curve's shape fits; a run of positive or negative means
    at some ages would show the curve is the wrong shape there.
    """
    res = frame.assign(residual=np.asarray(result.resid),
                       group=np.where(frame["india"] == 1, "India", "Finalists"))  # fmt: skip
    return res.groupby(["group", "age"])["residual"].agg(["count", "mean", "std"]).reset_index()