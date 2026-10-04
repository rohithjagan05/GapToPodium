"""Print the standings headers and one athlete's raw row from a cached Olympedia results page.

Exploration helper, not part of the pipeline.
Usage: python -m scripts.peek_athlete_row 2013905 Yarraji
"""

import sys

from bs4 import BeautifulSoup

from src.fetcher import Fetcher
from src.scrapers.olympedia import BASE_URL, _find_standings_table


def main() -> None:
    result_id, name = sys.argv[1], sys.argv[2]
    html = Fetcher().get(f"{BASE_URL}/results/{result_id}")
    table = _find_standings_table(BeautifulSoup(html, "lxml"))
    if table is None:
        print("no standings table")
        return
    rows = table.find_all("tr")
    headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
    print(f"{len(headers)} headers:", headers)
    for tr in rows[1:]:
        if name.lower() in tr.get_text(" ", strip=True).lower():
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            print(f"{len(cells)} cells:", cells)
            print("raw:", tr)


if __name__ == "__main__":
    main()