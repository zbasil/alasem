"""Download StatsBomb Open Data 2015/16 (La Liga, Premier League, Serie A, Ligue 1) events
and keep only goals, red cards and period lengths -> data/statsbomb/sb1516_goals_reds.jsonl.gz

    python scripts/sb_extract.py

Data: StatsBomb Open Data (https://github.com/statsbomb/open-data), attribution "Data: StatsBomb".
"""
import gzip
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from zsc.paths import SB_EXTRACT  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SB = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPS = [("11", "27"), ("2", "27"), ("12", "27"), ("7", "27")]   # (competition, season 2015/16)
OUT = SB_EXTRACT


def get(url):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    err = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                b = r.read()
                return gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
        except Exception as e:  # retry
            err = e
    raise err


def one(m):
    ev = json.loads(get(f"{SB}/events/{m['match_id']}.json"))
    home, away = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
    goals, reds, plen = [], [], {}
    for e in ev:
        p, t, team = e.get("period"), e.get("type", {}).get("name"), e.get("team", {}).get("name")
        if p in (1, 2):
            plen[p] = max(plen.get(p, 0), e["minute"] + e["second"] / 60)
        if t == "Shot" and e.get("shot", {}).get("outcome", {}).get("name") == "Goal" and p in (1, 2, 3, 4):
            goals.append({"team": team, "period": p, "minute": e["minute"], "second": e["second"], "og": False})
        if t == "Own Goal For" and p in (1, 2, 3, 4):
            goals.append({"team": team, "period": p, "minute": e["minute"], "second": e["second"], "og": True})
        card = ((e.get("foul_committed") or {}).get("card") or {}).get("name") or \
            ((e.get("bad_behaviour") or {}).get("card") or {}).get("name")
        if card in ("Red Card", "Second Yellow") and p in (1, 2):
            reds.append({"team": team, "period": p, "minute": e["minute"], "second": e["second"], "card": card})
    return {"match_id": m["match_id"], "competition": m["competition"]["competition_name"], "date": m["match_date"],
            "home": home, "away": away, "home_score": m["home_score"], "away_score": m["away_score"],
            "ev_home_goals": sum(g["team"] == home for g in goals), "ev_away_goals": sum(g["team"] == away for g in goals),
            "goals": goals, "reds": reds, "period_len": plen}


def main():
    matches = []
    for c, s in COMPS:
        matches += json.loads(get(f"{SB}/matches/{c}/{s}.json"))
    with gzip.open(OUT, "wt", encoding="utf-8") as out, ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(one, matches), 1):
            out.write(json.dumps(r) + "\n")
            if i % 100 == 0:
                print(i, "of", len(matches), flush=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
