"""Validate the latest raw data from all three sources before it goes to the warehouse.

Reads the newest Olympedia and World Championships Parquet files, the newest World Athletics run
and the seed file, then checks: missing values, medallists without marks, medal counts, gold
beating bronze, plausible mark ranges, duplicates, seed links and early-season personal bests.
FAIL means fix before Phase 2; INFO means a person should look, but it may be real (ties,
stripped medals). Exit code 1 if anything fails. Usage: python -m src.validate
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from textwrap import indent

import pandas as pd

from src.config import RAW_DIR, SEEDS_DIR
from src.events import DISCIPLINES
from src.marks import parse_mark

PASS, FAIL, INFO = "PASS", "FAIL", "INFO"
TRACK_GROUPS = {"sprints", "hurdles", "middle_distance", "long_distance"}

# Plausible marks per discipline (seconds, metres or points), men and women, 2000 onwards. The
# "better" end of each range sits beyond the world record, so a genuine record never fails; a mark
# better than that is almost certainly a parsing or source error. The "worse" end is wide enough
# for heat runners; marks beyond it are reported as INFO (injuries, universality places).
PLAUSIBLE: dict[str, tuple[float, float]] = {
    "100m": (9.0, 15.0),
    "200m": (18.5, 31.0),
    "400m": (42.0, 70.0),
    "800m": (98.0, 165.0),  # 1:38 to 2:45
    "1500m": (200.0, 330.0),  # 3:20 to 5:30
    "5000m": (750.0, 1260.0),  # 12:30 to 21:00
    "10000m": (1550.0, 2700.0),  # 25:50 to 45:00
    "marathon": (7000.0, 14400.0),  # 1:56:40 to 4:00:00
    "110mh": (12.5, 18.0),
    "100mh": (12.0, 18.0),
    "400mh": (45.0, 75.0),
    "3000msc": (470.0, 780.0),  # 7:50 to 13:00
    "20kmw": (4500.0, 8100.0),  # 1:15 to 2:15
    "50kmw": (12600.0, 21600.0),  # 3:30 to 6:00
    "hj": (1.40, 2.50),
    "pv": (3.00, 6.50),
    "lj": (5.00, 9.00),
    "tj": (11.50, 18.50),
    "sp": (10.0, 24.0),
    "dt": (35.0, 77.0),
    "ht": (45.0, 88.0),
    "jt": (35.0, 99.0),
    "dec": (4000.0, 9200.0),
    "hep": (3500.0, 7400.0),
}


@dataclass
class CheckResult:
    source: str
    name: str
    status: str
    detail: str
    examples: pd.DataFrame | None = None


def discipline_of(event_key: str) -> str:
    """'400mh_m' -> '400mh'."""
    return event_key.rsplit("_", 1)[0]


def with_values(df: pd.DataFrame, mark_col: str = "mark_raw") -> pd.DataFrame:
    """Add mark_value: the mark as a number (seconds, metres or points), or NaN if it won't parse.

    Road events (marathon, race walks) use parse_mark's road rule for Wikipedia's "1:26.34".
    """
    values = [
        parse_mark(mark, road=DISCIPLINES.get(discipline_of(key), ("",))[0] == "road")
        for mark, key in zip(df[mark_col], df["event_key"], strict=True)
    ]
    return df.assign(mark_value=pd.to_numeric(pd.Series(values, index=df.index), errors="coerce"))


def _blank(value) -> bool:
    if isinstance(value, str):
        return not value.strip()
    return bool(pd.isna(value))


def _result(source: str, name: str, bad: pd.DataFrame, total: int, if_bad: str = FAIL,
            what: str = "rows") -> CheckResult:  # fmt: skip
    if bad.empty:
        return CheckResult(source, name, PASS, f"{total} {what} checked")
    return CheckResult(source, name, if_bad, f"{len(bad)} of {total} {what}", bad)


# --- checks that work on any source ---------------------------------------------------------


def check_required(df: pd.DataFrame, columns: Sequence[str], source: str,
                   name: str | None = None) -> CheckResult:  # fmt: skip
    """No missing or blank values in the given columns."""
    bad = df[df[list(columns)].map(_blank).any(axis=1)]
    return _result(source, name or f"no missing {', '.join(columns)}", bad, len(df))


def check_medallists_have_marks(df: pd.DataFrame, source: str) -> CheckResult:
    medallists = df[df["medal"].notna()]
    bad = medallists[medallists["mark_value"].isna()]
    return _result(source, "every medallist has a mark that parses", bad, len(medallists),
                   what="medallists")  # fmt: skip


def check_medal_counts(df: pd.DataFrame, group_cols: list[str], source: str) -> CheckResult:
    """Exactly 3 medals per event; other counts (ties, stripped medals) are listed as INFO."""
    counts = df[df["medal"].notna()].groupby(group_cols).size()
    odd = counts[counts != 3].reset_index(name="medals")
    return _result(source, "3 medals per event (ties and stripped medals are real)", odd,
                   len(counts), if_bad=INFO, what="events")  # fmt: skip


def check_gold_beats_bronze(df: pd.DataFrame, group_cols: list[str], source: str) -> CheckResult:
    """Every gold mark at least as good as every bronze mark; events without a bronze are skipped."""
    medals = df[df["medal"].isin(["Gold", "Bronze"]) & df["mark_value"].notna()]
    bad, checked = [], 0
    for keys, group in medals.groupby(group_cols):
        discipline = discipline_of(group["event_key"].iloc[0])
        if discipline not in DISCIPLINES:
            continue
        golds = group.loc[group["medal"] == "Gold", "mark_value"]
        bronzes = group.loc[group["medal"] == "Bronze", "mark_value"]
        if golds.empty or bronzes.empty:
            continue
        checked += 1
        higher_is_better = DISCIPLINES[discipline][1]
        ok = golds.min() >= bronzes.max() if higher_is_better else golds.max() <= bronzes.min()
        if not ok:
            bad.append({**dict(zip(group_cols, keys, strict=True)),
                        "gold": golds.tolist(), "bronze": bronzes.tolist()})  # fmt: skip
    return _result(source, "gold beats bronze", pd.DataFrame(bad), checked, what="events")


def check_ranges(df: pd.DataFrame, source: str) -> list[CheckResult]:
    """Marks better than plausible are almost certainly errors (FAIL). Marks worse than plausible
    are usually real, e.g. an injured athlete finishing a heat or a universality place (INFO)."""
    marks = df[df["mark_value"].notna()]
    disciplines = marks["event_key"].map(discipline_of)
    low = disciplines.map(lambda d: PLAUSIBLE.get(d, (float("-inf"), float("inf")))[0])
    high = disciplines.map(lambda d: PLAUSIBLE.get(d, (float("-inf"), float("inf")))[1])
    higher_is_better = disciplines.map(lambda d: DISCIPLINES.get(d, ("", False))[1]).astype(bool)
    too_low = marks["mark_value"] < low
    too_high = marks["mark_value"] > high
    better = (too_high & higher_is_better) | (too_low & ~higher_is_better)
    worse = (too_low & higher_is_better) | (too_high & ~higher_is_better)
    return [
        _result(source, "no marks better than plausible (likely errors)", marks[better],
                len(marks), what="marks"),
        _result(source, "marks worse than plausible (injuries, universality places)",
                marks[worse], len(marks), if_bad=INFO, what="marks"),
    ]


def check_no_duplicates(df: pd.DataFrame, key_cols: list[str], source: str) -> CheckResult:
    """No two rows share the same key (rows with a missing key part are not compared)."""
    keyed = df.dropna(subset=key_cols)
    bad = keyed[keyed.duplicated(key_cols, keep=False)]
    return _result(source, f"no duplicate {', '.join(key_cols)}", bad, len(keyed))


# --- source-specific checks ---------------------------------------------------------------


def check_marks_parse(df: pd.DataFrame, source: str) -> CheckResult:
    bad = df[df["mark_value"].isna()]
    return _result(source, "every mark parses", bad, len(df), what="marks")


def check_wa_athletes(athletes: pd.DataFrame, source: str = "world athletics") -> list[CheckResult]:
    not_indian = athletes[athletes["country_code"] != "IND"]
    no_birth = athletes[athletes["birth_date"].isna()]
    return [
        _result(source, "every athlete is Indian", not_indian, len(athletes), what="athletes"),
        _result(source, "birth dates present", no_birth, len(athletes), if_bad=INFO,
                what="athletes"),
    ]


def check_early_season_pbs(marks: pd.DataFrame, source: str = "world athletics") -> CheckResult:
    """Outdoor track PBs dated January-March: often fine (Indian season), but confirm not indoor."""
    pbs = marks[(marks["kind"] == "personal_best") & ~marks["indoor"].astype(bool)
                & ~marks["not_legal"].astype(bool)]  # fmt: skip
    groups = pbs["event_key"].map(lambda k: DISCIPLINES.get(discipline_of(k), ("", False))[0])
    months = pd.to_datetime(pbs["date"], errors="coerce").dt.month
    early = pbs[groups.isin(TRACK_GROUPS) & months.between(1, 3)]
    columns = ["wa_id", "event_key", "mark_raw", "date"]
    return _result(source, "track PBs from January-March (confirm they are outdoor)",
                   early[columns], len(pbs), if_bad=INFO, what="outdoor PBs")  # fmt: skip


def check_seed_ids(seeds: pd.DataFrame, source: str = "seeds") -> list[CheckResult]:
    with_id = seeds[seeds["wa_id"].str.strip() != ""]
    duplicated = with_id[with_id.duplicated("wa_id", keep=False)]
    missing = seeds[seeds["wa_id"].str.strip() == ""][["athlete_name", "notes"]]
    return [
        _result(source, "no duplicate wa_id", duplicated, len(with_id), what="athletes"),
        _result(source, "every athlete has a wa_id", missing, len(seeds), if_bad=INFO,
                what="athletes"),
    ]


def check_seed_links(seeds: pd.DataFrame, olympedia: pd.DataFrame,
                     source: str = "seeds") -> CheckResult:  # fmt: skip
    """Every seeded olympedia_athlete_id exists among Indian rows in the Olympedia data."""
    linked = seeds[seeds["olympedia_athlete_id"].str.strip() != ""]
    indian_ids = set(olympedia.loc[olympedia["noc"] == "IND", "olympedia_athlete_id"]
                     .dropna().astype(int).astype(str))  # fmt: skip
    bad = linked[~linked["olympedia_athlete_id"].isin(indian_ids)]
    return _result(source, "olympedia_athlete_id found in Olympedia (IND)",
                   bad[["athlete_name", "olympedia_athlete_id"]], len(linked),
                   what="athletes")  # fmt: skip


# --- loading and running --------------------------------------------------------------------


def load_inputs(raw_dir: Path = RAW_DIR,
                seeds_path: Path = SEEDS_DIR / "india_athletes.csv") -> dict:  # fmt: skip
    """The newest file from each source (file and folder names carry UTC timestamps)."""
    olympedia = max((raw_dir / "olympedia").glob("*.parquet"), default=None)
    worlds = max((raw_dir / "worlds").glob("*.parquet"), default=None)
    wa_runs = [p for p in (raw_dir / "wa").glob("*") if (p / "marks.parquet").exists()]
    wa_run = max(wa_runs, default=None)
    return {
        "olympedia": pd.read_parquet(olympedia) if olympedia else None,
        "worlds": pd.read_parquet(worlds) if worlds else None,
        "wa_athletes": pd.read_parquet(wa_run / "athletes.parquet") if wa_run else None,
        "wa_marks": pd.read_parquet(wa_run / "marks.parquet") if wa_run else None,
        "seeds": (pd.read_csv(seeds_path, dtype=str, keep_default_na=False)
                  if seeds_path.exists() else None),
    }


def run_checks(inputs: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    for key in ("olympedia", "worlds", "wa_athletes", "wa_marks", "seeds"):
        if inputs.get(key) is None:
            results.append(CheckResult(key, "input present", FAIL, "no file found"))

    if inputs.get("olympedia") is not None:
        o = with_values(inputs["olympedia"])
        group = ["edition_year", "event_key"]
        results += [
            check_required(o, ["edition_year", "event_key", "athlete_name", "noc"], "olympedia"),
            check_required(o[o["medal"].notna()], ["position"], "olympedia",
                           "every medallist has a position"),
            check_medallists_have_marks(o, "olympedia"),
            check_medal_counts(o, group, "olympedia"),
            check_gold_beats_bronze(o, group, "olympedia"),
            *check_ranges(o, "olympedia"),
            check_no_duplicates(o, [*group, "olympedia_athlete_id"], "olympedia"),
        ]
    if inputs.get("worlds") is not None:
        w = with_values(inputs["worlds"])
        group = ["championship_year", "event_key"]
        results += [
            check_required(w, ["championship_year", "event_key", "medal", "athlete_name",
                               "country_name"], "worlds"),
            check_medallists_have_marks(w, "worlds"),
            check_medal_counts(w, group, "worlds"),
            check_gold_beats_bronze(w, group, "worlds"),
            *check_ranges(w, "worlds"),
            check_no_duplicates(w, [*group, "athlete_name"], "worlds"),
        ]
    if inputs.get("wa_athletes") is not None:
        athletes = inputs["wa_athletes"]
        results += check_wa_athletes(athletes)
        results.append(check_no_duplicates(athletes, ["wa_id"], "world athletics"))
    if inputs.get("wa_marks") is not None:
        m = with_values(inputs["wa_marks"])
        results += [
            check_marks_parse(m, "world athletics"),
            *check_ranges(m, "world athletics"),
            check_early_season_pbs(m),
        ]
    if inputs.get("seeds") is not None:
        results += check_seed_ids(inputs["seeds"])
        if inputs.get("olympedia") is not None:
            results.append(check_seed_links(inputs["seeds"], inputs["olympedia"]))
    return results


def report(results: Sequence[CheckResult]) -> int:
    """Print every result, examples for FAIL and INFO; return 1 if anything failed."""
    for r in results:
        print(f"[{r.status}] {r.source}: {r.name} - {r.detail}")
        if r.status != PASS and r.examples is not None and not r.examples.empty:
            print(indent(r.examples.head(10).to_string(index=False), "        "))
    failures = [r for r in results if r.status == FAIL]
    if failures:
        print(f"\n{len(failures)} check(s) failed:")
        for r in failures:
            print(f"  - {r.source}: {r.name}")
        return 1
    print("\nAll checks passed.")
    return 0


def main() -> int:
    return report(run_checks(load_inputs()))


if __name__ == "__main__":
    raise SystemExit(main())