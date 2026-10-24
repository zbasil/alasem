"""End-to-end forecast for the current season."""

from __future__ import annotations

import json
import os
from dataclasses import asdict

import numpy as np
import pandas as pd

from .dixon_coles import DCConfig, fit_dixon_coles
from .pipeline import promoted_teams, season_teams
from .simulate import simulate_season
from .standings import league_table
from .teams import arabic, english


def load_settings(outputs_dir: str):
    """Tuned model settings (from scripts/tune.py and scripts/season_backtest.py)."""
    with open(os.path.join(outputs_dir, "best_config.json")) as f:
        cfg = DCConfig(**json.load(f))
    drift = 0.05
    sb = os.path.join(outputs_dir, "season_backtest.json")
    if os.path.exists(sb):
        with open(sb) as f:
            drift = float(json.load(f)["chosen_drift_sd"])
    return cfg, drift


def run_forecast(matches: pd.DataFrame, season: int, ref_date, cfg: DCConfig, drift_sd: float,
                 upcoming: pd.DataFrame | None = None, n_sims: int = 10_000, seed: int = 2026,
                 overrides: pd.DataFrame | None = None) -> dict:
    """overrides: optional (home, away, mkt_lh, mkt_la) market expected goals
    for the next fixtures, used instead of the model for those games."""
    ref_date = pd.Timestamp(ref_date)
    teams = season_teams(matches, season)
    played = matches[(matches["season"] == season) & (matches["date"] < ref_date)]
    fit = fit_dixon_coles(matches, ref_date, cfg, current_teams=teams,
                          promoted=promoted_teams(matches, season), current_season=season)
    # spread calibrated on 14 past seasons (see scripts/season_backtest.py)
    sim = simulate_season(fit, played, teams, n_sims=n_sims, drift_sd=drift_sd,
                          parameter_uncertainty=False, overrides=overrides, seed=seed)

    summary = sim.summary()
    table = league_table(played, teams)

    # team ratings on an easy scale: expected goal difference per game
    # against an average team on neutral ground
    idx = fit.index
    att_s, dfn_s = fit.scaled()
    ratings = pd.DataFrame({"team": teams})
    ratings["attack"] = [att_s[idx[t]] for t in teams]
    ratings["defence"] = [dfn_s[idx[t]] for t in teams]
    mean_a = ratings["attack"].mean()
    mean_d = ratings["defence"].mean()
    base = np.exp(fit.c + fit.h / 2)
    ratings["xg_for"] = base * np.exp(ratings["attack"] - mean_d)
    ratings["xg_against"] = base * np.exp(mean_a - ratings["defence"])
    ratings["xgd_per_game"] = ratings["xg_for"] - ratings["xg_against"]
    ratings = ratings.sort_values("xgd_per_game", ascending=False).reset_index(drop=True)

    out = {"fit": fit, "sim": sim, "summary": summary, "table": table, "ratings": ratings,
           "played": played, "config": cfg, "drift_sd": drift_sd, "ref_date": ref_date, "season": season}
    if upcoming is not None and len(upcoming):
        nxt = fit.predict(upcoming["home"], upcoming["away"])
        for c in ["date", "time_uk", "matchday"]:
            if c in upcoming:
                nxt.insert(0, c, upcoming[c].values)
        out["next_round"] = nxt
    return out


def to_json(res: dict, backtest: dict | None = None, season_bt: dict | None = None) -> dict:
    """Plain dict for the results page."""
    s = res["summary"]
    teams_out = []
    for _, r in s.iterrows():
        teams_out.append({
            "team": r["team"], "en": english(r["team"]), "ar": arabic(r["team"]),
            "pts_now": int(r["pts_now"]), "exp_pts": round(float(r["exp_pts"]), 1),
            "pts_p10": float(r["pts_p10"]), "pts_p90": float(r["pts_p90"]),
            "p_title": float(r["p_title"]), "p_top4": float(r["p_top4"]), "p_top6": float(r["p_top6"]),
            "p_releg": float(r["p_releg"]), "exp_pos": float(r["exp_pos"]),
            "pos": [float(r[f"pos_{k}"]) for k in range(1, len(s) + 1)],
        })
    table = []
    for _, r in res["table"].iterrows():
        table.append({"pos": int(r["Pos"]), "team": r["team"], "en": english(r["team"]), "ar": arabic(r["team"]),
                      "P": int(r["P"]), "W": int(r["W"]), "D": int(r["D"]), "L": int(r["L"]),
                      "GF": int(r["GF"]), "GA": int(r["GA"]), "GD": int(r["GD"]), "Pts": int(r["Pts"])})
    data = {
        "season": f"{res['season']}/{(res['season'] + 1) % 100:02d}",
        "as_of": res["ref_date"].strftime("%Y-%m-%d"),
        "matches_played": int(len(res["played"])),
        "n_sims": int(res["sim"].positions.shape[0]),
        "config": asdict(res["config"]),
        "drift_sd": res["drift_sd"],
        "teams": teams_out,
        "table": table,
        "ratings": [{"team": r["team"], "ar": arabic(r["team"]), "en": english(r["team"]),
                     "xg_for": round(float(r["xg_for"]), 2), "xg_against": round(float(r["xg_against"]), 2),
                     "xgd": round(float(r["xgd_per_game"]), 2)} for _, r in res["ratings"].iterrows()],
    }
    if "next_round" in res:
        data["next_round"] = [{
            "date": str(r.get("date", "")), "time_uk": str(r.get("time_uk", "")),
            "home": r["home"], "away": r["away"],
            "home_ar": arabic(r["home"]), "away_ar": arabic(r["away"]),
            "home_en": english(r["home"]), "away_en": english(r["away"]),
            "xg_home": round(float(r["xg_home"]), 2), "xg_away": round(float(r["xg_away"]), 2),
            "p_home": float(r["p_home"]), "p_draw": float(r["p_draw"]), "p_away": float(r["p_away"]),
            "likely_score": r["likely_score"], "p_likely_score": float(r["p_likely_score"]),
        } for _, r in res["next_round"].iterrows()]
    if backtest:
        data["backtest"] = backtest
    if season_bt:
        data["season_backtest"] = season_bt
    return data
