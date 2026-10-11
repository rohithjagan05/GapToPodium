import pandas as pd

from src import charts


def test_event_labels():
    assert charts.event_label("jt_m") == "Javelin (M)"
    assert charts.event_label("3000msc_w") == "Steeplechase (W)"


def test_every_chart_writes_a_png(tmp_path):
    ci = pd.DataFrame({"event_key": ["jt_m", "lj_m", "hep_w"], "gap_best": [-4.37, -1.21, 19.28],
                       "gap_level": [-0.08, 0.76, None], "gap_low": [-1.85, -1.21, None],
                       "gap_high": [5.52, 2.29, None]})  # fmt: skip
    matched = pd.DataFrame({"discipline_group": ["throws", "long_distance", "long_distance"],
                            "world_rank": [1, 93, 6], "sb_consistent": [True, True, True]})  # fmt: skip
    imp = pd.DataFrame({"wa_id": ["a", "a", "b"], "improvement_pct": [1.0, 2.0, 1.5]})
    depth = pd.Series([34, 32, 46], index=[2016, 2021, 2024])
    paths = [
        charts.gap_intervals_chart(ci, tmp_path / "gap.png"),
        charts.rank_bands_chart(matched, {"long_distance"}, tmp_path / "ranks.png"),
        charts.improvement_chart(imp, imp, tmp_path / "improvement.png"),
        charts.india_depth_chart(depth, tmp_path / "depth.png"),
    ]
    assert all(p.exists() and p.stat().st_size > 5000 for p in paths)
    with open(paths[0], "rb") as handle:
        assert handle.read(8) == b"\x89PNG\r\n\x1a\n"