import subprocess
import sys

import pandas as pd
import pytest

from flows import pipeline as pl
from src.export import export_serving
from src.publish import attach_names, make_findings


def test_plan_runs_validation_before_loading_and_publishes_last():
    names = [name for name, _, _ in pl.plan()]
    assert names == ["validate", "load BigQuery", "dbt build", "publish results"]
    assert pl.plan()[2][2].name == "dbt"  # dbt runs inside the dbt project folder


def test_plan_with_scrape_refreshes_every_source_first():
    names = [name for name, _, _ in pl.plan(scrape=True)]
    assert names[:6] == [name for name, _ in pl.SCRAPE_STEPS]
    assert names.index("build finalists seed") < names.index("scrape finalists")
    assert names[-4:] == ["validate", "load BigQuery", "dbt build", "publish results"]


def test_a_failing_step_raises_so_the_flow_stops(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        pl.run_step.fn("fail", [sys.executable, "-c", "import sys; sys.exit(3)"], tmp_path)


def test_findings_are_built_from_the_model_and_backtest():
    effects = pd.DataFrame({"term": ["india", "india:years"], "estimate": [-4.861, -0.3],
                            "ci_low": [-6.749, -0.6], "ci_high": [-2.974, 0.0]})  # fmt: skip
    scores = pd.DataFrame({"contender": ["boosting", "mixed_model"], "mae": [1.961, 2.391],
                           "coverage_80": [0.82, 0.86]})  # fmt: skip
    findings = make_findings(effects, scores, 72, 305)
    assert findings["gap_at_18_points"] == 4.86
    assert findings["gap_at_18_ci_95"] == [2.97, 6.75]
    assert findings["backtest_mae_points"] == {"boosting": 1.96, "mixed_model": 2.39}
    assert findings["projection_range_coverage_80"] == 0.82


def test_names_are_attached_and_unknown_ids_stay_blank():
    proj = pd.DataFrame({"unit": ["1|jt_m", "9|hj_w"]})
    out = attach_names(proj, pd.Series({"1": "Athlete A"}))
    assert out["athlete"].tolist() == ["Athlete A", ""]
    assert out["event"].tolist() == ["jt_m", "hj_w"]


def test_dashboard_tables_are_written_next_to_the_api_files(tmp_path):
    from tests.test_api import FINDINGS, GAPS, PROJ

    curves = pd.DataFrame({"group": ["India"], "age": [18], "perf_index": [84.4321]})
    paths = export_serving(GAPS, PROJ, FINDINGS, tmp_path, extra={"curves": curves})
    assert paths[-1].name == "curves.csv"
    assert pd.read_csv(paths[-1])["perf_index"].tolist() == [84.432]