"""Run the 2026/27 forecast from the local data snapshot.

    python run_forecast.py            # 10,000 simulated seasons
    python run_forecast.py --sims 50000
"""

from __future__ import annotations

import argparse
import json
import os

import pandas as pd

from zsc.dashboard import accuracy_rows, dashboard_tables, write_tables
from zsc.forecast import load_settings, run_forecast, to_json
from zsc.pipeline import ROOT, load_snapshot
from zsc.teams import arabic
from zsc.paths import RAW_UPCOMING_FWP  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=10_000)
    ap.add_argument("--date", default="2026-10-23", help="forecast date (uses matches before it)")
    args = ap.parse_args()

    out_dir = os.path.join(ROOT, "outputs")
    cfg, drift = load_settings(out_dir)
    m = load_snapshot()
    upcoming = pd.read_csv(RAW_UPCOMING_FWP)
    done = set(zip(m.loc[m["season"] == 2026, "home"], m.loc[m["season"] == 2026, "away"]))
    upcoming = upcoming[[(h, a) not in done for h, a in zip(upcoming["home"], upcoming["away"])]].reset_index(drop=True)
    res = run_forecast(m, 2026, args.date, cfg, drift, upcoming=upcoming, n_sims=args.sims)

    res["summary"].assign(ar=res["summary"]["team"].map(arabic)).to_csv(
        os.path.join(out_dir, "forecast_summary.csv"), index=False)
    res["table"].to_csv(os.path.join(out_dir, "current_table.csv"), index=False)
    res["ratings"].to_csv(os.path.join(out_dir, "team_ratings.csv"), index=False)
    if "next_round" in res:
        res["next_round"].to_csv(os.path.join(out_dir, "next_round.csv"), index=False)

    bt = sb = None
    p = os.path.join(out_dir, "backtest_report.json")
    if os.path.exists(p):
        with open(p) as f:
            bt = json.load(f)
    p = os.path.join(out_dir, "season_backtest.json")
    if os.path.exists(p):
        with open(p) as f:
            sbj = json.load(f)
            sb = {"chosen_drift_sd": sbj["chosen_drift_sd"],
                  "metrics": sbj["variants"][f"drift_{sbj['chosen_drift_sd']}"],
                  "cut_after_matches": sbj["cut_after_matches"], "seasons": sbj["seasons"]}
    data = to_json(res, bt, sb)
    with open(os.path.join(out_dir, "forecast.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # CSV files for the results dashboard
    acc = None
    preds_path = os.path.join(out_dir, "backtest_predictions_test.csv")
    if bt and sb and os.path.exists(preds_path):
        acc = accuracy_rows(bt, sb, pd.read_csv(preds_path))
    write_tables(dashboard_tables(data, acc), os.path.join(out_dir, "dashboard"))

    s = res["summary"]
    print(f"Forecast as of {args.date}: {len(res['played'])} matches played, {args.sims} simulations, drift_sd={drift}")
    print(s[["team", "pts_now", "exp_pts", "p_title", "p_top4", "p_top6", "p_releg"]].round(3).to_string())
    if "next_round" in res:
        print(res["next_round"].round(3).to_string())


if __name__ == "__main__":
    main()
