"""API-Football (v3) adapter: lineups, absences and fixture ids. Switched off until a key is provided.

Activation (docs/ACTIVATION.md):
    1. get a key at https://www.api-football.com/ (free tier: 100 requests per day)
    2. put it in .env as API_FOOTBALL_KEY=... (or in the environment)
    3. set "enabled": true for "api_football" in config/settings.json
    4. python -m zsc update   (fetches fixtures, injuries and the lineups of matches within the next 2 hours)

Requests (header x-apisports-key):
    GET /fixtures?league=140&season=<year>           fixture ids, kick-off times, status
    GET /injuries?league=140&season=<year>            players missing or doubtful per fixture
    GET /fixtures/lineups?fixture=<id>                formation, starting XI with grid positions, substitutes
Raw answers are kept as they arrive under data/raw/api_football/ (with fetch time); the standard tables are
data/standard/lineups.csv and data/standard/absences.csv, keyed by the project's own match ids.

Written to the documented v3 format; not yet run against the live service (no key in this project so far).
tests/test_apifootball.py checks the mapping on answers shaped like the documented examples.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from . import config
from .paths import RAW, STANDARD
from .registry import match_id as make_match_id, team_id
from .teams import canonical

BASE = "https://v3.football.api-sports.io"
LEAGUE = 140                      # La Liga in API-Football
RAW_DIR = os.path.join(RAW, "api_football")
LINEUPS = os.path.join(STANDARD, "lineups.csv")
ABSENCES = os.path.join(STANDARD, "absences.csv")


def key() -> str:
    return config.env("API_FOOTBALL_KEY", "")


def enabled() -> bool:
    src = config.settings()["sources"].get("api_football", {})
    return bool(src.get("enabled")) and bool(key())


def status() -> dict:
    src = config.settings()["sources"].get("api_football", {})
    if not key():
        return {"status": "needs_key", "text_ar": "يحتاج مفتاح API_FOOTBALL_KEY"}
    if not src.get("enabled"):
        return {"status": "needs_key", "text_ar": "المفتاح موجود بس المصدر غير مفعّل بالإعدادات (enabled)"}
    if os.path.exists(LINEUPS) or os.path.exists(ABSENCES):
        return {"status": "active", "text_ar": "مفعّل"}
    return {"status": "partial", "text_ar": "مفعّل؛ ينتظر أول تحديث"}


def _get(path: str, params: dict) -> dict:
    q = "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(f"{BASE}{path}?{q}", headers={"x-apisports-key": key()})
    with urllib.request.urlopen(req, timeout=config.settings()["update"]["timeout_seconds"]) as r:
        body = json.loads(r.read())
    if body.get("errors"):
        raise RuntimeError(f"API-Football: {body['errors']}")
    return body


def _save(name: str, body: dict) -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, name)
    body = {"fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": BASE, **body}
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)
    return path


def fetch(season: int | None = None, lineup_window_hours: float = 2.0, log=print) -> dict:
    """Fixtures + injuries for the season, and lineups of matches starting within the window (or just played)."""
    if not enabled():
        return {"status": "skipped", "reason": status()["text_ar"]}
    season = season or config.season()
    fx = _get("/fixtures", {"league": LEAGUE, "season": season})
    _save(f"fixtures_{season}.json", fx)
    inj = _get("/injuries", {"league": LEAGUE, "season": season})
    _save(f"injuries_{season}.json", inj)
    now = datetime.now(timezone.utc)
    n = 0
    for item in fx.get("response", []):
        ko = datetime.fromisoformat(item["fixture"]["date"].replace("Z", "+00:00"))
        hours = (ko - now).total_seconds() / 3600
        if -3 <= hours <= lineup_window_hours:
            fid = item["fixture"]["id"]
            _save(f"lineups_{fid}.json", _get("/fixtures/lineups", {"fixture": fid}))
            n += 1
    log(f"  API-Football: {len(fx.get('response', []))} fixtures, {len(inj.get('response', []))} injury rows, {n} lineups")
    standardise(season)
    return {"status": "fresh", "lineups": n}


def id_map(fixtures: dict, season: int) -> dict:
    """API fixture id -> the project's match id (by canonical team names)."""
    comp = config.competition()
    out = {}
    for item in fixtures.get("response", []):
        h, a = canonical(item["teams"]["home"]["name"]), canonical(item["teams"]["away"]["name"])
        out[item["fixture"]["id"]] = make_match_id(comp, season, h, a)
    return out


def lineup_rows(body: dict, match_id: str) -> list[dict]:
    rows = []
    for t in body.get("response", []):
        tid = team_id(canonical(t["team"]["name"]))
        for starter, key_ in ((True, "startXI"), (False, "substitutes")):
            for p in t.get(key_) or []:
                pl = p["player"]
                rows.append({"match_id": match_id, "team_id": tid, "formation": t.get("formation"), "starter": starter,
                             "player_id": pl.get("id"), "player": pl.get("name"), "number": pl.get("number"),
                             "pos": pl.get("pos"), "grid": pl.get("grid"), "coach": (t.get("coach") or {}).get("name")})
    return rows


def absence_rows(body: dict, ids: dict) -> list[dict]:
    rows = []
    for r in body.get("response", []):
        rows.append({"match_id": ids.get(r["fixture"]["id"]), "team_id": team_id(canonical(r["team"]["name"])),
                     "player_id": r["player"].get("id"), "player": r["player"].get("name"),
                     "type": r["player"].get("type"), "reason": r["player"].get("reason"), "date": r["fixture"].get("date")})
    return rows


def standardise(season: int | None = None) -> None:
    season = season or config.season()
    fpath = os.path.join(RAW_DIR, f"fixtures_{season}.json")
    if not os.path.exists(fpath):
        return
    fixtures = json.load(open(fpath, encoding="utf-8"))
    ids = id_map(fixtures, season)
    rows = []
    for name in sorted(os.listdir(RAW_DIR)):
        if name.startswith("lineups_"):
            fid = int(name.split("_")[1].split(".")[0])
            if fid in ids:
                rows += lineup_rows(json.load(open(os.path.join(RAW_DIR, name), encoding="utf-8")), ids[fid])
    if rows:
        pd.DataFrame(rows).to_csv(LINEUPS, index=False)
    ipath = os.path.join(RAW_DIR, f"injuries_{season}.json")
    if os.path.exists(ipath):
        ab = absence_rows(json.load(open(ipath, encoding="utf-8")), ids)
        if ab:
            pd.DataFrame(ab).to_csv(ABSENCES, index=False)


def lineups_for(match_id: str) -> dict | None:
    if not os.path.exists(LINEUPS):
        return None
    df = pd.read_csv(LINEUPS)
    d = df[df["match_id"] == match_id]
    if d.empty:
        return None
    out = {}
    for tid, g in d.groupby("team_id"):
        out[tid] = {"formation": g["formation"].iloc[0], "coach": g["coach"].iloc[0],
                    "starters": g[g["starter"]][["player", "number", "pos", "grid"]].to_dict("records"),
                    "subs": g[~g["starter"]][["player", "number", "pos"]].to_dict("records")}
    return out


def absences_for(team: str) -> list[dict] | None:
    if not os.path.exists(ABSENCES):
        return None
    df = pd.read_csv(ABSENCES)
    d = df[df["team_id"] == team]
    if d.empty:
        return []
    d = d.sort_values("date").drop_duplicates("player", keep="last")
    return d[["player", "type", "reason", "date"]].to_dict("records")
