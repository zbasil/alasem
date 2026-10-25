"""Tune one prediction track on the selection seasons 2012/13-2022/23 only.

    python scripts/tune_track.py independent     # no market inputs at all
    python scripts/tune_track.py market          # market-implied goals in the training targets

The final test seasons 2023/24-2025/26 are never looked at here.
Writes outputs/models/config_<track>.json and outputs/models/tuning_<track>.txt
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.backtest import tune  # noqa: E402
from zsc.dixon_coles import DCConfig  # noqa: E402
from zsc.pipeline import load_snapshot  # noqa: E402

SELECTION = list(range(2012, 2023))
GRIDS = {
    "independent": {
        "beta_sot": [0.0, 0.1, 0.2, 0.3, 0.4, 0.6],
        "xi": [0.001, 0.002, 0.003, 0.004, 0.005, 0.006],
        "prior_sd": [0.2, 0.3, 0.4, 0.5, 0.7],
        "seasons_back": [1, 2, 3, 4],
        "rating_scale": [1.0, 1.05, 1.1, 1.15, 1.2],
    },
    "market": {
        "beta_mkt": [0.0, 0.25, 0.5, 0.6, 0.75, 0.9, 1.0],
        "xi": [0.001, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.006],
        "beta_sot": [0.0, 0.1, 0.2, 0.4],
        "prior_sd": [0.2, 0.3, 0.4, 0.5, 0.7],
        "seasons_back": [1, 2, 3, 4],
        "rating_scale": [1.0, 1.05, 1.1, 1.15, 1.2, 1.3],
    },
}
STARTS = {
    "independent": DCConfig(xi=0.003, prior_sd=0.4, seasons_back=3, beta_sot=0.2, beta_mkt=0.0),
    "market": DCConfig(beta_mkt=0.9, xi=0.005, prior_sd=0.7, seasons_back=2),
}


def main(track: str):
    out = os.path.join(ROOT, "outputs", "models")
    os.makedirs(out, exist_ok=True)
    logf = open(os.path.join(out, f"tuning_{track}.txt"), "w")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    t0 = time.time()
    m = load_snapshot()
    best, val, _ = tune(m, SELECTION, STARTS[track], GRIDS[track], passes=2, log=log)
    log(f"best {track} on selection seasons {SELECTION[0]}-{SELECTION[-1]}: rps={val:.5f} {best} ({time.time() - t0:.0f}s)")
    with open(os.path.join(out, f"config_{track}.json"), "w") as f:
        json.dump({"track": track, "selection_seasons": SELECTION, "selection_rps": val, "config": asdict(best)}, f, indent=2)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "independent")
