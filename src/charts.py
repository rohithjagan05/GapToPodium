"""Phase 3 charts: static PNGs for the notebook and the README (docs/images/).

One visual system for every chart: a light surface, recessive grid, thin marks, India in blue
and the comparison group in orange (the first two slots of a validated colourblind-safe palette),
and text in ink colours rather than series colours.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files, no window (works in tests and on servers)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
INDIA, OTHER, NEUTRAL = "#2a78d6", "#eb6834", "#8a8984"

EVENT_NAMES = {
    "100m": "100 m", "200m": "200 m", "400m": "400 m", "800m": "800 m", "1500m": "1500 m",
    "5000m": "5000 m", "10000m": "10,000 m", "3000msc": "Steeplechase", "marathon": "Marathon",
    "110mh": "110 m hurdles", "100mh": "100 m hurdles", "400mh": "400 m hurdles",
    "20kmw": "20 km walk", "hj": "High jump", "pv": "Pole vault", "lj": "Long jump",
    "tj": "Triple jump", "sp": "Shot put", "dt": "Discus", "ht": "Hammer", "jt": "Javelin",
    "dec": "Decathlon", "hep": "Heptathlon",
}  # fmt: skip


def event_label(event_key: str) -> str:
    """'jt_m' -> "Javelin (M)"."""
    discipline, sex = event_key.rsplit("_", 1)
    return f"{EVENT_NAMES.get(discipline, discipline)} ({sex.upper()})"


def _figure(width: float, height: float):
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8, length=0)
    return fig, ax


def _finish(fig, ax, title: str, subtitle: str, path: Path) -> Path:
    # title and subtitle sit a fixed distance above the plot, whatever the figure's height
    ax.annotate(title, (0, 1), xycoords="axes fraction", xytext=(0, 24), textcoords="offset points",
                fontsize=11, color=INK, fontweight="bold")  # fmt: skip
    ax.annotate(subtitle, (0, 1), xycoords="axes fraction", xytext=(0, 10),
                textcoords="offset points", fontsize=8, color=INK_2)  # fmt: skip
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    return path


def gap_intervals_chart(ci: pd.DataFrame, path: Path) -> Path:
    """Each event's gap: repeatable level with its 95% interval, and the single best mark.

    ci needs event_key, gap_best, gap_level, gap_low, gap_high (from analysis.gap_intervals).
    """
    df = ci.assign(sort=ci["gap_level"].fillna(ci["gap_best"])).sort_values("sort", ascending=False)
    fig, ax = _figure(7, 0.24 * len(df) + 1.2)
    y = np.arange(len(df))
    ax.axvline(0, color=INK_2, linewidth=1, zorder=1)
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    has_ci = df["gap_low"].notna().to_numpy()
    ax.hlines(y[has_ci], df["gap_low"][has_ci], df["gap_high"][has_ci], color=INDIA,
              linewidth=2, alpha=0.35, zorder=2, label="95% interval")  # fmt: skip
    ax.scatter(df["gap_level"], y, s=28, color=INDIA, zorder=3, label="Repeatable level (best 3)")
    ax.scatter(df["gap_best"], y, s=28, facecolors=SURFACE, edgecolors=NEUTRAL, linewidths=1.2,
               zorder=3, label="Single best mark")  # fmt: skip
    ax.set_yticks(y, [event_label(k) for k in df["event_key"]], fontsize=7.5, color=INK)
    ax.set_ylim(-0.7, len(df) - 0.3)
    ax.set_xlabel("Gap to the Olympic bronze threshold, % (0 = threshold; positive = behind)",
                  fontsize=8, color=INK_2)  # fmt: skip
    ax.legend(loc="upper right", fontsize=7, frameon=False, labelcolor=INK_2)
    return _finish(fig, ax, "How far India is from the podium, and how sure we are",
                   "India's best athlete per event, 2026 races; events without three races show "
                   "the single best only", path)  # fmt: skip


def rank_bands_chart(matched: pd.DataFrame, tactical_groups: set[str], path: Path) -> Path:
    """H1: share of Olympic medallists by their season-best world rank, tactical vs all-out events."""
    ok = matched[matched["sb_consistent"].eq(True)]
    bands = pd.cut(ok["world_rank"].astype(float), [0, 3, 10, 30, np.inf],
                   labels=["1-3", "4-10", "11-30", "31+"])  # fmt: skip
    kind = np.where(ok["discipline_group"].isin(tactical_groups), "Tactical events", "All-out events")
    shares = pd.crosstab(kind, bands, normalize="index") * 100
    fig, ax = _figure(6.5, 3.4)
    x = np.arange(len(shares.columns))
    for i, (name, colour) in enumerate([("All-out events", NEUTRAL), ("Tactical events", OTHER)]):
        values = shares.loc[name].to_numpy()
        bars = ax.bar(x + (i - 0.5) * 0.38, values, width=0.36, color=colour, label=name, zorder=2)
        ax.bar_label(bars, fmt="%.0f%%", fontsize=7, color=INK_2, padding=2)
    ax.set_xticks(x, [f"World rank {b}" for b in shares.columns], fontsize=8, color=INK)
    ax.set_yticks([])
    ax.legend(fontsize=7.5, frameon=False, labelcolor=INK_2)
    return _finish(fig, ax, "In tactical events, 1 medallist in 4 came from outside the top 10",
                   "Olympic medallists 2016-2024 by their season-best world rank that year",
                   path)  # fmt: skip


def improvement_chart(india: pd.DataFrame, finalists: pd.DataFrame, path: Path) -> Path:
    """H2: each athlete's median yearly improvement at ages 18-24, India vs 2024 finalists."""
    groups = [("2024 finalists", finalists, OTHER), ("India", india, INDIA)]
    fig, ax = _figure(6.5, 3.0)
    rng = np.random.default_rng(0)
    for i, (_, df, colour) in enumerate(groups):
        values = df.groupby("wa_id")["improvement_pct"].median().clip(-10, 15).to_numpy()
        ax.scatter(values, i + rng.uniform(-0.18, 0.18, len(values)), s=10, color=colour,
                   alpha=0.55, linewidths=0, zorder=2)  # fmt: skip
        median = np.median(values)
        ax.vlines(median, i - 0.3, i + 0.3, color=INK, linewidth=2, zorder=3)
        ax.text(median, i + 0.34, f"median {median:.2f}%", fontsize=7.5, color=INK, ha="center")
    ax.axvline(0, color=GRID, linewidth=1, zorder=1)
    ax.set_yticks([0, 1], [f"{name}\n({df['wa_id'].nunique()} athletes)" for name, df, _ in groups],
                  fontsize=8, color=INK)  # fmt: skip
    ax.set_ylim(-0.6, 1.75)
    ax.set_xlabel("Median yearly improvement, ages 18-24 (%, clipped to -10..15)", fontsize=8,
                  color=INK_2)  # fmt: skip
    return _finish(fig, ax, "Indian athletes improve at least as fast as future finalists",
                   "One dot per athlete; percent change between back-to-back season bests",
                   path)  # fmt: skip


