"""Season schedule: fixtures, results and predictions in Baghdad time."""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from .teams import arabic, canonical

OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/football.json/master/{y}-{y2}/es.1.json"


def load_openfootball(path_or_url: str) -> pd.DataFrame:
    if path_or_url.startswith("http"):
        import urllib.request
        with urllib.request.urlopen(path_or_url, timeout=60) as r:
            js = json.loads(r.read())
    else:
        js = json.load(open(path_or_url, encoding="utf-8"))
    rows = []
    for mt in js["matches"]:
        md = int(str(mt.get("round", "0")).split()[-1])
        rows.append({"matchday": md, "date": mt["date"], "time_local": mt.get("time") or "",
                     "home": canonical(mt["team1"]), "away": canonical(mt["team2"])})
    return pd.DataFrame(rows)


def to_baghdad(date: str, time_local: str, tz: str = "Europe/Madrid") -> tuple[str, str]:
    if not time_local:
        return date, ""
    t = pd.Timestamp(f"{date} {time_local}").tz_localize(tz).tz_convert("Asia/Baghdad")
    return t.strftime("%Y-%m-%d"), t.strftime("%H:%M")


def build_fixtures(schedule: pd.DataFrame, results: pd.DataFrame, predictions: pd.DataFrame,
                   sportradar: pd.DataFrame | None = None, today: str | None = None) -> pd.DataFrame:
    """One row per fixture of the season.

    results:     played matches (home, away, hg, ag)
    predictions: model probabilities for unplayed fixtures (home, away, p_home, p_draw, p_away, xg_home, xg_away)
    sportradar:  optional near-term schedule (home, away, kickoff_utc, sr_p_home, sr_p_draw, sr_p_away)
    """
    today = pd.Timestamp(today or pd.Timestamp.now("UTC").strftime("%Y-%m-%d"))
    fx = schedule.copy()
    res = results[["home", "away", "hg", "ag"]].copy()
    fx = fx.merge(res, on=["home", "away"], how="left")
    fx = fx.merge(predictions[["home", "away", "p_home", "p_draw", "p_away", "xg_home", "xg_away"]],
                  on=["home", "away"], how="left")
    if sportradar is not None and len(sportradar):
        sr = sportradar[["home", "away", "kickoff_utc", "sr_p_home", "sr_p_draw", "sr_p_away"]]
        fx = fx.merge(sr, on=["home", "away"], how="left")
    else:
        fx["kickoff_utc"] = np.nan
        for c in ("sr_p_home", "sr_p_draw", "sr_p_away"):
            fx[c] = np.nan
    dates, times = [], []
    for r in fx.itertuples():
        if isinstance(r.kickoff_utc, str) and r.kickoff_utc:
            t = pd.Timestamp(r.kickoff_utc).tz_convert("Asia/Baghdad")
            dates.append(t.strftime("%Y-%m-%d"))
            times.append(t.strftime("%H:%M"))
        else:
            d, tm = to_baghdad(r.date, r.time_local)
            dates.append(d)
            times.append(tm)
    fx["date_baghdad"], fx["time_baghdad"] = dates, times
    played = fx["hg"].notna()
    past = pd.to_datetime(fx["date"]) < today - pd.Timedelta(days=1)
    fx["status"] = np.where(played, "played", np.where(past, "pending", "scheduled"))
    fx["status_ar"] = fx["status"].map({"played": "انتهت", "scheduled": "قادمة",
                                        "pending": "لم تُستكمل / مؤجلة"})
    fx["home_ar"] = fx["home"].map(arabic)
    fx["away_ar"] = fx["away"].map(arabic)
    for c in ("p_home", "p_draw", "p_away", "sr_p_home", "sr_p_draw", "sr_p_away"):
        fx[c] = (100 * fx[c]).round(1)
    fx[["xg_home", "xg_away"]] = fx[["xg_home", "xg_away"]].round(2)
    fx["score"] = np.where(played, fx["hg"].fillna(0).astype(int).astype(str) + "-" + fx["ag"].fillna(0).astype(int).astype(str), "")
    fx["row_id"] = fx["home"] + "|" + fx["away"]
    cols = ["row_id", "matchday", "date_baghdad", "time_baghdad", "home", "away", "home_ar", "away_ar", "status",
            "status_ar", "score", "hg", "ag", "p_home", "p_draw", "p_away", "xg_home", "xg_away",
            "sr_p_home", "sr_p_draw", "sr_p_away"]
    return fx[cols].sort_values(["matchday", "date_baghdad", "time_baghdad"]).reset_index(drop=True)
