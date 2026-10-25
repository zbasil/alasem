"""Build the data snapshot used by the model (run once; needs internet).

Sources
  * history  : football-data.co.uk results via the datasets/football-datasets
               GitHub mirror (seasons 1993/94 - 2025/26)  -> data/history/
  * odds     : football-data.co.uk Bet365 odds + shots on target via the
               xgabora/Club-Football-Match-Data GitHub dataset -> data/odds/
  * 2026/27  : openfootball (matchdays 1-7), footballwebpages.co.uk and
               laliga.com (9 Oct - 21 Oct 2026), cross-checked against the
               official table of 21 Oct 2026            -> data/current/
"""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import CURRENT_SEASON_TABLE, RAW_FD_EXTRACT, RAW_MANUAL, RAW_ODDS, RAW_OFFICIAL_TABLE  # noqa: E402

from zsc.data import COLUMNS, attach_odds, standardise_football_data, validate_season  # noqa: E402
from zsc.standings import compute_table  # noqa: E402
from zsc.teams import canonical  # noqa: E402

RAW = "https://raw.githubusercontent.com"
OPENFOOTBALL = RAW + "/openfootball/football.json/master/2026-27/es.1.json"
XGABORA = RAW + "/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def build_odds() -> pd.DataFrame:
    path = RAW_ODDS
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["date"])
    m = pd.read_csv(io.BytesIO(get(XGABORA)), low_memory=False)
    sp = m[m["Division"] == "SP1"]
    out = pd.DataFrame({
        "date": pd.to_datetime(sp["MatchDate"]),
        "home": sp["HomeTeam"].map(canonical),
        "away": sp["AwayTeam"].map(canonical),
        "hg": sp["FTHome"].astype(int),
        "ag": sp["FTAway"].astype(int),
        "hst": sp["HomeTarget"],
        "ast": sp["AwayTarget"],
        "odds_h": sp["OddHome"], "odds_d": sp["OddDraw"], "odds_a": sp["OddAway"],
        "odds_o25": sp["Over25"], "odds_u25": sp["Under25"],
    })
    out.to_csv(path, index=False)
    return out


def build_current(odds: pd.DataFrame) -> pd.DataFrame:
    # 1) openfootball: everything played up to 20 Sep 2026
    js = json.loads(get(OPENFOOTBALL))
    rows = []
    for mt in js["matches"]:
        s = mt.get("score")
        ft = s.get("ft") if isinstance(s, dict) else (s if isinstance(s, list) else None)
        if not ft:
            continue
        rows.append({"date": mt["date"], "home": canonical(mt["team1"]), "away": canonical(mt["team2"]),
                     "hg": int(ft[0]), "ag": int(ft[1]), "source": "openfootball"})
    of = pd.DataFrame(rows)
    of = of[of["date"] <= "2026-09-20"]

    # 2) results after the openfootball snapshot, each checked on two pages
    manual = pd.read_csv(RAW_MANUAL)
    manual["home"] = manual["home"].map(canonical)
    manual["away"] = manual["away"].map(canonical)

    cur = pd.concat([of, manual[["date", "home", "away", "hg", "ag", "source"]]], ignore_index=True)
    cur["date"] = pd.to_datetime(cur["date"])
    cur["season"] = 2026
    for c in COLUMNS:
        if c not in cur:
            cur[c] = float("nan")
    src = cur["source"]
    cur = attach_odds(cur[COLUMNS], odds)       # raises if any score disagrees

    # 3) Bet365 odds + shots on target for 4 Sep - 11 Oct 2026, read from
    #    football-data.co.uk/mmz4281/2627/SP1.csv (two independent extractions
    #    agreed on every value except three over/under pairs, which a third
    #    targeted read settled; scores re-checked here by attach_odds)
    fd = standardise_football_data(
        pd.read_csv(RAW_FD_EXTRACT), 2026)
    cur = attach_odds(cur, fd)
    cur["source"] = src.values
    return cur.sort_values(["date", "home"]).reset_index(drop=True)


def main() -> None:
    odds = build_odds()
    cur = build_current(odds)

    problems = validate_season(cur, n_teams=20)
    assert not problems, problems

    # The results up to the table's date must reproduce the official table exactly.
    official = pd.read_csv(RAW_OFFICIAL_TABLE)
    official["team"] = official["team"].map(canonical)
    mine = compute_table(cur[cur["date"] <= "2026-10-21"]).set_index("team")
    for _, r in official.iterrows():
        got = mine.loc[r["team"], ["P", "W", "D", "L", "GF", "GA", "Pts"]].tolist()
        exp = [r["P"], r["W"], r["D"], r["L"], r["GF"], r["GA"], r["Pts"]]
        assert got == exp, (r["team"], got, exp)

    cur.to_csv(CURRENT_SEASON_TABLE, index=False)
    n_odds = cur["odds_h"].notna().sum()
    print(f"2026/27: {len(cur)} matches written; {n_odds} with odds; table check passed for 20/20 teams")


if __name__ == "__main__":
    main()
