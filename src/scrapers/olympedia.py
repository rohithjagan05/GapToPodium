"""Olympedia scraper: overall standings for individual Olympic athletics events, 2000-2024.

For each Games it reads the athletics page (the list of events), then each event's results
page, and keeps one row per athlete: position, athlete, country, medal, and the mark from the
furthest round they reached. Relays are skipped in v1. Raw output goes to data/raw/olympedia/.
"""

from __future__ import annotations

import argparse
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import pandas as pd
from bs4 import BeautifulSoup

from src.config import OLYMPEDIA_EDITIONS, RAW_DIR
from src.events import is_excluded, parse_event_name
from src.fetcher import Fetcher

logger = logging.getLogger(__name__)

BASE_URL = "https://www.olympedia.org"
MEDALS = ("Gold", "Silver", "Bronze")
EMPTY_CELLS = {"", "–", "—", "-"}  # a round the athlete did not take part in
HEADINGS = ["h1", "h2", "h3", "h4", "h5"]
COLUMNS = [
    "edition_year",
    "result_id",
    "event_name",
    "event_key",
    "position",
    "position_raw",
    "athlete_name",
    "olympedia_athlete_id",
    "noc",
    "round_reached",
    "mark_raw",
    "medal",
]

_POSITION = re.compile(r"^=?(\d+)$")  # "3", or "=3" for a tie
_ATHLETE_HREF = re.compile(r"^/athletes/(\d+)$")
_RESULT_HREF = re.compile(r"^/results/(\d+)$")


class PageFetcher(Protocol):
    """Anything with a get(url) -> html method: the real Fetcher, or a fake one in tests."""

    def get(self, url: str) -> str: ...


@dataclass(frozen=True)
class EventLink:
    result_id: int
    name: str


def parse_event_links(html: str) -> list[EventLink]:
    """Every /results/<id> link on a Games' athletics page, each result ID once, in page order."""
    soup = BeautifulSoup(html, "lxml")
    links: list[EventLink] = []
    seen: set[int] = set()
    for a in soup.select('a[href^="/results/"]'):
        match = _RESULT_HREF.match(a["href"])
        if not match:
            continue
        result_id = int(match.group(1))
        if result_id in seen:
            continue
        seen.add(result_id)
        links.append(EventLink(result_id, a.get_text(" ", strip=True)))
    return links


def parse_position(text: str) -> int | None:
    """'1' -> 1, '=3' -> 3; anything else (DNS, DNF, AC, blank, '4 h1 r2/4') -> None."""
    match = _POSITION.match(text.strip())
    return int(match.group(1)) if match else None


def _find_standings_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "Pos" in headers and "Competitor" in headers:
            return table
    return None


def _athlete_key(cell) -> str:
    """Match athletes across tables by their profile link, or by name if there is no link."""
    link = cell.find("a", href=_ATHLETE_HREF)
    return link["href"] if link else cell.get_text(" ", strip=True)


def _furthest_round(cells, round_columns) -> tuple[str | None, str | None]:
    """The last round column with a result in it, and that result."""
    round_reached, mark_raw = None, None
    for i, round_name in round_columns:
        if "split" in (cells[i].get("class") or []):
            continue  # hidden split times and walk warnings, not a round result
        text = cells[i].get_text(" ", strip=True)
        if text not in EMPTY_CELLS:
            round_reached, mark_raw = round_name, text  # later rounds overwrite earlier
    return round_reached, mark_raw


def _round_table_marks(standings) -> dict[str, tuple[str, str | None]]:
    """Fallback when the standings table has no round columns: read each round's own table.

    Below the standings, every round has a heading ("Round One", "Semi-Finals", "Final Round")
    and a table of all its athletes, followed by one table per heat under "Heat #n" headings.
    Heat tables repeat the round table, so they are skipped. Each athlete keeps the result from
    the last round they appear in. An athlete listed in a round without a mark (e.g. DNF in the
    final) still reached that round; their Pos text, such as "DNF", is kept as the result.
    """
    marks: dict[str, tuple[str, str | None]] = {}
    for table in standings.find_all_next("table"):
        if "biodata" in (table.get("class") or []):
            continue  # small info tables: date, format, wind
        heading = table.find_previous(HEADINGS)
        round_name = heading.get_text(" ", strip=True) if heading else ""
        if round_name.startswith("Heat #"):
            continue
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
        if not {"Competitor", "NOC"} <= set(headers):
            continue
        comp_i, mark_i = headers.index("Competitor"), headers.index("NOC") + 1
        pos_i = headers.index("Pos") if "Pos" in headers else None
        if mark_i >= len(headers) or not headers[mark_i]:
            continue
        for tr in rows[1:]:
            cells = tr.find_all("td")
            if len(cells) <= mark_i:
                continue
            text = cells[mark_i].get_text(" ", strip=True)
            if text in EMPTY_CELLS:
                pos_text = cells[pos_i].get_text(strip=True) if pos_i is not None else ""
                text = pos_text if pos_text and parse_position(pos_text) is None else None
            marks[_athlete_key(cells[comp_i])] = (round_name, text)
    return marks


