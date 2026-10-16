"""Phase 6: reads the files in serving/ and shapes them for the Streamlit site.

Pure functions only: no Streamlit, no BigQuery, no model fitting, no network. The site shows the numbers the
pipeline wrote (python -m src.publish), so the tests run offline on the committed files.
"""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

SITE_ROOT = Path(__file__).resolve().parent.parent
SERVING_DIR = SITE_ROOT / "serving"

NO_MARK = "No mark in the data"

# Same event names as src/charts.py, so the site and the notebook label events the same way.
EVENT_NAMES = {
    "100m": "100 m", "200m": "200 m", "400m": "400 m", "800m": "800 m", "1500m": "1500 m",
    "5000m": "5000 m", "10000m": "10,000 m", "3000msc": "Steeplechase", "marathon": "Marathon",
    "110mh": "110 m hurdles", "100mh": "100 m hurdles", "400mh": "400 m hurdles",
    "20kmw": "20 km walk", "hj": "High jump", "pv": "Pole vault", "lj": "Long jump",
    "tj": "Triple jump", "sp": "Shot put", "dt": "Discus", "ht": "Hammer", "jt": "Javelin",
    "dec": "Decathlon", "hep": "Heptathlon",
}  # fmt: skip

# Plain names for the models in backtest.csv. Unknown names are shown as they are.
BACKTEST_NAMES = {
    "last_season": "Last season's mark",
    "age_trend": "Age trend",
    "fixed_curve": "Fixed curve",
    "boosting": "Gradient boosting",
    "mixed_model": "Mixed-effects model",
}


def event_label(event_key: str) -> str:
    """'jt_m' -> 'Javelin (M)'."""
    discipline, sex = event_key.rsplit("_", 1)
    return f"{EVENT_NAMES.get(discipline, discipline)} ({sex.upper()})"


def load_serving(directory: Path = SERVING_DIR) -> dict:
    """Read every file the site uses. Marks stay text, so '10.09' and '27:00.22' show as written."""
    folder = Path(directory)
    return {
        "gaps": pd.read_csv(folder / "gaps.csv",
                            dtype={"india_best_athlete": str, "india_best_mark_raw": str}),
        "projections": pd.read_csv(folder / "projections.csv"),
        "curves": pd.read_csv(folder / "curves.csv"),
        "backtest": pd.read_csv(folder / "backtest.csv"),
        "findings": json.loads((folder / "findings.json").read_text(encoding="utf-8")),
    }


def gap_table(gaps: pd.DataFrame, tactical: bool | None = None) -> pd.DataFrame:
    """One row per event. tactical=True keeps only tactical events, False only the others.

    For tactical events (middle distance, long distance, road) read the world rank, not the gap.
    """
    df = gaps if tactical is None else gaps[gaps["tactical_event"] == tactical]
    table = pd.DataFrame({
        "Event": df["event_key"].map(event_label),
        "Best Indian athlete": df["india_best_athlete"].fillna(NO_MARK),
        "Best mark": df["india_best_mark_raw"].fillna("-"),
        "Gap to bronze (%)": df["gap_pct"],
        "World rank": df["india_world_rank"].astype("Int64"),
        "Tactical event": df["tactical_event"].astype(bool),
    })  # fmt: skip
    return table.sort_values("Event").reset_index(drop=True)


def gap_chart_data(gaps: pd.DataFrame) -> pd.DataFrame:
    """Gap per event for the non-tactical events that have a mark. Tactical events are left out."""
    df = gaps[~gaps["tactical_event"].astype(bool) & gaps["gap_pct"].notna()]
    chart = pd.DataFrame({"Event": df["event_key"].map(event_label), "Gap": df["gap_pct"]})
    return chart.sort_values("Gap").reset_index(drop=True)


def gap_at_age(curves: pd.DataFrame, age: int) -> float:
    """Finalists' average index minus India's at one age. Positive means India is behind."""
    values = curves[curves["age"] == age].set_index("group")["perf_index"]
    return round(float(values["Finalists"] - values["India"]), 2)


