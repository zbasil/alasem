"""Tables (CSV files) that feed the results dashboard."""

from __future__ import annotations

import os

import pandas as pd


def _pct(x: float) -> float:
    return round(100.0 * float(x), 1)


def uk_to_baghdad(date: str, time_uk: str) -> str:
    """'2026-10-25', '20:00' (UK local time) -> '23:00' (Baghdad). Empty if unknown."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        t = datetime.strptime(f"{date} {time_uk}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/London"))
        return t.astimezone(ZoneInfo("Asia/Baghdad")).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def dashboard_tables(data: dict, accuracy: list[dict] | None = None) -> dict[str, pd.DataFrame]:
    """data = zsc.forecast.to_json(...) output."""
    out = {}
    nr = data.get("next_round", [])
    out["run_info"] = pd.DataFrame([{
        "season": data["season"], "as_of": data["as_of"], "matches_played": data["matches_played"],
        "n_sims": data["n_sims"], "n_sims_text": f"{data['n_sims']:,}", "next_matches": len(nr),
    }])
    out["forecast"] = pd.DataFrame([{
        "team": t["team"], "ar": t["ar"], "en": t["en"],
        "pts_now": t["pts_now"], "exp_pts": round(t["exp_pts"]),
        "pts_low": int(round(t["pts_p10"])), "pts_high": int(round(t["pts_p90"])),
        "title_pct": _pct(t["p_title"]), "top4_pct": _pct(t["p_top4"]),
        "europe_pct": _pct(t["p_top6"]), "releg_pct": _pct(t["p_releg"]),
        "exp_pos": round(t["exp_pos"], 1),
    } for t in data["teams"]])
    # title contenders first (the dashboard's three tiles read rows 0-2)
    out["forecast"] = out["forecast"].sort_values(["title_pct", "exp_pts"], ascending=False).reset_index(drop=True)
    out["positions"] = pd.DataFrame([{
        "team": t["team"], "ar": t["ar"], "pos": k + 1, "pct": _pct(p)}
        for t in data["teams"] for k, p in enumerate(t["pos"])])
    out["next_round"] = pd.DataFrame([{
        "match": f"{m['home']} v {m['away']}", "date": m["date"], "time_uk": m["time_uk"],
        "time_baghdad": uk_to_baghdad(m["date"], m["time_uk"]),
        "home": m["home"], "away": m["away"], "home_ar": m["home_ar"], "away_ar": m["away_ar"],
        "home_pct": _pct(m["p_home"]), "draw_pct": _pct(m["p_draw"]), "away_pct": _pct(m["p_away"]),
        "xg_home": m["xg_home"], "xg_away": m["xg_away"],
        "likely_score": m["likely_score"], "likely_score_pct": _pct(m["p_likely_score"]),
    } for m in nr])
    out["table_now"] = pd.DataFrame([{
        "pos": r["pos"], "team": r["team"], "ar": r["ar"], "P": r["P"], "W": r["W"], "D": r["D"],
        "L": r["L"], "GF": r["GF"], "GA": r["GA"], "GD": r["GD"], "Pts": r["Pts"]} for r in data["table"]])
    out["ratings"] = pd.DataFrame([{
        "team": r["team"], "ar": r["ar"], "xg_for": r["xg_for"], "xg_against": r["xg_against"],
        "xgd": r["xgd"]} for r in data["ratings"]])
    if accuracy:
        out["accuracy"] = pd.DataFrame(accuracy)
    return out


def accuracy_rows(backtest: dict, season_bt: dict, test_preds: pd.DataFrame) -> list[dict]:
    """Headline accuracy figures from scripts/tune.py and scripts/season_backtest.py.

    test_preds: outputs/backtest_predictions_test.csv (held-out matches)."""
    from .evaluate import outcome_index
    from .market import implied_1x2
    y = outcome_index(test_preds["hg"], test_preds["ag"])
    pm = test_preds[["p_home", "p_draw", "p_away"]].values
    pk = implied_1x2(test_preds["odds_h"], test_preds["odds_d"], test_preds["odds_a"])
    backtest = dict(backtest)
    backtest["hit_model"] = float((pm.argmax(1) == y).mean())
    backtest["hit_market"] = float((pk.argmax(1) == y).mean())
    backtest["hit_home"] = float((y == 0).mean())          # always pick the home team
    fm = backtest["final_model"]
    backtest["skill_share"] = 100 * (fm["rps_base_rates"] - fm["rps"]) / (fm["rps_base_rates"] - fm["rps_mkt"])
    sm = season_bt["metrics"]
    seasons = backtest["test_seasons"]
    period = f"{seasons[0]}/{(seasons[0] + 1) % 100:02d}-{seasons[-1]}/{(seasons[-1] + 1) % 100:02d}"
    rows = [
        {"id": "rps", "ar": "خطأ الاحتمالات (RPS) — كل ما أقل أحسن", "model": round(fm["rps"], 4),
         "bookmaker": round(fm["rps_mkt"], 4), "baseline": round(fm["rps_base_rates"], 4),
         "unit": "", "period": period, "n": fm["n"]},
        {"id": "hit", "ar": "نسبة إصابة النتيجة (فوز/تعادل/خسارة)", "model": round(100 * backtest["hit_model"], 1),
         "bookmaker": round(100 * backtest["hit_market"], 1), "baseline": round(100 * backtest["hit_home"], 1),
         "unit": "%", "period": period, "n": fm["n"]},
        {"id": "skill", "ar": "نسبة دقة الموديل من دقة شركات المراهنات", "model": round(backtest["skill_share"], 1),
         "bookmaker": 100.0, "baseline": 0.0, "unit": "%", "period": period, "n": fm["n"]},
        {"id": "points", "ar": "متوسط خطأ النقاط النهائية (توقع من الجولة 10)", "model": round(sm["points_MAE"], 1),
         "bookmaker": None, "baseline": round(sm["naive_points_MAE"], 1), "unit": "نقطة",
         "period": f"{season_bt['seasons'][0]}/{(season_bt['seasons'][0] + 1) % 100:02d}-"
                   f"{season_bt['seasons'][-1]}/{(season_bt['seasons'][-1] + 1) % 100:02d}",
         "n": sm["teams"]},
        {"id": "coverage", "ar": "مرات وقوع النقاط الحقيقية داخل مدى الـ80%", "model": round(100 * sm["coverage_80"], 1),
         "bookmaker": None, "baseline": 80.0, "unit": "%",
         "period": f"{season_bt['seasons'][0]}/{(season_bt['seasons'][0] + 1) % 100:02d}-"
                   f"{season_bt['seasons'][-1]}/{(season_bt['seasons'][-1] + 1) % 100:02d}",
         "n": sm["teams"]},
    ]
    return rows


def write_tables(tables: dict[str, pd.DataFrame], folder: str) -> list[str]:
    os.makedirs(folder, exist_ok=True)
    paths = []
    for name, df in tables.items():
        p = os.path.join(folder, f"{name}.csv")
        df.to_csv(p, index=False, encoding="utf-8")
        paths.append(p)
    return paths
