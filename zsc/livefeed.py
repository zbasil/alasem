"""Live layer (version 3.1): ESPN scoreboards -> one normalised file the app polls.

    python scripts/free_update.py      fetches ESPN and calls build_live(), which writes
                                       outputs/live/now.json and app/data/live/now.json

Why a file and not every browser calling ESPN: the update job (GitHub Actions, or your computer) asks ESPN once
and every viewer reads the same small static file, so viewers never multiply the requests to the source. An
optional edge proxy (workers/live-proxy) can serve fresher scores the same way; see docs/LIVE.md.

What this module guarantees
- Each ESPN game is tied to one of our fixtures (stable match_id) by competition, team names and kick-off time;
  anything it cannot tie is listed under "unmatched", never guessed.
- Events get stable ids, so the app and notifications never show the same goal twice.
- Corrections are kept: an event that disappears from the source (a goal ruled out by VAR, a card rescinded) is
  moved to "retracted", and a score that goes down is recorded in "score_history".
- Unknown stays unknown: a missing score, minute or stat is null, never 0.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timezone

from .paths import ROOT

LIVE_OUT = os.path.join(ROOT, "outputs", "live")
LIVE_APP = os.path.join(ROOT, "app", "data", "live")

# names ESPN uses that no token rule can tie to ours (normalised form -> our team id)
ALIASES = {
    "manchester city": "MCI", "manchester united": "MUN", "man utd": "MUN", "spurs": "TOT",
    "wolverhampton wanderers": "WOL", "wolves": "WOL", "internazionale": "INT", "inter milan": "INT",
    "paris saint germain": "PSG", "psg": "PSG", "atletico madrid": "ATM", "atletico de madrid": "ATM",
    "athletic bilbao": "ATH", "athletic club": "ATH", "celta vigo": "RCC", "celta de vigo": "RCC",
    "real betis": "RBB", "betis": "RBB", "bayern munchen": "BMU", "bayern munich": "BMU",
    "borussia dortmund": "BVB", "fc porto": "FCP", "porto": "FCP", "sporting lisbon": "SPO", "sporting cp": "SPO",
    "bodo glimt": "BOG", "bodoe glimt": "BOG", "slavia praha": "SLA", "slavia prague": "SLA",
    "slovan bratislava": "SLO", "shakhtar donetsk": "SHA", "rb leipzig": "RBL", "rasenballsport leipzig": "RBL",
    "vfb stuttgart": "VFB", "psv eindhoven": "PSV", "psv": "PSV", "club brugge": "BRU", "lens": "RCL",
    "as roma": "ROM", "roma": "ROM", "aek athens": "AEK", "nottingham forest": "NFO", "nottm forest": "NFO",
}
STOP = {"fc", "cf", "afc", "ac", "sc", "cd", "ud", "rcd", "sd", "club", "de", "as", "fk", "sk", "ssc", "1907", "the", "and"}

# ESPN status names -> our states. Anything unknown falls back on ESPN's coarse state (pre/in/post).
STATUS = {
    "STATUS_SCHEDULED": "pre", "STATUS_FIRST_HALF": "live", "STATUS_SECOND_HALF": "live", "STATUS_IN_PROGRESS": "live",
    "STATUS_HALFTIME": "ht", "STATUS_END_OF_REGULATION": "live", "STATUS_OVERTIME": "live", "STATUS_EXTRA_TIME": "live",
    "STATUS_SHOOTOUT": "live", "STATUS_FULL_TIME": "ft", "STATUS_FINAL": "ft", "STATUS_FINAL_AET": "ft",
    "STATUS_FINAL_PEN": "ft", "STATUS_POSTPONED": "postponed", "STATUS_CANCELED": "cancelled",
    "STATUS_SUSPENDED": "suspended", "STATUS_ABANDONED": "abandoned", "STATUS_DELAYED": "delayed",
}
COARSE = {"pre": "pre", "in": "live", "post": "ft"}


def norm(name: str | None) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace("&", " and "))
    return " ".join(t for t in s.split() if t not in STOP)


def _ts(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def team_lookup(teams: dict) -> dict:
    """normalised name -> team id, from our own English names, ids and the alias table"""
    out = {}
    for tid, t in teams.items():
        for nm in (t.get("en"), t.get("short_en"), tid):
            if nm:
                out.setdefault(norm(nm), tid)
    for k, v in ALIASES.items():
        if v in teams:
            out[norm(k)] = v
    return out


def resolve_team(side: dict, lookup: dict, candidates: set) -> str | None:
    """our id for an ESPN side, only among the teams playing that day in that competition"""
    names = [norm(side.get("name")), norm(side.get("short")), norm(side.get("abbr"))]
    for n in names:
        if n and lookup.get(n) in candidates:
            return lookup[n]
    # token containment: "tottenham hotspur" ~ "tottenham", "brighton and hove albion" ~ "brighton"
    best = None
    for n in names[:2]:
        if not n:
            continue
        toks = set(n.split())
        for key, tid in lookup.items():
            if tid not in candidates or not key:
                continue
            kt = set(key.split())
            if kt and (kt <= toks or toks <= kt):
                if best and best != tid:
                    return None  # ambiguous: refuse rather than guess
                best = tid
    return best


def match_games(comp: str, games: list[dict], fixtures: list[dict], teams: dict) -> tuple[dict, list]:
    """{match_id: game} and the games that could not be tied to a fixture"""
    lookup = team_lookup(teams)
    tied, unmatched = {}, []
    for g in games:
        ko = _ts(g.get("kickoff_utc"))
        near = [f for f in fixtures if f.get("kickoff_utc") and ko is not None and abs(_ts(f["kickoff_utc"]) - ko) <= 36 * 3600]
        cands = {f["home"] for f in near} | {f["away"] for f in near}
        h = resolve_team(g.get("home") or {}, lookup, cands)
        a = resolve_team(g.get("away") or {}, lookup, cands)
        hit = [f for f in near if f["home"] == h and f["away"] == a] if h and a else []
        if not hit and (h or a):
            # one side tied and the kick-off within 3 hours: same match (ESPN and openfootball time zones differ)
            hit = [f for f in near if (f["home"] == h or f["away"] == a) and abs(_ts(f["kickoff_utc"]) - ko) <= 3 * 3600]
        if len(hit) == 1 and hit[0]["match_id"] not in tied:
            tied[hit[0]["match_id"]] = g
        else:
            unmatched.append({"comp": comp, "espn_id": g.get("espn_id"), "home": (g.get("home") or {}).get("name"),
                              "away": (g.get("away") or {}).get("name"), "kickoff_utc": g.get("kickoff_utc"),
                              "reason": "ambiguous" if len(hit) > 1 else "no fixture"})
    return tied, unmatched


def minute_of(clock: str | None) -> int | None:
    """"49'" -> 49, "90'+4'" -> 94 (shown as 90+4 by the app through `clock`), "HT" -> None"""
    m = re.match(r"\s*(\d+)'?(?:\s*\+\s*(\d+))?", str(clock or ""))
    return int(m.group(1)) + int(m.group(2) or 0) if m else None


def event_kind(e: dict) -> str:
    t = str(e.get("type") or "").lower()
    if e.get("own_goal") or "own goal" in t:
        return "own_goal"
    if e.get("goal"):
        return "penalty_goal" if e.get("penalty") or "penalty" in t else "goal"
    if "penalty" in t and ("miss" in t or "saved" in t):
        return "penalty_missed"
    if e.get("red") or "red card" in t:
        return "second_yellow" if "second" in t or "2nd" in t else "red"
    if e.get("yellow") or "yellow" in t:
        return "yellow"
    if "substitution" in t:
        return "sub"
    if "var" in t:
        return "var"
    return "other"


def normalise_events(g: dict, side_of_team: dict) -> list[dict]:
    out, seen = [], {}
    for e in g.get("events", []) or []:
        kind = event_kind(e)
        players = [p for p in e.get("players") or [] if p]
        base = f'{g.get("espn_id")}:{kind}:{e.get("minute") or ""}:{(players or [""])[0]}'
        seen[base] = seen.get(base, 0) + 1
        eid = base if seen[base] == 1 else f"{base}:{seen[base]}"
        out.append({"id": eid, "kind": kind, "minute": minute_of(e.get("minute")), "clock": e.get("minute"),
                    "side": side_of_team.get(str(e.get("team_id"))), "players": players, "text": e.get("type")})
    out.sort(key=lambda x: (x["minute"] is None, x["minute"] or 0))
    return out


def live_entry(g: dict, prev: dict | None, stamp: str) -> dict:
    state = STATUS.get(g.get("status_name") or "") or COARSE.get(g.get("state") or "", "unknown")
    hs, as_ = (g.get("home") or {}).get("score"), (g.get("away") or {}).get("score")
    score = [hs, as_] if state != "pre" and hs is not None and as_ is not None else None
    side_of_team = {str((g.get(s) or {}).get("espn_id")): s for s in ("home", "away")}
    events = normalise_events(g, side_of_team)
    prev = prev or {}
    # corrections: events that vanished from the source stay visible as retracted, scores that went down are logged
    now_ids = {e["id"] for e in events}
    retracted = [e for e in prev.get("retracted", []) if e["id"] not in now_ids]
    retracted += [dict(e, retracted_utc=stamp) for e in prev.get("events", [])
                  if e["id"] not in now_ids and e["id"] not in {r["id"] for r in retracted}]
    history = list(prev.get("score_history", []))
    if score and (not history or history[-1]["score"] != score):
        history.append({"score": score, "seen_utc": stamp,
                        "correction": bool(history and sum(score) < sum(history[-1]["score"]))})
    entry = {"espn_id": g.get("espn_id"), "state": state, "detail": g.get("detail"), "clock": g.get("clock") if state == "live" else None,
             "minute": minute_of(g.get("clock")) if state == "live" else None, "period": g.get("period"),
             "score": score, "events": events, "retracted": retracted[-20:], "score_history": history[-30:],
             "fetched_utc": stamp,
             "changed_utc": prev.get("changed_utc") if prev.get("score") == score and len(prev.get("events", [])) == len(events)
             and prev.get("state") == state else stamp}
    s = g.get("summary")
    if isinstance(s, dict):
        entry["lineups"] = s.get("lineups") or []
        entry["has_lineups"] = bool(s.get("has_lineups"))
        entry["key_events"] = s.get("events") or []
        abbr = {str((g.get(x) or {}).get("abbr")): x for x in ("home", "away")}
        entry["stats"] = {abbr.get(k, k): v for k, v in (s.get("stats") or {}).items()}
        entry["info"] = s.get("info") or {}
    elif prev.get("lineups"):
        for k in ("lineups", "has_lineups", "key_events", "stats", "info"):
            if k in prev:
                entry[k] = prev[k]
    return entry


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def app_fixtures() -> dict:
    """{comp: (fixtures, teams)} from the app snapshot, the same ids the pages use"""
    base = os.path.join(ROOT, "app", "data")
    out = {}
    fx = _load(os.path.join(base, "fixtures.json"), {}).get("fixtures", [])
    if fx:
        out["ESP1"] = (fx, _load(os.path.join(base, "teams.json"), {}).get("teams", {}))
    for comp in ("ENG1", "UCL"):
        d = os.path.join(base, "c", comp)
        f2 = _load(os.path.join(d, "fixtures.json"), {}).get("fixtures", [])
        if f2:
            out[comp] = (f2, _load(os.path.join(d, "teams.json"), {}).get("teams", {}))
    return out


def build_live(games_by_comp: dict, stamp: str | None = None, fixtures: dict | None = None,
               out_dirs: tuple = (LIVE_OUT, LIVE_APP), source_report: dict | None = None) -> dict:
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fixtures = fixtures if fixtures is not None else app_fixtures()
    prev_doc = _load(os.path.join(out_dirs[0], "now.json"), {}) if out_dirs else {}
    prev = prev_doc.get("matches", {})
    matches, unmatched = {}, []
    for comp, games in games_by_comp.items():
        if comp not in fixtures:
            continue
        fx, teams = fixtures[comp]
        tied, um = match_games(comp, games, fx, teams)
        unmatched += um
        for mid, g in tied.items():
            matches[mid] = dict(live_entry(g, prev.get(mid), stamp), comp=comp)
    # keep finished matches of the last 36 hours that today's scoreboard no longer lists (the day rolled over)
    for mid, e in prev.items():
        if mid not in matches and e.get("state") in ("ft", "live", "ht") and (_ts(stamp) or 0) - (_ts(e.get("fetched_utc")) or 0) < 36 * 3600:
            matches[mid] = dict(e, stale=e.get("state") != "ft")
    doc = {"generated_utc": stamp, "source": "ESPN public site API (unofficial, personal non-commercial use)",
           "n_live": sum(1 for e in matches.values() if e["state"] in ("live", "ht") and not e.get("stale")),
           "matches": matches, "unmatched": unmatched, "sources": source_report or {}}
    proxy = os.environ.get("LIVE_PROXY", "").strip()
    if proxy.startswith("https://"):
        doc["proxy"] = proxy.rstrip("/")   # the app reads live scores from this shared edge cache between runs
    for d in out_dirs:
        os.makedirs(d, exist_ok=True)
        tmp = os.path.join(d, "now.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, os.path.join(d, "now.json"))
    return doc
