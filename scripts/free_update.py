"""Fetch every free source and put the results in the app (version 3).

    python scripts/free_update.py            fetch, write outputs/free/*.json and app/data/free/*.json
    python scripts/free_update.py --notify   also push goals / red cards / full time of favourite teams to ntfy

Runs on your computer or on GitHub Actions (.github/workflows/update.yml); no key and no payment. One failing
source never stops the others; each file says when and from where it was fetched.
"""
import json
import os
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from zsc import free_sources as fs  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "free")
APP = os.path.join(ROOT, "app", "data", "free")


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, os.path.join(OUT, name))


def main(argv):
    cfg = json.load(open(os.path.join(ROOT, "config", "free_sources.json"), encoding="utf-8"))
    stamp = fs.now_utc()
    report = {}
    if cfg["fpl"]["enabled"]:
        try:
            js = fs.fpl_bootstrap()
            save("fpl_availability.json", {"fetched_utc": stamp, "source": "Fantasy Premier League API",
                                           "players": fs.parse_fpl_availability(js)})
            save("fpl_players.json", {"fetched_utc": stamp, "source": "Fantasy Premier League API",
                                      "players": fs.parse_fpl_players(js)})
            report["fpl"] = "ok"
        except Exception as e:
            report["fpl"] = f"failed: {e}"
    if cfg["espn"]["enabled"]:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        games = {}
        for comp in cfg["espn"]["competitions"]:
            try:
                rows = fs.espn_scoreboard(comp, today)
                for r in rows:
                    if r["state"] in ("in", "post"):
                        try:
                            r["summary"] = fs.espn_summary(comp, r["espn_id"])
                        except Exception as e:
                            r["summary_error"] = str(e)
                games[comp] = rows
                report[f"espn_{comp}"] = f"ok ({len(rows)})"
            except Exception as e:
                report[f"espn_{comp}"] = f"failed: {e}"
        save("espn_today.json", {"fetched_utc": stamp, "source": "ESPN public site API (unofficial)", "games": games})
        if "--notify" in argv and cfg["ntfy"]["enabled"]:
            report["ntfy"] = notify(cfg, games)
    if cfg["understat"]["enabled"]:
        for comp in cfg["understat"]["competitions"]:
            try:
                rows = fs.understat_league(comp, cfg["understat"]["season"])
                save(f"understat_{comp}.json", {"fetched_utc": stamp, "source": "Understat", "matches": rows})
                report[f"understat_{comp}"] = f"ok ({len(rows)})"
            except Exception as e:
                report[f"understat_{comp}"] = f"failed: {e}"
    if cfg["rss"]["enabled"] and cfg["rss"]["feeds"]:
        save("headlines.json", {"fetched_utc": stamp, "items": fs.rss_headlines(cfg["rss"]["feeds"])})
        report["rss"] = "ok"
    save("_status.json", {"fetched_utc": stamp, "report": report})
    if os.path.isdir(OUT):
        os.makedirs(APP, exist_ok=True)
        for n in os.listdir(OUT):
            if n.endswith(".json"):
                shutil.copy2(os.path.join(OUT, n), os.path.join(APP, n))
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


def notify(cfg, games):
    """Goals, red cards and full time of favourite teams; a state file stops repeats."""
    topic = os.environ.get(cfg["ntfy"]["topic_env"], "")
    if not topic:
        return "skipped: set the NTFY_TOPIC environment variable (a long random name)"
    state_p = os.path.join(OUT, "_ntfy_state.json")
    seen = set(json.load(open(state_p))) if os.path.exists(state_p) else set()
    favs = {t.upper() for t in cfg["ntfy"]["fav_teams"]}
    sent = 0
    for comp, rows in games.items():
        for g in rows:
            abbrs = {(g["home"] or {}).get("abbr", "").upper(), (g["away"] or {}).get("abbr", "").upper()}
            if not abbrs & favs:
                continue
            score = f'{g["home"].get("name")} {g["home"].get("score")} - {g["away"].get("score")} {g["away"].get("name")}'
            items = [(f'{g["espn_id"]}:{i}', e) for i, e in enumerate(g.get("events", []))]
            for key, e in items:
                kind = "goal" if e["goal"] else ("red_card" if e["red"] else None)
                if kind in cfg["ntfy"]["events"] and key not in seen:
                    title = "هدف!" if kind == "goal" else "طرد!"
                    fs.ntfy_send(topic, title, f'{e["minute"]} {", ".join(p for p in e["players"] if p)} · {score}',
                                 server=cfg["ntfy"]["server"])
                    seen.add(key)
                    sent += 1
            ft_key = f'{g["espn_id"]}:ft'
            if g["completed"] and "full_time" in cfg["ntfy"]["events"] and ft_key not in seen:
                fs.ntfy_send(topic, "نهاية المباراة", score, server=cfg["ntfy"]["server"])
                seen.add(ft_key)
                sent += 1
    json.dump(sorted(seen), open(state_p, "w"))
    return f"sent {sent}"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
