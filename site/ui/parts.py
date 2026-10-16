"""HTML pieces for the Golden Hour page. Each function takes data and returns one HTML string.

The strings are single lines with no blank lines or indentation, because st.markdown would
otherwise treat parts of them as Markdown (an indented line becomes a code block).
Numbers are computed in src/site_data.py; this module only positions and labels them.
"""

from __future__ import annotations

import math
from html import escape

import pandas as pd

from src import site_data as sd

_PATHS = {
    "dashboard": '<path d="M3 19h18"/><path d="M5 19l3-6h4l-1.5 6"/><path d="M12.5 19l4-9h3l-1 9"/>',
    "events": '<path d="M3 7h18M3 12h18M3 17h18"/><circle cx="16" cy="9.5" r="1.4"/><circle cx="8.5" cy="14.5" r="1.4"/>',
    "careers": '<path d="M3 19c4 0 6-3 8-7s4-7 10-7"/><path d="M15.5 5h5.5v5.5"/>',
    "models": '<circle cx="12" cy="13.5" r="7.5"/><path d="M12 13.5V9.5M9.5 3h5M12 3v3M18.2 7.3l1.3-1.3"/>',
    "y2028": ('<path d="M7.5 20C4.5 17 3.5 13 5 9"/><path d="M16.5 20c3-3 4-7 2.5-11"/>'
              '<path d="M4.4 13.2c1.6.4 2.6-.2 3.1-1.7M6 17.2c1.7 0 2.6-.8 2.8-2.3M19.6 13.2c-1.6.4-2.6-.2-3.1-1.7M18 17.2c-1.7 0-2.6-.8-2.8-2.3"/>'
              '<circle cx="12" cy="9" r="2.3"/>'),
    "mission": '<path d="M6 3h9l3 3v15H6z"/><path d="M15 3v3h3M9 11h6M9 15h6M9 7.5h3"/>',
    "api": ('<path d="M12 11v10M9 21h6"/><circle cx="12" cy="9" r="1.6"/>'
            '<path d="M8.6 5.6a4.8 4.8 0 000 6.8M15.4 5.6a4.8 4.8 0 010 6.8M6.1 3.1a8.3 8.3 0 000 11.8M17.9 3.1a8.3 8.3 0 010 11.8"/>'),
    "code": '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
}  # fmt: skip


def icon(name: str) -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_PATHS[name]}</svg>')


def _pct(value: float, lo: float, hi: float) -> float:
    """Where value sits between lo and hi, as a percentage, clamped to 0-100."""
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


def _num(value, fmt: str = ".1f", missing: str = "-") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return missing
    return format(value, fmt)


# ---------- navigation ----------


def dock(active: str, status: str, age_days: float, api_docs: str, repo: str) -> str:
    """The floating dock. Section links jump within the dashboard; Mission control is its own view."""
    on_dashboard = active == "dashboard"
    base = "" if on_dashboard else "?view=dashboard"

    def item(key: str, label: str, href: str, cls: str = "", external: bool = False) -> str:
        state = " active" if key == active else ""
        target = ' target="_blank" rel="noopener"' if external else ' target="_self"'
        ext = '<span class="ext"></span>' if external else ""
        return (f'<a class="{cls}{state}" href="{href}"{target} aria-label="{label}">{icon(key)}{ext}'
                f'<span class="label">{label}</span></a>')

    words = {"ok": "API live", "warn": "API waking", "down": "API down"}[status]
    pulse = " pulse" if status == "ok" else ""
    age = f"{age_days:.0f}d" if age_days >= 1 else "today"
    return (
        '<nav class="dock" aria-label="Sections">'
        '<div class="group">'
        + item("dashboard", "Dashboard", f"{base}#top" if base else "#top")
        + item("events", "Every event", f"{base}#events")
        + item("careers", "Over a career", f"{base}#careers")
        + item("models", "Models tested", f"{base}#models")
        + item("y2028", "LA 2028", f"{base}#y2028")
        + '</div><div class="divider"></div><div class="group">'
        + item("mission", "Mission control", "?view=mission")
        + '</div><div class="divider"></div><div class="group">'
        + item("api", "API docs", api_docs, "utility", external=True)
        + item("code", "Code on GitHub", repo, "utility", external=True)
        + f'</div><div class="status" title="{words}"><span class="dot {status}{pulse}" role="img" '
        f'aria-label="{words}"></span><span class="age">data<br>{age}</span></div></nav>'
    )


