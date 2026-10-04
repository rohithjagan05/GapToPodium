"""Outline every table on a cached Olympedia results page: heading above it, headers, size.

Exploration helper. Usage: python -m scripts.peek_page_outline 2013905
"""

import sys

from bs4 import BeautifulSoup

from src.fetcher import Fetcher
from src.scrapers.olympedia import BASE_URL


def main() -> None:
    result_id = sys.argv[1]
    soup = BeautifulSoup(Fetcher().get(f"{BASE_URL}/results/{result_id}"), "lxml")
    for i, table in enumerate(soup.find_all("table")):
        heading = table.find_previous(["h1", "h2", "h3", "h4", "h5"])
        heading_text = heading.get_text(" ", strip=True) if heading else None
        rows = table.find_all("tr")
        headers = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])] if rows else []
        first = [c.get_text(" ", strip=True) for c in rows[1].find_all("td")] if len(rows) > 1 else []
        print(f"[{i}] class={table.get('class')} heading={heading_text!r} rows={len(rows) - 1}")
        print(f"     headers={headers}")
        print(f"     first row={first}")


if __name__ == "__main__":
    main()