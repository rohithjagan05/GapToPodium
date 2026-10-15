"""Rebuild the served results from the warehouse and the latest scrapes, without a notebook.

    python -m src.publish

Same steps as notebooks/phase4_trajectories.ipynb: fair thresholds, career trajectories, the
mixed-effects model (the gap at 18), the backtest (model accuracy), 2028 projections, then the
files in serving/ that the API and dashboards read.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis import average_over_games, match_medallists, season_best_bronze
from src.backtest import run_backtest, score
from src.config import RAW_DIR, SEEDS_DIR
from src.export import export_serving
from src.projection import project
from src.trajectory import (
    age_aligned,
    fit_trajectory_model,
    group_effects,
    latest_run,
    load_group,
    mean_curves,
    model_frame,
    pick_thresholds,
)

GROUPS = {"India": ("wa", "india_athletes.csv", None),
          "Finalists": ("wa_finalists", "finalists_2024.csv", "IND")}  # fmt: skip
PODIUM_SQL = """
    SELECT championship_year, event_key, athlete_name, country_code, position, mark_value,
           higher_is_better, discipline_group
    FROM staging.stg_olympic_results
    WHERE position BETWEEN 1 AND 3 AND championship_year IN (2016, 2020, 2024)
"""


def make_findings(effects: pd.DataFrame, scores: pd.DataFrame, n_india: int,
                  n_finalists: int) -> dict:  # fmt: skip
    """The headline numbers served at /findings, from the model's effects and the backtest."""
    gap = effects.set_index("term").loc["india"]
    by_model = scores.set_index("contender")
    return {
        "performance_index": "mark as % of Olympic bronze level (medallists' season bests); "
                             "100 = bronze",
        "gap_at_18_points": round(float(-gap["estimate"]), 2),
        "gap_at_18_ci_95": [round(float(-gap["ci_high"]), 2), round(float(-gap["ci_low"]), 2)],
        "athletes": {"india": n_india, "finalists_2024": n_finalists},
        "projection_model": "gradient boosting",
        "backtest_mae_points": {c: round(float(by_model.loc[c, "mae"]), 2) for c in by_model.index},
        "projection_range_coverage_80": round(float(by_model.loc["boosting", "coverage_80"]), 2),
    }  # fmt: skip


def attach_names(proj: pd.DataFrame, names: pd.Series) -> pd.DataFrame:
    """Add athlete and event columns from the unit ("wa_id|event_key"); unknown IDs stay blank."""
    wa_id, event = proj["unit"].str.split("|").str[0], proj["unit"].str.split("|").str[1]
    return proj.assign(athlete=wa_id.map(names).fillna(""), event=event)


def compute_results(gap: pd.DataFrame, toplists: pd.DataFrame, podium: pd.DataFrame,
                    raw_dir: Path = RAW_DIR, seeds_dir: Path = SEEDS_DIR) -> dict:  # fmt: skip
    """Every served table, computed from the warehouse tables and the latest scrape runs."""
    sb = average_over_games(season_best_bronze(match_medallists(podium, toplists)))
    thresholds = pick_thresholds(gap[["event_key", "bronze_threshold"]].merge(sb, on="event_key",
                                                                              how="left"))  # fmt: skip
    th = dict(zip(thresholds["event_key"], thresholds["threshold"]))
    traj = {}
    for name, (subdir, seed, exclude) in GROUPS.items():
        sbs, births = load_group(latest_run(raw_dir / subdir), seeds_dir / seed, exclude)
        traj[name] = age_aligned(sbs, births, th)
    frame = model_frame(traj["India"], traj["Finalists"])
    result = fit_trajectory_model(frame)
    scores = score(run_backtest(frame))
    names = pd.read_csv(seeds_dir / "india_athletes.csv", dtype=str).set_index("wa_id")["athlete_name"]
    findings = make_findings(group_effects(result), scores, traj["India"]["wa_id"].nunique(),
                             traj["Finalists"]["wa_id"].nunique())  # fmt: skip
    return {"gaps": gap, "projections": attach_names(project(frame), names), "findings": findings,
            "curves": mean_curves(result), "backtest": scores}  # fmt: skip


def main() -> None:
    from src.warehouse import query, table

    results = compute_results(table("marts.mart_gap_to_podium"), table("staging.stg_wa_toplists"),
                              query(PODIUM_SQL))  # fmt: skip
    paths = export_serving(results["gaps"], results["projections"], results["findings"],
                           extra={"curves": results["curves"], "backtest": results["backtest"]})  # fmt: skip
    for path in paths:
        print(f"wrote {path.name}")
    print(f"gap at 18: {results['findings']['gap_at_18_points']} points")


if __name__ == "__main__":
    main()