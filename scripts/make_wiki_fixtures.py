"""Save the medal-summary tables of cached Wikipedia World Championships pages as fixtures.

Exploration helper. Keeps only tables whose header row has Event, Gold, Silver and Bronze,
including annulled (pink) rows, and never overwrites an existing fixture. Wikipedia text is
CC BY-SA 4.0, so each fixture names its source page. Usage: python -m scripts.make_wiki_fixtures
"""

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from src.config import PROJECT_ROOT
from src.fetcher import Fetcher

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
PAGES = {
    "wiki_worlds_2013.html": "https://en.wikipedia.org/wiki/2013_World_Championships_in_Athletics",
    "wiki_worlds_2019.html": "https://en.wikipedia.org/wiki/2019_World_Athletics_Championships",
    "wiki_worlds_2023.html": "https://en.wikipedia.org/wiki/2023_World_Athletics_Championships",
}


def medal_tables(soup: BeautifulSoup) -> list:
    tables = []
    for table in soup.find_all("table"):
        first = table.find("tr")
        headers = {th.get_text(strip=True) for th in first.find_all("th")} if first else set()
        if {"Event", "Gold", "Silver", "Bronze"} <= headers:
            tables.append(table)
    return tables


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher()
    for filename, url in PAGES.items():
        path = FIXTURES_DIR / filename
        if path.exists():
            print(f"skipped {filename}: already exists")
            continue
        tables = medal_tables(BeautifulSoup(fetcher.get(url), "lxml"))
        body = "\n".join(str(t) for t in tables)
        today = datetime.now(UTC).date().isoformat()
        path.write_text(
            f"<!-- Medal-summary tables from {url} (Wikipedia, CC BY-SA 4.0), saved {today}"
            " for offline tests. -->\n"
            f'<html><head><meta charset="utf-8"></head><body>\n{body}\n</body></html>\n',
            encoding="utf-8",
        )
        print(f"saved {filename}: {len(tables)} tables, {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()