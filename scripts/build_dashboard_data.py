"""Refresh every table the app reads (outputs/dashboard/*.csv).

    python scripts/build_dashboard_data.py [--date 2026-10-24] [--sportradar data/live/<scores>.json]

1. season forecast (runs run_forecast.py)
2. fixtures and results for the whole season, Baghdad time, with predictions
3. accuracy (match + in-play backtests) and the in-play calibration
4. track record of logged pre-match predictions
5. the model facts the method text quotes
6. empty live tables if no live run has happened yet
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import RAW_OPENFOOTBALL, RAW_SPORTRADAR  # noqa: E402

from zsc.data import remaining_fixtures  # noqa: E402
from zsc.dixon_coles import fit_dixon_coles  # noqa: E402
from zsc.fixtures import build_fixtures, load_openfootball  # noqa: E402
from zsc.forecast import load_settings  # noqa: E402
from zsc.impact import IMPACT_SIMS  # noqa: E402
from zsc.pipeline import load_snapshot, promoted_teams, season_teams  # noqa: E402
from zsc.teams import arabic  # noqa: E402
from zsc.tracking import score_log, sportradar_fixtures  # noqa: E402

DASH = os.path.join(ROOT, "outputs", "dashboard")
LIVE_COLS = {
    "live_matches": ["event_id", "kickoff_utc", "date_baghdad", "time_baghdad", "home", "away", "home_ar", "away_ar",
                     "status", "status_ar", "hg", "ag", "pre_home_pct", "pre_draw_pct", "pre_away_pct", "now_home_pct",
                     "now_draw_pct", "now_away_pct", "likely_final", "xg_home_pre", "xg_away_pre", "updated_utc"],
    "live_insights": ["event_id", "phase", "row_id", "side", "team_ar", "kind", "rank", "text"],
    "live_stats": ["event_id", "part", "part_ar", "stat", "row_id", "label_ar", "home", "away"],
    "live_timeline": ["event_id", "minute", "hg", "ag", "p_home", "p_draw", "p_away", "row_id"],
    "live_impact": ["event_id", "row_id", "team", "team_ar", "metric", "label_ar", "before_pct", "now_pct", "change_pts"],
}
SOURCE_AR = {"model": "حاسوب زهراء الخارق", "sportradar": "SportRadar"}


def latest_sportradar():
    files = sorted(glob.glob(os.path.join(RAW_SPORTRADAR, "scores_*.json")))
    return files[-1] if files else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=pd.Timestamp.now("UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--sportradar", default=None)
    ap.add_argument("--sims", type=int, default=10_000)
    a = ap.parse_args()

    # 1. season forecast
    subprocess.run([sys.executable, os.path.join(ROOT, "run_forecast.py"), "--date", a.date, "--sims", str(a.sims)],
                   check=True, stdout=subprocess.DEVNULL)

    m = load_snapshot()
    cfg, drift = load_settings(os.path.join(ROOT, "outputs"))
    season = int(m["season"].max())
    teams = season_teams(m, season)
    played = m[m["season"] == season]
    fit = fit_dixon_coles(m, pd.Timestamp(a.date) + pd.Timedelta(days=1), cfg, current_teams=teams,
                          promoted=promoted_teams(m, season), current_season=season)

    # 2. fixtures
    rem = remaining_fixtures(played, teams)
    pred = fit.predict(rem["home"], rem["away"])
    sr_path = a.sportradar or latest_sportradar()
    sr = sportradar_fixtures(sr_path) if sr_path else None
    sch = load_openfootball(RAW_OPENFOOTBALL)
    fx = build_fixtures(sch, played, pred, sr, today=a.date)
    fx.to_csv(os.path.join(DASH, "fixtures.csv"), index=False)

    # 3. accuracy: add the in-play rows and calibration
    acc_p = os.path.join(DASH, "accuracy.csv")
    acc = pd.read_csv(acc_p)
    acc = acc[~acc["id"].isin(["ht_rps", "ht_hit"])]
    rep = json.load(open(os.path.join(ROOT, "outputs", "inplay_report.json")))
    wf = rep["half_time_walk_forward"]
    ch = wf[rep["chosen"]]
    pre = wf["pre-match only"]
    per = f"{rep['test_seasons'][0]}/{(rep['test_seasons'][0] + 1) % 100:02d}-{rep['test_seasons'][1]}/{(rep['test_seasons'][1] + 1) % 100:02d}"
    n_ht = sum(r["n"] for r in rep["calibration"]) // 3
    acc = pd.concat([acc, pd.DataFrame([
        {"id": "ht_rps", "ar": "توقع النتيجة النهائية وقت الاستراحة (RPS، أقل أحسن)", "model": round(ch["rps"], 4),
         "bookmaker": None, "baseline": round(pre["rps"], 4), "unit": "", "period": per, "n": n_ht},
        {"id": "ht_hit", "ar": "إصابة النتيجة النهائية وقت الاستراحة", "model": round(100 * ch["hit"], 1),
         "bookmaker": None, "baseline": round(100 * pre["hit"], 1), "unit": "%", "period": per, "n": n_ht},
    ])], ignore_index=True)
    acc.to_csv(acc_p, index=False)
    cal = pd.DataFrame(rep["calibration"])
    cal["bin_ar"] = [f"{100 * lo:.0f}-{100 * min(hi, 1):.0f}٪" for lo, hi in zip(cal["lo"], cal["hi"])]
    cal["forecast_pct"] = (100 * cal["forecast"]).round(1)
    cal["observed_pct"] = (100 * cal["observed"]).round(1)
    cal[["bin_ar", "n", "forecast_pct", "observed_pct"]].to_csv(os.path.join(DASH, "inplay_calibration.csv"), index=False)

    # 4. track record
    log_p = os.path.join(ROOT, "data", "predictions", "log.csv")
    log = pd.read_csv(log_p) if os.path.exists(log_p) else pd.DataFrame()
    per_match, summ = score_log(log, played) if len(log) else (pd.DataFrame(), pd.DataFrame())
    track_cols = ["row_id", "home_ar", "away_ar", "score", "source", "source_ar", "p_home", "p_draw", "p_away", "rps", "hit"]
    if len(per_match):
        per_match = per_match.copy()
        per_match["row_id"] = per_match["home"] + "|" + per_match["away"] + "|" + per_match["source"]
        per_match["home_ar"] = per_match["home"].map(arabic)
        per_match["away_ar"] = per_match["away"].map(arabic)
        per_match["score"] = per_match["hg"].astype(int).astype(str) + "-" + per_match["ag"].astype(int).astype(str)
        per_match["source_ar"] = per_match["source"].map(SOURCE_AR)
        for c in ("p_home", "p_draw", "p_away"):
            per_match[c] = (100 * per_match[c]).round(1)
        per_match["rps"] = per_match["rps"].round(4)
        per_match[track_cols].to_csv(os.path.join(DASH, "track.csv"), index=False)
    else:
        pd.DataFrame(columns=track_cols).to_csv(os.path.join(DASH, "track.csv"), index=False)
    if len(summ):
        summ["source_ar"] = summ["source"].map(SOURCE_AR)
        summ["rps"] = summ["rps"].round(4)
        summ["hit_pct"] = (100 * summ["hit"]).round(1)
        summ[["source", "source_ar", "n", "rps", "hit_pct"]].to_csv(os.path.join(DASH, "track_summary.csv"), index=False)
    else:
        pd.DataFrame(columns=["source", "source_ar", "n", "rps", "hit_pct"]).to_csv(
            os.path.join(DASH, "track_summary.csv"), index=False)
    logged = log.groupby("source").size().to_dict() if len(log) else {}

    # 5. the model facts quoted in the method text
    sb = rep["statsbomb"]
    facts = pd.DataFrame([
        ("first_half_pct", "نسبة الأهداف بالشوط الأول (٪)", f"{100 * rep['first_half_share']:.0f}"),
        ("state_matches", "مباريات اختبار أثر النتيجة وقت الاستراحة", f"{n_ht:,}"),
        ("red_own_pct", "نقص تسجيل الفريق اللي انطرد منه لاعب (٪)", f"{100 * (1 - sb['red_own']):.0f}"),
        ("red_opp_pct", "زيادة تسجيل خصمه (٪)", f"{100 * (sb['red_opp'] - 1):.0f}"),
        ("red_matches", "مباريات بيها طرد (StatsBomb 2015/16)", f"{sb['red_matches']:,}"),
        ("impact_sims", "مواسم محاكاة لأثر كل مباراة", f"{IMPACT_SIMS:,}"),
    ], columns=["id", "ar", "value"])
    facts.to_csv(os.path.join(DASH, "model_facts.csv"), index=False)

    # 6. live tables exist
    for name, cols in LIVE_COLS.items():
        p = os.path.join(DASH, f"{name}.csv")
        if not os.path.exists(p):
            pd.DataFrame(columns=cols).to_csv(p, index=False)

    print(f"fixtures: {len(fx)} ({(fx['status'] == 'played').sum()} played); track: {len(per_match)} scored rows; "
          f"logged predictions: {logged}")


if __name__ == "__main__":
    main()
