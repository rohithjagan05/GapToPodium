"""World Athletics profile scraper for the athletes in data/seeds/india_athletes.csv.

For each seeded athlete with a wa_id it downloads the profile page, saves the embedded
__NEXT_DATA__ JSON to data/raw/wa/<run time>/<wa_id>.json (FR-5), and flags athletes whose
profile name or country does not match the seed (FR-6). It then extracts athletes.parquet
(birth dates) and marks.parquet (personal bests, season bests and season-by-season progression)
for senior Olympic disciplines. The site ignores the name part of the URL and uses only the
numeric ID (confirmed 4 Oct 2026), so a generic name part is used.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import RAW_DIR, SEEDS_DIR
from src.events import wa_discipline_code
from src.fetcher import Fetcher, RetryableHTTPError

logger = logging.getLogger(__name__)

PROFILE_URL = "https://worldathletics.org/athletes/india/athlete-{wa_id}"
SEED_FILE = SEEDS_DIR / "india_athletes.csv"
RAW_WA_DIR = RAW_DIR / "wa"
PROBLEMS_FILE = RAW_DIR / "wa_mismatches.csv"
PROBLEM_COLUMNS = ["seed_name", "wa_id", "issue", "detail"]
ATHLETE_COLUMNS = ["wa_id", "seed_name", "profile_name", "sex", "birth_date", "country_code"]
MARK_COLUMNS = ["wa_id", "event_key", "kind", "season", "mark_raw", "date", "venue",
                "competition", "wind", "indoor", "not_legal"]  # fmt: skip


class PageFetcher(Protocol):
    def get(self, url: str) -> str: ...


@dataclass(frozen=True)
class SeedAthlete:
    name: str
    sex: str
    events: tuple[str, ...]
    wa_id: str


def read_seeds(path: Path = SEED_FILE) -> list[SeedAthlete]:
    """Seeded athletes that have a numeric wa_id; others are skipped with a note."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    athletes: list[SeedAthlete] = []
    blank = 0
    for row in df.itertuples(index=False):
        wa_id = row.wa_id.strip()
        if not wa_id:
            blank += 1
            continue
        if not wa_id.isdigit():
            logger.warning("%s: wa_id %r is not a number; skipped", row.athlete_name, wa_id)
            continue
        events = tuple(e.strip() for e in row.events.split(";") if e.strip())
        athletes.append(SeedAthlete(row.athlete_name.strip(), row.sex.strip(), events, wa_id))
    if blank:
        logger.info("%s seeded athletes have no wa_id yet; skipped", blank)
    for wa_id, count in Counter(a.wa_id for a in athletes).items():
        if count > 1:
            logger.warning("wa_id %s appears %s times in the seed file", wa_id, count)
    return athletes


def extract_next_data(html: str) -> dict | None:
    """The JSON inside <script id="__NEXT_DATA__">, or None if the page has none."""
    tag = BeautifulSoup(html, "lxml").find("script", id="__NEXT_DATA__")
    if tag is None or not tag.string:
        return None
    return json.loads(tag.string)


def get_competitor(data: dict | None) -> dict | None:
    """data['props']['pageProps']['competitor'], or None if any level is missing."""
    node = data
    for key in ("props", "pageProps", "competitor"):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, dict) else None


def profile_name(competitor: dict) -> str:
    """'Neeraj CHOPRA' from basicData's givenName and familyName."""
    basic = competitor.get("basicData") or {}
    parts = [basic.get("givenName") or "", basic.get("familyName") or ""]
    return " ".join(p.strip() for p in parts if p and p.strip())


def _words(name: str) -> set[str]:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z]+", ascii_name.lower()))


def names_match(seed_name: str, profile: str) -> bool:
    """True if all words of one name appear in the other, ignoring case, order and accents.

    'Avinash Sable' matches 'Avinash Mukund SABLE'; 'Pahal Kiran' matches 'Kiran PAHAL'.
    """
    a, b = _words(seed_name), _words(profile)
    return bool(a) and bool(b) and (a <= b or b <= a)


