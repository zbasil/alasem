"""Free data sources (version 3): no key, no payment.

    ESPN public site API   scores, live clock, lineups with formations, goals and cards for La Liga (esp.1),
                           the Premier League (eng.1) and the Champions League (uefa.champions)
    Fantasy Premier League the official game's public API: every EPL player's availability (injured, doubtful,
                           suspended, with the club's news and chance of playing) and season stats (minutes,
                           goals, assists, expected goals and assists)
    Understat              expected goals of every La Liga and Premier League match this season (not the
                           Champions League)
    RSS feeds              headlines (title, source, link only) from any free feed
    ntfy.sh                free, open-source push notifications to the ntfy phone app (no account)

Where they run: on your computer (`python scripts/free_update.py`) or free on GitHub Actions
(.github/workflows/update.yml). A Claude artifact page cannot reach these hosts, so their results reach the
published app only through an update run outside Claude (or a Claude session that fetches them for you).

Terms (read them before sharing anything publicly): the ESPN and Understat endpoints are unofficial and meant
for personal, non-commercial use; the FPL API serves the game and is widely used by fan tools; RSS feeds are for
syndication, so show title + source + link, never the article text; ntfy.sh topics are public by name, so use a
long random topic.

Field names were checked against live responses (ESPN scoreboard and FPL bootstrap-static, 24 Oct 2026); every
parser treats a missing field as unknown, never as zero.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (Zahraa Football Supercomputer; personal use)"}
ESPN_LEAGUE = {"ESP1": "esp.1", "ENG1": "eng.1", "UCL": "uefa.champions"}
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}"
FPL_BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES = "https://fantasy.premierleague.com/api/fixtures/"
UNDERSTAT_LEAGUE = {"ESP1": "La_liga", "ENG1": "EPL"}
FPL_STATUS_AR = {"a": "متاح", "d": "مشكوك فيه", "i": "مصاب", "s": "موقوف", "u": "غير متاح", "n": "غير مؤهل"}


def http_get(url: str, timeout: int = 20, retries: int = 3) -> bytes:
    err = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # network, HTTP error, timeout
            err = e
            time.sleep(1.5 * (i + 1))
    raise IOError(f"{url}: {err}")


def http_json(url: str, **kw):
    return json.loads(http_get(url, **kw).decode("utf-8"))


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# ESPN
# --------------------------------------------------------------------------

def espn_scoreboard(comp: str, day: str | None = None) -> list[dict]:
    """Matches of one day (YYYYMMDD, default today) with live state."""
    url = ESPN_BASE.format(league=ESPN_LEAGUE[comp]) + "/scoreboard" + (f"?dates={day}" if day else "")
    return parse_espn_scoreboard(http_json(url))


def parse_espn_scoreboard(js: dict) -> list[dict]:
    out = []
    for ev in js.get("events", []) or []:
        comp = (ev.get("competitions") or [{}])[0]
        st = (ev.get("status") or comp.get("status") or {})
        typ = st.get("type") or {}
        sides = {}
        for c in comp.get("competitors", []) or []:
            t = c.get("team") or {}
            sides[c.get("homeAway")] = {"espn_id": t.get("id"), "abbr": t.get("abbreviation"), "name": t.get("displayName"),
                                        "score": None if c.get("score") in (None, "") else int(c["score"])}
        events = []
        for d in comp.get("details", []) or []:
            dt = d.get("type") or {}
            events.append({"minute": (d.get("clock") or {}).get("displayValue"), "type": dt.get("text") or dt.get("id"),
                           "team_id": (d.get("team") or {}).get("id"),
                           "players": [a.get("displayName") or (a.get("athlete") or {}).get("displayName")
                                       for a in d.get("athletesInvolved", []) or []],
                           "goal": bool(d.get("scoringPlay")), "red": bool(d.get("redCard")), "yellow": bool(d.get("yellowCard"))})
        out.append({"espn_id": ev.get("id"), "kickoff_utc": ev.get("date"), "state": typ.get("state"),
                    "completed": bool(typ.get("completed")), "detail": typ.get("shortDetail") or typ.get("detail"),
                    "clock": st.get("displayClock"), "home": sides.get("home", {}), "away": sides.get("away", {}),
                    "events": events})
    return out


def espn_summary(comp: str, event_id: str) -> dict:
    url = ESPN_BASE.format(league=ESPN_LEAGUE[comp]) + f"/summary?event={urllib.parse.quote(str(event_id))}"
    return parse_espn_summary(http_json(url))


def parse_espn_summary(js: dict) -> dict:
    """Lineups (formation, starters, bench, substitutions), key events and team stats of one match."""
    lineups = []
    for r in js.get("rosters", []) or []:
        t = r.get("team") or {}
        players = []
        for p in r.get("roster", []) or []:
            a = p.get("athlete") or {}
            players.append({"name": a.get("displayName"), "jersey": p.get("jersey"),
                            "pos": (p.get("position") or {}).get("abbreviation"), "starter": bool(p.get("starter")),
                            "subbed_in": bool(p.get("subbedIn")), "subbed_out": bool(p.get("subbedOut"))})
        lineups.append({"side": r.get("homeAway"), "team": t.get("displayName"), "abbr": t.get("abbreviation"),
                        "formation": r.get("formation"), "players": players})
    events = []
    for k in js.get("keyEvents", []) or []:
        events.append({"minute": (k.get("clock") or {}).get("displayValue"), "type": (k.get("type") or {}).get("text"),
                       "team": (k.get("team") or {}).get("displayName"), "text": k.get("text") or k.get("shortText")})
    stats = {}
    for t in (js.get("boxscore") or {}).get("teams", []) or []:
        name = (t.get("team") or {}).get("abbreviation")
        stats[name] = {s.get("name"): _num(s.get("displayValue")) for s in t.get("statistics", []) or []}
    return {"lineups": lineups, "events": events, "stats": stats,
            "has_lineups": any(len(l["players"]) for l in lineups)}


# --------------------------------------------------------------------------
# Fantasy Premier League
# --------------------------------------------------------------------------

def fpl_bootstrap() -> dict:
    return http_json(FPL_BOOTSTRAP, timeout=40)


def parse_fpl_availability(js: dict) -> list[dict]:
    """Every EPL player not fully available, with the club's note and chance of playing."""
    teams = {t["id"]: t for t in js.get("teams", [])}
    out = []
    for e in js.get("elements", []):
        st = e.get("status")
        if st in (None, "a") and not e.get("news"):
            continue
        t = teams.get(e.get("team"), {})
        out.append({"team": t.get("short_name"), "team_name": t.get("name"), "player": e.get("web_name"),
                    "status": st, "status_ar": FPL_STATUS_AR.get(st, st),
                    "chance_next": e.get("chance_of_playing_next_round"), "news": e.get("news") or "",
                    "updated": e.get("news_added")})
    return sorted(out, key=lambda r: (r["team"] or "", r["chance_next"] if r["chance_next"] is not None else -1))


