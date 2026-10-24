"""Season projections, match importance and the inputs of the in-browser what-if simulator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .dixon_coles import FittedDC, score_matrix
from .simulate import simulate_season
from .standings import compute_table, h2h_matrices, league_table


def place_chances(positions: np.ndarray, teams: list[str], places: list[dict]) -> pd.DataFrame:
    """P(finishing within each configured band of places) per team."""
    out = pd.DataFrame({"team": teams})
    for pl in places:
        out[f"p_{pl['key']}"] = ((positions >= pl["from"]) & (positions <= pl["to"])).mean(0)
    return out


def projection(fit: FittedDC, played: pd.DataFrame, teams: list[str], n_sims: int, drift_sd: float,
               seed: int = 2026, fixed_dist: dict | None = None) -> dict:
    """Simulate the rest of the season; returns summary rows, positions matrix and points."""
    sim = simulate_season(fit, played, teams, n_sims=n_sims, drift_sd=drift_sd, parameter_uncertainty=False,
                          fixed_dist=fixed_dist, seed=seed)
    rules = config.season_rules()
    pc = place_chances(sim.positions, sim.teams, rules["places"]).set_index("team")
    base = sim.base_table.set_index("team")
    n = len(sim.teams)
    rows = []
    for k, t in enumerate(sim.teams):
        pts = sim.points[:, k]
        pos = sim.positions[:, k]
        row = {"team": t, "pts_now": int(base.loc[t, "Pts"]), "exp_pts": float(pts.mean()),
               "pts_p10": float(np.percentile(pts, 10)), "pts_p90": float(np.percentile(pts, 90)),
               "exp_pos": float(pos.mean()), "pos_dist": [float((pos == i).mean()) for i in range(1, n + 1)]}
        for c in pc.columns:
            row[c] = float(pc.loc[t, c])
        rows.append(row)
    return {"rows": rows, "n_sims": n_sims, "sim": sim}


def mc_se(p: float, n: int) -> float:
    """Monte Carlo standard error of a simulated probability."""
    return float(np.sqrt(max(p * (1 - p), 1e-12) / n))


def conditional_matrix(lam: float, mu: float, rho: float, outcome: str, G: int = 11) -> np.ndarray:
    """Final-score distribution of a match given its outcome (H, D or A)."""
    m = score_matrix(lam, mu, rho, max_goals=G - 1)[0]
    i, j = np.indices(m.shape)
    keep = {"H": i > j, "D": i == j, "A": i < j}[outcome]
    m = np.where(keep, m, 0.0)
    return m / m.sum()


def importance(fit: FittedDC, played: pd.DataFrame, teams: list[str], matches: pd.DataFrame,
               n_sims: int, drift_sd: float, metrics=("p_title", "p_ucl", "p_releg")) -> list[dict]:
    """How much each upcoming match can move the season race.

    For each match the season is simulated three times (home win, draw, away win) with the same random
    numbers. Importance = sum over teams of |P(event | home win) - P(event | away win)| for the title,
    Champions League places and relegation (percentage points), so it measures stakes, not fame."""
    out = []
    for r in matches.itertuples():
        res = {}
        for oc in ("H", "D", "A"):
            mat = conditional_matrix(r.xg_home, r.xg_away, r.rho, oc)
            pr = projection(fit, played, teams, n_sims, drift_sd, seed=7, fixed_dist={(r.home, r.away): mat})
            res[oc] = {row["team"]: row for row in pr["rows"]}
        swings = []
        total = 0.0
        for t in teams:
            for mtr in metrics:
                d = res["H"][t][mtr] - res["A"][t][mtr]
                total += abs(d)
                if abs(d) >= 0.01:
                    swings.append({"team": t, "metric": mtr, "home_win": res["H"][t][mtr], "draw": res["D"][t][mtr],
                                   "away_win": res["A"][t][mtr]})
        swings.sort(key=lambda s: -abs(s["home_win"] - s["away_win"]))
        out.append({"match_id": r.match_id, "home": r.home, "away": r.away, "importance": round(100 * total, 1),
                    "swings": swings[:8], "n_sims": n_sims})
    out.sort(key=lambda x: -x["importance"])
    return out


def whatif_inputs(fit: FittedDC, played: pd.DataFrame, teams: list[str], remaining: pd.DataFrame,
                  drift_sd: float) -> dict:
    """Everything the browser simulator needs to re-run the season with user-chosen results."""
    teams = sorted(teams)
    idx = fit.index
    att, dfn = fit.scaled()
    base = compute_table(played, teams).set_index("team").loc[teams]
    hp, hg, hpl = h2h_matrices(played, teams)
    n = len(teams)
    return {
        "teams": teams, "c": float(fit.c), "h": float(fit.h), "rho": float(fit.rho), "scale": float(fit.scale),
        "attack": [float(att[idx[t]]) for t in teams], "defence": [float(dfn[idx[t]]) for t in teams],
        "drift_sd": float(drift_sd), "share_left": len(remaining) / (n * (n - 1)),
        "pts": base["Pts"].astype(int).tolist(), "gf": base["GF"].astype(int).tolist(),
        "ga": base["GA"].astype(int).tolist(), "played": base["P"].astype(int).tolist(),
        "h2h_pts": hp.tolist(), "h2h_gf": hg.tolist(), "h2h_played": hpl.tolist(),
        "fixtures": [{"match_id": r.match_id, "h": teams.index(r.home), "a": teams.index(r.away),
                      "lam": float(r.xg_home), "mu": float(r.xg_away)} for r in remaining.itertuples()],
        "places": config.season_rules()["places"],
    }


def current_table(played: pd.DataFrame, teams: list[str]) -> list[dict]:
    t = league_table(played, teams)
    return [{"pos": int(r.Pos), "team": r.team, "P": int(r.P), "W": int(r.W), "D": int(r.D), "L": int(r.L),
             "GF": int(r.GF), "GA": int(r.GA), "GD": int(r.GD), "Pts": int(r.Pts)} for r in t.itertuples()]
