"""Builds the app's data snapshot (the JSON 'API' the web app reads).

    python -m zsc export          (also run by `python -m zsc update`)

Output: snapshots/<UTC stamp>/*.json, then copied to app/data/ in one atomic swap; the last
`keep_snapshots` snapshots stay for restore (`python -m zsc restore <stamp>`).

Files
    meta.json              platform, versions, data status, rules, glossary
    teams.json             every team (ids, names, colours)
    fixtures.json          all 380 fixtures with status, score, displayed prediction, importance
    matches/mdNN.json      match centre, one file per matchday: predictions of both tracks + SportRadar,
                           reasons, top scores, change history, data notes, retro check, live data,
                           scenario inputs, facts of played matches
    season.json            table, projection, model ratings, what-if inputs, changes, importance
    teams/<id>.json        team card
    accuracy.json          evaluation digest + live track record
    archive/index.json     deep-analysis archive (StatsBomb) and archive/<id>.json per match
    players.json           archive player comparisons (per 90)
    stories.json           data stories with their evidence
"""

from __future__ import annotations

import glob
import json
import os
import shutil
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import apifootball, config, predict, predlog, store
from . import season as seasonmod
from .backtest import walk_forward
from .evaluate import outcome_index, rps
from .inplay import InPlayModel
from .paths import (APP_DATA, LIVE, MODELS, OUTPUTS, PREMATCH_LOG, RAW_SPORTRADAR, REPORTS, SNAPSHOTS)
from .pipeline import load_snapshot, season_teams
from .registry import TEAMS, names as team_names, team_id
from .teams import canonical

WEEKDAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
STATUS_AR = {"played": "انتهت", "scheduled": "قادمة", "abandoned": "أُوقفت وتُعاد", "result_pending": "بانتظار النتيجة",
             "live": "مباشر", "HT": "استراحة", "postponed": "مؤجلة"}
GLOSSARY = {
    "xg_pre": "الأهداف المتوقعة قبل المباراة: معدل الأهداف اللي يتوقعه الموديل لكل فريق قبل صافرة البداية. مو xG الفرص.",
    "xg_chances": "xG الفرص: احتمال كل تسديدة تصير هدف حسب مكانها ونوعها (من بيانات الأحداث). مجموعها xG الفريق بالمباراة.",
    "rps": "RPS: خطأ الاحتمالات على سلّم فوز ← تعادل ← خسارة. صفر = توقع مثالي، وكل ما أقل أحسن.",
    "logloss": "Log loss: يعاقب الثقة الزايدة بالتوقع الغلط. كل ما أقل أحسن.",
    "brier": "Brier: مربع الفرق بين الاحتمالات الثلاثة والنتيجة. كل ما أقل أحسن.",
    "hit": "نسبة الاختيار الصحيح: كم مرة صارت النتيجة الأرجح (فوز/تعادل/خسارة).",
    "exact": "إصابة النتيجة الرقمية: كم مرة صارت النتيجة الأرجح بالأرقام (مثل 2-1). أصعب بكثير من اختيار الفائز.",
    "calibration": "المعايرة: لما الموديل يگول 70٪، هل يصير الشي تقريباً 70٪ من المرات؟",
    "track_market": "مدعوم بالسوق: الموديل تعلّم قوة الفرق من النتائج ومن الأهداف اللي توقعها السوق بالمباريات السابقة.",
    "track_independent": "مستقل: الموديل يعتمد على الأهداف والتسديدات على المرمى بس، بدون أي معلومة من السوق.",
    "importance": "أهمية المباراة: مجموع التغيّر بفرص اللقب ودوري الأبطال والهبوط لكل الفرق بين فوز صاحب الأرض وفوز الضيف.",
    "ppda": "PPDA: عدد تمريرات الخصم بنصف ملعبه مقابل كل محاولة افتكاك. كل ما أقل، الضغط أعلى.",
    "field_tilt": "ميلان الملعب: حصة الفريق من اللمسات بالثلث الهجومي.",
    "mc_noise": "ضجيج المحاكاة: نسب الموسم جاية من محاكاة عشوائية، فتتغير شوية بين تشغيلين حتى لو ما تغيرت البيانات.",
}


def now_utc() -> pd.Timestamp:
    return pd.Timestamp.now("UTC").floor("s")


def iso(ts) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notna(ts) and ts != "" else ""


def baghdad(ts) -> dict:
    if ts is None or (isinstance(ts, float) and np.isnan(ts)) or ts == "":
        return {"date": "", "time": "", "weekday_ar": ""}
    t = pd.Timestamp(ts)
    t = (t.tz_localize("UTC") if t.tzinfo is None else t).tz_convert(config.tz())
    return {"date": t.strftime("%Y-%m-%d"), "time": t.strftime("%H:%M"), "weekday_ar": WEEKDAYS_AR[t.weekday()]}


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return iso(o)
    return o


# short Arabic names for tight spaces (legends, small tables); the full name everywhere else
SHORT_AR = {"ATH": "أتلتيك", "ATM": "أتلتيكو", "RBB": "بيتيس", "RCC": "سيلتا", "DEP": "ديبورتيفو", "RMA": "الريال",
            "RAC": "راسينغ", "RSO": "سوسيداد", "RVC": "رايو", "SPO": "خيخون", "LPA": "لاس بالماس", "MAL": "مايوركا",
            "GIR": "جيرونا", "VLL": "بلد الوليد", "LEG": "ليغانيس", "ALM": "ألميريا", "CAD": "قادش", "GRA": "غرناطة",
            "OVI": "أوفييدو", "HUE": "هويسكا", "EIB": "إيبار", "ZAR": "سرقسطة"}


def team_info(name: str) -> dict:
    c = canonical(name)
    tid, color, kit = TEAMS[c]
    en, ar = team_names(c)
    return {"id": tid, "key": c, "en": en, "ar": ar, "short": SHORT_AR.get(tid, ar), "color": color, "kit": list(kit)}


# --------------------------------------------------------------------------