def parse_fpl_players(js: dict, min_minutes: int = 1) -> list[dict]:
    """Season stats of every EPL player (expected goals/assists are FPL's, from Opta)."""
    teams = {t["id"]: t for t in js.get("teams", [])}
    pos = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    out = []
    for e in js.get("elements", []):
        mins = e.get("minutes") or 0
        if mins < min_minutes:
            continue
        out.append({"player": e.get("web_name"), "team": teams.get(e.get("team"), {}).get("short_name"),
                    "pos": pos.get(e.get("element_type")), "minutes": mins, "starts": e.get("starts"),
                    "goals": e.get("goals_scored"), "assists": e.get("assists"), "xg": _num(e.get("expected_goals")),
                    "xa": _num(e.get("expected_assists")), "xgi": _num(e.get("expected_goal_involvements")),
                    "yellow": e.get("yellow_cards"), "red": e.get("red_cards"), "saves": e.get("saves"),
                    "clean_sheets": e.get("clean_sheets")})
    return out


# --------------------------------------------------------------------------
# Understat
# --------------------------------------------------------------------------

def understat_league(comp: str, season: int) -> list[dict]:
    """Matches of a league season with each side's expected goals. Understat has changed its page format
    before; both the embedded-JSON page and the JSON endpoint are tried."""
    lg = UNDERSTAT_LEAGUE[comp]
    try:
        js = http_json(f"https://understat.com/getLeagueData/{lg}/{season}")
        dates = js.get("dates") or js.get("datesData") or []
    except Exception:
        html = http_get(f"https://understat.com/league/{lg}/{season}").decode("utf-8", "replace")
        dates = parse_understat_embedded(html, "datesData")
    return parse_understat_dates(dates)


