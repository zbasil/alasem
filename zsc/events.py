"""Deep match analysis on event data (StatsBomb open-data format).

StatsBomb coordinates: pitch 120 x 80 yards, every event recorded from the
acting team's point of view, attacking from left (x=0) to right (x=120).

Definitions used (all documented on the page):
    on target       shot outcome Goal, Saved or Saved to Post
    big chance      shot with xG >= 0.30
    progressive     completed pass or carry that brings the ball at least 25%
                    closer to the opponent's goal (and at least 10 yards), ending
                    outside the team's own defensive third
    final third     x >= 80; box: x >= 102 and 18 <= y <= 62
    field tilt      a team's share of all completed passes made in the final third
    PPDA            opponent passes in their own 60% of the pitch divided by the
                    pressing team's tackles, interceptions and fouls in its
                    attacking 60% (lower = more intense pressing)
"""

from __future__ import annotations

import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd

ON_TARGET = {"Goal", "Saved", "Saved to Post"}
TOUCH_TYPES = {"Pass", "Ball Receipt*", "Carry", "Shot", "Dribble", "Duel", "Interception", "Ball Recovery",
               "Clearance", "Block", "Miscontrol", "Dispossessed", "Foul Won", "Goal Keeper", "50/50", "Shield"}

# Arabic short names for the players of the archive matches (fallback: StatsBomb nickname)
PLAYERS_AR = {
    "Lionel Andrés Messi Cuccittini": "ميسي", "Xavier Hernández Creus": "تشافي", "Andrés Iniesta Luján": "إنييستا",
    "David Villa Sánchez": "دافيد فيا", "Pedro Eliezer Rodríguez Ledesma": "بيدرو", "Sergio Busquets i Burgos": "بوسكيتس",
    "Gerard Piqué Bernabéu": "بيكيه", "Carles Puyol i Saforcada": "بويول", "Eric-Sylvain Bilal Abidal": "أبيدال",
    "Daniel Alves da Silva": "داني ألفيش", "Víctor Valdés Arribas": "فالديس", "Seydou Kéita": "كيتا",
    "Bojan Krkíc Pérez": "بويان", "Jeffren Isaac Suárez Bermúdez": "جيفرين", "Maxwell Scherrer Cabelino Andrade": "ماكسويل",
    "Adriano Correia Claro": "أدريانو", "Javier Alejandro Mascherano": "ماسكيرانو", "José Manuel Pinto Colorado": "بينتو",
    "Cristiano Ronaldo dos Santos Aveiro": "رونالدو", "Ángel Fabián Di María Hernández": "دي ماريا", "Mesut Özil": "أوزيل",
    "Karim Benzema": "بنزيما", "Sami Khedira": "خضيرة", "Xabier Alonso Olano": "تشابي ألونسو", "Sergio Ramos García": "راموس",
    "Kléper Laveran Lima Ferreira": "بيبي", "Ricardo Alberto Silveira de Carvalho": "كارفاليو",
    "Marcelo Vieira da Silva Júnior": "مارسيلو", "Álvaro Arbeloa Coca": "أربيلوا", "Iker Casillas Fernández": "كاسياس",
    "Lassana Diarra": "لاس ديارا", "Gonzalo Gerardo Higuaín": "هيغواين", "Pedro León Sánchez Gil": "بيدرو ليون",
    "Raúl Albiol i Tortajada": "ألبيول", "Mahamadou Diarra": "محمدو ديارا", "Jerzy Dudek": "دوديك",
    "Danilo Luiz da Silva": "دانيلو", "Jesé Rodríguez Ruiz": "خيسي", "Francisco Román Alarcón Suárez": "إيسكو",
    "Mateo Kovačić": "كوفاتشيتش", "Luka Modrić": "مودريتش", "Raphaël Varane": "فاران", "Carlos Henrique Casimiro": "كاسيميرو",
    "Toni Kroos": "كروس", "Keylor Navas Gamboa": "نافاس", "James David Rodríguez Rubio": "خاميس",
    "Daniel Carvajal Ramos": "كارفاخال", "Gareth Frank Bale": "بيل", "Francisco Casilla Cortés": "كيكو كاسيا",
    "Lucas Vázquez Iglesias": "لوكاس فاسكيز", "José Ignacio Fernández Iglesias": "ناتشو",
    "Sandro Ramírez Castillo": "ساندرو", "Neymar da Silva Santos Junior": "نيمار", "Claudio Andrés Bravo Muñoz": "برافو",
    "Jordi Alba Ramos": "جوردي ألبا", "Luis Alberto Suárez Díaz": "سواريز", "Ivan Rakitić": "راكيتيتش",
    "Thomas Vermaelen": "فيرمالين", "Sergi Roberto Carnicer": "سيرجي روبرتو", "Munir El Haddadi Mohamed": "منير",
    "Jérémy Mathieu": "ماتيو", "Marc-André ter Stegen": "تير شتيغن", "Rafael Alcântara do Nascimento": "رافينيا",
    "Marc Bartra Aregall": "بارترا", "Arda Turan": "أردا توران",
}


