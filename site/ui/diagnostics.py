"""Live checks for Mission control and the dock: API health, build info and contributors.

Everything here fails soft: a sleeping API, a missing .git folder or no git binary give a
neutral answer instead of an error, so the page always renders.
"""

from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import streamlit as st

from src import site_data as sd

ROOT = Path(__file__).resolve().parents[2]
HEALTH_TIMEOUT = 2.5  # seconds; Render's free tier can take far longer to wake up


@st.cache_data(ttl=60, show_spinner=False)
def ping(url: str) -> dict:
    """Time one GET of the API's /health. seconds is None when the request timed out."""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT) as response:
            answered = response.status == 200
        return {"answered": answered, "seconds": time.perf_counter() - start}
    except TimeoutError:
        return {"answered": False, "seconds": None}
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError) or "timed out" in str(error.reason):
            return {"answered": False, "seconds": None}
        return {"answered": False, "seconds": time.perf_counter() - start}
    except OSError:
        return {"answered": False, "seconds": time.perf_counter() - start}


def api_state(url: str) -> tuple[str, str]:
    """(status, text for the diagnostics row)."""
    result = ping(url)
    status = sd.api_status(result["seconds"], result["answered"])
    if result["answered"]:
        text = f"{result['seconds'] * 1000:.0f} ms"
    elif result["seconds"] is None:
        text = "waking up"
    else:
        text = "unreachable"
    return status, text


@st.cache_data(show_spinner=False)
def build_info() -> dict:
    """The deployed commit, the API version and the people in the git history."""
    commit = sd.head_commit(ROOT / ".git")
    try:
        api_source = (ROOT / "src" / "api.py").read_text(encoding="utf-8")
    except OSError:
        api_source = ""
    try:
        log = subprocess.run(["git", "shortlog", "-sne", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, timeout=3, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        log = ""
    return {"commit": commit, "api_version": sd.api_version(api_source),
            "people": sd.parse_shortlog(log)}


@st.cache_data(show_spinner=False)
def readme_phases() -> list[dict]:
    try:
        return sd.roadmap((ROOT / "README.md").read_text(encoding="utf-8"))
    except OSError:
        return []