# ---------- hero and right rail ----------


def hero(gap: float, lo: float, hi: float, india: float, finalists: float, n_india: int,
         n_finalists: int, n_events: int, names: list[str]) -> str:
    """The headline gap, its 95% range and the finish-line track at age 18."""
    whole, hundredths = divmod(round(gap * 100), 100)
    lo_axis, hi_axis = 80, 102

    def x(v: float) -> float:
        return _pct(v, lo_axis, hi_axis)

    stack_india = "".join(f'<i style="background:var(--india);color:#fff">{escape(sd.initials(n))}</i>'
                          for n in names[:3])
    stack_fin = "".join(f'<i style="background:var(--finalists);opacity:{o}"></i>' for o in (1, .8, .6))
    ticks = "".join(f'<span style="left:{x(t):.2f}%">{t}</span>' for t in (80, 85, 90, 95, 100))
    left, right = sorted((x(india), x(finalists)))
    return (
        '<span id="top" class="anchor"></span>'
        '<section class="sheet hero">'
        '<div class="lanes-bg"></div>'
        '<p class="overline">Measured at age 18, against the average 2024 Olympic finalist</p>'
        '<div class="hero-row">'
        f'<div class="hero-num" aria-hidden="true"><span class="count" style="--a:{whole};--b:{hundredths}"></span></div>'
        f'<span class="sr">{gap:.2f}</span>'
        '<div class="hero-unit">points behind<small>India\'s athletes trail the average 2024 Olympic '
        'finalist by this much on the performance index (100 = bronze level), already at 18.</small></div>'
        '</div>'
        f'<div class="ci"><b>95% range</b>{lo:.2f} to {hi:.2f}</div>'
        f'<div class="track" role="img" aria-label="At age 18 the average finalist is at {finalists:.1f} '
        f'and India at {india:.1f}; bronze level is 100.">'
        f'<div class="finish" style="left:{x(100):.2f}%"><span class="finish-label">bronze 100</span></div>'
        f'<div class="lane"><span class="lane-label">Finalists<span class="mono">{finalists:.1f}</span></span>'
        f'<span class="runner finalists" style="left:{x(finalists):.2f}%"></span></div>'
        f'<div class="lane"><span class="lane-label">India<span class="mono">{india:.1f}</span></span>'
        f'<span class="runner india" style="left:{x(india):.2f}%"></span>'
        f'<span class="bracket" style="left:{left:.2f}%;width:{right - left:.2f}%;top:-1.05rem">'
        f'<span>{gap:.2f}</span></span></div>'
        f'<div class="ticks">{ticks}</div></div>'
        '<div class="float-pills">'
        f'<span class="fpill"><span class="stack">{stack_india}</span><b>{n_india}</b> Indian athletes</span>'
        f'<span class="fpill"><span class="stack">{stack_fin}</span><b>{n_finalists}</b> Olympic finalists</span>'
        f'<span class="fpill"><b>{n_events}</b> events</span>'
        '</div></section>'
    )


def closest(top: pd.DataFrame, n_reaching: int) -> str:
    """The folded 'Closest to bronze' sheet: the leader large, the next two below."""
    if top.empty:
        return '<section class="sheet fold sun-edge lift closest"><p class="overline">Closest to bronze</p><p class="note">No athletes in the data.</p></section>'
    lead = top.iloc[0]
    delta = lead["last_index"] - 100
    sign, cls = ("+", "up") if delta >= 0 else ("", "down")
    rows = "".join(
        f'<div class="runner-up"><div><div class="n">{escape(r.athlete)}</div><div class="e">{escape(r.event)}</div></div>'
        f'<div><div class="v">{r.last_index:.2f}</div><div class="p">2028: {r.projected:.1f}</div></div></div>'
        for r in top.iloc[1:].itertuples()
    )
    return (
        '<section class="sheet fold sun-edge lift closest">'
        '<p class="overline">Closest to bronze right now</p>'
        f'<div class="who">{escape(lead.athlete)}</div><span class="chip">{escape(lead.event)}</span>'
        f'<div class="big-metric"><span class="mono">{lead.last_index:.2f}</span>'
        f'<span class="delta {cls}">{sign}{delta:.2f} vs bronze</span></div>'
        f'<p class="note" style="margin:.1rem 0 .6rem;font-size:13px">Latest season index. Projected for 2028: '
        f'<span class="mono">{lead.projected:.1f}</span></p>'
        f'{rows}'
        f'<a class="rail-link" href="#y2028" target="_self">See all {n_reaching} athletes whose 2028 range reaches bronze</a>'
        '</section>'
    )


