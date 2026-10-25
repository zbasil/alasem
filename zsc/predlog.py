"""Prediction log (version 2): append-only, versioned, keyed by stable match ids.

Two separate files:
    data/predictions/prematch_log.csv   forecasts issued before kick-off (the only ones scored as
                                        pre-match forecasts)
    data/predictions/live_log.csv       forecasts issued during a match (minute, score, cards)

Every row records what was predicted, by which model version, from which data
version, when the data were fetched and when the forecast was issued. Rows
are never edited: a new forecast for the same match and track is a new row
that names the one it supersedes, so the full history can be reviewed.

Scoring uses, for each match and track, the last pre-match row issued before
the match's actual kick-off, joined to the latest results by match id (not by
team names). Postponed matches keep their rows; the kick-off they were really
played at decides which rows count. Corrected results are re-scored
automatically because scoring always reads the current results.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .evaluate import brier, log_loss, outcome_index, rps

PRE_COLS = ["prediction_id", "match_id", "competition", "season", "id_source", "external_id",
            "home_id", "away_id", "kind", "track", "model_version", "config_hash", "data_version",
            "data_fetched_at", "issued_at", "kickoff_utc", "p_home", "p_draw", "p_away",
            "xg_home", "xg_away", "rho", "score1", "p_score1", "score2", "p_score2", "score3", "p_score3",
            "supersedes", "note", "inputs"]
LIVE_COLS = PRE_COLS + ["minute", "period", "hg", "ag", "red_home", "red_away"]
TEXT_COLS = ["prediction_id", "match_id", "competition", "id_source", "external_id", "home_id", "away_id", "kind",
             "track", "model_version", "config_hash", "data_version", "data_fetched_at", "issued_at", "kickoff_utc",
             "score1", "score2", "score3", "supersedes", "note", "inputs"]
TRACKS = {"market": "حاسوب زهراء (مدعوم بالسوق)", "independent": "حاسوب زهراء (مستقل)",
          "sportradar": "SportRadar"}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def prediction_id(match_id: str, track: str, issued_at: str, kind: str = "prematch") -> str:
    h = hashlib.sha1(f"{match_id}|{track}|{kind}|{issued_at}".encode()).hexdigest()[:10]
    return f"{match_id}:{track}:{h}"


def read(path: str, cols=PRE_COLS) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path, dtype={c: object for c in TEXT_COLS})
        for c in cols:
            if c not in df:
                df[c] = np.nan
        return df[cols]
    return pd.DataFrame(columns=cols)


def append(path: str, rows: pd.DataFrame, kind: str = "prematch") -> pd.DataFrame:
    """Validate and append rows. Returns the rows actually written.

    Refuses: probabilities that do not sum to 1, missing match ids, pre-match rows issued at or
    after kick-off. Skips (idempotent): a row identical in probabilities, model version and data
    version to the latest row of the same match and track."""
    cols = PRE_COLS if kind == "prematch" else LIVE_COLS
    rows = rows.copy().reset_index(drop=True)
    for c in cols:
        if c not in rows:
            rows[c] = np.nan
    for c in TEXT_COLS:
        rows[c] = rows[c].astype(object)
    if rows["match_id"].isna().any():
        raise ValueError("every prediction needs a match_id")
    p = rows[["p_home", "p_draw", "p_away"]].astype(float).to_numpy()
    if not np.allclose(p.sum(1), 1.0, atol=1e-6) or (p < 0).any():
        raise ValueError("probabilities must be non-negative and sum to 1")
    rows["kind"] = kind
    if kind == "prematch":
        late = [_ts(i) >= _ts(k) for i, k in zip(rows["issued_at"], rows["kickoff_utc"])]
        if any(late):
            bad = rows.loc[late, ["match_id", "issued_at", "kickoff_utc"]]
            raise ValueError("refusing pre-match predictions issued at or after kick-off:\n" + bad.to_string())
    old = read(path, cols)
    keep = []
    for i, r in rows.iterrows():
        prev = old[(old["match_id"] == r["match_id"]) & (old["track"] == r["track"])]
        if kind == "live":
            prev = prev[prev["minute"] == r["minute"]]
        if len(prev):
            last = prev.sort_values("issued_at").iloc[-1]
            same_p = np.allclose(last[["p_home", "p_draw", "p_away"]].astype(float), [r["p_home"], r["p_draw"], r["p_away"]],
                                 atol=1e-9)
            if r["track"] == "sportradar":
                # an outside source: a reading is new only when its probabilities changed
                same = same_p
            else:
                same = same_p and last["model_version"] == r["model_version"] and last["data_version"] == r["data_version"]
            if same:
                continue
            rows.at[i, "supersedes"] = last["prediction_id"]
        if pd.isna(r["prediction_id"]):
            rows.at[i, "prediction_id"] = prediction_id(r["match_id"], r["track"], r["issued_at"], kind)
        keep.append(i)
    new = rows.loc[keep, cols]
    if len(new):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        out = pd.concat([old, new], ignore_index=True) if len(old) else new
        tmp = path + ".tmp"
        out.to_csv(tmp, index=False)
        os.replace(tmp, path)                    # atomic: a failed write never leaves half a file
    return new


def latest_prematch(log: pd.DataFrame, kickoffs: dict[str, str] | None = None) -> pd.DataFrame:
    """Last pre-match row per (match, track) issued before the actual kick-off."""
    if not len(log):
        return log
    lg = log.copy()
    if kickoffs:
        ko = lg["match_id"].map(kickoffs).fillna(lg["kickoff_utc"])
    else:
        ko = lg["kickoff_utc"]
    ok = [(_ts(i) < _ts(k)) for i, k in zip(lg["issued_at"], ko)]
    lg = lg[ok]
    return lg.sort_values("issued_at").groupby(["match_id", "track"], as_index=False).last()


def score(log: pd.DataFrame, results: pd.DataFrame, kickoffs: dict[str, str] | None = None):
    """results: match_id, hg, ag (latest, corrections included).
    Returns (per-match rows, summary per track on the matches every track predicted)."""
    lg = latest_prematch(log, kickoffs)
    m = lg.merge(results[["match_id", "hg", "ag"]], on="match_id", how="inner")
    if m.empty:
        return m, pd.DataFrame(columns=["track", "n", "rps", "logloss", "brier", "hit"])
    y = outcome_index(m["hg"].astype(int), m["ag"].astype(int))
    pm = m[["p_home", "p_draw", "p_away"]].astype(float).to_numpy()
    m["rps"], m["logloss"], m["brier"] = rps(pm, y), log_loss(pm, y), brier(pm, y)
    m["hit"] = (pm.argmax(1) == y).astype(int)
    m["exact_hit"] = (m["score1"] == m["hg"].astype(int).astype(str) + "-" + m["ag"].astype(int).astype(str)).astype(int)
    n_tracks = m["track"].nunique()
    common = m.groupby("match_id")["track"].nunique()
    common = common[common == n_tracks].index
    mc = m[m["match_id"].isin(common)]
    summ = mc.groupby("track").agg(n=("rps", "size"), rps=("rps", "mean"), logloss=("logloss", "mean"),
                                   brier=("brier", "mean"), hit=("hit", "mean")).reset_index()
    return m, summ
