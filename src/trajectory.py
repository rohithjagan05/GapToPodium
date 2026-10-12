"""Phase 4 trajectory helpers: line up athletes' season bests by age on one common scale.

The question from Phase 3: Indian athletes improve as fast as eventual Olympic finalists and peak
at the same age, so is the gap already there at 18? To compare athletes across events, every
season best becomes a performance index: the mark as a percentage of the event's bronze
threshold, where 100 means bronze level and a higher number is always better.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis import season_bests
from src.scrapers.world_athletics import read_seeds

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