def _problem(seed: SeedAthlete, issue: str, detail: str) -> dict:
    return {"seed_name": seed.name, "wa_id": seed.wa_id, "issue": issue, "detail": detail}


def scrape_profiles(
    seeds: Sequence[SeedAthlete], fetcher: PageFetcher, out_dir: Path
) -> tuple[dict[str, dict], list[dict]]:
    """Fetch each profile, save its JSON as out_dir/<wa_id>.json, and check name and country.

    Returns the competitor data per wa_id, and a list of problems: profile not found, no profile
    data, name mismatch, or a country other than IND.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    competitors: dict[str, dict] = {}
    problems: list[dict] = []
    for seed in seeds:
        url = PROFILE_URL.format(wa_id=seed.wa_id)
        try:
            html = fetcher.get(url)
        except requests.HTTPError as exc:
            problems.append(_problem(seed, "profile not found", str(exc)))
            continue
        except RetryableHTTPError as exc:
            if exc.status_code < 500:
                raise  # still refused (202/429) after waiting: stop, and rerun later
            problems.append(_problem(seed, "server error", str(exc)))
            continue
        data = extract_next_data(html)
        competitor = get_competitor(data)
        if competitor is None:
            problems.append(_problem(seed, "no profile data", url))
            continue
        path = out_dir / f"{seed.wa_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        name = profile_name(competitor)
        country = (competitor.get("basicData") or {}).get("countryCode")
        issues = []
        if not names_match(seed.name, name):
            issues.append(_problem(seed, "name mismatch", name))
        if country != "IND":
            issues.append(_problem(seed, "country is not IND", str(country)))
        problems.extend(issues)
        if issues:
            continue  # saved as evidence, but a profile that fails a check never feeds marks
        competitors[seed.wa_id] = competitor
    return competitors, problems


def disciplines_seen(competitors: dict[str, dict]) -> Counter:
    """How many athletes have each (discipline name, indoor) pair in their bests or progression."""
    seen: Counter = Counter()
    for competitor in competitors.values():
        pairs = set()
        pbs = (competitor.get("personalBests") or {}).get("results") or []
        for item in [*pbs, *(competitor.get("progressionOfSeasonsBests") or [])]:
            pairs.add((item.get("discipline"), bool(item.get("indoor"))))
        seen.update(pairs)
    return seen


def parse_wa_date(text: str | None) -> date | None:
    """'24 DEC 1997' -> date(1997, 12, 24); anything else -> None."""
    if not text:
        return None
    try:
                # A calendar date, not a moment: pin it to UTC so no local-time conversion can creep in.
        return datetime.strptime(text.strip().title(), "%d %b %Y").replace(tzinfo=UTC).date()
    except ValueError:
        return None


def _season(value) -> int | None:
    return int(value) if value is not None and str(value).isdigit() else None


def _mark_row(seed: SeedAthlete, event_key: str, kind: str, item: dict,
              season=None, indoor=None) -> dict:  # fmt: skip
    return {
        "wa_id": seed.wa_id,
        "event_key": event_key,
        "kind": kind,
        "season": _season(season),
        "mark_raw": item.get("mark"),
        "date": parse_wa_date(item.get("date")),
        "venue": item.get("venue"),
        "competition": item.get("competition") or item.get("eventName"),
        "wind": item.get("wind"),
        "indoor": bool(item.get("indoor", indoor)),
        "not_legal": bool(item.get("notLegal")),
    }


def extract_athlete(seed: SeedAthlete, competitor: dict) -> tuple[dict, list[dict]]:
    """One athlete row and their marks in senior Olympic disciplines."""
    basic = competitor.get("basicData") or {}
    athlete = {
        "wa_id": seed.wa_id,
        "seed_name": seed.name,
        "profile_name": profile_name(competitor),
        "sex": seed.sex,
        "birth_date": parse_wa_date(basic.get("birthDate")),
        "country_code": basic.get("countryCode"),
    }

    def key_for(discipline: str | None) -> str | None:
        code = wa_discipline_code(discipline or "")
        return f"{code}_{seed.sex}" if code else None

    marks: list[dict] = []
    for item in (competitor.get("personalBests") or {}).get("results") or []:
        if key := key_for(item.get("discipline")):
            marks.append(_mark_row(seed, key, "personal_best", item))
    season_bests = competitor.get("seasonsBests") or {}
    season = (season_bests.get("parameters") or {}).get("seasonsBestsSeason")
    for item in season_bests.get("results") or []:
        if key := key_for(item.get("discipline")):
            marks.append(_mark_row(seed, key, "season_best", item, season=season))
    for progression in competitor.get("progressionOfSeasonsBests") or []:
        key = key_for(progression.get("discipline"))
        if key is None:
            continue
        for item in progression.get("results") or []:
            marks.append(_mark_row(seed, key, "season_progression", item,
                                   season=item.get("season"), indoor=progression.get("indoor")))  # fmt: skip
    return athlete, marks


def extract_tables(
    seeds: Sequence[SeedAthlete], competitors: dict[str, dict]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """athletes and marks tables for every seeded athlete whose profile was saved."""
    athletes: list[dict] = []
    marks: list[dict] = []
    for seed in seeds:
        competitor = competitors.get(seed.wa_id)
        if competitor is None:
            continue
        athlete, rows = extract_athlete(seed, competitor)
        athletes.append(athlete)
        marks.extend(rows)
    athletes_df = pd.DataFrame(athletes, columns=ATHLETE_COLUMNS)
    marks_df = pd.DataFrame(marks, columns=MARK_COLUMNS).astype({"season": "Int64"})
    return athletes_df, marks_df


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.scrapers.world_athletics",
        description="Save World Athletics profile JSON for seeded athletes into data/raw/wa/.",
    )
    parser.add_argument("--seeds", type=Path, default=SEED_FILE, help="seed CSV path")
    parser.add_argument("--limit", type=int, default=None, help="only the first N athletes")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Scrape the seeded profiles, save raw JSON and extracted tables, print a summary."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    seeds = read_seeds(args.seeds)[: args.limit]
    if not seeds:
        logger.error("no seeded athletes with a wa_id; fill wa_id in %s", args.seeds)
        return 1
    run_dir = RAW_WA_DIR / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists; raw files are never overwritten")
    competitors, problems = scrape_profiles(seeds, Fetcher(), run_dir)
    pd.DataFrame(problems, columns=PROBLEM_COLUMNS).to_csv(PROBLEMS_FILE, index=False)
    athletes, marks = extract_tables(seeds, competitors)
    athletes.to_parquet(run_dir / "athletes.parquet", index=False)
    marks.to_parquet(run_dir / "marks.parquet", index=False)

    print(f"\nSaved {len(competitors)} of {len(seeds)} profiles to {run_dir}")
    print(f"Problems: {len(problems)} (listed in {PROBLEMS_FILE})")
    for p in problems:
        print(f"  {p['seed_name']} ({p['wa_id']}): {p['issue']}: {p['detail']}")
    print("\nDisciplines seen (number of athletes):")
    for (name, indoor), count in sorted(disciplines_seen(competitors).items(),
                                        key=lambda kv: (str(kv[0][0]), kv[0][1])):  # fmt: skip
        print(f"  {name}{' [indoor]' if indoor else ''}: {count}")

    with_birth = int(athletes["birth_date"].notna().sum())
    print(f"\nExtracted {len(athletes)} athletes ({with_birth} with a birth date) and "
          f"{len(marks)} marks: {marks['kind'].value_counts().to_dict()}")  # fmt: skip
    pbs = marks[(marks["kind"] == "personal_best") & ~marks["indoor"] & ~marks["not_legal"]]
    print("\nOutdoor personal bests in each athlete's seeded events:")
    for seed in seeds:
        for event_key in seed.events:
            row = pbs[(pbs["wa_id"] == seed.wa_id) & (pbs["event_key"] == event_key)]
            if row.empty:
                print(f"  {seed.name:<24} {event_key:<10} no outdoor PB found")
            else:
                best = row.iloc[0]
                print(f"  {seed.name:<24} {event_key:<10} {best['mark_raw']:<10} {best['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())