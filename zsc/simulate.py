"""Monte Carlo simulation of the rest of a season."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import remaining_fixtures
from .dixon_coles import FittedDC, score_matrix
from .standings import compute_table, h2h_matrices, rank_order


@dataclass
class SimResult:
    teams: list
    positions: np.ndarray      # (n_sims, n_teams) final position, 1 = champion
    points: np.ndarray         # (n_sims, n_teams) final points
    fixtures: pd.DataFrame     # remaining fixtures with model probabilities
    base_table: pd.DataFrame

    def summary(self, relegated: int = 3, ucl: int = 4, europe: int = 6) -> pd.DataFrame:
        n = len(self.teams)
        pos = self.positions
        out = pd.DataFrame({
            "team": self.teams,
            "pts_now": self.base_table.set_index("team").loc[self.teams, "Pts"].values,
            "exp_pts": self.points.mean(0),
            "pts_p10": np.percentile(self.points, 10, axis=0),
            "pts_p90": np.percentile(self.points, 90, axis=0),
            "exp_pos": pos.mean(0),
            "p_title": (pos == 1).mean(0),
            "p_top4": (pos <= ucl).mean(0),
            "p_top6": (pos <= europe).mean(0),
            "p_releg": (pos > n - relegated).mean(0),
        })
        for k in range(1, n + 1):
            out[f"pos_{k}"] = (pos == k).mean(0)
        return out.sort_values(["exp_pts", "p_title"], ascending=False).reset_index(drop=True)


def simulate_season(fit: FittedDC, played: pd.DataFrame, teams: list[str],
                    n_sims: int = 10_000, n_param_draws: int = 1000,
                    parameter_uncertainty: bool = True, drift_sd: float = 0.0,
                    overrides: pd.DataFrame | None = None, fixed_dist: dict | None = None,
                    seed: int = 2026) -> SimResult:
    """Simulate the remaining fixtures n_sims times.

    parameter_uncertainty  draw team ratings from the fitted model's
                           uncertainty (Laplace approximation)
    drift_sd               extra random change of every team's attack and
                           defence over the rest of the season (form, injuries,
                           transfers, coach changes), scaled by the square root
                           of the share of the season still to play
    overrides              optional table (home, away, mkt_lh, mkt_la): for these
                           fixtures use the betting market's expected goals
                           (the market beats any rating model on the very next
                           match because it knows team news)
    fixed_dist             optional {(home, away): matrix} of final-score
                           probabilities (rows = home goals) for matches in
                           progress, e.g. from the in-play model
    """
    rng = np.random.default_rng(seed)
    teams = sorted(teams)
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    base = compute_table(played, teams)
    pts0 = base.set_index("team").loc[teams, "Pts"].values
    gf0 = base.set_index("team").loc[teams, "GF"].values
    ga0 = base.set_index("team").loc[teams, "GA"].values
    hp0, hg0, _ = h2h_matrices(played, teams)

    rem = remaining_fixtures(played, teams)
    rh = rem["home"].map(idx).values
    ra = rem["away"].map(idx).values
    R = len(rem)

    # expected (point-estimate) probabilities for reporting
    pred = fit.predict(rem["home"], rem["away"])

    draws = max(1, min(n_param_draws, n_sims))
    per = np.full(draws, n_sims // draws)
    per[: n_sims % draws] += 1
    thetas = fit.sample_theta(draws, rng) if parameter_uncertainty else np.repeat(fit.theta()[None], draws, 0)
    if drift_sd > 0 and R:
        share_left = R / (n * (n - 1))
        nt = len(fit.teams)
        thetas = thetas.copy()
        thetas[:, 3:] += rng.normal(0.0, drift_sd * np.sqrt(share_left), size=(draws, 2 * nt))

    ov_i, ov_l, ov_m = np.array([], int), np.array([]), np.array([])
    if overrides is not None and len(overrides) and R:
        key = {(h, a): k for k, (h, a) in enumerate(zip(rem["home"], rem["away"]))}
        trip = [(key[(h, a)], l, m) for h, a, l, m in
                zip(overrides["home"], overrides["away"], overrides["mkt_lh"], overrides["mkt_la"])
                if (h, a) in key and np.isfinite(l) and np.isfinite(m)]
        if trip:
            ov_i, ov_l, ov_m = (np.array(v) for v in zip(*trip))
            ov_i = ov_i.astype(int)

    G = 11
    fixed_rows = {}
    if fixed_dist and R:
        key = {(h, a): k for k, (h, a) in enumerate(zip(rem["home"], rem["away"]))}
        for (h, a), mat in fixed_dist.items():
            if (h, a) not in key:
                raise ValueError(f"{h} v {a} is not a remaining fixture")
            mat = np.asarray(mat, dtype=float)
            sq = np.zeros((G, G))
            r_, c_ = min(G, mat.shape[0]), min(G, mat.shape[1])
            sq[:r_, :c_] = mat[:r_, :c_]
            sq /= sq.sum()
            fixed_rows[key[(h, a)]] = sq.reshape(-1)

    hg_all = np.empty((n_sims, R), dtype=np.int16)
    ag_all = np.empty((n_sims, R), dtype=np.int16)
    s0 = 0
    for b in range(draws if R else 0):
        lam, mu = fit.rates(rem["home"], rem["away"], thetas[b])
        if len(ov_i):
            lam[ov_i] = ov_l
            mu[ov_i] = ov_m
        m = score_matrix(lam, mu, thetas[b][2], max_goals=G - 1).reshape(R, -1)
        for k_, row in fixed_rows.items():
            m[k_] = row
        cdf = np.cumsum(m, axis=1)
        cdf[:, -1] = 1.0
        u = rng.random((per[b], R))
        k = (cdf[None, :, :] < u[:, :, None]).sum(-1)
        hg_all[s0:s0 + per[b]] = k // G
        ag_all[s0:s0 + per[b]] = k % G
        s0 += per[b]

    # season totals
    win_h = hg_all > ag_all
    win_a = hg_all < ag_all
    draw = ~(win_h | win_a)
    pts = np.tile(pts0, (n_sims, 1)).astype(np.int32)
    gf = np.tile(gf0, (n_sims, 1)).astype(np.int32)
    ga = np.tile(ga0, (n_sims, 1)).astype(np.int32)
    hp = np.tile(hp0, (n_sims, 1, 1)).astype(np.int16)
    hgm = np.tile(hg0, (n_sims, 1, 1)).astype(np.int16)
    for r in range(R):
        i, j = rh[r], ra[r]
        x, y = hg_all[:, r], ag_all[:, r]
        p_i = 3 * win_h[:, r] + draw[:, r]
        p_j = 3 * win_a[:, r] + draw[:, r]
        pts[:, i] += p_i
        pts[:, j] += p_j
        gf[:, i] += x
        ga[:, i] += y
        gf[:, j] += y
        ga[:, j] += x
        hp[:, i, j] += p_i
        hp[:, j, i] += p_j
        hgm[:, i, j] += x
        hgm[:, j, i] += y
    gd = gf - ga

    full = np.full((n, n), 2)
    np.fill_diagonal(full, 0)
    positions = np.empty((n_sims, n), dtype=np.int16)
    fair_play = rng.random((n_sims, n))        # unpredictable last resort
    for s in range(n_sims):
        order = rank_order(pts[s], gd[s], gf[s], hp[s], hgm[s], full, fair_play[s])
        positions[s, order] = np.arange(1, n + 1)

    fixtures = pred.copy()
    return SimResult(teams=teams, positions=positions, points=pts, fixtures=fixtures, base_table=base)
