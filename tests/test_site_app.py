"""Smoke test: the Streamlit page runs from top to bottom with the committed results, offline."""

import pytest

from src import site_data as sd

testing = pytest.importorskip("streamlit.testing.v1")


def test_the_page_runs_without_an_exception():
    app = testing.AppTest.from_file(str(sd.SITE_ROOT / "site" / "app.py"), default_timeout=120)
    app.run()
    assert not app.exception
    assert len(app.tabs) == 5
    assert not [w for w in app.warning]  # the result files agree with each other