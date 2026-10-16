"""Gap to the Podium: the public site (Phase 6a). It shows the results the pipeline wrote to serving/.

Run locally from the project folder:   streamlit run site/app.py
The logic lives in src/site_data.py (tested offline); this file only lays out the page.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # lets "from src import ..." work from any start folder

import altair as alt
import pandas as pd
import streamlit as st

from src import site_data as sd

INDIA, FINALISTS = "#2a78d6", "#eb6834"  # the two colours of the Phase 3 charts
API_DOCS = "https://gaptopodium.onrender.com/docs"
REPO = "https://github.com/rohithjagan05/GapToPodium"

st.set_page_config(page_title="Gap to the Podium", layout="wide")


@st.cache_data
def serving() -> dict:
    """Read the files once per session; they only change when the pipeline is rerun."""
    return sd.load_serving()


data = serving()
findings = data["findings"]


def overview() -> None:
    lo, hi = findings["gap_at_18_ci_95"]
    mae = findings["backtest_mae_points"]
    st.markdown(
        "India's best athletes are measured against the **Olympic bronze level**, which is "
        "index 100. The index is each athlete's season best as a share of the bronze mark, "
        "so a higher number is closer to a medal."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Gap at age 18", f"{findings['gap_at_18_points']:.2f} points",
              f"95% range {lo:.2f} to {hi:.2f}", delta_color="off")
    c2.metric("Typical error of the best model", f"{mae['boosting']:.2f} points",
              f"Mixed-effects model: {mae['mixed_model']:.2f}", delta_color="off",
              help="Average distance between a projected index and the index later achieved, "
                   "on data the model was not trained on.")
    c3.metric("Projection ranges that held", f"{findings['projection_range_coverage_80']:.0%}",
              "Target: 80%", delta_color="off",
              help="Share of past results that fell inside the 80% range the model gave.")
    st.caption(f"Results generated {findings['generated_at']} (UTC). Each number is a model "
               "estimate from past results, not a forecast of a medal.")


def gaps() -> None:
    st.markdown(
        "Each row is one Olympic event. For **tactical events** (middle distance, long distance "
        "and road) compare the **world rank**, not the gap, because a time gap says little there."
    )
    choice = st.radio("Show", ["All events", "Tactical events", "Other events"], horizontal=True)
    tactical = {"All events": None, "Tactical events": True, "Other events": False}[choice]
    st.dataframe(sd.gap_table(data["gaps"], tactical), hide_index=True)
    chart_data = sd.gap_chart_data(data["gaps"])
    if chart_data.empty:
        return
    st.subheader("Gap to bronze, other events")
    st.caption("Negative means India's best mark is already at or better than bronze level.")
    bars = (
        alt.Chart(chart_data)
        .mark_bar(color=INDIA)
        .encode(x=alt.X("Gap:Q", title="Gap to the bronze threshold (%)"),
                y=alt.Y("Event:N", sort=None, title=None))
        .properties(height=max(200, 18 * len(chart_data)))
    )
    st.altair_chart(bars)


def gap_at_18() -> None:
    st.markdown(
        "Average performance index by age, for India's athletes and for the 2024 Olympic "
        "finalists. The distance between the two lines is the gap."
    )
    curves = data["curves"]
    lines = (
        alt.Chart(curves)
        .mark_line(point=True)
        .encode(
            x=alt.X("age:Q", title="Age", scale=alt.Scale(domain=[16, 30])),
            y=alt.Y("perf_index:Q", title="Performance index (100 = bronze level)"),
            color=alt.Color("group:N", title=None,
                            scale=alt.Scale(domain=["India", "Finalists"],
                                            range=[INDIA, FINALISTS])),
        )
    )
    bronze = (alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(strokeDash=[4, 4], color="#8a8984")
              .encode(y="y:Q"))  # fmt: skip
    st.altair_chart(lines + bronze)
    gap = sd.gap_at_age(curves, 18)
    st.caption(f"At age 18 the gap is {gap:.2f} points. The model's 95% range for it is "
               f"{findings['gap_at_18_ci_95'][0]:.2f} to {findings['gap_at_18_ci_95'][1]:.2f}.")


def backtest() -> None:
    st.markdown(
        "Each model was asked to predict results it had not seen. Lower error is better. "
        "The ranges are the 80% ranges from the best model."
    )
    table = sd.backtest_table(data["backtest"])
    st.dataframe(table, hide_index=True)
    chart = table.rename(columns={"Model": "model", "MAE (points)": "mae"})
    st.altair_chart(
        alt.Chart(chart).mark_bar(color=INDIA)
        .encode(x=alt.X("mae:Q", title="Average error (points)"),
                y=alt.Y("model:N", sort="x", title=None))
    )


def projections() -> None:
    st.markdown(
        "Projected performance index at the 2028 Olympics, with an 80% range. Athletes whose "
        "age is outside the ages the model was trained on are flagged, because those are "
        "extrapolations."
    )
    proj = data["projections"]
    events = [None] + sorted(proj["event"].unique(), key=sd.event_label)
    c1, c2, c3 = st.columns([2, 2, 1])
    event = c1.selectbox("Event", events,
                         format_func=lambda e: "All events" if e is None else sd.event_label(e))
    athlete = c2.text_input("Athlete name contains", "")
    bronze_only = c3.checkbox("Range reaches bronze", help="Only ranges that reach bronze level.")
    table = sd.projection_table(proj, event=event, athlete=athlete.strip() or None,
                                reaches_bronze=True if bronze_only else None)
    st.dataframe(table, hide_index=True)
    st.caption("A projection is what the model expects from past careers. It is not a prediction "
               "of a result, and a wide range means the model is less sure.")


st.title("Gap to the Podium")
st.write("How far India's best athletes are from an Olympic medal, and where they could be at "
         "LA 2028.")
problems = sd.check_findings(findings, data["backtest"])
if problems:
    st.warning("The result files disagree with each other: " + "; ".join(problems))

tabs = st.tabs(["Overview", "Gaps by event", "Gap at 18", "Models tested", "2028 projections"])
with tabs[0]:
    overview()
with tabs[1]:
    gaps()
with tabs[2]:
    gap_at_18()
with tabs[3]:
    backtest()
with tabs[4]:
    projections()

st.divider()
st.caption(f"Live API: [{API_DOCS}]({API_DOCS}) · Code and method: [{REPO}]({REPO}) · "
           "Data: Olympedia, Wikipedia (CC BY-SA 4.0) and World Athletics.")