def india_depth_chart(counts: pd.Series, path: Path) -> Path:
    """Indian entries in the world top 100, summed over the 42 Olympic events, by season."""
    fig, ax = _figure(5.5, 3.0)
    bars = ax.bar(counts.index.astype(str), counts.to_numpy(), width=0.55, color=INDIA, zorder=2)
    ax.bar_label(bars, fontsize=8, color=INK, padding=2)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=8, labelcolor=INK)
    return _finish(fig, ax, "More Indian athletes in the world top 100",
                   "Indian entries across the 42 Olympic events' world top-100 lists; "
                   "2026 season in progress", path)  # fmt: skip



# --- Phase 4 ----------------------------------------------------------------------------------

def trajectory_chart(curves: pd.DataFrame, path: Path) -> Path:
    """Average performance index by age for India and 2024 finalists (mixed model's fixed part).

    curves needs group ("India" / "Finalists"), age and perf_index (trajectory.mean_curves).
    """
    wide = curves.pivot(index="age", columns="group", values="perf_index")
    fig, ax = _figure(6.5, 3.4)
    ax.axhline(100, color=INK_2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.text(wide.index.min(), 100.3, "bronze level (100)", fontsize=7, color=INK_2)
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    for name, colour in (("Finalists", OTHER), ("India", INDIA)):
        ax.plot(wide.index, wide[name], color=colour, linewidth=2, zorder=3)
        ax.text(wide.index.max() + 0.3, wide[name].iloc[-1],
                "2024 finalists" if name == "Finalists" else "India", fontsize=8, color=colour,
                va="center")  # fmt: skip
    at18 = wide.loc[18]
    ax.vlines(18, at18["India"], at18["Finalists"], color=INK, linewidth=1.2, zorder=4)
    ax.text(18.2, at18["India"] - 1.2, f"gap at 18: {at18['Finalists'] - at18['India']:.1f} points",
            fontsize=8, color=INK, va="top")  # fmt: skip
    ax.set_xlim(wide.index.min() - 0.5, wide.index.max() + 3)
    ax.set_xlabel("Age", fontsize=8, color=INK_2)
    ax.set_ylabel("Performance index (% of bronze level)", fontsize=8, color=INK_2)
    return _finish(fig, ax, "India's gap is already there at 18, and it stays",
                   "Average career curves from the mixed-effects model, ages 16-30", path)


def backtest_chart(scores: pd.DataFrame, chosen: str, path: Path) -> Path:
    """Mean absolute error of each contender on the hidden 2023-2026 seasons, best at the top."""
    labels = {"last_season": "Same as last season", "age_trend": "Last season + age trend",
              "fixed_curve": "Group curve only (plain regression)",
              "boosting": "Gradient boosting", "mixed_model": "Mixed-effects model"}  # fmt: skip
    df = scores.sort_values("mae", ascending=False)
    fig, ax = _figure(6.5, 0.42 * len(df) + 1.0)
    colours = [INDIA if c == chosen else NEUTRAL for c in df["contender"]]
    bars = ax.barh([labels.get(c, c) for c in df["contender"]], df["mae"], color=colours,
                   height=0.6, zorder=2)  # fmt: skip
    ax.bar_label(bars, fmt="%.2f", fontsize=8, color=INK, padding=3)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8, labelcolor=INK)
    return _finish(fig, ax, "Gradient boosting predicts unseen seasons best",
                   "Average miss in index points (lower is better); fit to 2022, predict 2023-2026",
                   path)  # fmt: skip


