"""Local web server: the app + a small JSON API (Python standard library only).

    python -m zsc serve [--port 8000]

Static files come from app/ (the app reads app/data/*.json, the current snapshot).
API
    GET  /api/health                       {"ok": true, "mode": "server", ...}
    GET  /api/status                       data status, snapshots, update job
    POST /api/update                       start an update in the background (fetch, rebuild, export)
    GET  /api/user/<name>                  saved user data: prefs, stories, notes
    PUT  /api/user/<name>                  replace it (JSON body, max 2 MB)
    GET  /api/challenge                    audience predictions, leaderboard (weekly + total) and rules
    POST /api/challenge                    {"player": "...", "match_id": "...", "pick": "H|D|A", "score": "2-1"?}
                                           refused once the match has kicked off
User data lives in data/userdata/ (never inside the snapshot, so updates never touch it).
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import config, store, update
from .paths import APP, APP_DATA, SNAPSHOTS, USERDATA

USER_NAMES = {"prefs", "stories", "notes", "scripts"}
MAX_BODY = 2 * 1024 * 1024
JOB = {"running": False, "log": [], "result": None, "started": None}
LOCK = threading.Lock()
RULES_AR = ["التوقع ينقفل بصافرة البداية (حسب موعد المباراة الرسمي).",
            "النتيجة الصحيحة (فوز/تعادل/خسارة): نقطة وحدة.",
            "النتيجة الرقمية الصحيحة: نقطتين إضافيتين (المجموع 3).",
            "الترتيب الأسبوعي من الاثنين للأحد بتوقيت بغداد، والترتيب العام لكل الموسم.",
            "توقعات الجمهور منفصلة عن توقعات الحاسوب، والحاسوب يشارك بالترتيب كمتسابق باسم «الحاسوب»."]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def fixtures_index() -> dict:
    fx = _read_json(os.path.join(APP_DATA, "fixtures.json"), {"fixtures": []})["fixtures"]
    return {f["match_id"]: f for f in fx}


def challenge_board() -> dict:
    data = _read_json(os.path.join(USERDATA, "challenge.json"), {"picks": []})
    fx = fixtures_index()
    from collections import defaultdict
    total, weekly = defaultdict(int), defaultdict(lambda: defaultdict(int))
    played = defaultdict(int)
    rows = []
    picks = list(data["picks"])
    # the computer's own entry: its most likely outcome and score, recorded like any player
    for mid, f in fx.items():
        if f.get("p") and f.get("score") is None:
            continue
    for p in picks:
        f = fx.get(p["match_id"])
        if not f or f.get("score") is None:
            continue
        hg, ag = f["score"]
        res = "H" if hg > ag else ("D" if hg == ag else "A")
        pts = (1 if p["pick"] == res else 0) + (2 if p.get("score") == f"{hg}-{ag}" else 0)
        wk = (f.get("kickoff_baghdad") or {}).get("date", "")
        wk_id = _iso_week(wk)
        total[p["player"]] += pts
        weekly[wk_id][p["player"]] += pts
        played[p["player"]] += 1
        rows.append({**p, "points": pts, "result": f"{hg}-{ag}"})
    board = sorted(({"player": k, "points": v, "played": played[k]} for k, v in total.items()), key=lambda r: -r["points"])
    weeks = {w: sorted(({"player": k, "points": v} for k, v in d.items()), key=lambda r: -r["points"]) for w, d in weekly.items()}
    return {"picks": data["picks"], "scored": rows, "total": board, "weekly": weeks, "rules_ar": RULES_AR}


def _iso_week(date: str) -> str:
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"
    except ValueError:
        return "unknown"


def _run_update():
    def log(msg):
        JOB["log"].append(msg)
        JOB["log"] = JOB["log"][-200:]
    try:
        JOB["result"] = update.run(log=log)
    except Exception as e:  # reported to the app
        JOB["result"] = {"error": str(e)}
    finally:
        JOB["running"] = False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=APP, **kw)

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def end_headers(self):
        if self.path.startswith("/data/") or self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("body too large")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw or b"{}")

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.api_get()
        return super().do_GET()

    def do_POST(self):
        return self.api_write()

    def do_PUT(self):
        return self.api_write()

    def api_get(self):
        p = self.path.split("?")[0]
        if p == "/api/health":
            return self._json({"ok": True, "mode": "server", "version": config.settings()["platform"]["version"],
                               "time": now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")})
        if p == "/api/status":
            snaps = sorted(d for d in os.listdir(SNAPSHOTS)) if os.path.isdir(SNAPSHOTS) else []
            return self._json({"status": store.status(), "snapshots": snaps[-20:], "job": {k: JOB[k] for k in ("running", "started")},
                               "job_log": JOB["log"][-30:], "job_result": JOB["result"]})
        if p == "/api/update":
            return self._json({k: JOB[k] for k in ("running", "started", "log", "result")})
        if p == "/api/challenge":
            return self._json(challenge_board())
        m = re.fullmatch(r"/api/user/([a-z]+)", p)
        if m and m.group(1) in USER_NAMES:
            return self._json(_read_json(os.path.join(USERDATA, f"{m.group(1)}.json"), {}))
        return self._json({"error": "not found"}, 404)

    def api_write(self):
        p = self.path.split("?")[0]
        try:
            body = self._body()
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        if p == "/api/update":
            with LOCK:
                if JOB["running"]:
                    return self._json({"error": "an update is already running"}, 409)
                JOB.update({"running": True, "log": [], "result": None,
                            "started": now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")})
            threading.Thread(target=_run_update, daemon=True).start()
            return self._json({"ok": True, "started": JOB["started"]})
        if p == "/api/challenge":
            player = str(body.get("player", "")).strip()[:40]
            mid, pick = body.get("match_id"), body.get("pick")
            score = body.get("score")
            if not player or pick not in ("H", "D", "A"):
                return self._json({"error": "player and pick (H/D/A) are required"}, 400)
            if score is not None and not re.fullmatch(r"\d{1,2}-\d{1,2}", str(score)):
                return self._json({"error": "score must look like 2-1"}, 400)
            f = fixtures_index().get(mid)
            if not f:
                return self._json({"error": "unknown match"}, 404)
            ko = f.get("kickoff_utc")
            if not ko or datetime.strptime(ko, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= now_utc():
                return self._json({"error": "locked: the match has kicked off"}, 409)
            if score:
                h, a = map(int, score.split("-"))
                if ("H" if h > a else ("D" if h == a else "A")) != pick:
                    return self._json({"error": "score and pick disagree"}, 400)
            path = os.path.join(USERDATA, "challenge.json")
            with LOCK:
                data = _read_json(path, {"picks": []})
                data["picks"] = [x for x in data["picks"] if not (x["player"] == player and x["match_id"] == mid)]
                data["picks"].append({"player": player, "match_id": mid, "pick": pick, "score": score,
                                      "at": now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")})
                _write_json(path, data)
            return self._json({"ok": True})
        m = re.fullmatch(r"/api/user/([a-z]+)", p)
        if m and m.group(1) in USER_NAMES:
            with LOCK:
                _write_json(os.path.join(USERDATA, f"{m.group(1)}.json"), body)
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)


def serve(host: str | None = None, port: int | None = None):
    s = config.settings()["server"]
    host = host or config.env("ZSC_HOST", s["host"])
    port = port or int(config.env("ZSC_PORT", str(s["port"])))
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("font/woff2", ".woff2")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Zahraa Football Supercomputer: http://{host}:{port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