def parse_understat_embedded(html: str, var: str):
    m = re.search(var + r"\s*=\s*JSON\.parse\('(.*?)'\)", html, flags=re.S)
    if not m:
        raise ValueError(f"{var} not found")
    raw = m.group(1).encode("utf-8").decode("unicode_escape")
    return json.loads(raw)


def parse_understat_dates(dates: list) -> list[dict]:
    out = []
    for d in dates:
        h, a = d.get("h") or {}, d.get("a") or {}
        g, x = d.get("goals") or {}, d.get("xG") or {}
        out.append({"understat_id": d.get("id"), "datetime": d.get("datetime"), "played": bool(d.get("isResult")),
                    "home": h.get("title"), "away": a.get("title"),
                    "hg": None if g.get("h") is None else int(g["h"]), "ag": None if g.get("a") is None else int(g["a"]),
                    "xg_home": _num(x.get("h")), "xg_away": _num(x.get("a"))})
    return out


# --------------------------------------------------------------------------
# RSS headlines and ntfy notifications
# --------------------------------------------------------------------------

def rss_headlines(feeds: list[dict], limit: int = 40) -> list[dict]:
    items = []
    for f in feeds:
        try:
            items += parse_rss(http_get(f["url"]).decode("utf-8", "replace"), f.get("name") or f["url"])
        except Exception as e:  # one broken feed never stops the others
            items.append({"error": str(e), "source": f.get("name")})
    good = [i for i in items if "error" not in i]
    good.sort(key=lambda i: i.get("published") or "", reverse=True)
    return good[:limit]


def parse_rss(xml_text: str, source: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for it in root.iter("item"):
        out.append({"title": (it.findtext("title") or "").strip(), "link": (it.findtext("link") or "").strip(),
                    "published": _rfc822(it.findtext("pubDate")), "source": source})
    for it in root.findall("a:entry", ns):
        link = it.find("a:link", ns)
        out.append({"title": (it.findtext("a:title", default="", namespaces=ns) or "").strip(),
                    "link": link.get("href") if link is not None else "",
                    "published": it.findtext("a:updated", default="", namespaces=ns), "source": source})
    return [o for o in out if o["title"] and o["link"].startswith(("http://", "https://"))]


def _rfc822(s: str | None) -> str:
    if not s:
        return ""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def ntfy_send(topic: str, title: str, message: str, click: str | None = None, tags: list | None = None,
              server: str = "https://ntfy.sh", dry_run: bool = False) -> dict:
    """Push a notification to everyone subscribed to the topic in the free ntfy app.
    Published as JSON so Arabic titles stay intact (HTTP headers cannot carry them)."""
    if not topic or len(topic) < 12:
        raise ValueError("use a long, random topic name (topics are public by name)")
    body = {"topic": topic, "title": title, "message": message, "tags": tags or ["soccer"]}
    if click:
        body["click"] = click
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(server.rstrip("/") + "/", data=data, method="POST",
                                 headers={"Content-Type": "application/json", **UA})
    if dry_run:
        return {"url": req.full_url, "body": body}
    with urllib.request.urlopen(req, timeout=15) as r:
        return {"status": r.status}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
