"""World Championships podium scraper: medal-summary tables on Wikipedia, 2013-2025.

One page per championship. Each medal-summary row names an event (in its 'details' link) and
the gold, silver and bronze athletes with country and mark. Ties put several athletes in one
cell; a vacant medal reads "Not awarded"; annulled results sit in pink rows and are skipped.
Relays (v2) and non-Olympic events are skipped. Raw output goes to data/raw/worlds/.
"""

from __future__ import annotations

import argparse
import logging
import re
from collections.abc import Sequence
from typing import Protocol

import pandas as pd
from bs4 import BeautifulSoup

from src.config import RAW_DIR
from src.events import is_worlds_excluded, parse_worlds_event_name
from src.fetcher import Fetcher
from src.marks import parse_mark
from src.raw import save_raw

logger = logging.getLogger(__name__)

WIKI_BASE = "https://en.wikipedia.org/wiki/"
# Page titles checked on 4 Oct 2026; editions before 2019 use "World Championships in Athletics".
WORLDS_PAGES: dict[int, str] = {
    2013: "2013_World_Championships_in_Athletics",
    2015: "2015_World_Championships_in_Athletics",
    2017: "2017_World_Championships_in_Athletics",
    2019: "2019_World_Athletics_Championships",
    2022: "2022_World_Athletics_Championships",
    2023: "2023_World_Athletics_Championships",
    2025: "2025_World_Athletics_Championships",
}
MEDALS = ("Gold", "Silver", "Bronze")
COLUMNS = [
    "championship_year",
    "event_title",
    "event_key",
    "medal",
    "athlete_name",
    "country_name",
    "country_code",
    "mark_raw",
    "source_url",
]
_COUNTRY_CODE = re.compile(r"\(([A-Z]{3})\)")  # "(UKR)" on pages before 2019


class PageFetcher(Protocol):
    """Anything with a get(url) -> html method: the real Fetcher, or a fake one in tests."""

    def get(self, url: str) -> str: ...


def _is_medal_table(table) -> bool:
    first = table.find("tr")
    headers = {th.get_text(strip=True) for th in first.find_all("th")} if first else set()
    return {"Event", "Gold", "Silver", "Bronze"} <= headers


def _is_annulled(tr) -> bool:
    """Wikipedia shows annulled (later disqualified) results in pink rows."""
    colour = f"{tr.get('bgcolor', '')} {tr.get('style', '')}".lower()
    return "pink" in colour


def _event_title(cell) -> str | None:
    """'Men's javelin throw' from the cell's 'details' link, or None if the cell has none."""
    link = cell.select_one("span.noprint a[title]")
    return link["title"].split(" – ", 1)[-1] if link else None


def parse_medal_cell(cell) -> list[tuple[str, str, str | None]]:
    """(athlete, country name, country code or None) for each athlete in a medal cell.

    Each athlete link is followed by a link to "<Country> at the <championships>"; ties list
    several such pairs in one cell. A cell reading "Not awarded" gives [].
    """
    athletes: list[tuple[str, str, str | None]] = []
    current: str | None = None
    for a in cell.find_all("a", href=True):
        href = a["href"]
        if "_at_the_" in href:
            if current is None:
                continue
            code = None
            if a.parent is not None and a.parent.name == "span":
                match = _COUNTRY_CODE.search(a.parent.get_text(" ", strip=True))
                code = match.group(1) if match else None
            athletes.append((current, a.get_text(" ", strip=True), code))
            current = None
        elif "File:" not in href and "Athletics_abbreviations" not in href:
            current = a.get_text(" ", strip=True)
    countries = sum("_at_the_" in a["href"] for a in cell.find_all("a", href=True))
    if countries != len(athletes):
        logger.warning("medal cell with %s countries but %s athletes: %r",
                       countries, len(athletes), cell.get_text(" ", strip=True)[:80])  # fmt: skip
    return athletes

