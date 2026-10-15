"""Phase 5 API: serves India's gap to the podium and the 2028 projections.

Run locally:  uvicorn src.api:app --reload   then open http://127.0.0.1:8000/docs
It reads the files written by src.export (serving/ by default, or the SERVING_DIR variable).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from src.export import SERVING_DIR

app = FastAPI(
    title="Gap to the Podium API",
    description="How far India's best athletes are from an Olympic medal, and where they could "
                "be at LA 2028. Performance index: 100 = Olympic bronze level.",
    version="1.0.0",
)  # fmt: skip


class EventGap(BaseModel):
    event_key: str
    india_best_athlete: str | None
    india_best_mark: str | None
    gap_pct: float | None
    india_world_rank: int | None
    tactical_event: bool


class Projection(BaseModel):
    athlete: str
    event: str
    last_season: int
    last_index: float
    target_age: int
    projected_2028: float
    low_80: float
    high_80: float
    range_reaches_bronze: bool
    beyond_trained_ages: bool


def _clean(value):
    """NaN and missing values become None, so they show as null in JSON."""
    return None if pd.isna(value) else value


@lru_cache(maxsize=1)
def load(directory: str) -> dict:
    """Read the serving files once per directory; later requests reuse them."""
    folder = Path(directory)
    gaps = pd.read_csv(folder / "gaps.csv")
    projections = pd.read_csv(folder / "projections.csv")
    findings = json.loads((folder / "findings.json").read_text())
    return {"gaps": gaps, "projections": projections, "findings": findings}


def data() -> dict:
    return load(os.getenv("SERVING_DIR", str(SERVING_DIR)))


def _gap(row) -> EventGap:
    rank = _clean(row["india_world_rank"])
    return EventGap(event_key=row["event_key"], india_best_athlete=_clean(row["india_best_athlete"]),
                    india_best_mark=_clean(row["india_best_mark_raw"]), gap_pct=_clean(row["gap_pct"]),
                    india_world_rank=None if rank is None else int(rank),
                    tactical_event=bool(row["tactical_event"]))  # fmt: skip


def _projection(row) -> Projection:
    return Projection(athlete=row["athlete"], event=row["event"],
                      last_season=int(row["last_season"]), last_index=row["last_index"],
                      target_age=int(row["target_age"]), projected_2028=row["projected"],
                      low_80=row["low"], high_80=row["high"],
                      range_reaches_bronze=bool(row["range_reaches_bronze"]),
                      beyond_trained_ages=bool(row["beyond_trained_ages"]))  # fmt: skip


@app.get("/health")
def health() -> dict:
    """Liveness check, plus when the served results were generated."""
    return {"status": "ok", "generated_at": data()["findings"].get("generated_at")}


@app.get("/findings")
def findings() -> dict:
    """The headline numbers: the gap at 18, the backtest winner and its accuracy."""
    return data()["findings"]


@app.get("/events", response_model=list[EventGap])
def events(tactical: bool | None = None) -> list[EventGap]:
    """India's best current mark and gap to the bronze threshold in every Olympic event.

    For tactical events (middle distance, long distance, road) read the world rank, not the gap.
    """
    gaps = data()["gaps"]
    if tactical is not None:
        gaps = gaps[gaps["tactical_event"] == tactical]
    return [_gap(row) for _, row in gaps.iterrows()]


@app.get("/events/{event_key}", response_model=EventGap)
def event(event_key: str) -> EventGap:
    """One event, e.g. jt_m for the men's javelin."""
    match = data()["gaps"][data()["gaps"]["event_key"] == event_key]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"unknown event '{event_key}'")
    return _gap(match.iloc[0])


@app.get("/projections", response_model=list[Projection])
def projections(event: str | None = None, athlete: str | None = None,
                reaches_bronze: bool | None = None,
                limit: int = Query(50, ge=1, le=500)) -> list[Projection]:  # fmt: skip
    """2028 projections with 80% ranges, best first. Filters: event, athlete (part of the name,
    any case), reaches_bronze (only those whose range reaches bronze level)."""
    p = data()["projections"]
    if event is not None:
        p = p[p["event"] == event]
    if athlete is not None:
        p = p[p["athlete"].str.contains(athlete, case=False, regex=False)]
    if reaches_bronze is not None:
        p = p[p["range_reaches_bronze"] == reaches_bronze]
    p = p.sort_values("projected", ascending=False).head(limit)
    return [_projection(row) for _, row in p.iterrows()]