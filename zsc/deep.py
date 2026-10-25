"""Deep match analysis: per-half insights in Arabic and tables for the app."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .events import (goals, load_events, pass_network, player_table, red_cards, shots_table, short_name,
                     team_metrics, touches, xg_timeline)
from .inplay import InPlayModel
from .live import count_ar
from .teams import arabic

PARTS = {"h1": ((1,), "الشوط الأول", 1.0), "h2": ((2,), "الشوط الثاني", 1.0), "full": ((1, 2), "المباراة كاملة", 2.0)}

STATS = [("goals", "الأهداف", 0), ("xg", "الأهداف المتوقعة xG", 2), ("shots", "التسديدات", 0),
         ("on_target", "على المرمى", 0), ("big_chances", "فرص محققة", 0), ("possession", "الاستحواذ ٪", 0),
         ("passes", "التمريرات", 0), ("pass_pct", "دقة التمرير ٪", 0), ("progressive", "حركات تقدمية", 0),
         ("box_entries", "دخول منطقة الجزاء", 0), ("field_tilt", "السيطرة الإقليمية ٪", 0),
         ("ppda", "PPDA (أقل = ضغط أقوى)", 1), ("high_recoveries", "استرجاع بالثلث الأخير", 0),
         ("dribbles", "مراوغات ناجحة", 0), ("corners", "الركنيات", 0), ("fouls", "الأخطاء", 0)]


def _x(v, nd=2):
    return f"{v:.{nd}f}"


def deep_insights(me: dict, op: dict, h: float):
    pos, neg = [], []
    xg, oxg = me["xg"], op["xg"]
    r = (xg + 0.1) / (oxg + 0.1)
    if xg >= 0.8 * h and r >= 2:
        pos.append((2.5 + min(r, 8) / 4, f"صناعة فرص أخطر بكثير: xG {_x(xg)} مقابل {_x(oxg)}"))
    elif xg >= oxg + 0.4 * h:
        pos.append((1.8, f"أفضلية بجودة الفرص: xG {_x(xg)} مقابل {_x(oxg)}"))
    if me["big_chances"] >= 2:
        pos.append((1.6 + me["big_chances"] / 4, f"{count_ar(me['big_chances'], 'فرصة محققة وحدة', 'فرصتين محققتين', 'فرص محققة', 'فرصة محققة')} (xG فوق 0.3)"))
    if me["goals"] - xg >= 0.9:
        pos.append((2.2, f"إنهاء ممتاز: {count_ar(me['goals'], 'هدف', 'هدفين', 'أهداف', 'هدف')} من xG {_x(xg)}"))
    if oxg <= 0.25 * h and me["shots_against"] <= 6 * h:
        pos.append((2.3, f"دفاع محكم: الخصم خلق xG {_x(oxg)} بس"))
    if not np.isnan(me["ppda"]) and me["ppda"] <= 9:
        pos.append((1.5 + (9 - me["ppda"]) / 6, f"ضغط عالي: PPDA {_x(me['ppda'], 1)}"))
    if me["high_recoveries"] >= 4 * h:
        pos.append((1.4, f"استرجاع عالي: {count_ar(me['high_recoveries'], 'كرة', 'كرتين', 'كرات', 'كرة')} بالثلث الأخير"))
    if me["field_tilt"] >= 65:
        pos.append((1.5 + (me["field_tilt"] - 65) / 20, f"سيطرة إقليمية: {me['field_tilt']:.0f}٪ من تمريرات الثلث الأخير"))
    if me["progressive"] >= 15 * h and me["progressive"] >= 1.5 * max(op["progressive"], 1):
        pos.append((1.4, f"تقدم بالكرة: {me['progressive']} حركة تقدمية مقابل {op['progressive']}"))
    if me["box_entries"] >= 8 * h and me["box_entries"] >= 1.8 * max(op["box_entries"], 1):
        pos.append((1.5, f"دخول متكرر لمنطقة الجزاء: {me['box_entries']} مرة مقابل {op['box_entries']}"))
    if me["pass_pct"] >= 88 and me["passes"] >= 200 * h:
        pos.append((1.1, f"تمرير دقيق: {me['pass_pct']:.0f}٪ من {me['passes']} تمريرة"))
    if me["dribbles"] >= 6 * h:
        pos.append((1.0, f"مراوغات ناجحة: {me['dribbles']}"))

    if xg <= 0.25 * h and me["shots"] <= 5 * h:
        neg.append((2.2, f"فرص قليلة: xG {_x(xg)} بس"))
    if me["big_chances_against"] >= 2:
        cnt = count_ar(me['big_chances_against'], 'فرصة محققة وحدة', 'فرصتين محققتين', 'فرص محققة', 'فرصة محققة')
        neg.append((2.0 + me["big_chances_against"] / 4, f"سمح {'بـ' if cnt[0].isdigit() else 'ب'}{cnt}"))
    if xg - me["goals"] >= 1.0:
        neg.append((2.1, f"إهدار: {count_ar(me['goals'], 'هدف واحد', 'هدفين', 'أهداف', 'هدف')} من xG {_x(xg)}"))
    if not np.isnan(me["ppda"]) and me["ppda"] >= 15:
        neg.append((1.3 + (me["ppda"] - 15) / 15, f"ضغط ضعيف: PPDA {_x(me['ppda'], 1)} والخصم يبني بهدوء"))
    if me["field_tilt"] <= 35:
        neg.append((1.5 + (35 - me["field_tilt"]) / 20, f"محصور بنصفه: {me['field_tilt']:.0f}٪ بس من تمريرات الثلث الأخير"))
    if me["pass_pct"] <= 75:
        neg.append((1.3, f"تمرير متقطع: دقة {me['pass_pct']:.0f}٪"))
    if me["lost_ball"] >= 14 * h and me["lost_ball"] >= 0.06 * max(me["passes"], 1):
        neg.append((1.0, f"فقدان الكرة بسهولة: {me['lost_ball']} مرة"))
    if me["possession"] >= 60 and xg < oxg:
        neg.append((1.9, f"استحواذ بلا خطورة: {me['possession']:.0f}٪ من الكرة وxG أقل من الخصم"))
    if me["red"] >= 1:
        neg.append((3.0, "طرد خلاه يلعب بنقص عددي"))
    if me["yellow"] >= 3 * h:
        neg.append((1.0, f"خشونة: {count_ar(me['yellow'], 'إنذار', 'إنذارين', 'إنذارات', 'إنذار')}"))

    def best(lst):
        seen, out = set(), []
        for _, t in sorted(lst, key=lambda x: -x[0]):
            k = t.split(":")[0]
            if k not in seen:
                seen.add(k)
                out.append(t)
        return out[:3]
    return best(pos), best(neg)


def model_events_sb(df, home):
    ev = []
    for g in goals(df):
        m = min(g["minute"], 45) if g["period"] == 1 else g["minute"]
        ev.append({"minute": int(m) + 1, "team": "home" if g["team"] == home else "away", "kind": "goal"})
    for r in red_cards(df):
        m = min(r["minute"], 45) if r["period"] == 1 else r["minute"]
        ev.append({"minute": int(m) + 1, "team": "home" if r["team"] == home else "away", "kind": "red"})
    return ev


def analyze_match(path: str, match_id: str, home: str, away: str, date: str, lam: float, mu: float,
                  model: InPlayModel, source: str = "StatsBomb"):
    df = load_events(path)
    h_ar, a_ar = arabic(home), arabic(away)
    gl = goals(df)
    hg = sum(g["team"] == home for g in gl)
    ag = sum(g["team"] == away for g in gl)
    out = {}

    # stats + insights per part
    stat_rows, ins_rows = [], []
    for part, (periods, label, h) in PARTS.items():
        mh, ma = team_metrics(df, home, away, periods), team_metrics(df, away, home, periods)
        for k, lab, nd in STATS:
            stat_rows.append({"match_id": match_id, "part": part, "part_ar": label, "stat": k, "label_ar": lab,
                              "row_id": f"{match_id}|{part}|{k}",
                              "home": None if np.isnan(mh[k]) else round(float(mh[k]), nd),
                              "away": None if np.isnan(ma[k]) else round(float(ma[k]), nd)})
        for side, me, op, nm in (("home", mh, ma, h_ar), ("away", ma, mh, a_ar)):
            pos, neg = deep_insights(me, op, h)
            for kind, lst in (("pos", pos), ("neg", neg)):
                for i, t in enumerate(lst):
                    ins_rows.append({"match_id": match_id, "part": part, "side": side, "team_ar": nm, "kind": kind,
                                     "rank": i + 1, "text": t, "row_id": f"{match_id}|{part}|{side}|{kind}|{i}"})
        notes = [f"حسب xG ب{label}: {h_ar} {_x(mh['xg'])} - {_x(ma['xg'])} {a_ar}"]
        gh, ga = mh["goals"], ma["goals"]
        if abs(mh["xg"] - ma["xg"]) >= 0.5:
            better = (h_ar, gh - ga) if mh["xg"] > ma["xg"] else (a_ar, ga - gh)
            if better[1] > 0:
                notes.append(f"النتيجة تعكس المجريات: {better[0]} كان الأخطر "
                             f"{'وفاز بالمباراة' if part == 'full' else 'وكسب الشوط'}.")
            elif better[1] < 0:
                notes.append(f"النتيجة أقسى من الأداء على {better[0]}: كان الأخطر حسب xG.")
        if mh["set_piece_xg"] >= 0.4 * h and mh["set_piece_xg"] >= 0.5 * mh["xg"]:
            notes.append(f"نص خطورة {h_ar} من الكرات الثابتة (xG {_x(mh['set_piece_xg'])}).")
        if ma["set_piece_xg"] >= 0.4 * h and ma["set_piece_xg"] >= 0.5 * ma["xg"]:
            notes.append(f"نص خطورة {a_ar} من الكرات الثابتة (xG {_x(ma['set_piece_xg'])}).")
        for i, t in enumerate(notes):
            ins_rows.append({"match_id": match_id, "part": part, "side": "match", "team_ar": "", "kind": "note",
                             "rank": i + 1, "text": t, "row_id": f"{match_id}|{part}|match|note|{i}"})
    out["stats"] = pd.DataFrame(stat_rows)

    # players
    pls = []
    for side, team in (("home", home), ("away", away)):
        pt = player_table(df, team)
        pt.insert(0, "side", side)
        pt.insert(0, "match_id", match_id)
        pls.append(pt)
    players = pd.concat(pls, ignore_index=True)
    players["row_id"] = players["match_id"] + "|" + players["player"]
    out["players"] = players
    top = players.sort_values("rating", ascending=False).iloc[0]
    ins_rows.append({"match_id": match_id, "part": "full", "side": "match", "team_ar": "", "kind": "note", "rank": 9,
                     "text": f"نجم المباراة حسب الحاسوب: {top['name_ar']} (تقييم {top['rating']:.1f})",
                     "row_id": f"{match_id}|full|match|note|star"})

    # shots (display: home attacks right)
    s = shots_table(df, home, away)
    s["name_ar"] = s["player"].map(lambda p: short_name(p))
    out["shots"] = pd.DataFrame({
        "match_id": match_id, "row_id": [f"{match_id}|{i}" for i in s["id"]], "side": s["side"],
        "player_ar": s["name_ar"], "minute": s["minute"] + 1, "period": s["period"],
        "x": s["dx"].round(1), "y": s["dy"].round(1), "xg": s["xg"].round(3), "outcome": s["outcome"],
        "is_goal": s["is_goal"], "pattern": s["play_pattern"]})

    # touches (each team attacking right)
    tch = []
    for side, team in (("home", home), ("away", away)):
        t = touches(df, team)
        tch.append(pd.DataFrame({"match_id": match_id, "side": side, "player_ar": t["player"].map(lambda p: short_name(p)),
                                 "x": t["x"].round(1), "y": t["y"].round(1), "period": t["period"]}))
    tch = pd.concat(tch, ignore_index=True)
    tch.insert(1, "row_id", [f"{match_id}|t{i}" for i in range(len(tch))])
    out["touches"] = tch

    # pass networks
    nodes, edges = [], []
    for side, team in (("home", home), ("away", away)):
        n, e, cut = pass_network(df, team)
        n["name_ar"] = n["player"].map(lambda p: short_name(p))
        pos = n.set_index("player")[["x", "y"]]
        for r in n.itertuples():
            nodes.append({"match_id": match_id, "row_id": f"{match_id}|{side}|{r.player}", "side": side,
                          "player_ar": r.name_ar, "number": r.number, "x": round(r.x, 1), "y": round(r.y, 1),
                          "touches": r.touches, "until_minute": cut})
        for r in e.itertuples():
            edges.append({"match_id": match_id, "row_id": f"{match_id}|{side}|{r.a}|{r.b}", "side": side,
                          "a_ar": short_name(r.a), "b_ar": short_name(r.b), "passes": int(r.n),
                          "x1": round(pos.loc[r.a, "x"], 1), "y1": round(pos.loc[r.a, "y"], 1),
                          "x2": round(pos.loc[r.b, "x"], 1), "y2": round(pos.loc[r.b, "y"], 1)})
        if len(e):
            topp = e.sort_values("n", ascending=False).iloc[0]
            nm = h_ar if side == "home" else a_ar
            ins_rows.append({"match_id": match_id, "part": "full", "side": "match", "team_ar": "", "kind": "note",
                             "rank": 8 if side == "home" else 7,
                             "text": f"أقوى ثنائي عند {nm}: {short_name(topp.a)} و{short_name(topp.b)} "
                                     f"({count_ar(int(topp.n), 'تمريرة وحدة', 'تمريرتين', 'تمريرات', 'تمريرة')} بينهم)",
                             "row_id": f"{match_id}|full|match|note|duo|{side}"})
    out["pass_nodes"], out["pass_edges"] = pd.DataFrame(nodes), pd.DataFrame(edges)
    out["insights"] = pd.DataFrame(ins_rows)

    # timelines
    end = int(min(95, max(91, df.loc[df["period"] == 2, "minute"].max() + 1)))
    xt = pd.DataFrame(xg_timeline(df, home, away, end))
    ev = model_events_sb(df, home)
    wp = pd.DataFrame(model.timeline(lam, mu, ev, end_minute=end))
    tl = xt.merge(wp, on="minute")
    tl.insert(0, "match_id", match_id)
    tl["row_id"] = tl["match_id"] + "|" + tl["minute"].astype(str)
    for c in ("p_home", "p_draw", "p_away"):
        tl[c] = (100 * tl[c]).round(2)
    tl[["xg_home", "xg_away"]] = tl[["xg_home", "xg_away"]].round(3)
    out["timeline"] = tl

    mf = team_metrics(df, home, away, (1, 2))
    ma = team_metrics(df, away, home, (1, 2))
    out["match"] = pd.DataFrame([{
        "match_id": match_id, "date": date, "home": home, "away": away, "home_ar": h_ar, "away_ar": a_ar,
        "hg": hg, "ag": ag, "xg_home": round(mf["xg"], 2), "xg_away": round(ma["xg"], 2),
        "label_ar": f"{h_ar} {hg}-{ag} {a_ar}", "source": source,
        "pre_home_pct": round(100 * wp.iloc[0]["p_home"], 1), "pre_draw_pct": round(100 * wp.iloc[0]["p_draw"], 1),
        "pre_away_pct": round(100 * wp.iloc[0]["p_away"], 1)}])

    # a report dict in the live format, for the story card
    ins = out["insights"]
    full_ins = ins[ins["part"] == "full"]
    rep = {"phase": "FT", "home": home, "away": away, "home_ar": h_ar, "away_ar": a_ar, "score": [hg, ag],
           "pre_match": {"p": [wp.iloc[0]["p_home"], wp.iloc[0]["p_draw"], wp.iloc[0]["p_away"]], "xg": [lam, mu]},
           "now": {"p": [float(hg > ag), float(hg == ag), float(hg < ag)]},
           "insights": {s_: {k: full_ins[(full_ins["side"] == s_) & (full_ins["kind"] == k)]["text"].tolist()
                              for k in ("pos", "neg")} for s_ in ("home", "away")},
           "notes": full_ins[full_ins["side"] == "match"]["text"].tolist(),
           "timeline": model.timeline(lam, mu, ev, end_minute=end), "events": ev}
    out["report"] = rep
    return out