def stat_stack(mae: float, coverage: float, n_reaching: int) -> str:
    """Three stat pills of different widths, right-aligned, so they cascade."""
    cov = round(coverage * 100)

    def pill(width: str, cap: str, value: str, label: str, tip: str, extra: str = "") -> str:
        return (f'<div class="spill has-tip" tabindex="0" style="width:{width};--cap:{cap}">{extra}'
                f'<span class="v">{value}</span><span class="l">{label}</span><div class="tip">{tip}</div></div>')

    return (
        '<div class="stat-stack">'
        + pill("100%", "var(--india)", f"{mae:.2f} pts", "Typical error of the best model on seasons it never saw",
               "<b>Mean absolute error</b> of gradient boosting in the backtest: the average distance "
               "between a projected index and the one the athlete actually reached.")
        + pill("86%", "var(--ok)", f"{cov}%", "of past results landed inside the 80% ranges. Target 80%",
               "<b>Range coverage</b>: an honest 80% range should catch about 80% of real outcomes. "
               f"The model's caught <span class=\"mono\">{cov}%</span>.",
               f'<span class="ring" style="--p:{cov};--t:80" aria-hidden="true"></span>')
        + pill("68%", "var(--bronze)", str(n_reaching), "2028 ranges reach bronze",
               "<b>Athlete-events</b> whose 80% range for 2028 reaches index 100. Plausible, not likely.")
        + '</div>'
    )


# ---------- event ladder ----------

LADDER_LO, LADDER_HI = -5.0, 20.0


def ladder(rows: pd.DataFrame) -> str:
    """Events ranked by gap, with bronze as a vertical line. Tactical events show world rank."""
    if rows.empty:
        return _empty("No events match this filter.")
    zero = _pct(0, LADDER_LO, LADDER_HI)
    timer = icon("models")
    out = []
    for r in rows.itertuples():
        athlete = sd.tidy_name(r.athlete) if r.athlete else ""
        mark = f'<span class="mk">{escape(r.mark)}</span>' if r.mark else ""
        label = (f'<div><div class="ev">{escape(r.event)}</div>'
                 f'<div class="ath">{escape(athlete) or "&nbsp;"}{mark}</div></div>')
        if r.kind in ("ahead", "behind"):
            end = _pct(r.gap, LADDER_LO, LADDER_HI)
            if r.kind == "ahead":
                bar = f'<span class="bar ahead" style="left:{end:.2f}%;width:{zero - end:.2f}%"></span>'
                val = f'<span class="val" style="left:calc({zero:.2f}% + 8px)">{r.gap:+.2f}%</span>'
            else:
                bar = f'<span class="bar behind" style="left:{zero:.2f}%;width:{end - zero:.2f}%"></span>'
                if end > 80:
                    val = f'<span class="val" style="right:calc({100 - end:.2f}% + 6px);color:#fff">{r.gap:+.2f}%</span>'
                else:
                    val = f'<span class="val" style="left:calc({end:.2f}% + 6px)">{r.gap:+.2f}%</span>'
            body = f'<div class="lbar"><span class="line" style="left:{zero:.2f}%"></span>{bar}{val}</div>'
        elif r.kind == "tactical":
            rank = f"#{int(r.rank)}" if pd.notna(r.rank) else "unranked"
            body = f'<div><span class="rank">{timer}{rank}</span> <span class="muted">world rank</span></div>'
        else:
            body = '<div class="muted">No Indian mark yet</div>'
        out.append(f'<div class="lrow {r.kind}" tabindex="0">{label}{body}</div>')
    scale = "".join(f'<span style="left:{_pct(t, LADDER_LO, LADDER_HI):.2f}%">{"bronze" if t == 0 else f"{t:+d}%"}</span>'
                    for t in (-5, 0, 5, 10, 15, 20))
    return (f'<div class="ladder-head"><div>Event</div><div class="scale">{scale}</div></div>'
            f'<div class="ladder-scroll"><div class="ladder">{"".join(out)}</div></div>')


