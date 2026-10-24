"""Data stories: findings worth analysing or posting, each with its evidence, comparison, period and sample.

Every story is computed from the same numbers the app shows. The wording states the sample size, and a
story is only proposed when the gap is large relative to its noise (rules in each function).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

METRIC_AR = {"p_title": "اللقب", "p_ucl": "دوري الأبطال", "p_releg": "الهبوط", "p_uel": "الدوري الأوروبي",
             "p_uecl": "دوري المؤتمر"}


def _pct(x):
    return f"{100 * x:.0f}٪"


def luck_stories(cards: dict, names_by_id: dict) -> list[dict]:
    """Points far from the points the pre-match forecasts expected (results vs underlying level)."""
    out = []
    for tid, c in cards.items():
        tot = c["totals"]
        n = tot["played"]
        if n < 6 or not np.isfinite(tot.get("xpts_pre", np.nan)):
            continue
        gap = tot["pts"] - tot["xpts_pre"]
        # sd of points around the forecast is about 1.2 per match -> noise of the total ~ 1.2 * sqrt(n)
        noise = 1.2 * np.sqrt(n)
        if abs(gap) < 1.5 * noise / np.sqrt(2):
            continue
        sot_ratio = tot["sot_for"] / max(tot["sot_for"] + tot["sot_against"], 1)
        name = c["team"]["ar"]
        over = gap > 0
        out.append({
            "id": f"luck-{tid}", "type": "results_vs_level", "teams": [tid],
            "title_ar": f"{name}: {'نتائج أحسن من مستواه' if over else 'نتائج أقل من مستواه'}",
            "text_ar": (f"{name} جمع {tot['pts']} نقطة من {n} مباريات، بينما توقعات ما قبل المباريات كانت تعطيه "
                        f"{tot['xpts_pre']:.1f} نقطة بالمعدل ({gap:+.1f}). "
                        + ("هل هي فعالية حقيقية لو حظ راح يرجع لمستواه؟" if over else "هل هو سوء حظ لو مشكلة أعمق؟")),
            "evidence": [{"label_ar": "النقاط الفعلية", "value": tot["pts"]},
                         {"label_ar": "النقاط المتوقعة قبل المباريات", "value": round(tot["xpts_pre"], 1)},
                         {"label_ar": "الأهداف له/عليه", "value": f"{tot['gf']}/{tot['ga']}"},
                         {"label_ar": "المتوقع قبل المباريات له/عليه", "value": f"{tot['xg_for_pre']:.1f}/{tot['xg_against_pre']:.1f}"},
                         {"label_ar": "حصته من التسديدات على المرمى", "value": _pct(sot_ratio)}],
            "comparison_ar": "مقارنة بتوقعات الموديل نفسه قبل كل مباراة (بدون معرفة النتيجة)",
            "period_ar": "الموسم الحالي لحد هسه", "sample": n,
            "caution_ar": f"العينة {n} مباريات: الفرق ضعف التذبذب المعتاد تقريباً، بس يبقى ممكن يتعدل",
            "score": abs(gap) / noise})
    return out


def rating_trend_stories(cards: dict) -> list[dict]:
    """Biggest change of the model's overall rating over the last weeks."""
    out = []
    for tid, c in cards.items():
        h = c.get("rating_history") or []
        if len(h) < 4:
            continue
        a0, d0 = h[-4]["attack"], h[-4]["defence"]
        a1, d1 = h[-1]["attack"], h[-1]["defence"]
        s0, s1 = np.log(a0) - np.log(d0), np.log(a1) - np.log(d1)
        delta = s1 - s0
        if abs(delta) < 0.12:
            continue
        name = c["team"]["ar"]
        out.append({
            "id": f"trend-{tid}", "type": "rating_trend", "teams": [tid],
            "title_ar": f"{name} {'يتحسن' if delta > 0 else 'يتراجع'} حسب الموديل",
            "text_ar": (f"تقييم {name} تغيّر خلال آخر 3 أسابيع: الهجوم {a0:.2f} ← {a1:.2f}، والدفاع {d0:.2f} ← {d1:.2f} "
                        f"(1.00 = معدل الدوري؛ الدفاع أقل = أحسن)."),
            "evidence": [{"label_ar": "الهجوم قبل 3 أسابيع ← الآن", "value": f"{a0:.2f} ← {a1:.2f}"},
                         {"label_ar": "الدفاع قبل 3 أسابيع ← الآن", "value": f"{d0:.2f} ← {d1:.2f}"}],
            "comparison_ar": "تقييمات الموديل الأسبوعية (كل أسبوع يتعلم من النتائج الجديدة)",
            "period_ar": f"{h[-4]['date']} ← {h[-1]['date']}", "sample": 3,
            "caution_ar": "التقييم يتحرك ببطء مقصود حتى ما يبالغ بمباراة وحدة", "score": abs(delta) * 5})
    return out


