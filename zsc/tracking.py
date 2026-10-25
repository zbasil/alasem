"""Prediction log and running track record.

Every forecast is written down BEFORE kick-off (with the time it was made),
then scored once the result is known. Several sources can be logged for the
same match (this model, SportRadar's published probabilities, the betting
market) so they are compared on exactly the same matches.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .evaluate import log_loss, outcome_index, rps
from .teams import canonical

LOG_COLUMNS = ["logged_at", "kickoff_utc", "home", "away", "source", "p_home", "p_draw", "p_away",
               "xg_home", "xg_away", "version"]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sportradar_fixtures(path_or_dict) -> pd.DataFrame:
    """Saved SportRadar 'scores' answer -> fixtures with canonical names."""
    js = path_or_dict if isinstance(path_or_dict, dict) else json.load(open(path_or_dict, encoding="utf-8"))
    rows = []
    for g in js["games"]:
        wp = g.get("win_probability") or {}
        sc = g.get("score")
        rows.append({
            "sr_id": g["id"], "status": g["status"],
            "kickoff_utc": pd.Timestamp(g["start_time"]).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home": canonical(g["home"]), "away": canonical(g["away"]),
            "hg": sc[0] if isinstance(sc, list) else np.nan, "ag": sc[1] if isinstance(sc, list) else np.nan,
            "sr_p_home": wp.get("home", np.nan) / 100 if wp else np.nan,
            "sr_p_draw": wp.get("draw", np.nan) / 100 if wp else np.nan,
            "sr_p_away": wp.get("away", np.nan) / 100 if wp else np.nan,
        })
    return pd.DataFrame(rows)


def append_log(path: str, rows: pd.DataFrame) -> pd.DataFrame:
    """Append predictions; refuses rows logged after their kick-off."""
    rows = rows.copy()
    for c in LOG_COLUMNS:
        if c not in rows:
            rows[c] = np.nan
    late = pd.to_datetime(rows["logged_at"]) >= pd.to_datetime(rows["kickoff_utc"])
    if late.any():
        raise ValueError("Refusing to log predictions made after kick-off:\n"
                         + rows.loc[late, ["home", "away", "kickoff_utc", "logged_at"]].to_string())
    p = rows[["p_home", "p_draw", "p_away"]].astype(float)
    if not np.allclose(p.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("Probabilities must sum to 1")
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=LOG_COLUMNS)
    out = pd.concat([old, rows[LOG_COLUMNS]], ignore_index=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.to_csv(path, index=False)
    return out


def score_log(log: pd.DataFrame, results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score the last pre-kick-off prediction of each source for each played match.

    Returns (per-match rows, summary per source on the matches every source predicted).
    """
    lg = log.copy()
    lg["logged_at"] = pd.to_datetime(lg["logged_at"])
    lg = lg.sort_values("logged_at").groupby(["home", "away", "source"], as_index=False).last()
    res = results[["home", "away", "hg", "ag"]].dropna()
    m = lg.merge(res, on=["home", "away"], how="inner")
    if m.empty:
        return m, pd.DataFrame(columns=["source", "n", "rps", "logloss", "hit"])
    y = outcome_index(m["hg"].astype(int), m["ag"].astype(int))
    pm = m[["p_home", "p_draw", "p_away"]].astype(float).values
    m["rps"] = rps(pm, y)
    m["logloss"] = log_loss(pm, y)
    m["hit"] = (pm.argmax(1) == y).astype(int)
    # compare on common matches only
    counts = m.groupby(["home", "away"])["source"].nunique()
    n_src = m["source"].nunique()
    common = counts[counts == n_src].index
    mc = m.set_index(["home", "away"]).loc[common].reset_index() if len(common) else m.iloc[0:0]
    summ = (mc.groupby("source").agg(n=("rps", "size"), rps=("rps", "mean"), logloss=("logloss", "mean"),
                                     hit=("hit", "mean")).reset_index())
    return m, summ