def _latest_sportradar() -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW_SPORTRADAR, "scores_*.json"))):
        js = json.load(open(path, encoding="utf-8"))
        for g in js.get("games", []):
            wp = g.get("win_probability")
            if not wp:
                continue
            rows.append({"home": canonical(g["home"]), "away": canonical(g["away"]), "sr_id": g["id"],
                         "fetched_at": js.get("fetched_at", ""), "kickoff_utc": iso(g["start_time"]),
                         "p_home": wp["home"] / 100, "p_draw": wp["draw"] / 100, "p_away": wp["away"] / 100})
    if not rows:
        return pd.DataFrame(columns=["home", "away", "sr_id", "fetched_at", "kickoff_utc", "p_home", "p_draw", "p_away"])
    return pd.DataFrame(rows)


def log_predictions(preds: dict, fixtures: pd.DataFrame, now: pd.Timestamp, data_version: str,
                    fetched_at: str, horizon_days: int = 10, log=print) -> int:
    """Append pre-match predictions (both tracks + SportRadar) for matches kicking off within the horizon."""
    comp, season = config.competition(), config.season()
    fx = fixtures.set_index("match_id")
    written = 0
    rows = []
    for track, p in preds.items():
        for r in p.itertuples():
            ko = fx.loc[r.match_id, "kickoff_utc"]
            if not isinstance(ko, str) or not ko:
                continue
            t = pd.Timestamp(ko)
            if not (now < t <= now + pd.Timedelta(days=horizon_days)):
                continue
            rows.append({"match_id": r.match_id, "competition": comp, "season": season, "id_source": "zsc",
                         "external_id": fx.loc[r.match_id, "sr_id"] if pd.notna(fx.loc[r.match_id, "sr_id"]) else "",
                         "home_id": team_id(r.home), "away_id": team_id(r.away), "track": track,
                         "model_version": predict.model_version(track),
                         "config_hash": predict.config_hash(predict.track_config(track)),
                         "data_version": data_version, "data_fetched_at": fetched_at, "issued_at": iso(now),
                         "kickoff_utc": ko, "p_home": r.p_home, "p_draw": r.p_draw, "p_away": r.p_away,
                         "xg_home": r.xg_home, "xg_away": r.xg_away, "rho": r.rho,
                         "score1": r.score1, "p_score1": r.p_score1, "score2": r.score2, "p_score2": r.p_score2,
                         "score3": r.score3, "p_score3": r.p_score3, "inputs": r.inputs})
    sr = _latest_sportradar()
    if len(sr):   # one reading per match per export: the latest fetch (earlier readings were logged by earlier exports)
        sr = sr.sort_values("fetched_at").drop_duplicates(["home", "away"], keep="last")
    for r in sr.itertuples():
        mid = f"{comp}-{season}-{team_id(r.home)}-{team_id(r.away)}"
        if mid not in fx.index or not r.kickoff_utc:
            continue
        if not (now < pd.Timestamp(r.kickoff_utc) <= now + pd.Timedelta(days=horizon_days)):
            continue
        tot = r.p_home + r.p_draw + r.p_away
        rows.append({"match_id": mid, "competition": comp, "season": season, "id_source": "zsc", "external_id": r.sr_id,
                     "home_id": team_id(r.home), "away_id": team_id(r.away), "track": "sportradar",
                     "model_version": "sportradar-published", "data_version": "sportradar",
                     "data_fetched_at": r.fetched_at, "issued_at": r.fetched_at or iso(now), "kickoff_utc": r.kickoff_utc,
                     "p_home": r.p_home / tot, "p_draw": r.p_draw / tot, "p_away": r.p_away / tot,
                     "note": "SportRadar published probabilities (normalised to sum to 1)"})
    if rows:
        df = pd.DataFrame(rows)
        # a SportRadar reading is logged once (its own fetch time is the issue time)
        new = predlog.append(PREMATCH_LOG, df, kind="prematch")
        written = len(new)
    log(f"  prediction log: {written} new rows")
    return written


def retro_predictions(m: pd.DataFrame, season: int) -> dict[str, pd.DataFrame]:
    """For every played match of the season: the forecast each track made with only the data of the days
    before (weekly refits, exactly as in the evaluation)."""
    out = {}
    for track in predict.TRACKS:
        wf = walk_forward(m, [season], predict.track_config(track))
        wf["match_id"] = [f"{config.competition()}-{season}-{team_id(h)}-{team_id(a)}" for h, a in zip(wf["home"], wf["away"])]
        out[track] = wf
    return out


def history_for(log_df: pd.DataFrame, match_id: str) -> list[dict]:
    """Versions of the pre-match forecast of one match with what changed between versions."""
    if not len(log_df):
        return []
    d = log_df[log_df["match_id"] == match_id].sort_values("issued_at")
    out = []
    for track, g in d.groupby("track"):
        prev = None
        for r in g.itertuples():
            item = {"track": track, "issued_at": r.issued_at, "model_version": r.model_version,
                    "data_version": r.data_version, "p": [r.p_home, r.p_draw, r.p_away],
                    "xg": [r.xg_home, r.xg_away] if pd.notna(r.xg_home) else None, "changes": []}
            if prev is not None:
                dp = [100 * (a - b) for a, b in zip(item["p"], prev["p"])]
                item["delta_pts"] = dp
                if r.model_version != prev["model_version"]:
                    item["changes"].append({"kind": "model", "text_ar": f"إصدار الموديل تغيّر: {prev['model_version']} ← {r.model_version}"})
                if r.data_version != prev["data_version"]:
                    item["changes"].append({"kind": "data", "text_ar": "انضافت نتائج أو بيانات جديدة (نسخة بيانات جديدة)"})
                try:
                    a, b = json.loads(prev["inputs"]), json.loads(r.inputs)
                    for k, lab in (("attack_home_x", "هجوم صاحب الأرض"), ("defence_home_x", "دفاع صاحب الأرض"),
                                   ("attack_away_x", "هجوم الضيف"), ("defence_away_x", "دفاع الضيف")):
                        if abs(b[k] - a[k]) >= 0.01:
                            item["changes"].append({"kind": "rating", "text_ar": f"تقييم {lab}: {a[k]:.2f} ← {b[k]:.2f}"})
                except (TypeError, ValueError, KeyError):
                    pass
                if track == "sportradar":
                    item["changes"].append({"kind": "source", "text_ar": "SportRadar حدّث احتمالاته المنشورة"})
                if not item["changes"]:
                    item["changes"].append({"kind": "none", "text_ar": "ماكو تغيير بالمدخلات"})
                item["noise_ar"] = "حساب دقيق (بدون محاكاة)، فأي فرق هو تغيير حقيقي بالمدخلات" if track != "sportradar" else ""
            out.append(item)
            prev = {"p": item["p"], "model_version": r.model_version, "data_version": r.data_version,
                    "inputs": r.inputs if isinstance(r.inputs, str) else "{}"}
    return out


