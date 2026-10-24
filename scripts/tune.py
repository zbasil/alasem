"""Tune the model on 2012/13-2022/23 (11 seasons), then test once on
2023/24-2025/26 (3 seasons never used for tuning).

A wide tuning window matters: the COVID seasons (2019/20, 2020/21) alone
would over-reward the market signal, because home advantage collapsed and the
betting market adapted faster than any results-based rating.

Writes outputs/tuning_log.txt, outputs/best_config.json, outputs/backtest_report.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.backtest import score, tune, walk_forward  # noqa: E402
from zsc.dixon_coles import DCConfig  # noqa: E402
from zsc.pipeline import load_snapshot  # noqa: E402

TUNE_SEASONS = list(range(2012, 2023))
TEST_SEASONS = [2023, 2024, 2025]

GRID = {
    "beta_mkt": [0.0, 0.25, 0.5, 0.6, 0.75, 0.9, 1.0],
    "xi": [0.001, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.006],
    "beta_sot": [0.0, 0.1, 0.2, 0.4],
    "prior_sd": [0.2, 0.3, 0.4, 0.5, 0.7],
    "seasons_back": [1, 2, 3, 4],
    "rating_scale": [1.0, 1.05, 1.1, 1.15, 1.2, 1.3],
}


def main():
    out = os.path.join(ROOT, "outputs")
    os.makedirs(out, exist_ok=True)
    logf = open(os.path.join(out, "tuning_log.txt"), "w")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    t0 = time.time()
    m = load_snapshot()
    # warm start from the first tuning run (beta_mkt=0.9, xi=0.005, prior_sd=0.7, 2 seasons)
    start = DCConfig(beta_mkt=0.9, xi=0.005, prior_sd=0.7, seasons_back=2)
    best, best_val, cache = tune(m, TUNE_SEASONS, start, GRID, passes=2, log=log)
    log(f"best on tuning seasons: rps={best_val:.5f} {best}  ({time.time() - t0:.0f}s)")

    # references on the TEST seasons (never used for tuning)
    report = {"tune_seasons": TUNE_SEASONS, "test_seasons": TEST_SEASONS, "best_config": asdict(best)}
    variants = {
        "goals_only": DCConfig(**{**asdict(best), "beta_sot": 0.0, "beta_mkt": 0.0}),
        "goals_plus_shots": DCConfig(**{**asdict(best), "beta_mkt": 0.0}),
        "final_model": best,
    }
    for name, cfg in variants.items():
        pred = walk_forward(m, TEST_SEASONS, cfg)
        res = score(pred)
        report[name] = res
        log(f"TEST {name}: " + ", ".join(f"{k}={v:.5f}" if isinstance(v, float) else f"{k}={v}" for k, v in res.items()))
        if name == "final_model":
            pred.to_csv(os.path.join(out, "backtest_predictions_test.csv"), index=False)
    with open(os.path.join(out, "best_config.json"), "w") as f:
        json.dump(asdict(best), f, indent=2)
    with open(os.path.join(out, "backtest_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=float)
    log(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
