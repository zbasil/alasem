"""Fresh data straight from the internet (used by the weekly Colab notebook).

Main source: football-data.co.uk (results, shots on target, Bet365 odds),
updated by the site twice a week. Fallback when that site is unreachable:
the datasets/football-datasets GitHub mirror for past seasons and
openfootball for the current season (results only, no odds).
"""

from __future__ import annotations

import io
import json
import urllib.request

import numpy as np
import pandas as pd

from .data import COLUMNS, fetch_football_data, season_code, standardise_football_data
from .market import add_market_goals, implied_1x2, implied_goals, implied_over
from .teams import canonical

MIRROR = "https://raw.githubusercontent.com/datasets/football-datasets/main/datasets/la-liga/season-{code}.csv"
OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/football.json/master/{y}-{y2}/es.1.json"
FIXTURES = "https://www.football-data.co.uk/fixtures.csv"


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (zsc model)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _openfootball_season(start_year: int) -> pd.DataFrame:
    js = json.loads(_get(OPENFOOTBALL.format(y=start_year, y2=f"{(start_year + 1) % 100:02d}")))
    rows = []
    for mt in js["matches"]:
        s = mt.get("score")
        ft = s.get("ft") if isinstance(s, dict) else (s if isinstance(s, list) else None)
        if not ft:
            continue
        rows.append({"date": pd.Timestamp(mt["date"]), "season": start_year,
                     "home": canonical(mt["team1"]), "away": canonical(mt["team2"]),
                     "hg": int(ft[0]), "ag": int(ft[1])})
    df = pd.DataFrame(rows)
    for c in COLUMNS:
        if c not in df:
            df[c] = np.nan
    return df[COLUMNS]


def merge_current(primary: pd.DataFrame, extra: pd.DataFrame, log=print) -> pd.DataFrame:
    """Add matches that only `extra` has (each home/away pair is played once a season).

    Rows present in both keep `primary` (it carries odds and shots). If the two
    sources disagree on any score, the second source is not used at all and a
    warning lists the disagreements.
    """
    if extra is None or extra.empty:
        return primary
    have = {(h, a): (x, y) for h, a, x, y in zip(primary["home"], primary["away"], primary["hg"], primary["ag"])}
    bad = [(h, a, have[(h, a)], (x, y)) for h, a, x, y in zip(extra["home"], extra["away"], extra["hg"], extra["ag"])
           if (h, a) in have and have[(h, a)] != (x, y)]
    if bad:
        log(f"  ⚠️ the second source disagrees on {len(bad)} score(s), so it was ignored: {bad}")
        return primary
    new = extra[[(h, a) not in have for h, a in zip(extra["home"], extra["away"])]]
    if len(new):
        log(f"  + {len(new)} newer results from the second source")
    return pd.concat([primary, new[primary.columns]], ignore_index=True)


def parse_extra_results(text: str, season: int) -> pd.DataFrame:
    """Lines 'YYYY-MM-DD, Home, Away, home goals, away goals' typed by hand."""
    rows = []
    for line in (text or "").strip().splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        d, h, a, x, y = [p.strip() for p in line.split(",")]
        rows.append({"date": pd.Timestamp(d), "season": season, "home": canonical(h), "away": canonical(a),
                     "hg": int(x), "ag": int(y)})
    df = pd.DataFrame(rows, columns=["date", "season", "home", "away", "hg", "ag"])
    for c in COLUMNS:
        if c not in df:
            df[c] = np.nan
    return df[COLUMNS]


