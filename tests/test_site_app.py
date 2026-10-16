"""Smoke tests: both views of the Streamlit page run top to bottom with the committed results, offline.

The API health check cannot reach the internet in CI, so these tests also show the page still renders
when the check fails.
"""

import pytest

from src import site_data as sd

testing = pytest.importorskip("streamlit.testing.v1")

APP = str(sd.SITE_ROOT / "site" / "app.py")


def run(view: str | None = None):
    page = testing.AppTest.from_file(APP, default_timeout=120)
    if view:
        page.query_params["view"] = view
    page.run()
    return page


def html(page) -> str:
    return " ".join(m.value for m in page.markdown)


@pytest.fixture(scope="module")
def dashboard():
    return run()


@pytest.fixture(scope="module")
def mission():
    return run("mission")


def test_the_dashboard_runs_without_an_exception(dashboard):
    assert not dashboard.exception
    assert not dashboard.warning  # the result files agree with each other


def test_the_hero_shows_the_gap_at_18(dashboard):
    page = html(dashboard)
    assert "4.86" in page
    assert "2024 Olympic finalist" in page
    assert "2.97 to 6.75" in page  # the 95% range


def test_the_dashboard_has_every_section_and_the_dock(dashboard):
    page = html(dashboard)
    for anchor in ('id="top"', 'id="careers"', 'id="events"', 'id="models"', 'id="y2028"'):
        assert anchor in page
    assert 'class="dock"' in page
    assert "Neeraj Chopra" in page  # closest to bronze


def test_the_ladder_lists_all_42_events_by_default(dashboard):
    assert html(dashboard).count('class="lrow ') == 42


def test_ladder_filter_keeps_only_events_ahead_of_bronze(dashboard):
    pills = dashboard.pills(key="ladder_filter")
    ahead = next(o for o in pills.options if o.startswith("Ahead"))
    page = pills.set_value(ahead).run()
    assert not page.exception
    assert html(page).count('class="lrow ') == 2


def test_models_race_switches_measure(dashboard):
    page = dashboard.segmented_control(key="race_metric").set_value("By seasons ahead").run()
    assert not page.exception
    assert "seasons ahead (1 to 4)" in html(page)


def test_2028_filters_narrow_the_projections(dashboard):
    page = dashboard.toggle(key="proj_reach").set_value(True).run()
    assert not page.exception
    assert html(page).count('class="srow"') == 11  # ranges that reach bronze
    page = page.text_input(key="proj_name").input("Chopra").run()
    assert html(page).count('class="srow"') == 1


def test_legend_pills_can_hide_a_line(dashboard):
    page = dashboard.pills(key="legend").set_value(["India"]).run()
    assert not page.exception


def test_mission_control_runs_and_shows_its_panels(mission):
    assert not mission.exception
    page = html(mission)
    for text in ("Find the gap early", "System status", "This build", "The pipeline", "People",
                 "One scale for every event"):
        assert text in page
    assert page.count('class="phase ') == 8  # phases 0 to 7 from the README roadmap


def test_the_header_toggle_switches_view(dashboard):
    page = dashboard.segmented_control(key="view").set_value("Mission control").run()
    assert not page.exception
    assert "System status" in html(page)
    assert page.query_params["view"] == ["mission"] or page.query_params["view"] == "mission"


def test_an_unknown_view_falls_back_to_the_dashboard():
    page = run("nonsense")
    assert not page.exception
    assert 'id="careers"' in html(page)
