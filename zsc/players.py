"""Player statistics from StatsBomb event data: per match, per season, per 90 minutes, position-fair ratings.

Two ratings, both the project's own (StatsBomb open data has no player ratings):
    season rating (0-10)  10 x the weighted average of the player's percentiles among players of the same position
                          group (per 90 minutes, at least MIN_MINUTES); fair across positions by construction
    match rating (3-10)   6.5 + 1.5 x the weighted z-score of the match's per-90 numbers against the same position
                          group's distribution over the season; shrunk to 6.5 for short appearances
Version 1 of the match rating (zsc/events.py player_table) added attacking outputs to a base of 6 and gave
defenders and goalkeepers little to earn; scripts/sb_players_1516.py measures that bias before and after.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

MIN_MINUTES = 900
VERSION = "player-rating-2.0"

GROUPS = {
    "GK": ["Goalkeeper"],
    "CB": ["Center Back", "Left Center Back", "Right Center Back"],
    "FB": ["Left Back", "Right Back", "Left Wing Back", "Right Wing Back"],
    "DM": ["Center Defensive Midfield", "Left Defensive Midfield", "Right Defensive Midfield"],
    "CM": ["Center Midfield", "Left Center Midfield", "Right Center Midfield", "Left Midfield", "Right Midfield"],
    "AM": ["Center Attacking Midfield", "Left Attacking Midfield", "Right Attacking Midfield", "Left Wing", "Right Wing"],
    "FW": ["Center Forward", "Left Center Forward", "Right Center Forward", "Secondary Striker"],
}
GROUP_OF = {p: g for g, ps in GROUPS.items() for p in ps}
GROUP_AR = {"GK": "حارس", "CB": "قلب دفاع", "FB": "ظهير", "DM": "وسط دفاعي", "CM": "وسط", "AM": "صانع لعب / جناح", "FW": "مهاجم"}

# per-90 metrics used by the ratings, with weights per position group (each row sums to 1)
WEIGHTS = {
    "FW": {"np_goals": .2, "np_xg": .25, "xa": .1, "key_passes": .1, "touches_box": .1, "dribbles": .1, "pressures_high": .1, "shots": .05},
    "AM": {"xa": .2, "key_passes": .15, "np_xg": .15, "dribbles": .15, "prog_carries": .1, "prog_passes": .1, "np_goals": .1, "pressures_high": .05},
    "CM": {"prog_passes": .2, "pass_pct": .1, "xa": .1, "key_passes": .1, "tackles_int": .15, "recoveries": .15, "pressures": .1, "prog_carries": .1},
    "DM": {"tackles_int": .25, "recoveries": .2, "prog_passes": .15, "pass_pct": .15, "pressures": .15, "blocks": .1},
    "FB": {"tackles_int": .2, "prog_passes": .15, "prog_carries": .15, "xa": .15, "crosses": .1, "recoveries": .1, "pressures": .1, "dribbles": .05},
    "CB": {"tackles_int": .2, "clearances": .15, "aerials_won": .15, "blocks": .1, "pass_pct": .15, "prog_passes": .15, "recoveries": .1},
    "GK": {"save_pct": .5, "goals_prevented": .5},
}
METRIC_AR = {
    "np_goals": "أهداف بدون جزاء", "np_xg": "xG بدون جزاء", "xa": "xA (صناعة متوقعة)", "assists": "صناعة",
    "key_passes": "تمريرات مفتاحية", "shots": "تسديدات", "touches_box": "لمسات بمنطقة الجزاء",
    "dribbles": "مراوغات ناجحة", "prog_passes": "تمريرات تقدمية", "prog_carries": "حمل كرة تقدمي",
    "pass_pct": "دقة التمرير ٪", "crosses": "عرضيات ناجحة", "tackles_int": "افتكاك + قطع", "recoveries": "استرجاع",
    "pressures": "ضغط", "pressures_high": "ضغط بالثلث الهجومي", "blocks": "صد", "clearances": "إبعاد",
    "aerials_won": "هوائيات مكسوبة", "save_pct": "نسبة التصديات ٪", "goals_prevented": "أهداف منعها (حسب xG)",
}
ON_TARGET = {"Goal", "Saved", "Saved To Post", "Saved to Post"}
TOUCH_TYPES = {"Pass", "Carry", "Dribble", "Shot", "Ball Receipt*", "Clearance", "Interception", "Ball Recovery",
               "Block", "Miscontrol", "Dispossessed", "Goal Keeper", "Duel", "Foul Won", "Shield"}


def _dist(x, y):
    return float(np.hypot(120.0 - x, 40.0 - y))


def _progressive(x0, y0, x1, y1) -> bool:
    d0, d1 = _dist(x0, y0), _dist(x1, y1)
    return (d0 - d1) >= max(10.0, 0.25 * d0) and x1 >= 40


def _in_box(x, y) -> bool:
    return x >= 102 and 18 <= y <= 62


def match_rows(events: list, home: str, away: str, nick: dict | None = None):
    """Per player-match counts and per team-half counts for one match (raw StatsBomb event list)."""
    nick = nick or {}
    end = {1: 45.0, 2: 90.0}
    for e in events:
        if e.get("period") in (1, 2):
            t = e["minute"] + e["second"] / 60.0
            end[e["period"]] = max(end[e["period"]], t)
    full_end = end[2]
    on = {}                                     # player -> (team, start, end)
    pos_count = defaultdict(Counter)
    for e in events:
        if e["type"]["name"] == "Starting XI":
            for p in e["tactics"]["lineup"]:
                on[p["player"]["name"]] = [e["team"]["name"], 0.0, full_end]
                pos_count[p["player"]["name"]][p["position"]["name"]] += 5
    xg_by_key = {}
    for e in events:
        if e["type"]["name"] == "Shot" and e["shot"].get("key_pass_id"):
            xg_by_key[e["shot"]["key_pass_id"]] = e["shot"].get("statsbomb_xg") or 0.0
    stats = defaultdict(lambda: defaultdict(float))
    halves = defaultdict(lambda: defaultdict(float))
    gk_faced = defaultdict(lambda: defaultdict(float))
    for e in events:
        t = e["type"]["name"]
        per = e.get("period")
        if per not in (1, 2):
            continue
        team = (e.get("team") or {}).get("name")
        pl = (e.get("player") or {}).get("name")
        tm = e["minute"] + e["second"] / 60.0
        if t == "Substitution" and pl:
            if pl in on:
                on[pl][2] = tm
            rep = e["substitution"]["replacement"]["name"]
            on[rep] = [team, tm, full_end]
            if e.get("position"):
                pos_count[rep][e["position"]["name"]] += 1
            continue
        card = ((e.get("foul_committed") or {}).get("card") or {}).get("name") or \
            ((e.get("bad_behaviour") or {}).get("card") or {}).get("name")
        if card in ("Red Card", "Second Yellow") and pl in on:
            on[pl][2] = min(on[pl][2], tm)
        if not pl:
            continue
        s = stats[pl]
        if e.get("position"):
            pos_count[pl][e["position"]["name"]] += 1
        loc = e.get("location") or [np.nan, np.nan]
        x, y = loc[0], loc[1]
        if t in TOUCH_TYPES:
            s["touches"] += 1
            if x == x and _in_box(x, y):
                s["touches_box"] += 1
        if t == "Shot":
            sh = e["shot"]
            xg = sh.get("statsbomb_xg") or 0.0
            pen = (sh.get("type") or {}).get("name") == "Penalty"
            goal = (sh.get("outcome") or {}).get("name") == "Goal"
            ont = (sh.get("outcome") or {}).get("name") in ON_TARGET
            s["shots"] += 1
            s["sot"] += ont
            if pen:
                s["pens"] += goal
            else:
                s["np_goals"] += goal
                s["np_xg"] += xg
            hv = halves[(team, per)]
            hv["shots"] += 1
            hv["sot"] += ont
            hv["xg"] += xg
            hv["goals"] += goal
            if ont:
                opp = away if team == home else home
                gk_faced[opp]["sot"] += 1
                gk_faced[opp]["xg"] += xg
                gk_faced[opp]["goals"] += goal
        elif t == "Own Goal For":
            halves[(team, per)]["goals"] += 1
        elif t == "Pass":
            ps = e["pass"]
            done = ps.get("outcome") is None
            ex, ey = (ps.get("end_location") or [np.nan, np.nan])[:2]
            s["passes"] += 1
            s["passes_cmp"] += done
            if ps.get("goal_assist"):
                s["assists"] += 1
            if ps.get("goal_assist") or ps.get("shot_assist"):
                s["key_passes"] += 1
                s["xa"] += xg_by_key.get(e["id"], 0.0)
            if done and x == x and ex == ex:
                if _progressive(x, y, ex, ey):
                    s["prog_passes"] += 1
                if _in_box(ex, ey) and not _in_box(x, y):
                    s["box_passes"] += 1
                if ps.get("cross"):
                    s["crosses"] += 1
            if ps.get("aerial_won"):
                s["aerials_won"] += 1
        elif t == "Carry":
            ex, ey = (e["carry"].get("end_location") or [np.nan, np.nan])[:2]
            if x == x and ex == ex and _progressive(x, y, ex, ey):
                s["prog_carries"] += 1
        elif t == "Dribble":
            s["dribbles_att"] += 1
            s["dribbles"] += ((e["dribble"].get("outcome") or {}).get("name") == "Complete")
        elif t == "Duel":
            d = e["duel"]
            if (d.get("type") or {}).get("name") == "Tackle" and (d.get("outcome") or {}).get("name") in ("Won", "Success", "Success In Play", "Success Out"):
                s["tackles"] += 1
            if (d.get("type") or {}).get("name") == "Aerial Lost":
                s["aerials_lost"] += 1
        elif t == "Interception":
            if ((e.get("interception") or {}).get("outcome") or {}).get("name") in ("Won", "Success", "Success In Play", "Success Out"):
                s["interceptions"] += 1
        elif t == "Block":
            s["blocks"] += 1
        elif t == "Clearance":
            s["clearances"] += 1
            if (e.get("clearance") or {}).get("aerial_won"):
                s["aerials_won"] += 1
        elif t == "Ball Recovery":
            if not (e.get("ball_recovery") or {}).get("recovery_failure"):
                s["recoveries"] += 1
                if x == x and x >= 80:
                    s["recoveries_high"] += 1
        elif t == "Pressure":
            s["pressures"] += 1
            if x == x and x >= 80:
                s["pressures_high"] += 1
        elif t == "Foul Committed":
            s["fouls"] += 1
        elif t in ("Dispossessed", "Miscontrol"):
            s["lost"] += 1
        elif t == "Goal Keeper":
            gtype = ((e.get("goalkeeper") or {}).get("type") or {}).get("name", "")
            if gtype in ("Shot Saved", "Shot Saved To Post", "Shot Saved Off Target", "Penalty Saved", "Save"):
                s["saves"] += 1
        if card == "Yellow Card":
            s["yellow"] += 1
        elif card in ("Red Card", "Second Yellow"):
            s["red"] += 1
    rows = []
    for p, (team, a, b) in on.items():
        mins = max(0.0, min(b, full_end) - a)
        if mins <= 0:
            continue
        s = stats.get(p, {})
        pos = pos_count[p].most_common(1)[0][0] if pos_count[p] else ""
        row = {"player": p, "nickname": nick.get(p) or p, "team": team, "home": team == home, "minutes": mins,
               "position": pos, "group": GROUP_OF.get(pos, "CM")}
        for k in ("np_goals", "pens", "np_xg", "shots", "sot", "assists", "xa", "key_passes", "passes", "passes_cmp",
                  "prog_passes", "box_passes", "crosses", "prog_carries", "dribbles", "dribbles_att", "touches",
                  "touches_box", "tackles", "interceptions", "blocks", "clearances", "aerials_won", "aerials_lost",
                  "recoveries", "recoveries_high", "pressures", "pressures_high", "fouls", "lost", "saves", "yellow", "red"):
            row[k] = float(s.get(k, 0.0))
        if row["group"] == "GK":
            f = gk_faced.get(team, {})
            # shots faced while on the pitch: approximated by the whole match (goalkeepers rarely change)
            row["gk_sot_faced"], row["gk_xg_faced"], row["gk_goals"] = f.get("sot", 0.0), f.get("xg", 0.0), f.get("goals", 0.0)
        rows.append(row)
    half_rows = [{"team": tm, "period": per, **{k: float(v) for k, v in d.items()}} for (tm, per), d in halves.items()]
    return rows, half_rows


def per90(df: pd.DataFrame) -> pd.DataFrame:
    """Per-90 metrics used by the ratings (df: summed counts with a minutes column)."""
    m = df["minutes"].clip(lower=1) / 90.0
    out = pd.DataFrame(index=df.index)
    for k in ("np_goals", "np_xg", "xa", "assists", "key_passes", "shots", "touches_box", "dribbles", "prog_passes",
              "prog_carries", "crosses", "recoveries", "pressures", "pressures_high", "blocks", "clearances", "aerials_won"):
        out[k] = df[k] / m
    out["tackles_int"] = (df["tackles"] + df["interceptions"]) / m
    out["pass_pct"] = 100.0 * df["passes_cmp"] / df["passes"].replace(0, np.nan)
    if "gk_sot_faced" in df:
        sf = df["gk_sot_faced"].fillna(0)
        out["save_pct"] = 100.0 * (sf - df["gk_goals"].fillna(0)) / sf.replace(0, np.nan)
        out["goals_prevented"] = (df["gk_xg_faced"].fillna(0) - df["gk_goals"].fillna(0)) / m
    return out


def season_table(pm: pd.DataFrame) -> pd.DataFrame:
    """Sum player-match rows into one row per player; the position group is the one with the most minutes."""
    num = [c for c in pm.columns if pm[c].dtype.kind in "fi" and c not in ("home",)]
    agg = pm.groupby("player")[num].sum()
    agg["matches"] = pm.groupby("player").size()
    grp = pm.groupby(["player", "group"])["minutes"].sum().reset_index().sort_values("minutes").groupby("player").last()["group"]
    posn = pm.groupby(["player", "position"])["minutes"].sum().reset_index().sort_values("minutes").groupby("player").last()["position"]
    team = pm.groupby(["player", "team"])["minutes"].sum().reset_index().sort_values("minutes").groupby("player").last()["team"]
    nick = pm.groupby("player")["nickname"].first()
    agg["group"], agg["position"], agg["team"], agg["nickname"] = grp, posn, team, nick
    return agg.reset_index()


def season_ratings(season: pd.DataFrame) -> pd.DataFrame:
    """Percentiles within the position group (players with at least MIN_MINUTES) and the weighted 0-10 rating."""
    p9 = per90(season)
    out = season.join(p9.add_prefix("p90_"))
    out["rating"] = np.nan
    for g, w in WEIGHTS.items():
        sel = (out["group"] == g) & (out["minutes"] >= MIN_MINUTES)
        if sel.sum() < 5:
            continue
        score = 0.0
        for k, wt in w.items():
            col = out.loc[sel, "p90_" + k]
            pctl = col.rank(pct=True, method="average").fillna(0.5)
            out.loc[sel, "pct_" + k] = pctl
            score = score + wt * pctl
        out.loc[sel, "rating"] = (10 * score).round(1)
    return out


def match_rating(pm: pd.DataFrame, ref: pd.DataFrame) -> pd.Series:
    """Position-relative match rating (version 2); ref = player-match rows of the season (each group's scale).

    The weighted z-score of a match is turned into its rank among the same position group's matches of the season
    and mapped onto one common scale (6.5 = the group's median, the top 1% above 9.3). Every position therefore has
    the same distribution of ratings: a great match by a centre-back scores as high as a great match by a winger.
    Appearances shorter than 60 minutes are pulled towards 6.5 in proportion (per-90 numbers of a cameo are noisy)."""
    from scipy.stats import norm
    base = ref[ref["minutes"] >= 45]
    rp9 = per90(base)
    p9 = per90(pm)
    out = pd.Series(6.5, index=pm.index)
    for g, w in WEIGHTS.items():
        sel = pm["group"] == g
        if not sel.any():
            continue
        rg = rp9[base["group"] == g]
        z = pd.Series(0.0, index=pm.index[sel])
        zr = pd.Series(0.0, index=rg.index)
        for k, wt in w.items():
            mu, sd = rg[k].mean(), rg[k].std()
            if not (sd and sd == sd):
                continue
            z = z + wt * (p9.loc[sel, k].fillna(mu) - mu) / sd
            zr = zr + wt * (rg[k].fillna(mu) - mu) / sd
        ref_sorted = np.sort(zr.to_numpy())
        q = (np.searchsorted(ref_sorted, z.to_numpy(), side="right") - 0.5) / max(len(ref_sorted), 1)
        q = np.clip(q, 0.002, 0.998)
        r = 6.5 + 1.2 * norm.ppf(q)
        shrink = np.minimum(1.0, pm.loc[sel, "minutes"].to_numpy() / 60.0)   # short appearances stay near 6.5
        out.loc[sel] = np.clip(6.5 + (r - 6.5) * shrink, 3.0, 10.0)
    return out.round(1)


def match_rating_v1(pm: pd.DataFrame) -> pd.Series:
    """The previous formula (zsc/events.py player_table), recomputed from the same counts for comparison."""
    r = (6.0 + 1.0 * (pm["np_goals"] + pm["pens"]) + 0.7 * pm["assists"] + 1.2 * pm["np_xg"] + 1.2 * pm["xa"]
         + 0.06 * (pm["prog_passes"] + pm["prog_carries"]) + 0.15 * pm["key_passes"] + 0.1 * pm["dribbles"]
         + 0.1 * (pm["tackles"] + pm["interceptions"]) + 0.02 * pm["pressures"] + 0.04 * pm["recoveries"]
         - 0.08 * pm["lost"] - 0.3 * pm["yellow"] - 1.5 * pm["red"])
    r = np.where(pm["minutes"] >= 15, r, 6.0 + (r - 6.0) * pm["minutes"] / 15)
    return pd.Series(np.clip(r, 3.0, 10.0), index=pm.index).round(1)


def to_json(players: pd.DataFrame, team_ids: dict, label: str) -> dict:
    keep = players[players["minutes"] >= 270].copy()
    metrics = sorted({k for w in WEIGHTS.values() for k in w} | {"assists", "shots"})
    rows = []
    for r in keep.itertuples():
        d = r._asdict()
        rows.append({
            "player_id": r.player,
            "name": r.nickname, "full_name": r.player, "team": team_ids.get(r.team, r.team), "team_name": r.team,
            "group": r.group, "group_ar": GROUP_AR.get(r.group, r.group), "position": r.position,
            "minutes": int(round(r.minutes)), "matches": int(r.matches),
            "np_goals": int(r.np_goals), "pens": int(r.pens), "assists": int(r.assists),
            "np_xg": round(r.np_xg, 2), "xa": round(r.xa, 2),
            "per90": {k: (None if pd.isna(d.get("p90_" + k)) else round(float(d.get("p90_" + k)), 3)) for k in metrics if ("p90_" + k) in d},
            "pct": {k: round(float(d["pct_" + k]), 3) for k in metrics if ("pct_" + k) in d and not pd.isna(d["pct_" + k])},
            "rating": None if pd.isna(r.rating) else float(r.rating),
            "enough_minutes": bool(r.minutes >= MIN_MINUTES),
        })
    return {"season_label": label, "version": VERSION, "min_minutes": MIN_MINUTES,
            "source": "StatsBomb Open Data (بيانات: StatsBomb)", "groups": GROUP_AR, "weights": WEIGHTS,
            "metrics_ar": METRIC_AR, "players": rows}


def write_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
