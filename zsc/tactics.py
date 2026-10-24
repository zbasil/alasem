"""Tactical match-ups from event data (StatsBomb): flank against flank, pressing against build-up.

Coordinates: each team's events are recorded as if it attacks towards x = 120; y = 0 is its left touchline. The
opponent's frame is turned 180 degrees, so a team's left channel (y < 26.7) faces the opponent's right channel
(y > 53.3 in the opponent's own frame).
"""

from __future__ import annotations

from collections import Counter, defaultdict

CHANNELS = {"left": (0.0, 26.67), "centre": (26.67, 53.33), "right": (53.33, 80.01)}
CHANNEL_AR = {"left": "اليسار", "centre": "العمق", "right": "اليمين"}
MIRROR = {"left": "right", "centre": "centre", "right": "left"}


def _channel(y):
    for k, (a, b) in CHANNELS.items():
        if a <= y < b:
            return k
    return "centre"


def matchups(events: list, home: str, away: str, name=lambda p: p) -> dict:
    """Per team and channel: attacking actions into the final third, xG, crosses and the players behind them, against
    the opponent's defensive actions in the matching channel of its own defensive third; plus pressing vs build-up."""
    att = {t: defaultdict(lambda: {"actions": 0, "completed": 0, "xg": 0.0, "shots": 0, "crosses": 0, "players": Counter()}) for t in (home, away)}
    dfn = {t: defaultdict(lambda: {"actions": 0, "players": Counter()}) for t in (home, away)}
    press = {t: {"opp_build_passes": 0, "def_actions_high": 0, "high_recoveries": 0, "pressures_high": 0} for t in (home, away)}
    build = {t: {"own_half_passes_pressed": 0, "own_half_passes_pressed_ok": 0} for t in (home, away)}
    for e in events:
        if e.get("period") not in (1, 2):
            continue
        t = e["type"]["name"]
        team = (e.get("team") or {}).get("name")
        if team not in att:
            continue
        opp = away if team == home else home
        pl = (e.get("player") or {}).get("name")
        if ((e.get("position") or {}).get("name")) == "Goalkeeper":
            pl = None                                       # long goal kicks are not wing play
        loc = e.get("location")
        if not loc:
            continue
        x, y = loc[0], loc[1]
        if t == "Pass":
            ps = e["pass"]
            end = ps.get("end_location") or loc
            ok = ps.get("outcome") is None
            if end[0] >= 80 and (x < 80 or ps.get("cross")):
                a = att[team][_channel(end[1] if not ps.get("cross") else y)]
                a["actions"] += 1
                a["completed"] += ok
                a["crosses"] += bool(ps.get("cross"))
                if pl:
                    a["players"][pl] += 1
            if x <= 72:                                     # build-up in own 60%: counted for the opponent's PPDA
                press[opp]["opp_build_passes"] += 1
            if x < 60 and e.get("under_pressure"):
                build[team]["own_half_passes_pressed"] += 1
                build[team]["own_half_passes_pressed_ok"] += ok
        elif t == "Carry":
            end = e["carry"].get("end_location") or loc
            if end[0] >= 80 and x < 80:
                a = att[team][_channel(end[1])]
                a["actions"] += 1
                a["completed"] += 1
                if pl:
                    a["players"][pl] += 1
        elif t == "Dribble" and x >= 80:
            a = att[team][_channel(y)]
            a["actions"] += 1
            a["completed"] += ((e["dribble"].get("outcome") or {}).get("name") == "Complete")
            if pl:
                a["players"][pl] += 1
        elif t == "Shot":
            a = att[team][_channel(y)]
            a["shots"] += 1
            a["xg"] += e["shot"].get("statsbomb_xg") or 0.0
        defensive = t in ("Interception", "Clearance", "Block", "Ball Recovery") or \
            (t == "Duel" and ((e.get("duel") or {}).get("type") or {}).get("name") == "Tackle")
        if (defensive or t == "Pressure") and x <= 40:
            d = dfn[team][_channel(y)]
            d["actions"] += 1
            if pl:
                d["players"][pl] += 1
        if (defensive or t == "Foul Committed") and x >= 48:
            press[team]["def_actions_high"] += 1
        if t == "Ball Recovery" and x >= 80:
            press[team]["high_recoveries"] += 1
        if t == "Pressure" and x >= 80:
            press[team]["pressures_high"] += 1
    flanks = []
    for team in (home, away):
        opp = away if team == home else home
        for ch in ("left", "centre", "right"):
            a = att[team][ch]
            d = dfn[opp][MIRROR[ch]]
            flanks.append({
                "team_side": "home" if team == home else "away", "channel": ch, "channel_ar": CHANNEL_AR[ch],
                "attack_actions": a["actions"], "attack_completed": a["completed"], "crosses": a["crosses"],
                "shots": a["shots"], "xg": round(a["xg"], 2),
                "attackers": [name(p) for p, _ in a["players"].most_common(2)],
                "opp_channel_ar": CHANNEL_AR[MIRROR[ch]], "defend_actions": d["actions"],
                "defenders": [name(p) for p, _ in d["players"].most_common(2)]})
    pressing = []
    for team in (home, away):
        opp = away if team == home else home
        p, b = press[team], build[opp]
        pressing.append({
            "team_side": "home" if team == home else "away",
            "ppda": round(p["opp_build_passes"] / p["def_actions_high"], 1) if p["def_actions_high"] else None,
            "high_recoveries": p["high_recoveries"], "pressures_high": p["pressures_high"],
            "opp_pressed_passes": b["own_half_passes_pressed"],
            "opp_pressed_pass_pct": round(100 * b["own_half_passes_pressed_ok"] / b["own_half_passes_pressed"], 0) if b["own_half_passes_pressed"] else None})
    return {"flanks": flanks, "pressing": pressing,
            "note_ar": "القنوات من منظور الفريق المهاجم (يسار/عمق/يمين)، ودفاع الخصم بالقناة المقابلة بثلثه الدفاعي. "
                       "PPDA = تمريرات الخصم ببنائه مقابل كل فعل دفاعي بالضغط العالي (أقل = ضغط أعلى)."}