def short_name(full: str, nick: dict | None = None) -> str:
    if full in PLAYERS_AR:
        return PLAYERS_AR[full]
    if nick and nick.get(full):
        return nick[full]
    return full.split()[-1] if full else ""


def _get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def load_events(path: str) -> pd.DataFrame:
    if path.endswith(".gz"):
        import gzip
        with gzip.open(path, "rt", encoding="utf-8") as f:
            ev = json.load(f)
    else:
        ev = json.load(open(path, encoding="utf-8"))
    rows = []
    for e in ev:
        t = e["type"]["name"]
        loc = e.get("location") or [np.nan, np.nan]
        end = (_get(e, "pass", "end_location") or _get(e, "carry", "end_location")
               or _get(e, "shot", "end_location") or [np.nan, np.nan])
        if t == "Pass":
            outcome = _get(e, "pass", "outcome", "name", default="Complete")
        elif t == "Shot":
            outcome = _get(e, "shot", "outcome", "name")
        elif t == "Dribble":
            outcome = _get(e, "dribble", "outcome", "name")
        elif t == "Duel":
            outcome = _get(e, "duel", "outcome", "name")
        else:
            outcome = None
        card = _get(e, "foul_committed", "card", "name") or _get(e, "bad_behaviour", "card", "name")
        rows.append({
            "id": e["id"], "index": e["index"], "period": e["period"], "minute": e["minute"], "second": e["second"],
            "type": t, "team": _get(e, "team", "name"), "player": _get(e, "player", "name"),
            "x": loc[0], "y": loc[1], "end_x": end[0], "end_y": end[1], "outcome": outcome,
            "xg": _get(e, "shot", "statsbomb_xg"), "shot_type": _get(e, "shot", "type", "name"),
            "key_pass_id": _get(e, "shot", "key_pass_id"),
            "goal_assist": bool(_get(e, "pass", "goal_assist", default=False)),
            "shot_assist": bool(_get(e, "pass", "shot_assist", default=False)),
            "pass_type": _get(e, "pass", "type", "name"), "recipient": _get(e, "pass", "recipient", "name"),
            "duel_type": _get(e, "duel", "type", "name"), "play_pattern": _get(e, "play_pattern", "name"),
            "card": card, "replacement": _get(e, "substitution", "replacement", "name"),
            "possession_team": _get(e, "possession_team", "name"), "possession": e.get("possession"),
            "tactics": e.get("tactics"),
        })
    df = pd.DataFrame(rows)
    df["t"] = df["minute"] + df["second"] / 60.0
    return df[df["period"] <= 4].reset_index(drop=True)


def teams_of(df: pd.DataFrame, home_first: tuple[str, str] | None = None) -> tuple[str, str]:
    xi = df[df["type"] == "Starting XI"]["team"].tolist()
    if home_first:
        return home_first
    return xi[0], xi[1]