def split_marks(text: str, n: int) -> list[str | None]:
    """The mark text for each of the n athletes in one medal cell, in cell order.

    One athlete gets the whole cell text. Tied athletes usually share one mark, but a cell can
    list one mark per athlete in order (e.g. "13.18 13.30 [47]" for a bronze shared after an
    appeal), so when the number of marks equals the number of athletes, each gets their own.
    """
    text = text.strip()
    if n <= 1:
        return [text or None] * n
    values = [t for t in re.sub(r"\[.*?\]", " ", text).split() if parse_mark(t) is not None]
    return values if len(values) == n else [text or None] * n

def parse_medal_tables(html: str) -> list[dict]:
    """One dict per medallist from every medal-summary table on a championship page."""
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    for table in filter(_is_medal_table, soup.find_all("table")):
        for tr in table.find_all("tr"):
            if _is_annulled(tr):
                continue
            cells = tr.find_all(["td", "th"], recursive=False)
            title = _event_title(cells[0]) if cells else None
            if title is None:
                if tr.find("a", href=lambda h: h is not None and "_at_the_" in h):
                    logger.warning("row with athletes but no event skipped: %r",
                                   tr.get_text(" ", strip=True)[:80])  # fmt: skip
                continue  # header, spacer and legend rows
            event = parse_worlds_event_name(title)
            if event is None:
                if not is_worlds_excluded(title):
                    logger.warning("unknown Worlds event name %r, skipped", title)
                continue
            if event.is_relay:
                continue  # relays are v2
                        # A shared medal leaves the next medal as one merged cell ("Not awarded", colspan="2"),
            # so expand every cell by its colspan before reading the seven column slots.
            slots = [c for c in cells for _ in range(int(c.get("colspan", 1)))]
            if len(slots) < 7:
                logger.warning("%s: expected 7 columns, found %s; skipped", title, len(slots))
                continue
            pairs = [(slots[1], slots[2]), (slots[3], slots[4]), (slots[5], slots[6])]
            for medal, (who, mark) in zip(MEDALS, pairs, strict=True):
                athletes = parse_medal_cell(who)
                marks = split_marks(mark.get_text(" ", strip=True), len(athletes))
                for (athlete, country, code), mark_raw in zip(athletes, marks, strict=True):
                    rows.append(
                        {
                            "event_title": title,
                            "event_key": event.key,
                            "medal": medal,
                            "athlete_name": athlete,
                            "country_name": country,
                            "country_code": code,
                            "mark_raw": mark_raw,
                        }
                    )
    return rows


def scrape_championship(year: int, fetcher: PageFetcher) -> pd.DataFrame:
    """All individual Olympic-event medallists for one World Championships."""
    url = WIKI_BASE + WORLDS_PAGES[year]
    rows = parse_medal_tables(fetcher.get(url))
    if not rows:
        logger.warning("%s: no medal-summary rows on %s; layout changed?", year, url)
    for row in rows:
        row.update(championship_year=year, source_url=url)
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.astype({"championship_year": "Int64"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.scrapers.wikipedia_worlds",
        description="Scrape World Championships podiums from Wikipedia into data/raw/worlds/.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        choices=sorted(WORLDS_PAGES),
        default=sorted(WORLDS_PAGES),
        metavar="YEAR",
        help="Championship years to scrape (default: all of %(default)s).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Scrape the chosen championships, save one raw file, print checks. Returns an exit code."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fetcher = Fetcher()
    df = pd.concat([scrape_championship(y, fetcher) for y in args.years], ignore_index=True)
    if df.empty:
        logger.error("no rows scraped; nothing saved")
        return 1
    path = save_raw(df, RAW_DIR / "worlds", "worlds_podium")

    summary = df.groupby("championship_year").agg(
        events=("event_key", "nunique"), rows=("athlete_name", "size")
    )
    print("\n" + summary.to_string())
    unparsed = df[df["mark_raw"].map(parse_mark).isna()]
    print(f"\nRows whose mark does not parse: {len(unparsed)}")
    if len(unparsed):
        print(unparsed[["championship_year", "event_key", "athlete_name", "mark_raw"]]
              .head(15).to_string(index=False))  # fmt: skip
    india = df[df["country_name"] == "India"]
    columns = ["championship_year", "event_key", "medal", "athlete_name", "mark_raw"]
    print("\nIndian medals:\n" + (india[columns].to_string(index=False) if len(india) else "none"))
    print(f"\nSaved {len(df)} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())