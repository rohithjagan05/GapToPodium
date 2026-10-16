"""Gap to the podium: the public site (Phase 6b, "Golden Hour"). It shows what the pipeline wrote to serving/.

Run locally from the project folder:   streamlit run site/app.py
The numbers come from src/site_data.py (tested offline). The page is drawn by the modules in
site/ui/: theme (tokens and CSS), parts (HTML pieces), dashboard, mission and diagnostics.
Design spec: docs/design/dashboard_concept.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for folder in (ROOT, HERE):  # "from src import ..." and "from ui import ..." from any start folder
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import streamlit as st
from ui import dashboard, diagnostics, mission, parts, theme

from src import site_data as sd

API = "https://gaptopodium.onrender.com"
API_DOCS = f"{API}/docs"
HEALTH = f"{API}/health"
REPO = "https://github.com/rohithjagan05/GapToPodium"
VIEWS = {"dashboard": "Dashboard", "mission": "Mission control"}

st.set_page_config(page_title="Gap to the podium", page_icon="🏅", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(theme.CSS, unsafe_allow_html=True)


@st.cache_data
def serving() -> dict:
    """Read the files once; they only change when the pipeline is rerun."""
    return sd.load_serving()


def current_view() -> str:
    """The view comes from ?view= (so dock links and shared URLs work) and the header toggle."""
    wanted = st.query_params.get("view", "dashboard")
    return wanted if wanted in VIEWS else "dashboard"


def header(view: str, commit: str | None) -> str:
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.markdown('<div class="wordmark"><span class="sun"></span>Gap to the podium</div>',
                    unsafe_allow_html=True)
    with right:
        inner_l, inner_r = st.columns([3, 1.2], vertical_alignment="center")
        with inner_l:
            picked = st.segmented_control("View", list(VIEWS.values()), default=VIEWS[view], key="view",
                                          label_visibility="collapsed")
        with inner_r:
            badge = (f'<a class="badge" href="{REPO}/commit/{commit}" target="_blank" rel="noopener">'
                     f'build {commit[:7]}</a>') if commit else '<span class="badge">build local</span>'
            st.markdown(f'<div class="header-right">{badge}</div>', unsafe_allow_html=True)
    chosen = next((k for k, v in VIEWS.items() if v == picked), view)
    if chosen != st.query_params.get("view", "dashboard"):
        st.query_params["view"] = chosen
    return chosen


data = serving()
info = diagnostics.build_info()
view = header(current_view(), info["commit"])
st.markdown('<div class="gap-s"></div>', unsafe_allow_html=True)

problems = sd.check_findings(data["findings"], data["backtest"])
if problems:
    st.warning("The result files disagree with each other: " + "; ".join(problems))

if view == "mission":
    mission.render(data, API_DOCS, HEALTH, REPO)
else:
    dashboard.render(data)

# The dock is fixed-position, so it can be drawn last: the API check (up to a few seconds when
# the free host is asleep) then never holds up the content above.
status, _ = diagnostics.api_state(HEALTH)
st.markdown(parts.dock(view, status, sd.data_age_days(data["findings"]["generated_at"]), API_DOCS, REPO),
            unsafe_allow_html=True)