# ---------- models race ----------


def race(backtest: pd.DataFrame, metric: str) -> str:
    """Contenders as lanes; lower error sits further right, nearer the finish.

    metric: 'mae', 'rmse' or 'horizon' (four dots per lane, 1 to 4 seasons ahead).
    """
    bt = backtest.sort_values("mae").reset_index(drop=True)
    best = bt.loc[0, "contender"]
    cols = ["mae_h1", "mae_h2", "mae_h3", "mae_h4"] if metric == "horizon" else [metric]
    values = bt[cols].to_numpy().ravel()
    lo = math.floor(values.min() * 2) / 2 - 0.25
    hi = math.ceil(values.max() * 2) / 2 + 0.25

    def x(v: float) -> float:
        return 100 - _pct(v, lo, hi)

    lanes = []
    for r in bt.itertuples():
        is_best = r.contender == best
        name = escape(sd.BACKTEST_NAMES.get(r.contender, r.contender))
        pill = '<span class="best-pill">best</span>' if is_best else ""
        if metric == "horizon":
            dots = "".join(
                f'<span class="race-dot small{" best" if is_best else ""}" style="left:{x(getattr(r, c)):.2f}%">'
                f'<span class="v">{i}</span></span>' for i, c in enumerate(cols, start=1))
        else:
            v = getattr(r, metric)
            dots = (f'<span class="race-dot{" best" if is_best else ""}" style="left:{x(v):.2f}%">'
                    f'<span class="v">{v:.2f}</span></span>')
        lanes.append(f'<div class="race-lane{" best" if is_best else ""}"><div class="name">{name}{pill}</div>'
                     f'<div class="race-track">{dots}</div></div>')
    step = 0.5
    ticks, t = [], math.ceil(lo / step) * step
    while t <= hi:
        ticks.append(f'<span style="left:{x(t):.2f}%">{t:.1f}</span>')
        t += step
    axis_title = {"mae": "average error, points", "rmse": "RMSE, points",
                  "horizon": "average error by seasons ahead (1 to 4), points"}[metric]
    return (f'<div class="race">{"".join(lanes)}</div>'
            f'<div class="race-axis"><div>{axis_title}</div><div class="scale">{"".join(ticks)}</div></div>')


def model_table(backtest: pd.DataFrame) -> str:
    bt = backtest.sort_values("mae")
    best = bt.iloc[0]["contender"]
    rows = "".join(
        f'<tr class="{"best" if r.contender == best else ""}"><td>{escape(sd.BACKTEST_NAMES.get(r.contender, r.contender))}</td>'
        f'<td>{r.mae:.2f}</td><td>{r.rmse:.2f}</td><td>{r.bias:+.2f}</td><td>{_num(r.coverage_80, ".0%")}</td></tr>'
        for r in bt.itertuples())
    return ('<table class="mtable"><thead><tr><th>Model</th><th>MAE</th><th>RMSE</th><th>Bias</th>'
            f'<th>80% cover</th></tr></thead><tbody>{rows}</tbody></table>')


# ---------- 2028 ----------

def sky_range(table: pd.DataFrame) -> tuple[float, float]:
    """An axis that fits the ranges shown and always includes bronze (100), in steps of 2."""
    lo = min(float(table["Low (80%)"].min()), 99.0)
    hi = max(float(table["High (80%)"].max()), 101.0)
    return math.floor(lo / 2) * 2 - 1, math.ceil(hi / 2) * 2 + 1


