"""Extract the embedded __NEXT_DATA__ JSON from one World Athletics profile and show its layout.

Exploration helper, not part of the pipeline. Saves the JSON (pretty-printed) under data/ and
prints every path whose key mentions a field we need, with a short preview of its value.
Usage: python -m scripts.peek_wa_profile <profile URL>
"""

import json
import re
import sys

from bs4 import BeautifulSoup

from src.config import DATA_DIR
from src.fetcher import Fetcher

INTERESTING = re.compile(r"birth|personalbest|seasonsbest|seasonbest|name|country|discipline",
                         re.IGNORECASE)  # fmt: skip
MAX_LINES = 80


def walk(node, path="", found=None):
    """Collect (path, value preview) for every key that matches INTERESTING."""
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if INTERESTING.search(key):
                preview = json.dumps(value, ensure_ascii=False)
                found.append((child, preview[:100]))
            walk(value, child, found)
    elif isinstance(node, list):
        for i, value in enumerate(node[:3]):  # first 3 items are enough to see the shape
            walk(value, f"{path}[{i}]", found)
    return found


def main() -> None:
    url = sys.argv[1]
    soup = BeautifulSoup(Fetcher().get(url), "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag is None or not tag.string:
        print("No __NEXT_DATA__ script found on the page.")
        return
    data = json.loads(tag.string)
    out = DATA_DIR / "peek_wa_profile.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out} ({out.stat().st_size} bytes)")
    found = walk(data)
    print(f"{len(found)} matching keys; first {MAX_LINES}:")
    for path, preview in found[:MAX_LINES]:
        print(f"  {path} = {preview}")


if __name__ == "__main__":
    main()