def _live_state(sr_id: str | float) -> dict | None:
    """Live / finished-match analysis written by scripts/live_run.py (data/live/<sr id>/report_*.json)."""
    if not isinstance(sr_id, str) or not sr_id:
        return None
    folder = os.path.join(LIVE, sr_id.replace(":", "_"))
    reps = {}
    for ph in ("HT", "FT"):
        p = os.path.join(folder, f"report_{ph}.json")
        if os.path.exists(p):
            reps[ph] = json.load(open(p, encoding="utf-8"))
    if not reps:
        return None
    last = reps.get("FT") or reps.get("HT")
    parts = {}
    for ph, rep in reps.items():
        for k, v in rep.get("stats", {}).items():
            key = "first_half" if (ph == "HT" and k == "full") else k
            parts[key] = v
    return {"phase": "FT" if "FT" in reps else "HT", "score": last.get("score"),
            "timeline": last.get("timeline", []), "events": last.get("events", []),
            "reports": {ph: {"insights": r.get("insights"), "notes": r.get("notes"), "now": r.get("now"),
                             "pre_match": r.get("pre_match"), "generated_at": r.get("generated_at", "")}
                        for ph, r in reps.items()},
            "stats": parts, "impact": last.get("impact_rows", []),
            "source": "SportRadar (team stats and key events) + Zahraa in-play model"}


def _data_notes(match_row, matches_cur: pd.DataFrame, names: dict) -> list[str]:
    notes = []
    for side in ("home", "away"):
        t = match_row[side]
        recent = matches_cur[(matches_cur["home"] == t) | (matches_cur["away"] == t)].sort_values("date").tail(5)
        miss = int(recent["odds_h"].isna().sum())
        if miss:
            notes.append(f"{miss} من آخر 5 مباريات لـ{names[t]['ar']} بدون أسعار سوق، فالمسار المدعوم بالسوق يعتمد على "
                         f"الأهداف والتسديدات بهاي المباريات")
    notes.append("التشكيلات والغيابات غير متوفرة بالمصادر المجانية: التوقع ما يعرف منو راح يلعب")
    return notes


# --------------------------------------------------------------------------

