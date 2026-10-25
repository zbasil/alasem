"""Live half-time / full-time match reports from SportRadar snapshots.

A snapshot is the answer of the sports-data tool (game_stats) saved as JSON.
The half-time snapshot holds the first half; the full-time snapshot holds the
whole match, so the second half is FT minus HT.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from .inplay import InPlayModel
from .teams import arabic, canonical

STAT_KEYS = ["shots_total", "shots_on_target", "shots_off_target", "shots_blocked", "corner_kicks", "fouls",
             "yellow_cards", "red_cards", "yellow_red_cards", "offsides", "ball_possession", "free_kicks",
             "goal_kicks", "throw_ins", "substitutions"]

STAT_LABELS_AR = {
    "goals": "الأهداف", "ball_possession": "الاستحواذ ٪", "shots_total": "التسديدات", "shots_on_target": "على المرمى",
    "shots_off_target": "خارج المرمى", "shots_blocked": "تسديدات مصدودة", "saves": "تصديات الحارس",
    "corner_kicks": "الركنيات", "fouls": "الأخطاء", "yellow_cards": "الإنذارات", "sent_off": "الطرد",
    "offsides": "التسلل", "free_kicks": "الضربات الحرة", "throw_ins": "رميات التماس", "goal_kicks": "ضربات المرمى",
    "substitutions": "التبديلات",
}
SHOWN_STATS = ["goals", "ball_possession", "shots_total", "shots_on_target", "shots_off_target", "shots_blocked",
               "saves", "corner_kicks", "fouls", "yellow_cards", "sent_off", "offsides"]


@dataclass
class Snapshot:
    home: str
    away: str
    hg: int
    ag: int
    stats: dict                      # {"home": {...}, "away": {...}}
    events: list = field(default_factory=list)   # [{"type", "time", "team"}]
    status: str = ""
    event_id: str = ""

    @property
    def last_minute(self) -> int:
        return max([int(e.get("time") or 0) for e in self.events] + [0])


def parse_game_stats(js: dict, event_id: str = "", status: str = "") -> Snapshot:
    """Accept the raw tool answer (team keys are abbreviations) or the saved normalised form."""
    if "teams" in js and js.get("home") in js["teams"]:
        h_ab, a_ab = js["home"], js["away"]
        home = canonical(js["teams"][h_ab]["name"])
        away = canonical(js["teams"][a_ab]["name"])
        hg, ag = int(js["score"][h_ab]), int(js["score"][a_ab])
        ts = js.get("team_stats") or {}
        stats = {"home": dict(ts.get(h_ab, {})), "away": dict(ts.get(a_ab, {}))}
    else:
        home, away = canonical(js["home"]), canonical(js["away"])
        hg, ag = int(js["score"]["home"]), int(js["score"]["away"])
        stats = {"home": dict(js["team_stats"]["home"]), "away": dict(js["team_stats"]["away"])}
    for side in ("home", "away"):
        for k in STAT_KEYS:
            v = stats[side].get(k)
            # a statistic the source did not send stays unknown (NaN), never 0: comparisons with NaN are
            # False, so no positive or negative point is ever claimed from a missing number
            stats[side][k] = float(v) if v is not None and v != "" else float("nan")
    return Snapshot(home, away, hg, ag, stats, list(js.get("key_events") or []),
                    status or js.get("status", ""), event_id or js.get("id", ""))


def goals_from_events(snap: Snapshot, upto: float | None = None) -> tuple[int, int]:
    hg = ag = 0
    for e in snap.events:
        if e.get("type") == "score_change" and (upto is None or int(e.get("time") or 0) <= upto):
            if "home_score" in e:
                hg, ag = int(e["home_score"]), int(e["away_score"])
            else:
                hg += e.get("team") == "home"
                ag += e.get("team") == "away"
    return hg, ag


def model_events(snap: Snapshot) -> list:
    """Goals and sendings-off in the in-play model's format.

    The scoring side is read from the running score (home_score / away_score),
    so own goals are credited correctly; the 'team' field is the fallback."""
    out = []
    ph = pa = 0
    for e in sorted(snap.events, key=lambda x: int(x.get("time") or 0)):
        t = e.get("type")
        minute = int(e.get("time") or 0)
        if t == "score_change":
            if "home_score" in e and "away_score" in e:
                nh, na = int(e["home_score"]), int(e["away_score"])
                for _ in range(max(0, nh - ph)):
                    out.append({"minute": minute, "team": "home", "kind": "goal"})
                for _ in range(max(0, na - pa)):
                    out.append({"minute": minute, "team": "away", "kind": "goal"})
                ph, pa = nh, na
            elif e.get("team") in ("home", "away"):
                out.append({"minute": minute, "team": e["team"], "kind": "goal"})
        elif t in ("red_card", "yellow_red_card") and e.get("team") in ("home", "away"):
            out.append({"minute": minute, "team": e["team"], "kind": "red"})
    return out


def phase_stats(full: Snapshot, first: Snapshot | None):
    """{'first_half': .., 'second_half': .., 'full': ..} each {'home': {...}, 'away': {...}}.

    Possession for the second half is derived from the two cumulative values,
    assuming halves of equal length (marked approximate)."""
    def add_goals(st, hg, ag):
        st = {s: dict(v) for s, v in st.items()}
        st["home"]["goals"], st["away"]["goals"] = float(hg), float(ag)
        for s, o in (("home", "away"), ("away", "home")):
            sot = st[o]["shots_on_target"]
            st[s]["saves"] = max(0.0, sot - st[o]["goals"]) if np.isfinite(sot) else float("nan")
            st[s]["sent_off"] = np.nansum([st[s]["red_cards"], st[s]["yellow_red_cards"]]) \
                if np.isfinite(st[s]["red_cards"]) or np.isfinite(st[s]["yellow_red_cards"]) else float("nan")
        return st

    out = {"full": add_goals(full.stats, full.hg, full.ag)}
    if first is not None:
        out["first_half"] = add_goals(first.stats, first.hg, first.ag)
        sh = {}
        for s in ("home", "away"):
            sh[s] = {k: (max(0.0, full.stats[s][k] - first.stats[s][k])
                         if np.isfinite(full.stats[s][k]) and np.isfinite(first.stats[s][k]) else float("nan"))
                     for k in STAT_KEYS}
            sh[s]["ball_possession"] = float(np.clip(2 * full.stats[s]["ball_possession"]
                                                     - first.stats[s]["ball_possession"], 0, 100))
        out["second_half"] = add_goals(sh, full.hg - first.hg, full.ag - first.ag)
        out["second_half"]["approx_possession"] = True
    return out


# ---------------------------------------------------------------------------
# insights (Arabic)
# ---------------------------------------------------------------------------

def _n(x) -> str:
    return str(int(round(x))) if np.isfinite(x) else "—"



def count_ar(n, one: str, two: str, few: str, many: str | None = None) -> str:
    """Arabic counted noun: 1 -> one, 2 -> two, 3-10 -> 'N few', 11+ -> 'N many'."""
    n = int(round(n))
    if n == 1:
        return one
    if n == 2:
        return two
    if 3 <= n <= 10 or n == 0:
        return f"{n} {few}"
    return f"{n} {many or one}"


def shots(n):
    return count_ar(n, "تسديدة وحدة", "تسديدتين", "تسديدات", "تسديدة")


def goals_ar(n):
    return count_ar(n, "هدف", "هدفين", "أهداف", "هدف")


def _ratio(a: float, b: float) -> float:
    return (a + 0.5) / (b + 0.5)


def team_insights(st: dict, op: dict, name_ar: str, opp_ar: str, halves: float = 1.0,
                  events: list | None = None, side: str = "home", pre_p: float | None = None,
                  result: str | None = None, period_end: int = 45):
    """Ranked positives and negatives for one team in one phase.

    Every candidate gets a strength score from how far the team is from its
    opponent (ratios) or from normal levels per half; the best three of each
    kind are kept. halves = 1 for a half, 2 for a whole match.
    events: goals/red cards in the in-play model's format, for timing notes.
    pre_p: this team's pre-match win probability; result: 'W', 'D' or 'L' at full time.
    """
    h = halves
    S, oS = st["shots_total"], op["shots_total"]
    T, oT = st["shots_on_target"], op["shots_on_target"]
    G, oG = st["goals"], op["goals"]
    P = st["ball_possession"]
    C, oC = st["corner_kicks"], op["corner_kicks"]
    F, Y, R = st["fouls"], st["yellow_cards"], st["sent_off"]
    OFF = st["offsides"]
    blocks = op["shots_blocked"]            # opponent shots blocked by this team
    saves = st["saves"]
    pos, neg = [], []
    rs = _ratio(S, oS)

    # shooting volume
    if S >= 4 * h and rs >= 2.0:
        pos.append((2.5 + min(rs, 5) / 2, f"سيطرة هجومية: {shots(S)} مقابل {_n(oS)}"))
    elif S >= 3 * h and rs >= 1.4:
        pos.append((1.5 + rs / 2, f"أفضلية بالتسديد: {_n(S)} مقابل {_n(oS)}"))
    if oS >= 4 * h and rs <= 0.5:
        neg.append((2.5 + min(1 / rs, 5) / 2, f"تحت الضغط: {opp_ar} سدد {count_ar(oS, 'مرة وحدة', 'مرتين', 'مرات', 'مرة')} مقابل {_n(S)}"))
    elif S <= 2 * h:
        neg.append((1.8, f"عقم هجومي: {shots(S)} بس"))
    elif oS >= 3 * h and rs <= 0.72:
        neg.append((1.3 + (1 / rs) / 2, f"أقل خطورة من الخصم: {shots(S)} مقابل {_n(oS)}"))

    # accuracy and finishing
    if S >= 3 * h:
        acc = T / S
        if acc >= 0.5:
            pos.append((1.2 + 4 * (acc - 0.4), f"دقة بالتسديد: {_n(T)} من {_n(S)} على المرمى ({100 * acc:.0f}٪)"))
        elif acc <= 0.3:
            neg.append((1.2 + 4 * (0.4 - acc), f"دقة ضعيفة: {shots(T)} بس على المرمى من {_n(S)}"))
    if G >= 1 and T > 0 and G / T >= 0.4:
        pos.append((1.6 + G / T, f"فعالية: {goals_ar(G)} من {shots(T)} على المرمى"))
    if T >= 3 * h and G == 0:
        neg.append((1.5 + T / (3 * h), f"إهدار: {shots(T)} على المرمى بدون هدف"))

    # defence and goalkeeper
    if oT <= 1 * h and oS <= 6 * h:
        pos.append((2.4 - oT / (2 * h), f"دفاع محكم: {opp_ar} سدد {shots(oT) if oT else 'ولا تسديدة'} بس على المرمى"))
    elif oT >= 5 * h:
        neg.append((1.5 + oT / (5 * h), f"دفاع مكشوف: {shots(oT)} على مرماه"))
    if saves >= 2 * h:
        pos.append((1.2 + saves / (2 * h), f"الحارس حاضر: {count_ar(saves, 'تصدي واحد', 'تصديين', 'تصديات', 'تصدي')}"))
    if blocks >= 2 * h:
        pos.append((1.0 + blocks / (3 * h), f"الدفاع صد {shots(blocks)} قبل توصل المرمى"))
    if oG >= 1 and oT <= oG + 1:
        neg.append((1.7, f"استقبل {goals_ar(oG)} من {shots(oT)} على المرمى بس"))

    # set pieces and territory
    rc = _ratio(C, oC)
    if C >= 3 * h and rc >= 2:
        pos.append((1.0 + min(rc, 6) / 3, f"ضغط من الركنيات: {_n(C)} مقابل {_n(oC)}"))
    if oC >= 3 * h and rc <= 0.5:
        neg.append((0.9 + min(1 / rc, 6) / 4, f"محاصَر بالركنيات: {_n(oC)} للخصم مقابل {_n(C)}"))

    # possession
    if P >= 58 and S > oS:
        pos.append((1.3 + (P - 58) / 15, f"سيطرة على الكرة: استحواذ {_n(P)}٪ مع أفضلية بالتسديد"))
    elif P >= 55 and S <= oS:
        neg.append((2.0 + (P - 55) / 10, f"استحواذ بلا خطورة: {_n(P)}٪ من الكرة بس {shots(S)} مقابل {_n(oS)}"))
    if P <= 42 and S > oS:
        pos.append((1.6, f"خطورة بدون الكرة: استحواذ {_n(P)}٪ بس سدد أكثر ({_n(S)} مقابل {_n(oS)})"))
    elif P <= 40 and S < oS:
        neg.append((1.4, f"بعيد عن الكرة: استحواذ {_n(P)}٪ بس"))

    # discipline
    if R >= 1:
        neg.append((4.0, "يلعب بنقص عددي بعد الطرد"))
    if Y >= 2 * h or (h == 1 and Y >= 2):
        neg.append((1.2 + Y / (2 * h), f"خطر البطاقات: {count_ar(Y, 'إنذار', 'إنذارين', 'إنذارات', 'إنذار')}"))
    if F >= 8 * h:
        neg.append((1.0 + F / (16 * h), f"أخطاء كثيرة: {count_ar(F, 'خطأ', 'خطأين', 'أخطاء', 'خطأ')}"))
    if F <= 4 * h and Y == 0:
        pos.append((0.9, f"انضباط: {count_ar(F, 'خطأ واحد', 'خطأين', 'أخطاء', 'خطأ')} وبدون إنذارات"))
    if OFF >= 3 * h:
        neg.append((0.9 + OFF / (6 * h), f"تسلل متكرر: {count_ar(OFF, 'حالة', 'حالتين', 'حالات', 'حالة')}، توقيت الانطلاقات يحتاج تعديل"))

    # goal timing
    other = "away" if side == "home" else "home"
    for e in events or []:
        if e["kind"] != "goal":
            continue
        late = (e["minute"] >= period_end - 5 and e["minute"] <= 45 + 8 and period_end == 45) or e["minute"] >= 85
        if not late:
            continue
        if e["team"] == side:
            pos.append((2.0, f"توقيت قاتل: هدف بالدقيقة {e['minute']}"))
        elif e["team"] == other:
            neg.append((1.9, f"غفلة بآخر الدقائق: استقبل هدف بالدقيقة {e['minute']}"))

    # result against expectation (full time)
    if pre_p is not None and result is not None:
        if result == "W" and pre_p < 0.35:
            pos.append((3.0, f"فوز أكبر من التوقعات: الموديل كان يعطيه {100 * pre_p:.0f}٪ بس"))
        elif result == "D" and pre_p < 0.3:
            pos.append((2.2, f"نقطة ثمينة: الموديل كان يعطيه {100 * pre_p:.0f}٪ للفوز بس"))
        elif result == "L" and pre_p >= 0.5:
            neg.append((3.0, f"خسارة مفاجئة: كان مرشح للفوز بنسبة {100 * pre_p:.0f}٪"))
        elif result == "D" and pre_p >= 0.55:
            neg.append((2.4, f"نقطتين ضايعة: كان مرشح للفوز بنسبة {100 * pre_p:.0f}٪"))

    def best(lst):
        seen, out = set(), []
        for sc, t in sorted(lst, key=lambda x: -x[0]):
            key = t.split(":")[0]
            if key not in seen:
                seen.add(key)
                out.append(t)
        return out[:3]
    return best(pos), best(neg)


def pct(x: float) -> str:
    return f"{100 * x:.0f}٪"


@dataclass
class LiveContext:
    lam: float                      # pre-match expected goals of the displayed pre-match forecast
    mu: float
    kickoff_utc: str = ""
    impact: list = field(default_factory=list)     # rows from impact.league_impact (dicts)
    rho: float | None = None        # the pre-match Dixon-Coles rho (minute 0 = the pre-match forecast)
    source: str = ""                # where lambda, mu, rho came from (prediction id or "refit")


def build_report(phase: str, full: Snapshot, first: Snapshot | None, ctx: LiveContext,
                 model: InPlayModel) -> dict:
    """phase: 'HT' (full is the half-time snapshot) or 'FT'."""
    home_ar, away_ar = arabic(full.home), arabic(full.away)
    ps = phase_stats(full, first if phase == "FT" else None)
    pre = model.probs(ctx.lam, ctx.mu, 0, 0, 0, rho=ctx.rho)
    events = model_events(full)
    reds_h = sum(1 for e in events if e["kind"] == "red" and e["team"] == "home")
    reds_a = sum(1 for e in events if e["kind"] == "red" and e["team"] == "away")
    rep = {"phase": phase, "event_id": full.event_id, "home": full.home, "away": full.away,
           "home_ar": home_ar, "away_ar": away_ar, "score": [full.hg, full.ag], "kickoff_utc": ctx.kickoff_utc,
           "pre_match": {"p": list(pre), "xg": [ctx.lam, ctx.mu], "rho": ctx.rho, "source": ctx.source},
           "model_version": getattr(model, "version", ""), "stats": ps, "events": events}

    if phase == "HT":
        now = model.probs(ctx.lam, ctx.mu, 45, full.hg, full.ag, reds_h, reds_a, period=1, rho=ctx.rho)
        i, j, pij = model.most_likely_final(ctx.lam, ctx.mu, 45, full.hg, full.ag, reds_h, reds_a, period=1, rho=ctx.rho)
        rep["now"] = {"p": list(now), "likely_final": f"{i}-{j}", "p_likely": pij}
        st = ps["full"]
        halves, label = 1.0, "الشوط الأول"
    else:
        now = (float(full.hg > full.ag), float(full.hg == full.ag), float(full.hg < full.ag))
        rep["now"] = {"p": list(now)}
        st = ps["full"]
        halves, label = 2.0, "المباراة كاملة"
    rep["label"] = label
    if phase == "FT":
        res_h = "W" if full.hg > full.ag else ("D" if full.hg == full.ag else "L")
        res_a = {"W": "L", "D": "D", "L": "W"}[res_h]
        kw_h = dict(pre_p=pre[0], result=res_h, period_end=90)
        kw_a = dict(pre_p=pre[2], result=res_a, period_end=90)
    else:
        kw_h = kw_a = dict(period_end=45)
    hp, hn = team_insights(st["home"], st["away"], home_ar, away_ar, halves, events, "home", **kw_h)
    ap, an = team_insights(st["away"], st["home"], away_ar, home_ar, halves, events, "away", **kw_a)
    rep["insights"] = {"home": {"pos": hp, "neg": hn}, "away": {"pos": ap, "neg": an}}

    notes = []
    timeline = model.timeline(ctx.lam, ctx.mu, events, end_minute=45 if phase == "HT" else 95, rho=ctx.rho)
    if phase == "HT":
        notes.append(f"حسب الموديل: فوز {home_ar} {pct(now[0])}، تعادل {pct(now[1])}، فوز {away_ar} {pct(now[2])} "
                     f"(قبل المباراة: {pct(pre[0])} / {pct(pre[1])} / {pct(pre[2])}).")
        notes.append(f"النتيجة الأرجح بنهاية المباراة: {rep['now']['likely_final']}.")
        d = full.hg - full.ag
        if d != 0:
            trail_ar = away_ar if d > 0 else home_ar
            p_back = now[1] + (now[2] if d > 0 else now[0])
            notes.append(f"{trail_ar} لازم يفتح اللعب: فرصة إنه يتعادل أو يقلبها {pct(p_back)}.")
        else:
            m_ = 55
            ph_next = model.probs(ctx.lam, ctx.mu, m_, 1, 0, reds_h, reds_a, period=2, rho=ctx.rho)[0]
            pa_next = model.probs(ctx.lam, ctx.mu, m_, 0, 1, reds_h, reds_a, period=2, rho=ctx.rho)[2]
            notes.append(f"الهدف الجاي يغيّر كل شي: إذا سجل {home_ar} أول بالدقيقة 55 تصير فرصته {pct(ph_next)}، "
                         f"وإذا سجل {away_ar} أول تصير فرصته {pct(pa_next)}.")
    else:
        # the moment that moved the win probability the most
        best = None          # (total variation, minute, scorer side, before row, after row)
        for a_, b_ in zip(timeline[:-1], timeline[1:]):
            if (a_["hg"], a_["ag"]) == (b_["hg"], b_["ag"]):
                continue
            tv = 0.5 * sum(abs(b_[k] - a_[k]) for k in ("p_home", "p_draw", "p_away"))
            side = "home" if b_["hg"] > a_["hg"] else "away"
            if best is None or tv > best[0]:
                best = (tv, b_["minute"] - 1, side, a_, b_)
        if best is not None:
            _, mn, side, a_, b_ = best
            nm, opp_nm = (home_ar, away_ar) if side == "home" else (away_ar, home_ar)
            own_k, opp_k = ("p_home", "p_away") if side == "home" else ("p_away", "p_home")
            if a_[opp_k] - b_[opp_k] > b_[own_k] - a_[own_k]:
                notes.append(f"أكبر لحظة بالمباراة: هدف {nm} بالدقيقة {mn} نزّل فرصة فوز {opp_nm} "
                             f"من {pct(a_[opp_k])} إلى {pct(b_[opp_k])}.")
            else:
                notes.append(f"أكبر لحظة بالمباراة: هدف {nm} بالدقيقة {mn} رفع فرصة فوزه "
                             f"من {pct(a_[own_k])} إلى {pct(b_[own_k])}.")
        if "second_half" in ps:
            s1, s2 = ps["first_half"], ps["second_half"]
            for side, nm in (("home", home_ar), ("away", away_ar)):
                a, b = s1[side]["shots_total"], s2[side]["shots_total"]
                if b >= a + 3:
                    notes.append(f"{nm} تحسن بالشوط الثاني: التسديدات من {_n(a)} إلى {_n(b)}.")
                elif a >= b + 3:
                    notes.append(f"{nm} تراجع بالشوط الثاني: التسديدات من {_n(a)} إلى {_n(b)}.")
    for row in (ctx.impact or [])[:2]:
        for col, lab in (("p_title", "اللقب"), ("p_top4", "دوري الأبطال"), ("p_releg", "الهبوط")):
            b, n_ = row[f"{col}_before"], row[f"{col}_now"]
            if abs(n_ - b) >= 0.02 and max(b, n_) >= 0.03:
                when = "حسب وضع المباراة هسه" if phase == "HT" else "بعد هالنتيجة"
                notes.append(f"{when}: فرصة {arabic(row['team'])} ب{lab} {pct(b)} ← {pct(n_)}.")
                break
    rep["notes"] = notes
    rep["timeline"] = timeline
    return rep


def report_markdown(rep: dict) -> str:
    """Chat-ready Arabic text."""
    h, a = rep["home_ar"], rep["away_ar"]
    title = "تحليل الشوط الأول" if rep["phase"] == "HT" else "تحليل نهاية المباراة"
    lines = [f"**{title}: {h} {rep['score'][0]}-{rep['score'][1]} {a}**", ""]
    for side, nm in (("home", h), ("away", a)):
        ins = rep["insights"][side]
        if ins["pos"] or ins["neg"]:
            lines.append(f"**{nm}**")
            lines += [f"- ✅ {t}" for t in ins["pos"]]
            lines += [f"- ⚠️ {t}" for t in ins["neg"]]
            lines.append("")
    lines.append("**أبرز الملاحظات**")
    lines += [f"- {t}" for t in rep["notes"]]
    return "\n".join(lines)


def _json_safe(o):
    """NaN / inf -> null (valid JSON for the web app); numpy scalars -> Python numbers."""
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_json_safe(obj), f, ensure_ascii=False, indent=1, default=float)
