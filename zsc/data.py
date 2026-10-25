"""Loading and validating match data.

Unified match table columns (one row per played match):
    date      pandas Timestamp (match day)
    season    int, first year of the season (2026 = 2026/27)
    home, away  canonical team names (see teams.py)
    hg, ag    full-time goals
    hst, ast  shots on target (NaN if unknown)
    odds_h, odds_d, odds_a   1X2 decimal odds (NaN if unknown)
    odds_o25, odds_u25       over/under 2.5 goals odds (NaN if unknown)
    hthg, htag               half-time goals (NaN if unknown)
"""

from __future__ import annotations

import glob
import io
import os
import re
from itertools import permutations

import numpy as np
import pandas as pd

from .teams import canonical

COLUMNS = ["date", "season", "home", "away", "hg", "ag", "hst", "ast",
           "odds_h", "odds_d", "odds_a", "odds_o25", "odds_u25", "hthg", "htag"]

FOOTBALL_DATA_URL = "https://www.football-data.co.uk/mmz4281/{code}/SP1.csv"


def season_code(start_year: int) -> str:
    """2026 -> '2627' (football-data.co.uk folder name)."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def code_to_start_year(code: str) -> int:
    first = int(code[:2])
    return 1900 + first if first >= 90 else 2000 + first


def _parse_dates(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    if s.str.match(r"^\d{4}-\d{2}-\d{2}").all():
        return pd.to_datetime(s.str[:10], format="%Y-%m-%d")
    # football-data.co.uk uses dd/mm/yy and dd/mm/yyyy
    out = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    short = out.isna()
    if short.any():
        out[short] = pd.to_datetime(s[short], format="%d/%m/%y", errors="coerce")
    if out.isna().any():
        bad = s[out.isna()].unique()[:5]
        raise ValueError(f"Unparseable dates: {bad}")
    return out


def _first_present(df: pd.DataFrame, names: list[str]) -> pd.Series:
    for n in names:
        if n in df.columns:
            return pd.to_numeric(df[n], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def standardise_football_data(raw: pd.DataFrame, season: int) -> pd.DataFrame:
    """Convert a football-data.co.uk style table to the unified format."""
    raw = raw.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"]).copy()
    out = pd.DataFrame({
        "date": _parse_dates(raw["Date"]),
        "season": season,
        "home": raw["HomeTeam"].map(canonical),
        "away": raw["AwayTeam"].map(canonical),
        "hg": pd.to_numeric(raw["FTHG"]).astype(int),
        "ag": pd.to_numeric(raw["FTAG"]).astype(int),
        "hst": _first_present(raw, ["HST"]),
        "ast": _first_present(raw, ["AST"]),
        # Bet365 first (the backtests were tuned on Bet365), market average next
        "odds_h": _first_present(raw, ["B365H", "AvgH", "BbAvH"]),
        "odds_d": _first_present(raw, ["B365D", "AvgD", "BbAvD"]),
        "odds_a": _first_present(raw, ["B365A", "AvgA", "BbAvA"]),
        "odds_o25": _first_present(raw, ["B365>2.5", "Avg>2.5", "BbAv>2.5"]),
        "odds_u25": _first_present(raw, ["B365<2.5", "Avg<2.5", "BbAv<2.5"]),
        "hthg": _first_present(raw, ["HTHG"]),
        "htag": _first_present(raw, ["HTAG"]),
    })
    return out[COLUMNS].reset_index(drop=True)


def load_history(history_dir: str, first_season: int = 1993) -> pd.DataFrame:
    """Read season-XXYY.csv files (football-data.co.uk columns)."""
    frames = []
    for path in sorted(glob.glob(os.path.join(history_dir, "season-*.csv"))):
        code = re.search(r"season-(\d{4})\.csv$", path).group(1)
        start = code_to_start_year(code)
        if start < first_season:
            continue
        frames.append(standardise_football_data(pd.read_csv(path), start))
    if not frames:
        raise FileNotFoundError(f"No season files in {history_dir}")
    df = pd.concat(frames, ignore_index=True)
    return df.sort_values(["date", "home"]).reset_index(drop=True)


def attach_odds(matches: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
    """Fill missing odds / shots columns from a second table.

    The second table must use the unified column names. Matches are joined on
    (date, home, away); goals must agree, otherwise a ValueError is raised.
    """
    key = ["date", "home", "away"]
    o = odds.copy()
    o["home"] = o["home"].map(canonical)
    o["away"] = o["away"].map(canonical)
    merged = matches.merge(o, on=key, how="left", suffixes=("", "_o"))
    both = merged["hg_o"].notna()
    bad = both & ((merged["hg"] != merged["hg_o"]) | (merged["ag"] != merged["ag_o"]))
    if bad.any():
        raise ValueError("Score mismatch between sources:\n"
                         + merged.loc[bad, key + ["hg", "ag", "hg_o", "ag_o"]].to_string())
    for c in ["hst", "ast", "odds_h", "odds_d", "odds_a", "odds_o25", "odds_u25", "hthg", "htag"]:
        if c + "_o" in merged:
            merged[c] = merged[c].fillna(merged[c + "_o"])
    return merged[COLUMNS]


def load_unified_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = _parse_dates(df["date"])
    df["home"] = df["home"].map(canonical)
    df["away"] = df["away"].map(canonical)
    for c in COLUMNS:
        if c not in df:
            df[c] = np.nan
    df["hg"] = df["hg"].astype(int)
    df["ag"] = df["ag"].astype(int)
    df["season"] = df["season"].astype(int)
    return df[COLUMNS].sort_values(["date", "home"]).reset_index(drop=True)


def fetch_football_data(start_year: int, url_template: str = FOOTBALL_DATA_URL) -> pd.DataFrame:
    """Download one season from football-data.co.uk (needs internet)."""
    import urllib.request
    url = url_template.format(code=season_code(start_year))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (zsc model)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8-sig", errors="replace")
    return standardise_football_data(pd.read_csv(io.StringIO(text)), start_year)


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_season(df: pd.DataFrame, n_teams: int | None = None, complete: bool = False) -> list[str]:
    """Return a list of problems (empty list = clean).

    Checks: no duplicate fixtures, no team playing itself, goals are
    non-negative integers, each ordered pair at most once, and (if complete)
    a full double round robin.
    """
    problems = []
    teams = sorted(set(df["home"]) | set(df["away"]))
    if n_teams is not None and len(teams) != n_teams:
        problems.append(f"expected {n_teams} teams, found {len(teams)}: {teams}")
    if (df["home"] == df["away"]).any():
        problems.append("a team plays itself")
    dup = df.duplicated(["home", "away"], keep=False)
    if dup.any():
        problems.append("duplicate fixtures: " + df.loc[dup, ["date", "home", "away"]].to_string())
    if (df["hg"] < 0).any() or (df["ag"] < 0).any():
        problems.append("negative goals")
    if complete:
        n = len(teams)
        if len(df) != n * (n - 1):
            problems.append(f"expected {n * (n - 1)} matches, found {len(df)}")
    return problems


def remaining_fixtures(played: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    """All (home, away) pairs of a double round robin that are not yet played."""
    done = set(zip(played["home"], played["away"]))
    rows = [(h, a) for h, a in permutations(sorted(teams), 2) if (h, a) not in done]
    return pd.DataFrame(rows, columns=["home", "away"])
