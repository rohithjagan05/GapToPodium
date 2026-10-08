"""Save and outline the embedded __NEXT_DATA__ JSON of any World Athletics page.

Exploration helper, not part of the pipeline. Prints every path whose key matches a pattern,
with a short preview of its value, and saves the JSON (pretty-printed) under data/.
Usage: python -m scripts.peek_next_data <url> [regex] [max_lines]
"""

import json
import re
import sys

from bs4 import BeautifulSoup

from src.config import DATA_DIR
from src.fetcher import Fetcher

DEFAULT_PATTERN = r"rank|mark|competitor|name|country|nationality|date|venue|results|total|url"


def walk(node, pattern, path="", found=None):
    """Collect (path, value preview) for every key matching the pattern; lists: first 3 items."""
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if pattern.search(key):
                found.append((child, json.dumps(value, ensure_ascii=False)[:100]))
            walk(value, pattern, child, found)
    elif isinstance(node, list):
        for i, value in enumerate(node[:3]):
            walk(value, pattern, f"{path}[{i}]", found)
    return found


def main() -> None:
    url = sys.argv[1]
    pattern = re.compile(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PATTERN, re.IGNORECASE)
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 80
    soup = BeautifulSoup(Fetcher().get(url), "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag is None or not tag.string:
        print("No __NEXT_DATA__ script found on the page.")
        return
    data = json.loads(tag.string)
    out = DATA_DIR / "peek_next_data.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    found = walk(data, pattern)
    print(f"Saved {out} ({out.stat().st_size} bytes); {len(found)} matching keys, first {limit}:")
    for path, preview in found[:limit]:
        print(f"  {path} = {preview}")


if __name__ == "__main__":
    main()