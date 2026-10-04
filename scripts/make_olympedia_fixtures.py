"""Save trimmed copies of cached Olympedia pages as offline test fixtures.

Exploration helper. Keeps only the tables the scraper parses, so fixtures stay small.
The pages must already be cached (run scripts.list_olympedia_events and
scripts.peek_results_page first). Usage: python -m scripts.make_olympedia_fixtures
"""

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from src.config import PROJECT_ROOT
from src.fetcher import Fetcher

FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
RESULTS_PAGES = {
    "olympedia_2024_javelin_m.html": "https://www.olympedia.org/results/2013734",
    "olympedia_2024_800m_m.html": "https://www.olympedia.org/results/2013553",
}
EVENTS_PAGE = ("olympedia_2024_ath_events.html", "https://www.olympedia.org/editions/63/sports/ATH")

# CSS selectors: links whose address starts with /athletes/ or /results/
ATHLETE_LINK = 'a[href^="/athletes/"]'
RESULT_LINK = 'a[href^="/results/"]'


def standings_table(soup: BeautifulSoup):
    """The first table whose header cells include 'Pos' and 'Competitor'."""
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "Pos" in headers and "Competitor" in headers:
            return table
    raise ValueError("no standings table found")


def event_link_tables(soup: BeautifulSoup) -> list:
    """Every table that contains a link to a results page."""
    tables = [t for t in soup.find_all("table") if t.select_one(RESULT_LINK)]
    if not tables:
        raise ValueError("no table with /results/ links found")
    return tables


def save(filename: str, url: str, tables: list) -> None:
    body = "\n".join(str(t) for t in tables)
    html = (
                f"<!-- Trimmed from {url} on {datetime.now(UTC).date().isoformat()} for offline tests. -->\n"
        f'<html><head><meta charset="utf-8"></head><body>\n{body}\n</body></html>\n'
    )
    path = FIXTURES_DIR / filename
    path.write_text(html, encoding="utf-8")
    print(f"saved {path.name}: {len(tables)} table(s), {path.stat().st_size} bytes")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher()

    for filename, url in RESULTS_PAGES.items():
        table = standings_table(BeautifulSoup(fetcher.get(url), "lxml"))
        save(filename, url, [table])
        rows = table.find_all("tr")
        athlete_links = table.select(ATHLETE_LINK)
        print(f"  {len(rows)} <tr> rows, {len(athlete_links)} athlete links")
        print("  first two rows as raw HTML:")
        for row in rows[:2]:
            print("   ", row)

    filename, url = EVENTS_PAGE
    tables = event_link_tables(BeautifulSoup(fetcher.get(url), "lxml"))
    save(filename, url, tables)
    for i, table in enumerate(tables):
        print(f"  table {i}: {len(table.select(RESULT_LINK))} result links")


if __name__ == "__main__":
    main()