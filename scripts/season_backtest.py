"""Season-level honesty check.

For every season 2012/13 - 2025/26: stop the clock after the first 100
matches (about 10 matchdays, where 2026/27 is today), fit the model with data
available at that moment only, simulate the rest of the season, and compare
with what really happened.

Reported: error of projected points, calibration of the points intervals,
and Brier scores for title / top-4 / relegation against simple baselines.
Writes outputs/season_backtest.json and outputs/season_backtest_teams.csv
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.dixon_coles import DCConfig, fit_dixon_coles  # noqa: E402
from zsc.pipeline import load_snapshot, promoted_teams, season_teams  # noqa: E402
from zsc.simulate import simulate_season  # noqa: E402
from zsc.standings import compute_table, league_table  # noqa: E402

SEASONS = list(range(2012, 2026))
CUT_MATCHES = 100


def run(m, cfg, drift_sd, n_sims=4000, param_unc=True, log=print):
    rows = []
    for s in SEASONS:
        sm = m[m["season"] == s].sort_values(["date", "home"]).reset_index(drop=True)
        cut_date = sm.loc[CUT_MATCHES - 1, "date"]
        played = sm[sm["date"] <= cut_date]
        teams = season_teams(m, s)
        fit = fit_dixon_coles(m, cut_date + pd.Timedelta(days=1), cfg, current_teams=teams,
                              promoted=promoted_teams(m, s), current_season=s)
        sim = simulate_season(fit, played, teams, n_sims=n_sims, drift_sd=drift_sd,
                              parameter_uncertainty=param_unc, seed=s)
        final = league_table(sm).set_index("team")
        now = compute_table(played, teams).set_index("team")
        for k, t in enumerate(sim.teams):
            pts = sim.points[:, k]
            pos = sim.positions[:, k]
            rows.append({
                "season": s, "team": t, "n_played_at_cut": int(now.loc[t, "P"]),
                "pts_at_cut": int(now.loc[t, "Pts"]),
                "pred_pts": pts.mean(), "pred_sd": pts.std(),
                "p10": np.percentile(pts, 10), "p90": np.percentile(pts, 90),
                "actual_pts": int(final.loc[t, "Pts"]), "actual_pos": int(final.loc[t, "Pos"]),
                "p_title": (pos == 1).mean(), "p_top4": (pos <= 4).mean(), "p_releg": (pos >= 18).mean(),
                # naive baseline: keep the current points-per-game rate
                "naive_pts": now.loc[t, "Pts"] / max(1, now.loc[t, "P"]) * 38,
            })
    return pd.DataFrame(rows)


def metrics(df: pd.DataFrame) -> dict:
    err = df["actual_pts"] - df["pred_pts"]
    z = err / df["pred_sd"]
    out = {
        "teams": len(df),
        "points_MAE": float(err.abs().mean()),
        "points_RMSE": float(np.sqrt((err ** 2).mean())),
        "naive_points_MAE": float((df["actual_pts"] - df["naive_pts"]).abs().mean()),
        "z_sd": float(z.std()),
        "coverage_80": float(((df["actual_pts"] >= df["p10"]) & (df["actual_pts"] <= df["p90"])).mean()),
    }
    for ev, cond in [("title", df["actual_pos"] == 1), ("top4", df["actual_pos"] <= 4),
                     ("releg", df["actual_pos"] >= 18)]:
        p = df[f"p_{ev}"]
        y = cond.astype(float)
        out[f"brier_{ev}"] = float(((p - y) ** 2).mean())
        # baseline: league-wide base rate, same for every team
        base = y.mean()
        out[f"brier_{ev}_baserate"] = float(((base - y) ** 2).mean())
    return out


def main():
    t0 = time.time()
    m = load_snapshot()
    with open(os.path.join(ROOT, "outputs", "best_config.json")) as f:
        cfg = DCConfig(**json.load(f))
    report = {"config": cfg.__dict__, "cut_after_matches": CUT_MATCHES, "seasons": SEASONS, "variants": {}}
    # The Laplace (quasi-likelihood) covariance overstates rating uncertainty
    # when the ratings are fitted mostly to smooth market expectations: with it
    # the simulated points spread was 32% too wide (z sd 0.76, 80% intervals
    # covering 91%). So the spread is calibrated directly on history instead:
    # match randomness + a "drift" in team strength, picked so that z sd ~ 1.
    report["laplace_uncertainty_check"] = metrics(run(m, cfg, 0.0, param_unc=True))
    print("with Laplace uncertainty:", report["laplace_uncertainty_check"], flush=True)
    best = None
    for drift in [0.0, 0.025, 0.05, 0.075, 0.1]:
        df = run(m, cfg, drift, param_unc=False)
        res = metrics(df)
        report["variants"][f"drift_{drift}"] = res
        print(f"drift={drift}: " + ", ".join(f"{k}={v:.4f}" for k, v in res.items() if k != "teams"), flush=True)
        if best is None or abs(res["z_sd"] - 1) < abs(best[1]["z_sd"] - 1):
            best = (drift, res, df)
    report["chosen_drift_sd"] = best[0]
    report["parameter_uncertainty"] = False
    best[2].to_csv(os.path.join(ROOT, "outputs", "season_backtest_teams.csv"), index=False)
    with open(os.path.join(ROOT, "outputs", "season_backtest.json"), "w") as f:
        json.dump(report, f, indent=2, default=float)
    print(f"chosen drift_sd={best[0]}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
