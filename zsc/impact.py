"""What a match in progress means for the league table.

Simulates the rest of the season twice with the same random numbers:
once with the match still to be played (pre-match view) and once with the
match fixed to its in-play final-score distribution. The difference is the
effect of what has happened in the match so far.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .simulate import simulate_season

METRICS = [("p_title", "اللقب"), ("p_top4", "دوري الأبطال"), ("p_top6", "أوروبا"), ("p_releg", "الهبوط")]
IMPACT_SIMS = 10_000  # seasons simulated before and after a live result


def league_impact(fit, played: pd.DataFrame, teams: list[str], home: str, away: str, final_matrix,
                  n_sims: int = IMPACT_SIMS, drift_sd: float = 0.05, overrides: pd.DataFrame | None = None,
                  seed: int = 7) -> pd.DataFrame:
    kw = dict(n_sims=n_sims, drift_sd=drift_sd, parameter_uncertainty=False, overrides=overrides, seed=seed)
    before = simulate_season(fit, played, teams, **kw).summary().set_index("team")
    now = simulate_season(fit, played, teams, fixed_dist={(home, away): final_matrix}, **kw).summary().set_index("team")
    rows = []
    for t in before.index:
        r = {"team": t, "exp_pts_before": before.loc[t, "exp_pts"], "exp_pts_now": now.loc[t, "exp_pts"]}
        for col, _ in METRICS:
            r[f"{col}_before"] = before.loc[t, col]
            r[f"{col}_now"] = now.loc[t, col]
        rows.append(r)
    out = pd.DataFrame(rows)
    out["max_shift"] = np.max(np.abs(np.stack([out[f"{c}_now"] - out[f"{c}_before"] for c, _ in METRICS])), axis=0)
    return out.sort_values("max_shift", ascending=False).reset_index(drop=True)


def point_mass(hg: int, ag: int, size: int = 11) -> np.ndarray:
    m = np.zeros((size, size))
    m[min(hg, size - 1), min(ag, size - 1)] = 1.0
    return m