def backtest_table(backtest: pd.DataFrame) -> pd.DataFrame:
    """The models compared on the held-out data, best (lowest error) first."""
    table = pd.DataFrame({
        "Model": backtest["contender"].map(lambda name: BACKTEST_NAMES.get(name, name)),
        "MAE (points)": backtest["mae"],
        "RMSE (points)": backtest["rmse"],
        "Bias (points)": backtest["bias"],
        "80% range coverage": backtest["coverage_80"],
    })  # fmt: skip
    return table.sort_values("MAE (points)").reset_index(drop=True)


def projection_table(projections: pd.DataFrame, event: str | None = None,
                     athlete: str | None = None, reaches_bronze: bool | None = None) -> pd.DataFrame:
    """2028 projections, highest first. Filters match the API: event, part of the name, and
    whether the 80% range reaches bronze level."""
    p = projections
    if event is not None:
        p = p[p["event"] == event]
    if athlete:
        p = p[p["athlete"].fillna("").str.contains(athlete, case=False, regex=False)]
    if reaches_bronze is not None:
        p = p[p["range_reaches_bronze"].astype(bool) == reaches_bronze]
    p = p.sort_values("projected", ascending=False)
    table = pd.DataFrame({
        "Athlete": p["athlete"].fillna(""),
        "Event": p["event"].map(event_label),
        "Last season": p["last_season"],
        "Age at 2028 (by birth year)": p["target_age"],
        "Projected index": p["projected"],
        "Low (80%)": p["low"],
        "High (80%)": p["high"],
        "Range reaches bronze": p["range_reaches_bronze"].astype(bool),
        "Beyond trained ages": p["beyond_trained_ages"].astype(bool),
    })  # fmt: skip
    return table.reset_index(drop=True)


def check_findings(findings: dict, backtest: pd.DataFrame) -> list[str]:
    """Problems where findings.json and backtest.csv disagree. An empty list means they agree."""
    problems = []
    by_model = backtest.set_index("contender")
    for name, mae in findings["backtest_mae_points"].items():
        if name not in by_model.index:
            problems.append(f"{name} is in findings.json but not in backtest.csv")
        elif not math.isclose(round(float(by_model.loc[name, "mae"]), 2), mae, abs_tol=1e-9):
            file_value = by_model.loc[name, "mae"]
            problems.append(f"{name}: findings say {mae}, backtest.csv gives {file_value}")
    coverage = round(float(by_model.loc["boosting", "coverage_80"]), 2)
    if not math.isclose(coverage, findings["projection_range_coverage_80"], abs_tol=1e-9):
        problems.append("80% range coverage differs between findings.json and backtest.csv")
    return problems  # fmt: skip


