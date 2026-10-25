"""Results history for head-to-head records and the claim lab (version 3.1).

    python -m zsc.history        writes outputs/history/{ESP1,ENG1}.json and copies them to app/data/history/

League matches only, from the files already used to train the models:
    La Liga          data/standard/matches.csv (1993/94 onwards) + this season from the app snapshot
    Premier League   data/raw/epl-mirror (football-data.co.uk via GitHub, 2000/01-2025/26) + this season
Cups, Super Cups and European matches are NOT included; every answer built on these files says so.
Compact columns keep each file small (the app loads it only on the pages that need it).
"""

from __future__ import annotations

import csv
import glob
import json
import os
import re
from datetime import datetime, timezone

from .paths import ROOT

OUT = os.path.join(ROOT, "outputs", "history")
APP = os.path.join(ROOT, "app", "data", "history")
COLS = ["d", "h", "a", "hg", "ag", "hthg", "htag", "s"]


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _season_of(day: str) -> int:
    y, m = int(day[:4]), int(day[5:7])
    return y if m >= 7 else y - 1


def _current(fixtures_path: str) -> list[dict]:
    out = []
    for f in _load(fixtures_path, {}).get("fixtures", []):
        if f.get("score") and f.get("kickoff_utc"):
            ht = f.get("ht") or [None, None]
            out.append({"d": f["kickoff_utc"][:10], "h": f["home"], "a": f["away"], "hg": f["score"][0], "ag": f["score"][1],
                        "hthg": ht[0], "htag": ht[1]})
    return out


def laliga() -> tuple[list[dict], dict]:
    teams = {k: {"en": v.get("en"), "ar": v.get("ar")} for k, v in _load(os.path.join(ROOT, "app", "data", "teams.json"), {}).get("teams", {}).items()}
    rows, cur_season = [], None
    snap = _current(os.path.join(ROOT, "app", "data", "fixtures.json"))
    if snap:
        cur_season = _season_of(snap[0]["d"])
    with open(os.path.join(ROOT, "data", "standard", "matches.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if cur_season is not None and int(r["season"]) >= cur_season:
                continue        # this season comes from the app snapshot (the newest results)
            hg, ag = _int(r["hg"]), _int(r["ag"])
            if hg is None or ag is None:
                continue
            rows.append({"d": r["date"], "h": r["home_id"], "a": r["away_id"], "hg": hg, "ag": ag,
                         "hthg": _int(r["hthg"]), "htag": _int(r["htag"]), "s": int(r["season"])})
            for side in ("home", "away"):
                tid = r[side + "_id"]
                teams.setdefault(tid, {"en": r[side], "ar": None})
    return rows + snap, teams


def slug(name: str) -> str:
    return "x" + re.sub(r"[^A-Z]", "", name.upper())[:6]


def premier_league() -> tuple[list[dict], dict]:
    from .multi import EPL, FD2CODE      # pandas-free import path is not needed: multi is part of the pipeline
    teams = {k: {"en": v[2], "ar": v[3]} for k, v in EPL.items()}
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "epl-mirror", "season-*.csv"))):
        code = re.search(r"season-(\d\d)\d\d", p).group(1)       # season-1920.csv -> 2019 (COVID matches ran into July)
        season = 2000 + int(code) if int(code) < 90 else 1900 + int(code)
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                hg, ag = _int(r.get("FTHG")), _int(r.get("FTAG"))
                if hg is None or ag is None or not r.get("Date"):
                    continue
                ids = []
                for nm in (r["HomeTeam"], r["AwayTeam"]):
                    tid = FD2CODE.get(nm) or slug(nm)
                    teams.setdefault(tid, {"en": nm, "ar": None})
                    ids.append(tid)
                d = r["Date"]
                if "/" in d:            # older football-data files use dd/mm/yy
                    dd, mm, yy = d.split("/")
                    d = f"{2000 + int(yy) if len(yy) == 2 else int(yy)}-{int(mm):02d}-{int(dd):02d}"
                rows.append({"d": d, "h": ids[0], "a": ids[1], "hg": hg, "ag": ag,
                             "hthg": _int(r.get("HTHG")), "htag": _int(r.get("HTAG")), "s": season})
    seen = {(r["d"], r["h"], r["a"]) for r in rows}
    cur = [r for r in _current(os.path.join(ROOT, "app", "data", "c", "ENG1", "fixtures.json")) if (r["d"], r["h"], r["a"]) not in seen]
    return rows + cur, teams


def pack(comp: str, rows: list[dict], teams: dict, source: str) -> dict:
    rows = sorted(rows, key=lambda r: (r["d"], r["h"]))
    used = {r["h"] for r in rows} | {r["a"] for r in rows}
    data = [[int(r["d"].replace("-", "")), r["h"], r["a"], r["hg"], r["ag"], r["hthg"], r["htag"], r.get("s") or _season_of(r["d"])] for r in rows]
    seasons = sorted({x[7] for x in data})
    return {"comp": comp, "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": source,
            "scope_ar": "مباريات الدوري فقط (بدون الكأس والسوبر والبطولات الأوروبية)",
            "coverage": {"from": rows[0]["d"] if rows else None, "to": rows[-1]["d"] if rows else None, "n": len(rows),
                         "seasons": [seasons[0], seasons[-1]] if seasons else None},
            "teams": {k: v for k, v in teams.items() if k in used}, "cols": COLS, "rows": data}


def build(write: bool = True) -> dict:
    out = {}
    ll, llt = laliga()
    out["ESP1"] = pack("ESP1", ll, llt, "football-data.co.uk (mirror on GitHub) + openfootball / SportRadar this season")
    pl, plt = premier_league()
    out["ENG1"] = pack("ENG1", pl, plt, "football-data.co.uk (mirror on GitHub) + openfootball / SportRadar this season")
    if write:
        for d in (OUT, APP):
            os.makedirs(d, exist_ok=True)
            for comp, doc in out.items():
                with open(os.path.join(d, f"{comp}.json"), "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    return out


if __name__ == "__main__":
    for c, d in build().items():
        print(c, d["coverage"], f'{len(d["teams"])} teams')
