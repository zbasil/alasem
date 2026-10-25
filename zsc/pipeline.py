"""Glue: assemble the full match table used for fitting and forecasting."""

from __future__ import annotations

import os

import pandas as pd


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_snapshot(root: str = ROOT, first_season: int = 2000) -> pd.DataFrame:
    """The model's training table: every played match from data/standard (built from data/raw by
    zsc.store.build) plus market-implied expected goals. The table of each data version is kept in
    data/model_inputs so a forecast can be reproduced later; its version is in .attrs["data_version"]."""
    from .store import model_table
    return model_table(first_season)


def season_teams(matches: pd.DataFrame, season: int) -> list[str]:
    s = matches[matches["season"] == season]
    return sorted(set(s["home"]) | set(s["away"]))


def promoted_teams(matches: pd.DataFrame, season: int) -> set[str]:
    now = set(season_teams(matches, season))
    before = set(season_teams(matches, season - 1))
    return now - before if before else set()
