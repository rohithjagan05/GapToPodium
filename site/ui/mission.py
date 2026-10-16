"""Mission control: why the project exists, live diagnostics, build, pipeline, people, method."""

from __future__ import annotations

from html import escape

import streamlit as st

from src import site_data as sd

from . import diagnostics, parts

LEAD = {"name": "Rohith Jagan", "role": "Project lead, data and modelling"}


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def render(data: dict, api_docs: str, health_url: str, repo: str) -> None:
    findings = data["findings"]
    gap = sd.gap_at_age(data["curves"], 18)
    info = diagnostics.build_info()

    left, right = st.columns([7, 5], gap="large")
    with left:
        html('<section class="sheet fold lift" style="min-height:100%">'
             '<p class="overline">Why this exists</p>'
             '<div class="mission-statement" role="heading" aria-level="2">Find the gap early, so it can be closed.</div>'
             '<p class="note">Gap to the podium measures how far India\'s best athletes are from an Olympic '
             'medal in every athletics event, using 25 years of Olympic and World Championship results and '
             'the careers of Indian athletes and Olympic finalists.</p>'
             '<p class="note">India\'s athletes improve at much the same rate as Olympic finalists and peak '
             f'at about the same age. The difference is where they start: <span class="hl">'
             f'{gap:.2f} points behind by age 18</span>, a gap carried through the career. That points to '
             'investing earlier, in junior development.</p></section>')
    with right, st.container(key="sheet_diag"):
        diagnostics_panel(data, health_url)

    html('<div class="gap-l"></div>')
    left, right = st.columns([4, 8], gap="large")
    with left:
        html(build_ticket(info, findings, repo, api_docs))
    with right:
        html('<section class="sheet"><p class="overline">The pipeline</p>'
             '<div class="section-title" role="heading" aria-level="2">From race results to this page</div>'
             '<p class="note">Olympedia, World Athletics and Wikipedia, into BigQuery and dbt, through '
             'career models, out through a live API to this site. Hover a phase.</p>'
             f'{parts.pipeline(diagnostics.readme_phases())}</section>')

    html('<div class="gap-l"></div>')
    left, right = st.columns([6, 6], gap="large")
    with left:
        html(people(info["people"], repo, api_docs))
    with right:
        html(method(api_docs, repo, len(data["gaps"])))


def diagnostics_panel(data: dict, health_url: str) -> None:
    findings = data["findings"]
    api_status, api_text = diagnostics.api_state(health_url)
    age = sd.data_age_days(findings["generated_at"])
    problems = sd.check_findings(findings, data["backtest"])
    coverage = findings["projection_range_coverage_80"]
    api_detail = {"ok": "The public API answered its health check.",
                  "warn": "The free host sleeps when idle; it wakes on the first request.",
                  "down": "The health check failed. The site still works from its own files."}[api_status]
    consistency = ("findings.json and backtest.csv agree." if not problems
                   else escape("; ".join(problems)))
    html('<p class="overline">Live diagnostics</p><div class="section-title" role="heading" aria-level="2">System status</div>'
         + parts.diag_row(api_status, "API", api_detail, api_text)
         + parts.diag_row(sd.freshness_status(age), "Results",
                          f"Generated {escape(findings['generated_at'].replace('T', ' ').replace('Z', ' UTC'))}",
                          f"{age:.1f} days old")
         + parts.diag_row("ok" if not problems else "down", "Consistency", consistency,
                          "all checks" if not problems else f"{len(problems)} issue(s)")
         + parts.diag_row(sd.coverage_status(coverage), "Range coverage",
                          "Share of real results inside the 80% ranges. Target 80%.", f"{coverage:.0%}"))
    if st.button("Re-check now", key="recheck"):
        diagnostics.ping.clear()
        st.rerun()


def build_ticket(info: dict, findings: dict, repo: str, api_docs: str) -> str:
    commit = info["commit"]
    site = (f'<a href="{repo}/commit/{commit}" target="_blank" rel="noopener">{commit[:7]}</a>'
            if commit else "unknown")
    model = escape(findings.get("projection_model", "model"))
    return ('<section class="sheet ticket"><p class="overline" style="font-family:var(--body)">This build</p>'
            f'<div><span class="k">site</span><span class="v">{site}</span></div>'
            f'<div><span class="k">api</span><span class="v">v{escape(info["api_version"] or "?")}</span></div>'
            f'<div><span class="k">data</span><span class="v">{escape(findings["generated_at"][:16].replace("T", " "))} UTC</span></div>'
            f'<div><span class="k">model</span><span class="v">{model}</span></div>'
            f'<div><span class="k">error</span><span class="v">{findings["backtest_mae_points"]["boosting"]:.2f} pts</span></div>'
            f'<div style="margin-top:.6rem"><a href="{api_docs}" target="_blank" rel="noopener">Open the API docs</a></div>'
            '</section>')


def people(log: list[dict], repo: str, api_docs: str) -> str:
    handle = repo.rstrip("/").split("/")[-2]
    log = log or [{"name": LEAD["name"], "commits": 0}]
    avatars = []
    for person in log[:5]:
        commits = f", {person['commits']} commits" if person["commits"] else ""
        avatars.append(f'<span class="a has-tip" tabindex="0">{escape(sd.initials(person["name"]))}'
                       f'<span class="tip">{escape(person["name"])}{commits}</span></span>')
    stack = "".join(avatars)
    more = f'<span class="a">+{len(log) - 5}</span>' if len(log) > 5 else ""
    return ('<section class="sheet"><p class="overline">People</p>'
            '<div class="people person">'
            f'<div class="avatar">{escape(sd.initials(LEAD["name"]))}</div>'
            f'<div><div class="n">{escape(LEAD["name"])}</div><span class="chip">{escape(LEAD["role"])}</span>'
            f'<div class="links"><a class="badge" href="https://github.com/{escape(handle)}" target="_blank" rel="noopener">@{escape(handle)}</a>'
            f'<a class="badge" href="{api_docs}" target="_blank" rel="noopener">API</a></div></div></div>'
            '<p class="overline" style="margin-top:1.4rem">In the commit history</p>'
            f'<div class="astack">{stack}{more}</div>'
            '<p class="overline" style="margin-top:1.4rem">Data from</p>'
            '<div class="legend-row"><span class="chip">Olympedia</span><span class="chip">World Athletics</span>'
            '<span class="chip">Wikipedia, CC BY-SA 4.0</span></div></section>')


def method(api_docs: str, repo: str, n_events: int) -> str:
    return ('<section class="sheet"><p class="overline">Method</p>'
            '<div class="section-title" role="heading" aria-level="2">One scale for every event</div>'
            '<div class="formula">index = mark as a % of the event\'s bronze level<br>'
            '<span style="color:var(--ink-3)">bronze level = medallists\' season bests at the last three Games</span><br>'
            '100 = bronze, higher is always better</div>'
            f'<p class="note">So all {n_events} Olympic events, men\'s and women\'s, share one scale. Every figure on this site is '
            'a model estimate from past results, not a forecast of a medal.</p>'
            f'<div class="legend-row" style="gap:.7rem"><a class="btn" href="{api_docs}" target="_blank" rel="noopener">Open the API</a>'
            f'<a class="badge" href="{repo}#readme" target="_blank" rel="noopener">Full method on GitHub</a></div></section>')