def goals(df: pd.DataFrame) -> list[dict]:
    """Goals in time order with the credited team (own goals included)."""
    out = []
    for _, r in df[(df["type"] == "Shot") & (df["outcome"] == "Goal")].iterrows():
        out.append({"period": r["period"], "minute": r["minute"], "t": r["t"], "team": r["team"],
                    "player": r["player"], "own_goal": False, "xg": r["xg"]})
    for _, r in df[df["type"] == "Own Goal For"].iterrows():
        out.append({"period": r["period"], "minute": r["minute"], "t": r["t"], "team": r["team"],
                    "player": None, "own_goal": True, "xg": None})
    return sorted(out, key=lambda g: (g["period"], g["t"]))


def red_cards(df: pd.DataFrame) -> list[dict]:
    r = df[df["card"].isin(["Red Card", "Second Yellow"])]
    return [{"period": a.period, "minute": a.minute, "team": a.team, "player": a.player} for a in r.itertuples()]


def _dist_goal(x, y):
    return np.sqrt((120.0 - x) ** 2 + (40.0 - y) ** 2)


def progressive_mask(d: pd.DataFrame) -> pd.Series:
    """Completed passes / carries that bring the ball much closer to goal."""
    ok = ((d["type"] == "Pass") & (d["outcome"] == "Complete")) | (d["type"] == "Carry")
    d0, d1 = _dist_goal(d["x"], d["y"]), _dist_goal(d["end_x"], d["end_y"])
    gain = d0 - d1
    return ok & (gain >= np.maximum(10.0, 0.25 * d0)) & (d["end_x"] >= 40)


def in_box(x, y):
    return (x >= 102) & (y >= 18) & (y <= 62)


def team_metrics(df: pd.DataFrame, team: str, opp: str, periods=(1, 2)) -> dict:
    d = df[df["period"].isin(periods)]
    me, op = d[d["team"] == team], d[d["team"] == opp]
    passes = me[me["type"] == "Pass"]
    op_passes = op[op["type"] == "Pass"]
    shots = me[me["type"] == "Shot"]
    op_shots = op[op["type"] == "Shot"]
    comp = passes[passes["outcome"] == "Complete"]
    gl = [g for g in goals(df) if g["period"] in periods]
    g_for = sum(1 for g in gl if g["team"] == team)
    g_against = sum(1 for g in gl if g["team"] == opp)
    ft_me = ((comp["x"] >= 80)).sum()
    ft_op = ((op_passes["outcome"] == "Complete") & (op_passes["x"] >= 80)).sum()
    # PPDA: opponent passes in their own 60% (their x <= 72) / my defensive actions in my attacking 60% (x >= 48)
    op_build = (op_passes["x"] <= 72).sum()
    def_act = me[((me["type"] == "Duel") & (me["duel_type"] == "Tackle")) | (me["type"] == "Interception")
                 | (me["type"] == "Foul Committed")]
    def_act_high = (def_act["x"] >= 48).sum()
    prog = progressive_mask(me)
    end_box = in_box(me["end_x"], me["end_y"]) & ~in_box(me["x"], me["y"])
    box_entries = (((me["type"] == "Pass") & (me["outcome"] == "Complete")) | (me["type"] == "Carry")) & end_box
    xg = float(shots["xg"].fillna(0).sum())
    np_xg = float(shots.loc[shots["shot_type"] != "Penalty", "xg"].fillna(0).sum())
    sp_xg = float(shots.loc[shots["play_pattern"].isin(["From Corner", "From Free Kick", "From Throw In"])
                            | shots["shot_type"].isin(["Free Kick", "Corner", "Penalty"]), "xg"].fillna(0).sum())
    n_all_passes = len(passes) + len(op_passes)
    return {
        "goals": g_for, "goals_against": g_against,
        "possession": 100.0 * len(passes) / n_all_passes if n_all_passes else 50.0,
        "passes": int(len(passes)), "pass_pct": 100.0 * len(comp) / len(passes) if len(passes) else 0.0,
        "shots": int(len(shots)), "on_target": int(shots["outcome"].isin(ON_TARGET).sum()),
        "xg": xg, "np_xg": np_xg, "set_piece_xg": sp_xg,
        "big_chances": int((shots["xg"].fillna(0) >= 0.30).sum()),
        "xg_against": float(op_shots["xg"].fillna(0).sum()),
        "big_chances_against": int((op_shots["xg"].fillna(0) >= 0.30).sum()),
        "shots_against": int(len(op_shots)),
        "progressive": int(prog.sum()),
        "final_third_passes": int(ft_me),
        "field_tilt": 100.0 * ft_me / (ft_me + ft_op) if (ft_me + ft_op) else 50.0,
        "box_entries": int(box_entries.sum()),
        "ppda": float(op_build / def_act_high) if def_act_high else float("nan"),
        "pressures": int((me["type"] == "Pressure").sum()),
        "high_pressures": int(((me["type"] == "Pressure") & (me["x"] >= 80)).sum()),
        "high_recoveries": int(((me["type"] == "Ball Recovery") & (me["x"] >= 80)).sum()),
        "tackles_int": int(len(def_act) - (def_act["type"] == "Foul Committed").sum()),
        "dribbles": int(((me["type"] == "Dribble") & (me["outcome"] == "Complete")).sum()),
        "lost_ball": int(me["type"].isin(["Dispossessed", "Miscontrol"]).sum()),
        "corners": int(((me["type"] == "Pass") & (me["pass_type"] == "Corner")).sum()),
        "fouls": int((me["type"] == "Foul Committed").sum()),
        "yellow": int(me["card"].isin(["Yellow Card"]).sum()),
        "red": int(me["card"].isin(["Red Card", "Second Yellow"]).sum()),
    }