def parse_standings(html: str) -> list[dict]:
    """One dict per athlete from a results page's overall standings table ([] if none found)."""
    table = _find_standings_table(BeautifulSoup(html, "lxml"))
    if table is None:
        return []
    headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
    if not {"Pos", "Competitor", "NOC"} <= set(headers):
        return []
    pos_i, comp_i, noc_i = (headers.index(h) for h in ("Pos", "Competitor", "NOC"))
    # Round columns sit after NOC and have a name; the unnamed ones hold medals and notes.
    round_columns = [(i, h) for i, h in enumerate(headers) if i > noc_i and h]
    # Some standings tables (e.g. the women's 100 m hurdles) have no round columns at all.
    fallback = {} if round_columns else _round_table_marks(table)

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < len(headers):
            continue  # not an athlete row
        if round_columns:
            round_reached, mark_raw = _furthest_round(cells, round_columns)
        else:
            round_reached, mark_raw = fallback.get(_athlete_key(cells[comp_i]), (None, None))
        link = cells[comp_i].find("a", href=_ATHLETE_HREF)
        medal_span = tr.find("span", class_=list(MEDALS))
        position_raw = cells[pos_i].get_text(strip=True)
        rows.append(
            {
                "position": parse_position(position_raw),
                "position_raw": position_raw,
                "athlete_name": cells[comp_i].get_text(" ", strip=True),
                "olympedia_athlete_id": (
                    int(_ATHLETE_HREF.match(link["href"]).group(1)) if link else None
                ),
                "noc": cells[noc_i].get_text(strip=True),
                "round_reached": round_reached,
                "mark_raw": mark_raw,
                "medal": medal_span.get_text(strip=True) if medal_span else None,
            }
        )
    return rows


def scrape_edition(year: int, fetcher: PageFetcher) -> pd.DataFrame:
    """All individual athletics events for one Games, one row per athlete per event."""
    events_url = f"{BASE_URL}/editions/{OLYMPEDIA_EDITIONS[year]}/sports/ATH"
    links = parse_event_links(fetcher.get(events_url))
    if not links:
        logger.warning("%s: no events found on %s; the layout may have changed", year, events_url)

    all_rows: list[dict] = []
    for link in links:
        event = parse_event_name(link.name)
        if event is None:
            if not is_excluded(link.name):
                logger.warning("%s: unknown event name %r, skipped", year, link.name)
            continue
        if event.is_relay:
            continue  # relays are v2
        url = f"{BASE_URL}/results/{link.result_id}"
        rows = parse_standings(fetcher.get(url))
        if not rows:
            logger.warning("%s %s: no standings table on %s; layout changed?", year, event.key, url)
            continue
        for row in rows:
            row.update(
                edition_year=year,
                result_id=link.result_id,
                event_name=link.name,
                event_key=event.key,
            )
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows, columns=COLUMNS)
    return df.astype(
        {"edition_year": "Int64", "result_id": "Int64", "position": "Int64",
         "olympedia_athlete_id": "Int64"}
    )  # fmt: skip


def save_raw(df: pd.DataFrame, out_dir: Path = RAW_DIR / "olympedia",
             now: datetime | None = None) -> Path:  # fmt: skip
    """Write a new timestamped Parquet file. Raw files are never overwritten."""
    now = now or datetime.now(UTC)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"olympedia_results_{now:%Y%m%dT%H%M%SZ}.parquet"
    if path.exists():
        raise FileExistsError(f"{path} already exists; raw files are never overwritten")
    df.assign(scraped_at=now).to_parquet(path, index=False)
    return path


def build_parser() -> argparse.ArgumentParser:
    """Define the command-line options."""
    parser = argparse.ArgumentParser(
        prog="python -m src.scrapers.olympedia",
        description="Scrape Olympic athletics final standings from Olympedia into data/raw/.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        choices=sorted(OLYMPEDIA_EDITIONS),
        default=sorted(OLYMPEDIA_EDITIONS),
        metavar="YEAR",
        help="Olympic years to scrape (default: all of %(default)s).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Scrape the chosen Games, save one raw file, print a summary. Returns an exit code."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fetcher = Fetcher()
    df = pd.concat([scrape_edition(year, fetcher) for year in args.years], ignore_index=True)
    if df.empty:
        logger.error("no rows scraped; nothing saved")
        return 1
    path = save_raw(df)

    summary = df.groupby("edition_year").agg(
        events=("event_key", "nunique"), rows=("athlete_name", "size")
    )
    print("\n" + summary.to_string())
    bronze = df.loc[df["medal"] == "Bronze", ["edition_year", "event_key", "athlete_name",
                                              "noc", "mark_raw"]]  # fmt: skip
    print("\nSample of bronze medals:\n" + bronze.head(10).to_string(index=False))
    print(f"\nSaved {len(df)} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())