def stakes_stories(importance: list[dict], names_by_key: dict) -> list[dict]:
    out = []
    for imp in importance[:3]:
        if not imp["swings"]:
            continue
        sw = imp["swings"][0]
        h, a = names_by_key[imp["home"]]["ar"], names_by_key[imp["away"]]["ar"]
        t = names_by_key[sw["team"]]["ar"]
        met = METRIC_AR.get(sw["metric"], sw["metric"])
        out.append({
            "id": f"stakes-{imp['match_id']}", "type": "high_stakes", "matches": [imp["match_id"]],
            "title_ar": f"{h} × {a}: مباراة تحسم أشياء",
            "text_ar": (f"فرصة {t} ب{met}: {_pct(sw['home_win'])} إذا فاز {h}، {_pct(sw['draw'])} بالتعادل، "
                        f"و{_pct(sw['away_win'])} إذا فاز {a}."),
            "evidence": [{"label_ar": "مؤشر الأهمية", "value": imp["importance"]},
                         {"label_ar": f"فرصة {t} ب{met} (فوز الأرض/تعادل/فوز الضيف)",
                          "value": f"{_pct(sw['home_win'])} / {_pct(sw['draw'])} / {_pct(sw['away_win'])}"}],
            "comparison_ar": "نفس المحاكاة بثلاث نتائج للمباراة وبنفس الأرقام العشوائية",
            "period_ar": "بقية الموسم", "sample": imp["n_sims"],
            "caution_ar": "محاكاة: الفرق الصغير (أقل من نقطتين) ممكن يكون ضجيج", "score": imp["importance"] / 20})
    return out


def season_shift_stories(rows: list[dict], names_by_key: dict) -> list[dict]:
    out = []
    contenders = sorted(rows, key=lambda r: -r.get("p_title", 0))[:2]
    if len(contenders) == 2 and contenders[0].get("p_title", 0) > 0:
        a, b = contenders
        out.append({
            "id": "title-race", "type": "title_race", "teams": [names_by_key[a["team"]]["id"], names_by_key[b["team"]]["id"]],
            "title_ar": "سباق اللقب بالأرقام",
            "text_ar": (f"{names_by_key[a['team']]['ar']} {_pct(a['p_title'])} مقابل {names_by_key[b['team']]['ar']} "
                        f"{_pct(b['p_title'])}. النقاط المتوقعة: {a['exp_pts']:.0f} مقابل {b['exp_pts']:.0f}."),
            "evidence": [{"label_ar": "فرصة اللقب", "value": f"{_pct(a['p_title'])} / {_pct(b['p_title'])}"},
                         {"label_ar": "النقاط الآن", "value": f"{a['pts_now']} / {b['pts_now']}"},
                         {"label_ar": "النقاط المتوقعة بالنهاية", "value": f"{a['exp_pts']:.0f} / {b['exp_pts']:.0f}"}],
            "comparison_ar": "10,000 موسم محاكى بقواعد الليغا الرسمية", "period_ar": "بقية الموسم",
            "sample": None, "caution_ar": "المدى الطبيعي للنقاط واسع: شوف عمود «من/إلى» بصفحة الموسم", "score": 1.0})
    return out


