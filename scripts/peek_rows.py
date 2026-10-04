"""Print the raw HTML of every table row that contains some text, on any web page.

If a matching row has cells spanning several rows (rowspan), the following rows it spans are
printed too, since part of that entry lives there.
Exploration helper, not part of the pipeline. Uses the cached, polite Fetcher.
Usage: python -m scripts.peek_rows <url> "<text>" [max_rows]
"""

import sys

from bs4 import BeautifulSoup

from src.fetcher import Fetcher


def main() -> None:
    url, needle = sys.argv[1], sys.argv[2].lower()
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    soup = BeautifulSoup(Fetcher().get(url), "lxml")
    shown = 0
    for t_i, table in enumerate(soup.find_all("table")):
        for tr in table.find_all("tr"):
            if needle not in tr.get_text(" ", strip=True).lower():
                continue
            print(f"--- table {t_i}:")
            print(tr)
            span = max(int(c.get("rowspan", 1)) for c in tr.find_all(["td", "th"]))
            following = tr
            for _ in range(span - 1):
                following = following.find_next_sibling("tr")
                if following is None:
                    break
                print("--- continuation row:")
                print(following)
            shown += 1
            if shown >= limit:
                return
    if not shown:
        print("no matching rows")


if __name__ == "__main__":
    main()