def team_cards(m, cur, fixtures, retro, fits, proj_rows, names, now) -> dict:
    """One card per current team."""
    disp = config.settings()["model"]["displayed_track"]
    rt = retro[disp].set_index("match_id")
    tf = {t: predict.team_factors(f).set_index("team") for t, f in fits.items()}
    pr = {r["team"]: r for r in proj_rows}
    fx = fixtures.copy()
    fx["ko"] = pd.to_datetime(fx["kickoff_utc"].replace("", np.nan), utc=True)
    cards = {}
    for t in sorted(set(cur["home"]) | set(cur["away"])):
        games = cur[(cur["home"] == t) | (cur["away"] == t)].sort_values("date")
        rows = []
        for g in games.itertuples():
            home = g.home == t
            gf, ga = (g.hg, g.ag) if home else (g.ag, g.hg)
            res = "W" if gf > ga else ("D" if gf == ga else "L")
            r = rt.loc[g.match_id] if g.match_id in rt.index else None
            xgf = (r["xg_home"] if home else r["xg_away"]) if r is not None else np.nan
            xga = (r["xg_away"] if home else r["xg_home"]) if r is not None else np.nan
            sot_f = g.hst if home else g.ast
            sot_a = g.ast if home else g.hst
            rows.append({"match_id": g.match_id, "date": g.date.strftime("%Y-%m-%d"), "home": home,
                         "opponent": team_id(g.away if home else g.home), "gf": int(gf), "ga": int(ga), "result": res,
                         "pts": 3 if res == "W" else (1 if res == "D" else 0),
                         "xg_for_pre": xgf, "xg_against_pre": xga, "sot_for": sot_f, "sot_against": sot_a,
                         "p_win_pre": ((r["p_home"] if home else r["p_away"]) if r is not None else np.nan)})
        df = pd.DataFrame(rows)
        # expected points from the pre-match forecasts (win prob * 3 + draw prob)
        if len(df):
            draws = [(rt.loc[mid, "p_draw"] if mid in rt.index else np.nan) for mid in df["match_id"]]
            df["p_draw_pre"] = draws
            df["xpts_pre"] = 3 * df["p_win_pre"] + df["p_draw_pre"]
        split = {}
        for side, sel in (("home", df["home"] if len(df) else []), ("away", ~df["home"] if len(df) else [])):
            sub = df[sel] if len(df) else df
            split[side] = {"played": int(len(sub)), "pts": int(sub["pts"].sum()) if len(sub) else 0,
                           "gf": int(sub["gf"].sum()) if len(sub) else 0, "ga": int(sub["ga"].sum()) if len(sub) else 0,
                           "ppg": float(sub["pts"].mean()) if len(sub) else None}
        # upcoming fixtures with difficulty (model expected points of this team) and rest days
        up = fx[((fx["home"] == t) | (fx["away"] == t)) & (fx["status"] != "played")].sort_values("ko").head(6)
        upcoming = []
        last_ko = pd.Timestamp(games["date"].max()).tz_localize("UTC") if len(games) else None
        prev_day = last_ko.normalize() if last_ko is not None else None
        for u in up.itertuples():
            home = u.home == t
            p = PRED_INDEX.get(u.match_id, {})
            xpts = 3 * (p.get("p_home") if home else p.get("p_away", np.nan)) + p.get("p_draw", np.nan) if p else np.nan
            # rest in calendar days between league matches (kick-off day when known, else the planned date)
            day = u.ko.tz_convert(config.tz()).tz_localize(None).normalize().tz_localize("UTC") if pd.notna(u.ko) \
                else pd.Timestamp(u.date).tz_localize("UTC")
            rest = int((day - prev_day).days) if prev_day is not None else None
            upcoming.append({"match_id": u.match_id, "opponent": team_id(u.away if home else u.home), "home": home,
                             "kickoff": baghdad(u.ko) if pd.notna(u.ko) else {"date": u.date, "time": "", "weekday_ar": ""},
                             "time_confirmed": bool(pd.notna(u.ko)),
                             "xpts": xpts, "difficulty": (None if not np.isfinite(xpts) else round(3 - xpts, 2)),
                             "rest_days": rest})
            prev_day = day
        hist_ratings = RATING_HISTORY.get(t, [])
        cards[team_id(t)] = {
            "team": names[t], "form": rows[-5:], "matches": rows,
            "totals": {"played": int(len(df)), "pts": int(df["pts"].sum()) if len(df) else 0,
                       "gf": int(df["gf"].sum()) if len(df) else 0, "ga": int(df["ga"].sum()) if len(df) else 0,
                       "xg_for_pre": float(df["xg_for_pre"].sum()) if len(df) else 0,
                       "xg_against_pre": float(df["xg_against_pre"].sum()) if len(df) else 0,
                       "xpts_pre": float(df["xpts_pre"].sum()) if len(df) else 0,
                       "sot_for": float(df["sot_for"].sum()) if len(df) else 0,
                       "sot_against": float(df["sot_against"].sum()) if len(df) else 0},
            "home_away": split,
            "ratings": {track: {"attack": float(tf[track].loc[t, "attack"]), "defence": float(tf[track].loc[t, "defence"])}
                        for track in tf},
            "rating_history": hist_ratings,
            "upcoming": upcoming,
            "season": pr.get(t),
            "absences": ({"status": "active", "rows": apifootball.absences_for(team_id(t)), "source": "API-Football"}
                         if apifootball.absences_for(team_id(t)) is not None else
                         {"status": "needs_key", "text_ar": "الغيابات تحتاج مصدر تشكيلات (API-Football): غير مفعّل. الخطوات بملف docs/ACTIVATION.md"}),
            "notes_ar": ["الأهداف المتوقعة هنا هي توقع ما قبل المباراة من الموديل، مو xG الفرص",
                         "أيام الراحة محسوبة من مباريات الدوري بس (الكأس والمباريات الأوروبية غير متوفرة)"],
        }
    return cards


PRED_INDEX: dict = {}
RATING_HISTORY: dict = {}


def rating_history(m: pd.DataFrame, season: int, track: str, cur: pd.DataFrame) -> dict:
    """Attack/defence multipliers of every team after each matchweek of the season (refits)."""
    out = {}
    dates = sorted(cur["date"].dt.normalize().unique())
    weeks = sorted(set(pd.Timestamp(d).to_period("W-MON").start_time for d in dates))
    for wk in weeks[1:] + [weeks[-1] + pd.Timedelta(days=7)]:
        try:
            fit = predict.fit_track(m, track, wk, season)
        except Exception:
            continue
        tf = predict.team_factors(fit).set_index("team")
        label = min(wk, pd.Timestamp(cur["date"].max()) + pd.Timedelta(days=1))   # data cut-off, never a future date
        for t in season_teams(m, season):
            out.setdefault(t, []).append({"date": label.strftime("%Y-%m-%d"), "attack": float(tf.loc[t, "attack"]),
                                          "defence": float(tf.loc[t, "defence"])})
    return out


# --------------------------------------------------------------------------

def accuracy_digest(report: dict, live_scored: tuple) -> dict:
    pre = report["prematch"]
    reg = report["registry"]
    per_match, summ = live_scored
    return {
        "generated_utc": report["generated_utc"], "registry": reg, "explain": report["explain"],
        "prematch": {k: {kk: vv for kk, vv in v.items() if kk != "breakdowns"} for k, v in pre.items()},
        "breakdowns": pre["test"].get("breakdowns", {}),
        "ablations": report["ablations"], "rest_days": report["rest_days"],
        "inplay": report["inplay"], "statsbomb": report["statsbomb"], "season": report["season"],
        "inplay_signal": _report("inplay_signal_test.json"), "rating_fairness": _report("player_rating_fairness.json"),
        "live_record": {"summary": summ.to_dict("records") if len(summ) else [],
                        "matches": per_match[["match_id", "track", "p_home", "p_draw", "p_away", "hg", "ag", "rps", "hit",
                                              "issued_at", "model_version"]].to_dict("records") if len(per_match) else []},
    }