def projections_chart(proj: pd.DataFrame, path: Path, top: int = 15) -> Path:
    """Projected 2028 index with its 80% range for the top projected Indian athlete-events.

    proj needs athlete, event, projected, low, high (projection.project plus names).
    """
    df = proj.nlargest(top, "projected").iloc[::-1]
    fig, ax = _figure(7, 0.3 * len(df) + 1.2)
    y = np.arange(len(df))
    ax.axvline(100, color=INK_2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.hlines(y, df["low"], df["high"], color=INDIA, linewidth=2.5, alpha=0.35, zorder=2,
              label="80% range")  # fmt: skip
    older = df["beyond_trained_ages"].to_numpy() if "beyond_trained_ages" in df else np.zeros(len(df), bool)
    ax.scatter(df["projected"][~older], y[~older], s=30, color=INDIA, zorder=3, label="Projected 2028")
    if older.any():
        ax.scatter(df["projected"][older], y[older], s=30, facecolors=SURFACE, edgecolors=INDIA,
                   linewidths=1.4, zorder=3, label="Over 30 in 2028 (less reliable)")  # fmt: skip
    ax.set_yticks(y, [f"{a} - {event_label(e)}" for a, e in zip(df["athlete"], df["event"])],
                  fontsize=7.5, color=INK)  # fmt: skip
    ax.set_xlabel("Performance index in 2028 (100 = bronze level)", fontsize=8, color=INK_2)
    ax.legend(loc="upper left", fontsize=7, frameon=False, labelcolor=INK_2)
    return _finish(fig, ax, "Where India's active athletes could be at LA 2028",
                   f"Top {len(df)} projections; gradient boosting, range from its backtest misses",
                   path)  # fmt: skip