def shots_table(df, home, away):
    """Shots in display coordinates: home attacks right, away attacks left."""
    s = df[df["type"] == "Shot"].copy()
    flip = s["team"] == away
    s["dx"] = np.where(flip, 120 - s["x"], s["x"])
    s["dy"] = np.where(flip, 80 - s["y"], s["y"])
    s["side"] = np.where(flip, "away", "home")
    s["is_goal"] = (s["outcome"] == "Goal").astype(int)
    return s


def touches(df, team):
    d = df[(df["team"] == team) & df["type"].isin(TOUCH_TYPES) & df["x"].notna()]
    return d


def substitutions(df, team) -> list[dict]:
    s = df[(df["team"] == team) & (df["type"] == "Substitution")]
    return [{"t": float(r.t) + (45 if r.period == 2 and r.minute < 45 else 0), "minute": r.minute, "off": r.player,
             "on": r.replacement} for r in s.itertuples()]


def starters(df, team) -> list[dict]:
    r = df[(df["team"] == team) & (df["type"] == "Starting XI")]
    if r.empty:
        return []
    lineup = r.iloc[0]["tactics"]["lineup"]
    return [{"player": p["player"]["name"], "number": p.get("jersey_number"),
             "position": p["position"]["name"]} for p in lineup]


def pass_network(df, team, min_count=3):
    """Starting XI until the team's first substitution: average positions and pass links."""
    subs = df[(df["team"] == team) & (df["type"] == "Substitution")]
    cutoff = (subs["period"].min(), subs.loc[subs["period"] == subs["period"].min(), "t"].min()) if len(subs) else (9, 999)
    xi = {p["player"]: p for p in starters(df, team)}
    d = df[(df["team"] == team) & (df["type"] == "Pass") & (df["outcome"] == "Complete")]
    d = d[(d["period"] < cutoff[0]) | ((d["period"] == cutoff[0]) & (d["t"] < cutoff[1]))]
    d = d[d["player"].isin(xi) & d["recipient"].isin(xi)]
    pos = defaultdict(list)
    for r in d.itertuples():
        pos[r.player].append((r.x, r.y))
        pos[r.recipient].append((r.end_x, r.end_y))
    nodes = []
    for p, pts in pos.items():
        a = np.array(pts)
        nodes.append({"player": p, "x": float(a[:, 0].mean()), "y": float(a[:, 1].mean()),
                      "touches": int(len(pts)), "number": xi[p]["number"]})
    pair = d.groupby(["player", "recipient"]).size().reset_index(name="n")
    pair["a"] = pair[["player", "recipient"]].min(axis=1)
    pair["b"] = pair[["player", "recipient"]].max(axis=1)
    edges = pair.groupby(["a", "b"])["n"].sum().reset_index()
    edges = edges[edges["n"] >= min_count]
    minute = None if cutoff[0] == 9 else int(cutoff[1])
    return pd.DataFrame(nodes), edges, minute