def closest_to_bronze(projections: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """The n athlete-events with the highest latest index (100 = bronze level), best first."""
    p = projections.sort_values("last_index", ascending=False).head(n)
    return pd.DataFrame({
        "athlete": p["athlete"].fillna(""),
        "event": p["event"].map(event_label),
        "last_index": p["last_index"],
        "projected": p["projected"],
    }).reset_index(drop=True)  # fmt: skip


def ladder_rows(gaps: pd.DataFrame) -> pd.DataFrame:
    """Every event for the event ladder, with a kind that decides how the row is drawn.

    kind: 'ahead' (gap below 0), 'behind', 'tactical' (show world rank, not the gap) or 'none'
    (no Indian mark). Order: gap events from closest to furthest, then tactical by rank, then none.
    """
    tactical = gaps["tactical_event"].astype(bool)
    has_mark = gaps["gap_pct"].notna()
    kind = pd.Series("behind", index=gaps.index)
    kind[has_mark & ~tactical & (gaps["gap_pct"] < 0)] = "ahead"
    kind[has_mark & tactical] = "tactical"
    kind[~has_mark] = "none"
    rows = pd.DataFrame({
        "event": gaps["event_key"].map(event_label),
        "athlete": gaps["india_best_athlete"].fillna(""),
        "mark": gaps["india_best_mark_raw"].fillna(""),
        "gap": gaps["gap_pct"],
        "rank": gaps["india_world_rank"].astype("Int64"),
        "kind": kind,
    })  # fmt: skip
    order = rows["kind"].map({"ahead": 0, "behind": 0, "tactical": 1, "none": 2})
    sort_value = rows["gap"].where(order == 0, rows["rank"].astype("Float64").where(order == 1))
    rows = rows.assign(_o=order, _v=sort_value.astype(float))
    return rows.sort_values(["_o", "_v", "event"]).drop(columns=["_o", "_v"]).reset_index(drop=True)


def data_age_days(generated_at: str, now: datetime | None = None) -> float:
    """Days since findings.json was written ('2026-10-15T18:13:42Z')."""
    made = datetime.fromisoformat(generated_at)
    now = now or datetime.now(UTC)
    return (now - made).total_seconds() / 86400


def freshness_status(age_days: float) -> str:
    """ok under 14 days, warn up to 60, down after that."""
    return "ok" if age_days < 14 else "warn" if age_days <= 60 else "down"


def coverage_status(coverage: float, target: float = 0.8) -> str:
    """How far the 80% ranges' real coverage is from 80%: ok within 5 points, warn within 10."""
    miss = abs(coverage - target)
    return "ok" if miss <= 0.05 + 1e-9 else "warn" if miss <= 0.10 + 1e-9 else "down"


def api_status(seconds: float | None, answered: bool) -> str:
    """ok if /health answered in under 1.5 s. A timeout is 'warn' (the free host is waking up);
    an answer that is an error, or no connection at all, is 'down'."""
    if answered:
        return "ok" if seconds is not None and seconds < 1.5 else "warn"
    return "warn" if seconds is None else "down"


def roadmap(readme: str) -> list[dict]:
    """The phase table from the README's roadmap: [{'phase': '0', 'what': ..., 'status': 'Done'}]."""
    phases = []
    for line in readme.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0].isdigit():
            phases.append({"phase": cells[0], "what": cells[1], "status": cells[2]})
    return phases


def api_version(api_source: str) -> str | None:
    """The version string in src/api.py's FastAPI(...) call, read as text (no import needed)."""
    found = re.search(r'version\s*=\s*"([^"]+)"', api_source)
    return found.group(1) if found else None


def head_commit(git_dir: Path) -> str | None:
    """The checked-out commit, read from .git without running git. None if it can't be found."""
    git_dir = Path(git_dir)
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref: "):
        return head or None
    ref = head[5:]
    loose = git_dir / ref
    if loose.exists():
        return loose.read_text(encoding="utf-8").strip()
    packed = git_dir / "packed-refs"
    if packed.exists():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if line.endswith(" " + ref):
                return line.split(" ", 1)[0]
    return None


# Commit authors that are tools, not people; left out of the site's contributor list.
NOT_PEOPLE_EMAILS = {"noreply@anthropic.com"}


def parse_shortlog(text: str) -> list[dict]:
    """'git shortlog -sne' output -> [{'name', 'email', 'commits'}], most commits first.

    AI assistants and bots ([bot] accounts) are left out: the list is for people.
    """
    people = []
    for line in text.splitlines():
        found = re.match(r"\s*(\d+)\s+(.+?)\s+<([^>]*)>", line)
        if found and (found.group(3).lower() in NOT_PEOPLE_EMAILS or found.group(2).endswith("[bot]")):
            continue
        if found:
            people.append({"name": found.group(2), "email": found.group(3),
                           "commits": int(found.group(1))})
    return sorted(people, key=lambda p: -p["commits"])


def tidy_name(name: str) -> str:
    """World Athletics writes surnames in capitals: 'Neeraj CHOPRA' -> 'Neeraj Chopra'."""
    return " ".join(w.title() if w.isupper() and len(w) > 2 else w for w in name.split())


def initials(name: str) -> str:
    """'Rohith Jagan' -> 'RJ', 'Claude' -> 'C'."""
    return "".join(part[0] for part in name.split()[:2]).upper()
