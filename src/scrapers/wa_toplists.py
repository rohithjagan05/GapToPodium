"""World Athletics toplists: the world's best athletes per event and season (season bests).

One page per event and season lists up to 100 athletes, each with rank, season-best mark, World
Athletics ID (from the profile link), date of birth, nationality and the race the mark came from.
Outdoor lists only, one mark per athlete. Raw output goes to data/raw/wa_toplists/.
Usage: python -m src.scrapers.wa_toplists [--seasons 2016 2021 ...] [--events jt_m ...]
"""

from __future__ import annotations

import argparse
import logging
import re
from collections.abc import Sequence
from typing import Protocol

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import RAW_DIR
from src.events import WA_TOPLIST_SLUGS, programme_event_keys
from src.fetcher import Fetcher, RetryableHTTPError
from src.raw import save_raw
from src.scrapers.world_athletics import parse_wa_date

logger = logging.getLogger(__name__)

BASE_URL = "https://worldathletics.org/records/toplists"
# The seasons of the last three Olympics (Tokyo 2020 was held in 2021), plus the current ones.
DEFAULT_SEASONS = (2016, 2021, 2024, 2025, 2026)
COLUMNS = ["season", "event_key", "rank", "mark_raw", "wind", "athlete_name", "wa_id",
           "birth_date", "country_code", "place", "venue", "date", "result_score",
           "source_url"]  # fmt: skip
_ATHLETE_HREF = re.compile(r"athlete=(\d+)")


class PageFetcher(Protocol):
    def get(self, url: str, refresh: bool = False) -> str: ...


def toplist_url(event_key: str, season: int, page: int = 1) -> str:
    """The outdoor, one-mark-per-athlete world toplist URL for an event and season."""
    discipline, sex = event_key.rsplit("_", 1)
    group, slug = WA_TOPLIST_SLUGS[discipline]
    gender = "men" if sex == "m" else "women"
    return (f"{BASE_URL}/{group}/{slug}/outdoor/{gender}/senior/{season}"
            f"?regionType=world&page={page}&bestResultsOnly=true")  # fmt: skip


def _as_int(text: str) -> int | None:
    text = text.strip()
    return int(text) if text.isdigit() else None


def _cell_text(cells: dict, name: str) -> str:
    cell = cells.get(name)
    return cell.get_text(" ", strip=True) if cell else ""


def parse_toplist(html: str) -> list[dict]:
    """One dict per athlete row. Cells are found by their data-th label, not their position."""
    rows = []
    for tr in BeautifulSoup(html, "lxml").select("table tr"):
        cells = {td.get("data-th", "").strip(): td for td in tr.find_all("td")}
        if "Competitor" not in cells or "Mark" not in cells:
            continue  # header or spacer row
        link = cells["Competitor"].find("a", href=_ATHLETE_HREF)
        rows.append(
            {
                "rank": _as_int(_cell_text(cells, "Rank")),
                "mark_raw": _cell_text(cells, "Mark") or None,
                "wind": _cell_text(cells, "WIND") or None,
                "athlete_name": _cell_text(cells, "Competitor"),
                "wa_id": _ATHLETE_HREF.search(link["href"]).group(1) if link else None,
                "birth_date": parse_wa_date(_cell_text(cells, "DOB")),
                "country_code": _cell_text(cells, "Nat") or None,
                "place": _cell_text(cells, "Pos") or None,
                "venue": _cell_text(cells, "Venue") or None,
                "date": parse_wa_date(_cell_text(cells, "Date")),
                "result_score": _as_int(_cell_text(cells, "ResultScore")),
            }
        )
    return rows


def _get_page(fetcher: PageFetcher, url: str, label: str, refresh: bool = False) -> str | None:
    """The page's HTML, or None after logging a missing page or a persistent server error."""
    try:
        return fetcher.get(url, refresh=refresh)
    except requests.HTTPError as exc:
        logger.warning("%s: %s", label, exc)
        return None
    except RetryableHTTPError as exc:
        if exc.status_code < 500:
            raise  # still refused (202/429) after waiting: stop, and rerun later
        logger.warning("%s: server error %s", label, exc.status_code)
        return None


def scrape_toplists(events: Sequence[str], seasons: Sequence[int],
                    fetcher: PageFetcher) -> pd.DataFrame:  # fmt: skip
    """Every requested event and season; pages that fail or have no rows are logged and skipped.

    World Athletics sometimes serves a normal-looking page (HTTP 200, so it gets cached) with no
    results table; such a page is fetched once more, fresh, before it is given up on.
    """
    all_rows: list[dict] = []
    for season in seasons:
        for event_key in events:
            url = toplist_url(event_key, season)
            label = f"{season} {event_key}"
            html = _get_page(fetcher, url, label)
            rows = parse_toplist(html) if html else []
            if html and not rows:
                logger.info("%s: no results table; fetching the page again", label)
                html = _get_page(fetcher, url, label, refresh=True)
                rows = parse_toplist(html) if html else []
            if not rows:
                logger.warning("%s: no toplist rows on %s", label, url)
                continue
            for row in rows:
                row.update(season=season, event_key=event_key, source_url=url)
            all_rows.extend(rows)
    df = pd.DataFrame(all_rows, columns=COLUMNS)
    return df.astype({"season": "Int64", "rank": "Int64", "result_score": "Int64"})


def build_parser() -> argparse.ArgumentParser:
    events = programme_event_keys()
    parser = argparse.ArgumentParser(
        prog="python -m src.scrapers.wa_toplists",
        description="Scrape World Athletics outdoor world toplists into data/raw/wa_toplists/.",
    )
    parser.add_argument("--seasons", nargs="+", type=int, default=list(DEFAULT_SEASONS),
                        metavar="YEAR", help="seasons (default: %(default)s)")  # fmt: skip
    parser.add_argument("--events", nargs="+", choices=events, default=events,
                        metavar="EVENT", help="event keys (default: the 42 Paris 2024 events)")  # fmt: skip
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df = scrape_toplists(args.events, args.seasons, Fetcher())
    if df.empty:
        logger.error("no toplist rows scraped; nothing saved")
        return 1
    path = save_raw(df, RAW_DIR / "wa_toplists", "wa_toplists")

    per_season = df.groupby("season").agg(events=("event_key", "nunique"),
                                          rows=("athlete_name", "size"))  # fmt: skip
    print("\n" + per_season.to_string())
    sizes = df.groupby(["season", "event_key"]).size()
    short = sizes[sizes < 100]
    print(f"\nEvent-seasons with fewer than 100 athletes: {len(short)}")
    if len(short):
        print(short.to_string())
    india = df[df["country_code"] == "IND"].groupby("season").size()
    print("\nIndian athletes in the world top 100, by season:\n" + india.to_string())
    print(f"\nSaved {len(df)} rows to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())