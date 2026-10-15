"""The whole pipeline as one Prefect flow: scrape, validate, load, transform, model, publish.

    python -m flows.pipeline            # reuse cached scrapes: validate onwards
    python -m flows.pipeline --scrape   # also refresh every source (slow and polite)

Each step runs the same command as its make target, as a Prefect task: logged, timed, and
retried if a network step fails. A failed step stops the flow, so later steps never run on
broken inputs (for example, nothing loads into BigQuery if validation fails).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from prefect import flow, task

from src.config import PROJECT_ROOT

PY = [sys.executable, "-m"]
SCRAPE_STEPS = [
    ("scrape Olympedia", PY + ["src.scrapers.olympedia"]),
    ("scrape World Championships", PY + ["src.scrapers.wikipedia_worlds"]),
    ("scrape Indian athletes", PY + ["src.scrapers.world_athletics"]),
    ("scrape world toplists", PY + ["src.scrapers.wa_toplists"]),
    ("build finalists seed", PY + ["src.finalists"]),
    ("scrape finalists", PY + ["src.scrapers.world_athletics", "--seeds",
                               "data/seeds/finalists_2024.csv", "--raw-subdir", "wa_finalists"]),
]  # fmt: skip


def plan(scrape: bool = False) -> list[tuple[str, list[str], Path]]:
    """The steps in order: (name, command, folder to run it in)."""
    steps = SCRAPE_STEPS if scrape else []
    steps = steps + [("validate", PY + ["src.validate"]), ("load BigQuery", PY + ["src.load_bigquery"])]
    root = [(name, cmd, PROJECT_ROOT) for name, cmd in steps]
    dbt = shutil.which("dbt") or "dbt"
    return root + [("dbt build", [dbt, "build"], PROJECT_ROOT / "dbt"),
                   ("publish results", PY + ["src.publish"], PROJECT_ROOT)]  # fmt: skip


@task(retries=2, retry_delay_seconds=60)
def run_step(name: str, command: list[str], cwd: Path) -> None:
    """Run one step; a non-zero exit raises, so Prefect retries it and then stops the flow."""
    print(f"--> {name}: {' '.join(str(c) for c in command)}")
    subprocess.run(command, cwd=cwd, check=True)


@flow(name="gap-to-podium", log_prints=True)
def pipeline(scrape: bool = False) -> None:
    for name, command, cwd in plan(scrape):
        run_step.with_options(name=name)(name, command, cwd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scrape", action="store_true", help="refresh every source first (slow)")
    pipeline(scrape=parser.parse_args().scrape)