def xg_timeline(df, home, away, end=95):
    s = df[df["type"] == "Shot"]
    rows = []
    for m in range(0, end + 1):
        def upto(team):
            q = s[(s["team"] == team) & (((s["period"] == 1) & (np.minimum(s["minute"], 45) < m))
                                          | ((s["period"] == 2) & (s["minute"] < m)))]
            return float(q["xg"].fillna(0).sum())
        rows.append({"minute": m, "xg_home": upto(home), "xg_away": upto(away)})
    return rows


def player_table(df, team, nick=None) -> pd.DataFrame:
    me = df[df["team"] == team]
    shots = df[df["type"] == "Shot"]
    ks = shots[shots["key_pass_id"].notna()]
    xa_by_pass = ks.groupby("key_pass_id")["xg"].sum()
    xi = [p["player"] for p in starters(df, team)]
    subs = substitutions(df, team)
    end_t = float(df["t"].max())
    on_off = {p: [0.0, end_t] for p in xi}
    for s in subs:
        if s["off"] in on_off:
            on_off[s["off"]][1] = s["t"]
        on_off[s["on"]] = [s["t"], end_t]
    for r in red_cards(df):
        if r["team"] == team and r["player"] in on_off:
            on_off[r["player"]][1] = r["minute"]
    rows = []
    gl = goals(df)
    for p, (a, b) in on_off.items():
        d = me[me["player"] == p]
        passes = d[d["type"] == "Pass"]
        comp = passes[passes["outcome"] == "Complete"]
        sh = d[d["type"] == "Shot"]
        key = passes[passes["shot_assist"] | passes["goal_assist"]]
        xa = float(xa_by_pass.reindex(key["id"]).fillna(0).sum()) if len(key) else 0.0
        g = sum(1 for x in gl if x["player"] == p and not x["own_goal"])
        ast = int(passes["goal_assist"].sum())
        prog = int(progressive_mask(d).sum())
        drib = int(((d["type"] == "Dribble") & (d["outcome"] == "Complete")).sum())
        ti = int((((d["type"] == "Duel") & (d["duel_type"] == "Tackle")) | (d["type"] == "Interception")).sum())
        prs = int((d["type"] == "Pressure").sum())
        rec = int((d["type"] == "Ball Recovery").sum())
        lost = int(d["type"].isin(["Dispossessed", "Miscontrol"]).sum())
        yel = int(d["card"].isin(["Yellow Card"]).sum())
        red = int(d["card"].isin(["Red Card", "Second Yellow"]).sum())
        xg = float(sh["xg"].fillna(0).sum())
        mins = max(0.0, min(b, 95) - a)
        rating = (6.0 + 1.0 * g + 0.7 * ast + 1.2 * xg + 1.2 * xa + 0.06 * prog + 0.15 * len(key) + 0.1 * drib
                  + 0.1 * ti + 0.02 * prs + 0.04 * rec - 0.08 * lost - 0.3 * yel - 1.5 * red)
        rating = float(np.clip(rating if mins >= 15 else 6.0 + (rating - 6.0) * mins / 15, 3.0, 10.0))
        rows.append({"player": p, "name_ar": short_name(p, nick), "minutes": round(mins), "rating": round(rating, 1),
                     "goals": g, "assists": ast, "xg": round(xg, 2), "xa": round(xa, 2), "shots": int(len(sh)),
                     "key_passes": int(len(key)), "progressive": prog, "passes": int(len(passes)),
                     "pass_pct": round(100.0 * len(comp) / len(passes), 0) if len(passes) else 0.0,
                     "dribbles": drib, "tackles_int": ti, "pressures": prs, "recoveries": rec, "lost": lost,
                     "touches": int(len(touches(d, team)))})
    return pd.DataFrame(rows).sort_values("rating", ascending=False).reset_index(drop=True)
