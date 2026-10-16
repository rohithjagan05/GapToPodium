"""The dashboard view: hero, right rail, career curves, event ladder, models race and 2028."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src import site_data as sd

from . import parts
from .theme import BRONZE, FINALISTS, INDIA, INK, INK_2, INK_3, style

COLOURS = {"India": INDIA, "Finalists": FINALISTS}


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def heading(anchor: str, overline: str, title: str, note: str = "") -> None:
    html(f'<span id="{anchor}" class="anchor"></span><p class="overline">{overline}</p>'
         f'<div class="section-title" role="heading" aria-level="2">{title}</div>' + (f'<p class="note">{note}</p>' if note else ""))


def render(data: dict) -> None:
    findings = data["findings"]
    curves = data["curves"]
    at18 = curves[curves["age"] == 18].set_index("group")["perf_index"]
    lo, hi = findings["gap_at_18_ci_95"]
    top = sd.closest_to_bronze(data["projections"])
    n_reaching = int(data["projections"]["range_reaches_bronze"].astype(bool).sum())

    left, right = st.columns([8, 4], gap="large")
    with left:
        html(parts.hero(sd.gap_at_age(curves, 18), lo, hi, float(at18["India"]), float(at18["Finalists"]),
                        findings["athletes"]["india"], findings["athletes"]["finalists_2024"],
                        len(data["gaps"]), list(top["athlete"])))
    with right:
        html(parts.closest(top, n_reaching))
        html(parts.stat_stack(findings["backtest_mae_points"]["boosting"],
                              findings["projection_range_coverage_80"], n_reaching))

    html('<div class="gap-l"></div>')
    left, right = st.columns([7, 5], gap="large")
    with left:
        with st.container(key="sheet_careers"):
            careers(data)
        html('<div class="gap-l"></div>')
        with st.container(key="sheet_models"):
            models(data)
    with right, st.container(key="sheet_events"):
        events(data)

    html('<div class="gap-l"></div>')
    with st.container(key="sheet_2028"):
        projections(data)


def careers(data: dict) -> None:
    curves = data["curves"]
    heading("careers", "Over a career", "The gap is there by 18",
            "Average performance index by age. The shaded band between the lines is the gap.")
    shown = st.pills("Lines", ["India", "Finalists"], selection_mode="multi", default=["India", "Finalists"],
                     key="legend", label_visibility="collapsed") or ["India", "Finalists"]
    st.altair_chart(career_chart(curves, shown), theme=None, width="stretch")
    gap = sd.gap_at_age(curves, 18)
    lo, hi = data["findings"]["gap_at_18_ci_95"]
    html(f'<div class="foot">At 18 the gap is <span class="mono">{gap:.2f}</span> points '
         f'(95% range <span class="mono">{lo:.2f}</span> to <span class="mono">{hi:.2f}</span>). '
         'Hover the chart for any age.</div>')


def career_chart(curves: pd.DataFrame, shown: list[str]) -> alt.LayerChart:
    """Gradient lines (one hue each, building up with age), the gap band, bronze and a hover card."""
    wide = curves.pivot(index="age", columns="group", values="perf_index").reset_index()
    wide["Gap"] = wide["Finalists"] - wide["India"]
    x = alt.X("age:Q", title="Age", scale=alt.Scale(domain=[16, 30], nice=False),
              axis=alt.Axis(values=list(range(16, 31, 2)), grid=False))
    y_scale = alt.Scale(domain=[78, 102], nice=False)
    y = alt.Y("perf_index:Q", title="Performance index (100 = bronze)", scale=y_scale,
              axis=alt.Axis(values=[80, 85, 90, 95, 100], gridDash=[2, 4]))

    def fade(colour: str) -> alt.Gradient:
        r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
        return alt.Gradient(gradient="linear", x1=0, x2=1, y1=0, y2=0,
                            stops=[alt.GradientStop(color=f"rgba({r},{g},{b},0.5)", offset=0),
                                   alt.GradientStop(color=colour, offset=1)])

    band = (alt.Chart(wide).mark_area(interpolate="monotone", opacity=0.16,
                                      color=alt.Gradient(gradient="linear", x1=0, x2=0, y1=0, y2=1,
                                                         stops=[alt.GradientStop(color=FINALISTS, offset=0),
                                                                alt.GradientStop(color=INDIA, offset=1)]))
            .encode(x=x, y=alt.Y("Finalists:Q", scale=y_scale), y2="India:Q"))  # fmt: skip
    bronze = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(color=BRONZE, strokeDash=[6, 4], strokeWidth=2).encode(
        y=alt.Y("y:Q", scale=y_scale))
    bronze_label = (alt.Chart(pd.DataFrame({"y": [100], "x": [16.1], "t": ["bronze 100"]}))
                    .mark_text(align="left", dy=-9, color=BRONZE, font="JetBrains Mono, monospace", fontSize=11)
                    .encode(x=alt.X("x:Q", scale=alt.Scale(domain=[16, 30])), y=alt.Y("y:Q", scale=y_scale), text="t:N"))
    eighteen = alt.Chart(pd.DataFrame({"age": [18]})).mark_rule(color=INK_3, strokeDash=[2, 3], opacity=0.7).encode(x="age:Q")

    layers = [band, bronze, bronze_label, eighteen]
    for group in ("Finalists", "India"):
        opacity = 1.0 if group in shown else 0.15
        g = curves[curves["group"] == group]
        layers.append(alt.Chart(g).mark_line(interpolate="monotone", strokeWidth=3.5, strokeCap="round",
                                             color=fade(COLOURS[group]), opacity=opacity).encode(x=x, y=y))
        end = g[g["age"] == g["age"].max()]
        layers.append(alt.Chart(end).mark_circle(size=90, color=COLOURS[group], opacity=opacity,
                                                 stroke="#120d14", strokeWidth=2).encode(x=x, y=y))
        layers.append(alt.Chart(end).mark_text(align="left", dx=10, color=INK if group in shown else INK_3,
                                               font="Figtree, sans-serif", fontSize=13, fontWeight=600)
                      .encode(x=x, y=y, text="group:N"))

    hover = alt.selection_point(name="age_hover", nearest=True, on="pointermove", fields=["age"],
                                empty=False, clear="pointerout")
    scrub = (alt.Chart(wide).mark_rule(color=INK_2, strokeWidth=1)
             .encode(x=x, opacity=alt.condition(hover, alt.value(0.55), alt.value(0)),
                     tooltip=[alt.Tooltip("age:Q", title="Age"),
                              alt.Tooltip("Finalists:Q", format=".1f"),
                              alt.Tooltip("India:Q", format=".1f"),
                              alt.Tooltip("Gap:Q", title="Gap (points)", format=".1f")])
             .add_params(hover))  # fmt: skip
    points = (alt.Chart(curves).mark_circle(size=70, stroke="#120d14", strokeWidth=2)
              .encode(x=x, y=y, color=alt.Color("group:N", scale=alt.Scale(domain=list(COLOURS), range=list(COLOURS.values())), legend=None),
                      opacity=alt.condition(hover, alt.value(1), alt.value(0))))  # fmt: skip
    layers += [scrub, points]
    return style(alt.layer(*layers).properties(height=330, width="container",
                                               padding={"left": 4, "right": 6, "top": 10, "bottom": 4}))


def events(data: dict) -> None:
    rows = sd.ladder_rows(data["gaps"])
    heading("events", "Every event", "Where each event stands",
            "Right of the bronze line is behind it. Tactical events show the world rank instead.")
    within = rows[(rows["kind"] == "behind") & (rows["gap"] <= 3)]
    options = {
        f"All {len(rows)}": rows,
        f"Ahead {int((rows['kind'] == 'ahead').sum())}": rows[rows["kind"] == "ahead"],
        f"Within 3% {len(within)}": within,
        f"Tactical {int((rows['kind'] == 'tactical').sum())}": rows[rows["kind"] == "tactical"],
        f"No mark {int((rows['kind'] == 'none').sum())}": rows[rows["kind"] == "none"],
    }
    first = next(iter(options))
    choice = st.pills("Filter events", list(options), default=first, key="ladder_filter",
                      label_visibility="collapsed") or first
    html(parts.ladder(options[choice]))
    html('<div class="foot">Gap: India\'s best mark against the bronze level, in %. Hover a row for the mark. '
         'Tactical events (middle and long distance, road) are won on tactics, so a time gap says '
         'little there. Scroll the list for all events.</div>')


def models(data: dict) -> None:
    heading("models", "Models tested", "Five contenders, one held-out finish",
            "Each model projected seasons it never saw. Lower error sits further right, nearer the finish.")
    labels = {"Average error": "mae", "Large misses (RMSE)": "rmse", "By seasons ahead": "horizon"}
    choice = st.segmented_control("Measure", list(labels), default="Average error", key="race_metric",
                                  label_visibility="collapsed") or "Average error"
    html(parts.race(data["backtest"], labels[choice]))
    html('<div class="gap-s"></div>' + parts.model_table(data["backtest"]))


def projections(data: dict) -> None:
    heading("y2028", "LA 2028", "Who could reach bronze",
            "Projected performance index at the 2028 Olympics with an 80% range. A range reaching 100 "
            "means a medal-level season is plausible, not likely.")
    proj = data["projections"]
    events = [None] + sorted(proj["event"].unique(), key=sd.event_label)
    c1, c2, c3 = st.columns([2, 2, 1.3], vertical_alignment="bottom")
    event = c1.selectbox("Event", events, format_func=lambda e: "All events" if e is None else sd.event_label(e),
                         key="proj_event")
    athlete = c2.text_input("Athlete name contains", "", key="proj_name", placeholder="e.g. Chopra")
    reach = c3.toggle("Range reaches bronze", key="proj_reach")
    table = sd.projection_table(proj, event=event, athlete=athlete.strip() or None,
                                reaches_bronze=True if reach else None)
    html(parts.sky_legend())
    shown = table.head(20)
    html(parts.constellation(shown[["Athlete", "Event", "Last season", "Age at 2028 (by birth year)",
                                    "Projected index", "Low (80%)", "High (80%)", "Range reaches bronze",
                                    "Beyond trained ages"]]))
    if len(table) > len(shown):
        html(f'<div class="foot">The {len(shown)} highest of {len(table)} projections in this filter. '
             'The table has them all.</div>')
    st.dataframe(table, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.1f")
                                for c in ["Projected index", "Low (80%)", "High (80%)"]})