def load_online(season: int, seasons_back: int = 4, extra_results: str = "", log=print) -> pd.DataFrame:
    frames = []
    for s in range(season - seasons_back, season + 1):
        try:
            df = fetch_football_data(s)
            log(f"  {s}/{(s + 1) % 100:02d}: {len(df)} matches from football-data.co.uk")
        except Exception as e:                        # noqa: BLE001
            log(f"  {s}/{(s + 1) % 100:02d}: football-data.co.uk failed ({e}); trying fallback")
            if s < season:
                raw = pd.read_csv(io.BytesIO(_get(MIRROR.format(code=season_code(s)))))
                df = standardise_football_data(raw, s)
            else:
                df = _openfootball_season(s)
            log(f"  {s}/{(s + 1) % 100:02d}: {len(df)} matches from fallback (no odds)")
        if s == season:
            # football-data.co.uk sometimes lags a few days: add anything newer from openfootball
            try:
                df = merge_current(df, _openfootball_season(s), log)
            except Exception as e:                    # noqa: BLE001
                log(f"  openfootball not reachable ({e})")
            manual = parse_extra_results(extra_results, s)
            if len(manual):
                df = merge_current(df, manual, log)
        frames.append(df)
    allm = pd.concat(frames, ignore_index=True).sort_values(["date", "home"]).reset_index(drop=True)
    return add_market_goals(allm)


def upcoming_fixtures(days: int = 8, today=None) -> pd.DataFrame:
    """Next fixtures from football-data.co.uk (with odds), else openfootball (no odds)."""
    try:
        up = upcoming_with_odds()
        if len(up):
            return up
    except Exception:                                 # noqa: BLE001
        pass
    today = pd.Timestamp.today().normalize() if today is None else pd.Timestamp(today)
    y = today.year if today.month >= 7 else today.year - 1
    js = json.loads(_get(OPENFOOTBALL.format(y=y, y2=f"{(y + 1) % 100:02d}")))
    rows = []
    for mt in js["matches"]:
        s = mt.get("score")
        ft = s.get("ft") if isinstance(s, dict) else (s if isinstance(s, list) else None)
        d = pd.Timestamp(mt["date"])
        if ft or not (today <= d <= today + pd.Timedelta(days=days)):
            continue
        rows.append({"date": d.strftime("%Y-%m-%d"), "time_uk": "", "home": canonical(mt["team1"]),
                     "away": canonical(mt["team2"]), "mkt_lh": np.nan, "mkt_la": np.nan})
    return pd.DataFrame(rows, columns=["date", "time_uk", "home", "away", "mkt_lh", "mkt_la"])


def upcoming_with_odds(days: int = 8) -> pd.DataFrame:
    """Next La Liga fixtures with Bet365 odds from football-data.co.uk/fixtures.csv."""
    raw = pd.read_csv(io.BytesIO(_get(FIXTURES)), encoding="utf-8-sig")
    raw = raw[raw["Div"] == "SP1"].copy()
    if raw.empty:
        return pd.DataFrame(columns=["date", "time_uk", "home", "away"])
    out = pd.DataFrame({
        "date": pd.to_datetime(raw["Date"], dayfirst=True).dt.strftime("%Y-%m-%d"),
        "time_uk": raw.get("Time", ""),
        "home": raw["HomeTeam"].map(canonical),
        "away": raw["AwayTeam"].map(canonical),
    })
    for a, b in [("odds_h", "B365H"), ("odds_d", "B365D"), ("odds_a", "B365A"),
                 ("odds_o25", "B365>2.5"), ("odds_u25", "B365<2.5")]:
        out[a] = pd.to_numeric(raw[b], errors="coerce") if b in raw else np.nan
    ok = out[["odds_h", "odds_d", "odds_a"]].notna().all(axis=1).values
    out["mkt_p_home"] = np.nan
    out["mkt_p_draw"] = np.nan
    out["mkt_p_away"] = np.nan
    out["mkt_lh"] = np.nan
    out["mkt_la"] = np.nan
    if ok.any():
        p = implied_1x2(out.loc[ok, "odds_h"], out.loc[ok, "odds_d"], out.loc[ok, "odds_a"])
        po = implied_over(out.loc[ok, "odds_o25"], out.loc[ok, "odds_u25"])
        lam, mu, _ = implied_goals(p[:, 0], p[:, 2], po)
        out.loc[ok, ["mkt_p_home", "mkt_p_draw", "mkt_p_away"]] = p
        out.loc[ok, "mkt_lh"] = lam
        out.loc[ok, "mkt_la"] = mu
    return out.reset_index(drop=True)