def _report(name: str):
    p = os.path.join(REPORTS, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def _archive() -> tuple[dict, dict, list]:
    """Deep-analysis archive from outputs/dashboard/deep_*.csv (built by scripts/build_archive.py)."""
    base = os.path.join(OUTPUTS, "dashboard")
    if not os.path.exists(os.path.join(base, "deep_matches.csv")):
        return {"matches": []}, {}, []
    rd = {k: pd.read_csv(os.path.join(base, f"deep_{k}.csv")) for k in
          ("matches", "insights", "stats", "shots", "timeline", "touches", "pass_nodes", "pass_edges", "players")}
    tac_p = os.path.join(base, "deep_tactics.json")
    tactics = json.load(open(tac_p, encoding="utf-8")) if os.path.exists(tac_p) else {}
    index = {"matches": rd["matches"].to_dict("records"),
             "source": "StatsBomb Open Data (بيانات: StatsBomb)", "note_ar": "خرائط اللمسات من بيانات الأحداث (كل لمسة مسجلة)، مو بيانات تتبّع لكل حركة لاعب"}
    per = {}
    for mm in rd["matches"].itertuples():
        mid = mm.match_id
        sel = {k: v[v["match_id"] == mid] for k, v in rd.items() if k != "matches"}
        touches = sel["touches"]
        grids = {}
        for (side, period), g in touches.groupby(["side", "period"]):
            grids.setdefault(side, {})[int(period)] = _grid(g["x"].to_numpy(), g["y"].to_numpy())
        players_grid = {}
        for (side, pl), g in touches.groupby(["side", "player_ar"]):
            players_grid.setdefault(side, {})[pl] = {str(per): _grid(gg["x"].to_numpy(), gg["y"].to_numpy())
                                                     for per, gg in g.groupby("period")}
        per[mid] = {"match": mm._asdict(), "insights": sel["insights"].to_dict("records"),
                    "stats": sel["stats"].to_dict("records"), "shots": sel["shots"].to_dict("records"),
                    "timeline": sel["timeline"].to_dict("records"), "heat": grids, "heat_players": players_grid,
                    "pass_nodes": sel["pass_nodes"].to_dict("records"), "pass_edges": sel["pass_edges"].to_dict("records"),
                    "players": sel["players"].to_dict("records"), "tactics": tactics.get(mid)}
    return index, per, []


def _grid(x: np.ndarray, y: np.ndarray, nx: int = 24, ny: int = 16) -> dict:
    """Touch counts on a 24 x 16 grid of the 120 x 80 pitch (5-yard cells)."""
    h, _, _ = np.histogram2d(np.clip(x, 0, 119.99), np.clip(y, 0, 79.99), bins=[nx, ny], range=[[0, 120], [0, 80]])
    return {"nx": nx, "ny": ny, "n": int(len(x)), "cells": h.astype(int).T.tolist()}


# --------------------------------------------------------------------------

def build(now=None, n_sims: int | None = None, importance_days: int = 8, log=print, write: bool = True) -> dict:
    t_start = datetime.now(timezone.utc)
    s = config.settings()
    comp, season = config.competition(), config.season()
    now = pd.Timestamp(now) if now is not None else now_utc()
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    n_sims = n_sims or s["model"]["season_sims"]
    disp = s["model"]["displayed_track"]
    reg = predict.registry()
    man = store.manifest()
    m = load_snapshot()
    data_version = m.attrs.get("data_version", man.get("data_version", ""))
    fx = store.load_fixtures()
    cur = m[m["season"] == season].copy()
    teams = season_teams(m, season)
    names = {t: team_info(t) for t in set(m["home"]) | set(m["away"])}
    log(f"export: data {data_version}, {len(cur)} played, now {iso(now)}")

    # forecasts use every result in the data (cut-off = the day after the last result), so a forecast is a
    # pure function of (data version, model version) and can be reproduced from the snapshot
    ref = pd.Timestamp(cur["date"].max()).normalize() + pd.Timedelta(days=1) if len(cur) else now.tz_convert(None).normalize()
    fits = {t: predict.fit_track(m, t, ref, season) for t in predict.TRACKS}
    remaining = fx[fx["status"] != "played"].copy()
    preds = {t: predict.predict_matches(fits[t], remaining[["match_id", "home", "away"]]) for t in predict.TRACKS}
    PRED_INDEX.clear()
    for r in preds[disp].itertuples():
        PRED_INDEX[r.match_id] = {"p_home": r.p_home, "p_draw": r.p_draw, "p_away": r.p_away}
    fetched_at = man.get("built_at", "")
    if write:
        log_predictions(preds, fx, now, data_version, fetched_at)
    plog = predlog.read(PREMATCH_LOG)

    # season projection (displayed track) and changes since the previous snapshot
    drift = float(reg["season"]["drift_sd"])
    proj = seasonmod.projection(fits[disp], cur, teams, n_sims, drift)
    prev_season = {}
    prev_p = os.path.join(APP_DATA, "season.json")
    if os.path.exists(prev_p):
        try:
            prev_season = {r["team"]: r for r in json.load(open(prev_p, encoding="utf-8"))["projection"]}
        except (ValueError, KeyError):
            prev_season = {}
    changes = []
    for r in proj["rows"]:
        old = prev_season.get(r["team"])
        if not old:
            continue
        for key in [f"p_{p['key']}" for p in config.season_rules()["places"]]:
            if key in old and key in r:
                d = r[key] - old[key]
                se = np.sqrt(seasonmod.mc_se(r[key], n_sims) ** 2 + seasonmod.mc_se(old[key], old.get("n_sims", n_sims)) ** 2)
                if abs(d) >= 0.005:
                    changes.append({"team": r["team"], "metric": key, "before": old[key], "now": r[key], "delta_pts": 100 * d,
                                    "noise_pts": 100 * 2 * se, "is_noise": bool(abs(d) < 2 * se)})
    for r in proj["rows"]:
        r["n_sims"] = n_sims

    # importance of the upcoming matches (next `importance_days`)
    fx_ko = pd.to_datetime(remaining["kickoff_utc"].replace("", np.nan), utc=True)
    soon = remaining[(fx_ko > now) & (fx_ko <= now + pd.Timedelta(days=importance_days))]
    soon_p = preds[disp][preds[disp]["match_id"].isin(soon["match_id"])]
    imp = seasonmod.importance(fits[disp], cur, teams, soon_p, s["model"]["importance_sims"], drift) if len(soon_p) else []
    imp_index = {i["match_id"]: i for i in imp}
    log(f"  importance computed for {len(imp)} upcoming matches")

    # retro forecasts for played matches (both tracks) and the live log record
    retro = retro_predictions(m, season)
    results = cur[["match_id", "hg", "ag"]]
    kick = dict(zip(fx["match_id"], fx["kickoff_utc"]))
    live_scored = predlog.score(plog, results, kickoffs=kick) if len(plog) else (pd.DataFrame(), pd.DataFrame())

    RATING_HISTORY.clear()
    RATING_HISTORY.update(rating_history(m, season, disp, cur))
    cards = team_cards(m, cur, fx, retro, fits, proj["rows"], names, now)

    # ---- fixtures + match files -------------------------------------------------------
    pidx = {t: p.set_index("match_id") for t, p in preds.items()}
    ridx = {t: r.set_index("match_id") for t, r in retro.items()}
    sr = _latest_sportradar()
    sr_idx = {f"{comp}-{season}-{team_id(r.home)}-{team_id(r.away)}": r for r in sr.sort_values("fetched_at").itertuples()}
    cur_idx = cur.set_index("match_id")
    ip = InPlayModel.load(os.path.join(MODELS, "inplay.json"))
    # displayed-track rows of the pre-match log issued before each match's kick-off, oldest first
    log_idx = {}
    if len(plog):
        kmap = dict(zip(fx["match_id"], fx["kickoff_utc"]))
        dl = plog[plog["track"] == disp].copy()
        dl = dl[[predlog._ts(i) < predlog._ts(kmap.get(m_) or k_) for i, m_, k_ in zip(dl["issued_at"], dl["match_id"], dl["kickoff_utc"])]]
        for m_, g_ in dl.sort_values("issued_at").groupby("match_id"):
            log_idx[m_] = g_
    fixtures_out, match_files = [], {}
    for r in fx.itertuples():
        mid = r.match_id
        home, away = names[r.home], names[r.away]
        played = mid in cur_idx.index
        ko = r.kickoff_utc if isinstance(r.kickoff_utc, str) and r.kickoff_utc else ""
        live = _live_state(r.sr_id)
        status = r.status
        if live and not played:
            status = "HT" if live["phase"] == "HT" else status
        row = {"match_id": mid, "matchday": int(r.matchday), "kickoff_utc": ko, "kickoff_baghdad": baghdad(ko) if ko else
               {"date": r.date, "time": "", "weekday_ar": ""}, "home": home["id"], "away": away["id"],
               "status": status, "status_ar": STATUS_AR.get(status, status), "score": None, "ht": None,
               "has_live": bool(live), "importance": imp_index.get(mid, {}).get("importance"),
               "live_score": live.get("score") if live and not played else None}
        tracks = {}
        facts = None
        if played:
            g = cur_idx.loc[mid]
            row["score"] = [int(g["hg"]), int(g["ag"])]
            if pd.notna(g["hthg"]):
                row["ht"] = [int(g["hthg"]), int(g["htag"])]
            odds = [g["odds_h"], g["odds_d"], g["odds_a"]]
            implied = None
            if all(pd.notna(o) and o > 1 for o in odds):
                inv = [1 / o for o in odds]
                implied = [v / sum(inv) for v in inv]
            facts = {"sot": [g["hst"], g["ast"]] if pd.notna(g["hst"]) else None,
                     "ht": row["ht"], "odds": odds if implied else None, "market_p": implied,
                     "sources": {"result": g["result_source"], "stats": g["stats_source"] or None,
                                 "half_time": g["ht_source"] or None, "odds": g["odds_source"] or None},
                     "missing": [lab for lab, ok in (("odds", implied is not None), ("shots_on_target", pd.notna(g["hst"])),
                                                     ("half_time", pd.notna(g["hthg"]))) if not ok]}
            for t in predict.TRACKS:
                if mid in ridx[t].index:
                    rr = ridx[t].loc[mid]
                    y = outcome_index([g["hg"]], [g["ag"]])
                    pm = np.array([[rr["p_home"], rr["p_draw"], rr["p_away"]]])
                    tracks[t] = {"kind": "retro", "p": pm[0].tolist(), "xg": [rr["xg_home"], rr["xg_away"]],
                                 "rps": float(rps(pm, y)[0]), "hit": bool(pm.argmax() == y[0]),
                                 "top_scores": [[f"{int(rr['likely_hg'])}-{int(rr['likely_ag'])}", rr["p_likely"]]],
                                 "label_ar": "توقع استرجاعي: بنفس الموديل وبيانات ما قبل الأسبوع فقط"}
        else:
            for t in predict.TRACKS:
                if mid in pidx[t].index:
                    pp = pidx[t].loc[mid]
                    tracks[t] = {"kind": "prematch", "p": [pp["p_home"], pp["p_draw"], pp["p_away"]],
                                 "xg": [pp["xg_home"], pp["xg_away"]], "rho": pp["rho"],
                                 "top_scores": [[pp[f"score{k}"], pp[f"p_score{k}"]] for k in (1, 2, 3)],
                                 "reasons": predict.explain({**pp.to_dict(), "home": r.home, "away": r.away},
                                                            {k: v["ar"] for k, v in names.items()}),
                                 "inputs": json.loads(pp["inputs"]),
                                 "model_version": predict.model_version(t), "data_version": data_version,
                                 "issued_at": iso(now)}
        if mid in sr_idx:
            q = sr_idx[mid]
            tot = q.p_home + q.p_draw + q.p_away
            tracks["sportradar"] = {"kind": "published", "p": [q.p_home / tot, q.p_draw / tot, q.p_away / tot],
                                    "issued_at": q.fetched_at}
        shown = tracks.get(disp)
        if shown:
            row["p"] = shown["p"]
            row["xg"] = shown.get("xg")
            if shown.get("top_scores"):
                row["top_score"] = shown["top_scores"][0][0]
            if played and "hit" in shown:
                row["retro_hit"] = shown["hit"]
        if "sportradar" in tracks:
            row["p_sr"] = tracks["sportradar"]["p"]
        # the forecast logged before kick-off (the one the track record scores) and the previous version
        lg = log_idx.get(mid)
        if lg is not None and len(lg):
            last = lg.iloc[-1]
            row["logged"] = {"p": [float(last["p_home"]), float(last["p_draw"]), float(last["p_away"])],
                             "score": last["score1"] if isinstance(last["score1"], str) else None,
                             "issued_at": last["issued_at"], "model_version": last["model_version"]}
            if shown and not played:
                cur_p = np.array(shown["p"])
                same = np.allclose(cur_p, row["logged"]["p"], atol=1e-6)
                prev = lg.iloc[-2] if same and len(lg) >= 2 else (None if same else last)
                if prev is not None:
                    row["prev_p"] = [float(prev["p_home"]), float(prev["p_draw"]), float(prev["p_away"])]
                    row["prev_issued_at"] = prev["issued_at"]
        takeaway = ""
        if shown:
            takeaway = predict.favourite_line({"p_home": shown["p"][0], "p_draw": shown["p"][1], "p_away": shown["p"][2],
                                               "home": r.home, "away": r.away}, names)
            row["takeaway_ar"] = takeaway
        fixtures_out.append(row)
        mf = {**row, "home_team": home, "away_team": away, "displayed_track": disp, "tracks": tracks,
              "takeaway_ar": takeaway, "history": history_for(plog, mid), "external_ids": {"sportradar": r.sr_id}
              if isinstance(r.sr_id, str) else {}, "data_notes": _data_notes({"home": r.home, "away": r.away}, cur, names),
              "importance": imp_index.get(mid), "live": live, "facts": facts,
              "lineups": apifootball.lineups_for(mid)}
        if shown and not played:
            mf["scenario_inputs"] = {"lam": shown["xg"][0], "mu": shown["xg"][1], "rho": tracks[disp]["rho"],
                                     "inplay": ip.to_json()}
        match_files[mid] = mf

    kid = {k: v["id"] for k, v in names.items()}
    for r in proj["rows"]:
        r["id"] = kid[r["team"]]
    for c in changes:
        c["id"] = kid[c["team"]]
    for i in imp:
        i["home_id"], i["away_id"] = kid[i["home"]], kid[i["away"]]
        for sw in i["swings"]:
            sw["team_id"] = kid[sw["team"]]
    table = seasonmod.current_table(cur, teams)
    for r in table:
        r["id"] = kid[r["team"]]
    whatif = seasonmod.whatif_inputs(fits[disp], cur, teams, preds[disp].merge(remaining[["match_id"]]), drift)
    whatif["team_ids"] = [kid[t] for t in whatif["teams"]]
    ratings = {}
    for t, f in fits.items():
        rr = predict.team_factors(f)
        rr = rr[rr["team"].isin(teams)].copy()
        rr["id"] = rr["team"].map(kid)
        ratings[t] = rr.to_dict("records")
    season_out = {
        "competition": comp, "season": season, "season_label": s["competition"]["season_label"],
        "generated_utc": iso(now), "n_sims": n_sims, "drift_sd": drift, "displayed_track": disp,
        "table": table, "projection": proj["rows"], "changes": changes,
        "ratings": ratings,
        "whatif": whatif,
        "importance": imp, "rules": {**config.season_rules(), "tiebreak": config.rules()["tiebreak"]},
        "mc_note_ar": f"النسب من {n_sims:,} موسم محاكى؛ الخطأ العشوائي بحدود ±{100 * 2 * seasonmod.mc_se(0.5, n_sims):.1f} نقطة مئوية لنسبة 50٪",
    }

    report = json.load(open(os.path.join(REPORTS, "evaluation.json"), encoding="utf-8"))
    acc = accuracy_digest(report, live_scored)
    arch_index, arch_matches, _ = _archive()
    players = _players_archive()
    from . import stories as storymod
    st = storymod.discover(cards, proj["rows"], imp, retro[disp], cur, names, arch_matches, players)

    status = store.status()
    meta = {
        "platform": s["platform"], "generated_utc": iso(now), "timezone": s["timezone"],
        "competition": {**s["competition"], "rules": config.season_rules()},
        "versions": {"platform": s["platform"]["version"], "data": data_version,
                     "prematch_market": reg["prematch_market"]["version"],
                     "prematch_independent": reg["prematch_independent"]["version"],
                     "inplay": reg["inplay"]["version"], "season": reg["season"]["version"]},
        "displayed_track": disp, "tracks_ar": predict.TRACK_AR,
        "data_status": {"last_build": man.get("built_at"), "last_build_ok": status.get("last_build_ok", True),
                        "last_good_build": status.get("last_good_build", man.get("built_at")),
                        "last_update_attempt": status.get("last_update_attempt"), "update_problems": status.get("problems", []),
                        "fetch": status.get("fetch", {}), "coverage": man.get("coverage_by_season", [])[-3:],
                        "gaps": man.get("current_season_gaps", []), "checks_ok": all(c["ok"] for c in man.get("checks", [])),
                        "n_checks": len(man.get("checks", [])), "warnings": man.get("warnings", []),
                        "corrections": man.get("corrections", [])},
        "sources": s["sources"], "glossary": GLOSSARY,
        "features": features(),
    }
    teams_out = {names[t]["id"]: names[t] for t in names}
    files = {"meta.json": meta, "teams.json": {"teams": teams_out, "current": [names[t]["id"] for t in teams],
                                               "key_to_id": kid},
             "fixtures.json": {"generated_utc": iso(now), "fixtures": fixtures_out}, "season.json": season_out,
             "accuracy.json": acc, "archive/index.json": arch_index, "players.json": players, "stories.json": st}
    # match centre files grouped by matchday (38 files instead of 380: quicker to publish and to cache)
    by_md: dict = {}
    for mid, mf in match_files.items():
        by_md.setdefault(int(mf["matchday"]), {})[mid] = mf
    for md, group in by_md.items():
        files[f"matches/md{md:02d}.json"] = {"matchday": md, "matches": group}
    for tid, c in cards.items():
        files[f"teams/{tid}.json"] = c
    for mid, a in arch_matches.items():
        files[f"archive/{mid}.json"] = a
    # version 3: Premier League and Champions League files (built by `python -m zsc multi`) ride along
    try:
        from .multi import stored_files
        for rel, obj in stored_files().items():
            files.setdefault(rel, obj)
        if "comps.json" in files:   # the app asks only for free-source files that exist
            files["comps.json"] = {**files["comps.json"], "free": sorted(k[5:] for k in files if k.startswith("free/"))}
    except Exception as e:  # never let the other competitions block a La Liga update
        log(f"  multi-competition files skipped: {e}")
    if write:
        stamp = write_snapshot(files, log=log)
        log(f"  snapshot {stamp}: {len(files)} files in {(datetime.now(timezone.utc) - t_start).seconds}s")
    return files


def features() -> list[dict]:
    out = []
    af = apifootball.status()
    for f in FEATURES:
        f = dict(f)
        if f["key"] == "lineups":
            f["status"] = af["status"]
            f["needs_ar"] = af["text_ar"] if af["status"] != "active" else "مفعّل (API-Football)"
        out.append(f)
    return out


FEATURES = [
    {"key": "prematch", "ar": "توقعات ما قبل المباراة (مساران)", "status": "active"},
    {"key": "season", "ar": "محاكاة الموسم وسيناريوهات «ماذا لو؟»", "status": "active"},
    {"key": "multi", "ar": "البريميرليغ ودوري الأبطال (مصادر مجانية)", "status": "active",
     "needs_ar": "`python -m zsc multi`؛ المصادر: openfootball وfootball-data (GitHub) وClubElo عبر xgabora وSportRadar عبر Claude"},
    {"key": "live_layer", "ar": "النتائج والأحداث والتشكيلات والاحتمالات المباشرة (ESPN، البطولات الثلاث)", "status": "partial",
     "needs_ar": "تلقائي على GitHub Actions كل 5 دقايق بأوقات المباريات (بعد تفعيل GitHub Pages)؛ حوالي 30 ثانية مع بروكسي Cloudflare الاختياري. docs/LIVE.md"},
    {"key": "live", "ar": "التحليل المباشر بنهاية كل شوط", "status": "partial",
     "needs_ar": "تقارير الشوط من جلسات Claude (SportRadar)؛ الاحتمالات المباشرة وقراءة المباراة من ملف ESPN تلقائياً"},
    {"key": "lab", "ar": "سجل المواجهات ومختبر التحقق", "status": "active",
     "needs_ar": "الدوري الإسباني من 1993/94 والإنجليزي من 2000/01؛ مباريات الدوري فقط"},
    {"key": "english", "ar": "الواجهة الإنجليزية", "status": "active"},
    {"key": "pwa", "ar": "تثبيت التطبيق على الموبايل والعمل بدون إنترنت", "status": "active"},
    {"key": "lineups", "ar": "التشكيلات والغيابات", "status": "free_adapter",
     "needs_ar": "مجاني: ESPN (تشكيلات الثلاث بطولات) وFPL (إصابات البريميرليغ)؛ يشتغل على جهازج أو GitHub لأن رابط Claude ما يوصل لهالمواقع"},
    {"key": "live_xg", "ar": "xG وخرائط تسديد للمباريات الحالية", "status": "free_adapter",
     "needs_ar": "مجاني: Understat (لاليغا والبريميرليغ، مو دوري الأبطال)؛ الخرائط الحرارية الكاملة تبقى من StatsBomb المفتوح (أرشيف)"},
    {"key": "players_now", "ar": "إحصائيات لاعبي الموسم الحالي", "status": "free_adapter",
     "needs_ar": "مجاني: FPL (البريميرليغ: دقائق، أهداف، xG، xA) وUnderstat (لاليغا والبريميرليغ)"},
    {"key": "news", "ar": "الأخبار", "status": "active",
     "needs_ar": "قصص الحاسوب شغالة؛ عناوين المواقع من خلاصات RSS المجانية عند التشغيل على جهازج أو GitHub"},
    {"key": "archive", "ar": "التحليل العميق (أرشيف StatsBomb)", "status": "active"},
    {"key": "audience", "ar": "تحدي الجمهور", "status": "active_local",
     "needs_ar": "مجاناً: بطاقة الاستوديو + استفتاء إنستغرام/تيك توك؛ أو رابط Claude لأصحاب الحسابات؛ أو Supabase بخطته المجانية"},
    {"key": "alerts", "ar": "التنبيهات", "status": "free_adapter",
     "needs_ar": "مجاناً: ntfy.sh (تطبيق ntfy على الموبايل) أو بوت تيليغرام؛ يرسلها التحديث التلقائي"},
]


def _players_archive() -> dict:
    p = os.path.join(OUTPUTS, "archive", "players_1516.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {"players": [], "status": "not_built"}


def write_snapshot(files: dict, log=print) -> str:
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    folder = os.path.join(SNAPSHOTS, stamp)
    for rel, obj in files.items():
        path = os.path.join(folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_clean(obj), f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(folder, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"stamp": stamp, "files": sorted(files)}, f)
    publish_snapshot(stamp)
    keep = config.settings()["update"]["keep_snapshots"]
    olds = sorted(d for d in os.listdir(SNAPSHOTS) if os.path.isdir(os.path.join(SNAPSHOTS, d)))
    for d in olds[:-keep]:
        shutil.rmtree(os.path.join(SNAPSHOTS, d), ignore_errors=True)
    return stamp


def publish_snapshot(stamp: str) -> None:
    """Make snapshots/<stamp> the app's current data (atomic directory swap)."""
    src = os.path.join(SNAPSHOTS, stamp)
    tmp = APP_DATA + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(src, tmp)
    old = APP_DATA + ".old"
    shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(APP_DATA):
        os.replace(APP_DATA, old)
    os.replace(tmp, APP_DATA)
    shutil.rmtree(old, ignore_errors=True)