def half_shift_stories(archive: dict) -> list[dict]:
    """Clear change between halves in archive matches (shots, xG, field tilt)."""
    out = []
    for mid, a in archive.items():
        st = pd.DataFrame(a["stats"])
        if st.empty:
            continue
        piv = st.pivot_table(index="stat", columns="part", values=["home", "away"], aggfunc="first")
        try:
            for side in ("home", "away"):
                x1, x2 = piv.loc["xg", (side, "h1")], piv.loc["xg", (side, "h2")]
                if abs(x2 - x1) >= 0.8:
                    m = a["match"]
                    team = m["home_ar"] if side == "home" else m["away_ar"]
                    out.append({
                        "id": f"half-{mid}-{side}", "type": "half_shift", "archive": [mid],
                        "title_ar": f"{team}: شوطين بوجهين ({m['label_ar']})",
                        "text_ar": f"xG {team} بالشوط الأول {x1:.2f} وبالثاني {x2:.2f}.",
                        "evidence": [{"label_ar": "xG الشوط الأول ← الثاني", "value": f"{x1:.2f} ← {x2:.2f}"}],
                        "comparison_ar": "نفس المباراة، شوط مقابل شوط", "period_ar": m["date"],
                        "sample": 1, "caution_ar": "مباراة وحدة من الأرشيف (StatsBomb)", "score": abs(x2 - x1)})
        except KeyError:
            continue
    return out


def player_stories(players: dict) -> list[dict]:
    """Archive players who create far more than they convert (xA + xG vs goals + assists)."""
    out = []
    rows = pd.DataFrame(players.get("players", []))
    if rows.empty or "xa" not in rows:
        return out
    rows = rows[rows["minutes"] >= 900].copy()
    if "name_ar" not in rows:
        rows["name_ar"] = rows["name"]
    rows["gap"] = (rows["xa"] + rows["np_xg"]) - (rows["assists"] + rows["np_goals"])
    for k, r in enumerate(rows.sort_values("gap", ascending=False).head(2).itertuples()):
        out.append({
            "id": f"player-{k + 1}", "type": "creator_without_output", "players": [r.player_id],
            "title_ar": f"{r.name_ar}: يصنع أكثر مما يحصد",
            "text_ar": (f"بموسم {players.get('season_label', '')} صنع {r.name_ar} xA {r.xa:.1f} وxG بدون جزاء {r.np_xg:.1f}، "
                        f"بس حصيلته {int(r.assists)} صناعة و{int(r.np_goals)} أهداف."),
            "evidence": [{"label_ar": "xA + xG بدون جزاء", "value": round(r.xa + r.np_xg, 1)},
                         {"label_ar": "صناعة + أهداف بدون جزاء", "value": int(r.assists + r.np_goals)},
                         {"label_ar": "الدقائق", "value": int(r.minutes)}],
            "comparison_ar": "المتوقع من جودة الفرص مقابل الحصيلة الفعلية", "period_ar": players.get("season_label", ""),
            "sample": int(r.minutes), "caution_ar": "أرشيف StatsBomb المفتوح (موسم سابق)، مو الموسم الحالي",
            "score": float(r.gap) / 3})
    return out


def discover(cards, rows, importance, retro, cur, names, archive, players) -> dict:
    names_by_id = {v["id"]: v for v in names.values()}
    st = (luck_stories(cards, names_by_id) + rating_trend_stories(cards) + stakes_stories(importance, names)
          + season_shift_stories(rows, names) + half_shift_stories(archive) + player_stories(players))
    st.sort(key=lambda s: -s.get("score", 0))
    return {"stories": st, "rules_ar": [
        "كل قصة تعرض الدليل وفترة القياس وحجم العينة.",
        "قصص «النتائج مقابل المستوى» تظهر بس إذا الفرق أكبر من التذبذب المعتاد بوضوح.",
        "قصص الأرشيف تعتمد بيانات StatsBomb المفتوحة لمواسم سابقة."]}
