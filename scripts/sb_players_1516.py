"""La Liga 2015/16 from StatsBomb Open Data: player statistics per 90, position-fair ratings, first-half team stats.

    python scripts/sb_players_1516.py

Downloads the 380 matches (events + lineups) into data/raw/statsbomb/cache/ (re-used on later runs; not part of the
project archive because it can be downloaded again), then writes
    outputs/archive/sb_laliga1516_player_match.csv.gz   one row per player and match (counts, minutes, position)
    outputs/archive/sb_laliga1516_team_halves.csv.gz    shots, shots on target, xG and goals per team and half
    outputs/archive/players_1516.json                   the app's player comparisons (per 90, percentiles, rating)
    reports/player_rating_fairness.json                 average match rating by position, old vs new formula
Data: StatsBomb Open Data (https://github.com/statsbomb/open-data), attribution "Data: StatsBomb".
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc import players as P  # noqa: E402
from zsc.paths import OUTPUTS, RAW_STATSBOMB, REPORTS  # noqa: E402
from zsc.registry import TEAMS  # noqa: E402
from zsc.teams import canonical  # noqa: E402

SB = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
CACHE = os.path.join(RAW_STATSBOMB, "cache")
OUT = os.path.join(OUTPUTS, "archive")


def get(url: str, cache_name: str):
    path = os.path.join(CACHE, cache_name)
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    err = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                b = r.read()
                b = gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
            with gzip.open(path + ".tmp", "wb") as f:
                f.write(b)
            os.replace(path + ".tmp", path)
            return json.loads(b)
        except Exception as e:  # retry
            err = e
    raise err


def one(m):
    mid = m["match_id"]
    ev = get(f"{SB}/events/{mid}.json", f"events_{mid}.json.gz")
    lu = get(f"{SB}/lineups/{mid}.json", f"lineups_{mid}.json.gz")
    nick = {p["player_name"]: (p.get("player_nickname") or p["player_name"]) for t in lu for p in t["lineup"]}
    home, away = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
    rows, halves = P.match_rows(ev, home, away, nick)
    for r in rows:
        r.update({"match_id": mid, "date": m["match_date"]})
    for r in halves:
        r.update({"match_id": mid, "date": m["match_date"], "home_team": home, "away_team": away})
    return rows, halves


def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    matches = get(f"{SB}/matches/11/27.json", "matches_11_27.json.gz")
    allrows, allhalves = [], []
    with ThreadPoolExecutor(8) as ex:
        for i, (rows, halves) in enumerate(ex.map(one, matches), 1):
            allrows += rows
            allhalves += halves
            if i % 50 == 0:
                print(f"{i} of {len(matches)} matches", flush=True)
    pm = pd.DataFrame(allrows)
    th = pd.DataFrame(allhalves)
    pm.to_csv(os.path.join(OUT, "sb_laliga1516_player_match.csv.gz"), index=False)
    th.to_csv(os.path.join(OUT, "sb_laliga1516_team_halves.csv.gz"), index=False)
    # season table, ratings, app file
    season = P.season_ratings(P.season_table(pm))
    team_ids = {}
    for t in set(pm["team"]):
        try:
            team_ids[t] = TEAMS[canonical(t)][0]
        except KeyError:
            team_ids[t] = t
    js = P.to_json(season, team_ids, "الليغا 2015/16")
    P.write_json(js, os.path.join(OUT, "players_1516.json"))
    # fairness of the match rating: old formula vs position-relative version 2
    pm["rating_v1"] = P.match_rating_v1(pm)
    pm["rating_v2"] = P.match_rating(pm, pm)
    full = pm[pm["minutes"] >= 60]
    fair = full.groupby("group")[["rating_v1", "rating_v2"]].mean().round(2)
    fair["player_matches"] = full.groupby("group").size()
    top = full.sort_values("rating_v1", ascending=False).head(200)["group"].value_counts(normalize=True).round(3)
    top2 = full.sort_values("rating_v2", ascending=False).head(200)["group"].value_counts(normalize=True).round(3)
    share = full["group"].value_counts(normalize=True).round(3)
    rep = {"season": "La Liga 2015/16 (StatsBomb Open Data)", "matches": len(matches), "player_matches_60min": int(len(full)),
           "mean_rating_by_group": fair.reset_index().to_dict("records"),
           "share_of_top200_match_ratings": {"v1": top.to_dict(), "v2": top2.to_dict(), "share_of_all_player_matches": share.to_dict()},
           "note": "v1 = previous formula (attacking outputs added to 6.0); v2 = position-relative z-scores (zsc/players.py)."}
    with open(os.path.join(REPORTS, "player_rating_fairness.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(fair.to_string())
    print("top-200 share v1:", top.to_dict())
    print("top-200 share v2:", top2.to_dict())
    print(f"players in app file: {len(js['players'])}; with >= {P.MIN_MINUTES} minutes: {sum(p['enough_minutes'] for p in js['players'])}")


if __name__ == "__main__":
    main()