def constellation(table: pd.DataFrame) -> str:
    """Projections with their 80% ranges. Hollow stars are beyond the trained ages."""
    if table.empty:
        return _empty("No projections match these filters.")
    SKY_LO, SKY_HI = sky_range(table)
    line = _pct(100, SKY_LO, SKY_HI)
    out = []
    for r in table.itertuples(index=False):
        athlete, event, _season, age, proj, low, high, reach, beyond = r
        a, b, p = (_pct(v, SKY_LO, SKY_HI) for v in (low, high, proj))
        over = ""
        if reach and high > 100:
            over = f'<span class="over" style="width:{(b - line) / max(b - a, 1e-9) * 100:.1f}%"></span>'
        flags = []
        if reach:
            flags.append("range reaches bronze")
        if beyond:
            flags.append("beyond trained ages, an extrapolation")
        tip = (f'<b>{escape(athlete)}</b>, {escape(event)}<br>Projected <span class="mono">{proj:.1f}</span>, '
               f'80% range <span class="mono">{low:.1f} to {high:.1f}</span><br>Age in 2028: '
               f'<span class="mono">{age}</span>{"<br>" + ", ".join(flags).capitalize() if flags else ""}')
        out.append(
            f'<div class="srow"><div><div class="who">{escape(athlete)}</div><div class="ev">{escape(event)}</div></div>'
            f'<div class="sky has-tip" tabindex="0" style="--x:{p:.1f}%"><span class="line" style="left:{line:.2f}%"></span>'
            f'<span class="cap" style="left:{a:.2f}%;width:{b - a:.2f}%">{over}</span>'
            f'<span class="star{" hollow" if beyond else ""}" style="left:{p:.2f}%"></span>'
            f'<div class="tip">{tip}</div></div></div>')
    step = 2 if SKY_HI - SKY_LO <= 16 else 5
    first = math.ceil(SKY_LO / step) * step
    ticks = "".join(f'<span style="left:{_pct(t, SKY_LO, SKY_HI):.2f}%">{t}</span>'
                    for t in range(int(first), int(SKY_HI) + 1, step))
    return (f'<div class="stars">{"".join(out)}</div>'
            f'<div class="race-axis" style="grid-template-columns:minmax(0,260px) 1fr;padding:0 .5rem">'
            f'<div>projected index, LA 2028</div><div class="scale">{ticks}</div></div>')


def sky_legend() -> str:
    return ('<div class="legend-row">'
            '<span class="lpill"><i style="background:var(--india);box-shadow:0 0 8px rgba(120,170,255,.8)"></i>Projection</span>'
            '<span class="lpill"><i style="background:rgba(42,120,214,.35);width:22px;border-radius:5px"></i>80% range</span>'
            '<span class="lpill"><i style="background:rgba(217,160,102,.78);width:14px;border-radius:5px"></i>Part of range past bronze</span>'
            '<span class="lpill"><i style="border:2px solid var(--india)"></i>Beyond trained ages</span>'
            '<span class="lpill"><i style="background:var(--bronze);width:3px;border-radius:2px;height:14px"></i>Bronze, 100</span>'
            '</div>')


def _empty(reason: str) -> str:
    return f'<div class="empty"><div class="lane-art"></div>{escape(reason)}</div>'


# ---------- Mission control ----------


def diag_row(status: str, key: str, detail: str, value: str) -> str:
    return (f'<div class="diag-row"><span class="dot {status}{" pulse" if status == "ok" else ""}" role="img" '
            f'aria-label="{status}"></span><div><div class="k">{escape(key)}</div><div class="d">{detail}</div></div>'
            f'<div class="v">{value}</div></div>')


def pipeline(phases: list[dict]) -> str:
    if not phases:
        return ""
    statuses = [p["status"].lower() for p in phases]
    current = next((i for i, s in enumerate(statuses) if s != "done"), len(phases) - 1)
    width = current / max(len(phases) - 1, 1)
    chips = []
    for p, s in zip(phases, statuses):
        cls = "done" if s == "done" else "next" if s == "next" else "planned"
        short = p["what"].split(":")[0].split(",")[0]
        chips.append(f'<div class="phase {cls} has-tip" tabindex="0"><span class="chip-n">{escape(p["phase"])}</span>'
                     f'<span class="what">{escape(short)}</span>'
                     f'<div class="tip"><b>Phase {escape(p["phase"])}, {escape(p["status"].lower())}</b><br>{escape(p["what"])}</div></div>')
    return (f'<div class="pipeline"><span class="done-line" style="width:calc((100% - 40px) * {width:.3f})"></span>'
            f'{"".join(chips)}</div>')
