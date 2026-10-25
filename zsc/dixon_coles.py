"""Dixon-Coles team-strength model.

    goals_home ~ Poisson(lambda),  lambda = exp(c + h + attack[home] - defence[away])
    goals_away ~ Poisson(mu),      mu     = exp(c +     attack[away] - defence[home])

with the Dixon & Coles (1997) correction tau(x, y) for the low scores
0-0, 1-0, 0-1, 1-1, exponential time-decay weights, and a normal prior on
every team rating (promoted teams get a lower prior mean).

The "target" the Poisson part is fitted to can blend three signals of team
strength for each past match:
    * the real goals
    * a shots-on-target proxy for expected goals  (k * shots on target)
    * the goals the betting market expected before kick-off
The tau correction always uses the real score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOALS = 10
RHO_BOUNDS = (-0.25, 0.10)


# --------------------------------------------------------------------------
# score distributions
# --------------------------------------------------------------------------

def score_matrix(lam, mu, rho, max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(home = x, away = y) for each match; shape (n, G+1, G+1)."""
    lam = np.atleast_1d(np.asarray(lam, dtype=float))
    mu = np.atleast_1d(np.asarray(mu, dtype=float))
    rho = np.broadcast_to(np.asarray(rho, dtype=float), lam.shape)
    k = np.arange(max_goals + 1)
    ph = poisson.pmf(k[None, :], lam[:, None])
    pa = poisson.pmf(k[None, :], mu[:, None])
    m = ph[:, :, None] * pa[:, None, :]
    m[:, 0, 0] *= 1.0 - lam * mu * rho
    m[:, 0, 1] *= 1.0 + lam * rho
    m[:, 1, 0] *= 1.0 + mu * rho
    m[:, 1, 1] *= 1.0 - rho
    m = np.clip(m, 0.0, None)
    return m / m.sum(axis=(1, 2), keepdims=True)


def outcome_probs(m: np.ndarray) -> np.ndarray:
    """(n, 3) array of P(home win), P(draw), P(away win)."""
    g = m.shape[1]
    home = np.tril(np.ones((g, g), dtype=bool), -1)      # x > y
    away = np.triu(np.ones((g, g), dtype=bool), 1)       # x < y
    draw = np.eye(g, dtype=bool)
    return np.stack([m[:, home].sum(1), m[:, draw].sum(1), m[:, away].sum(1)], axis=1)


def over_prob(m: np.ndarray, line: float = 2.5) -> np.ndarray:
    g = m.shape[1]
    tot = np.add.outer(np.arange(g), np.arange(g))
    return m[:, tot > line].sum(1)


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

@dataclass
class DCConfig:
    xi: float = 0.0019              # time decay per day (weight = exp(-xi * days))
    prior_sd: float = 0.35          # sd of the normal prior on attack/defence
    beta_sot: float = 0.0           # weight of the shots-on-target xG proxy in the target
    beta_mkt: float = 0.0           # weight of market-implied goals in the target
    promoted_attack: float = -0.19  # prior mean for newly promoted teams
    promoted_defence: float = -0.13  # (average first season of promoted teams, 2003-2018)
    seasons_back: int = 4           # seasons of history before the current one
    sot_k: float | None = None      # goals per shot on target (estimated if None)
    rating_scale: float = 1.0       # stretch of rating differences at prediction time
                                    # (>1 corrects the shrinkage of time-averaged ratings)


@dataclass
class FittedDC:
    teams: list
    c: float
    h: float
    rho: float
    attack: np.ndarray
    defence: np.ndarray
    cov: np.ndarray | None = None          # Laplace covariance of the full parameter vector
    info: dict = field(default_factory=dict)
    scale: float = 1.0                     # rating_scale
    center_a: float = 0.0                  # mean attack / defence of the current teams
    center_d: float = 0.0

    @property
    def index(self):
        return {t: i for i, t in enumerate(self.teams)}

    def theta(self) -> np.ndarray:
        return np.concatenate([[self.c, self.h, self.rho], self.attack, self.defence])

    def scaled(self, theta: np.ndarray | None = None):
        """Attack and defence after applying rating_scale around the current-team mean."""
        th = self.theta() if theta is None else theta
        n = len(self.teams)
        att, dfn = th[3:3 + n], th[3 + n:]
        return (self.center_a + self.scale * (att - self.center_a),
                self.center_d + self.scale * (dfn - self.center_d))

    def rates(self, home, away, theta: np.ndarray | None = None):
        """Expected goals (lambda, mu) for arrays of fixtures."""
        idx = self.index
        hi = np.array([idx[t] for t in home], dtype=int)
        ai = np.array([idx[t] for t in away], dtype=int)
        th = self.theta() if theta is None else theta
        c, h = th[0], th[1]
        att, dfn = self.scaled(th)
        lam = np.exp(c + h + att[hi] - dfn[ai])
        mu = np.exp(c + att[ai] - dfn[hi])
        return lam, mu

    def predict(self, home, away) -> pd.DataFrame:
        home, away = list(home), list(away)
        if not home:
            return pd.DataFrame(columns=["home", "away", "xg_home", "xg_away", "p_home", "p_draw",
                                         "p_away", "likely_score", "p_likely_score"])
        lam, mu = self.rates(home, away)
        m = score_matrix(lam, mu, self.rho)
        p = outcome_probs(m)
        best = m.reshape(len(home), -1).argmax(1)
        g = m.shape[1]
        return pd.DataFrame({
            "home": home, "away": away, "xg_home": lam, "xg_away": mu,
            "p_home": p[:, 0], "p_draw": p[:, 1], "p_away": p[:, 2],
            "likely_score": [f"{b // g}-{b % g}" for b in best],
            "p_likely_score": m.reshape(len(home), -1).max(1),
        })

    def sample_theta(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Parameter draws from the Laplace approximation (n, p)."""
        th = self.theta()
        if self.cov is None:
            return np.repeat(th[None, :], n, axis=0)
        draws = rng.multivariate_normal(th, self.cov, size=n, method="cholesky")
        draws[:, 2] = np.clip(draws[:, 2], *RHO_BOUNDS)
        return draws


def _blend_targets(df: pd.DataFrame, cfg: DCConfig, k: float):
    """Per-match Poisson targets (home, away) mixing goals / SOT proxy / market."""
    n = len(df)
    wg = np.full(n, max(0.0, 1.0 - cfg.beta_sot - cfg.beta_mkt))
    has_sot = df["hst"].notna().values & df["ast"].notna().values
    has_mkt = df["mkt_lh"].notna().values & df["mkt_la"].notna().values if "mkt_lh" in df else np.zeros(n, bool)
    ws = np.where(has_sot, cfg.beta_sot, 0.0)
    wm = np.where(has_mkt, cfg.beta_mkt, 0.0)
    tot = wg + ws + wm
    tot = np.where(tot <= 0, 1.0, tot)
    wg = np.where(wg + ws + wm <= 0, 1.0, wg)
    hg, ag = df["hg"].values.astype(float), df["ag"].values.astype(float)
    sh = np.nan_to_num(df["hst"].values.astype(float)) * k
    sa = np.nan_to_num(df["ast"].values.astype(float)) * k
    if "mkt_lh" in df:
        mh, ma = np.nan_to_num(df["mkt_lh"].values.astype(float)), np.nan_to_num(df["mkt_la"].values.astype(float))
    else:
        mh = ma = np.zeros(n)
    th = (wg * hg + ws * sh + wm * mh) / tot
    ta = (wg * ag + ws * sa + wm * ma) / tot
    return th, ta


class _Objective:
    """Negative penalised log-likelihood and its exact gradient."""

    def __init__(self, hi, ai, x, y, th, ta, w, prior_a, prior_d, prior_sd, n_teams):
        self.hi, self.ai, self.x, self.y = hi, ai, x, y
        self.th, self.ta, self.w = th, ta, w
        self.pa, self.pd = prior_a, prior_d
        self.inv_var = 1.0 / prior_sd ** 2
        self.n = n_teams
        self.m00 = (x == 0) & (y == 0)
        self.m01 = (x == 0) & (y == 1)
        self.m10 = (x == 1) & (y == 0)
        self.m11 = (x == 1) & (y == 1)

    def __call__(self, theta):
        n = self.n
        c, h, rho = theta[0], theta[1], theta[2]
        att, dfn = theta[3:3 + n], theta[3 + n:]
        loglam = c + h + att[self.hi] - dfn[self.ai]
        logmu = c + att[self.ai] - dfn[self.hi]
        lam, mu = np.exp(loglam), np.exp(logmu)

        tau = np.ones_like(lam)
        tau[self.m00] = 1.0 - lam[self.m00] * mu[self.m00] * rho
        tau[self.m01] = 1.0 + lam[self.m01] * rho
        tau[self.m10] = 1.0 + mu[self.m10] * rho
        tau[self.m11] = 1.0 - rho
        tau = np.maximum(tau, 1e-10)

        ll = self.w * (self.th * loglam - lam + self.ta * logmu - mu + np.log(tau))
        pen = 0.5 * self.inv_var * (np.sum((att - self.pa) ** 2) + np.sum((dfn - self.pd) ** 2))
        f = -ll.sum() + pen

        # d log tau / d log lambda, d log mu, d rho
        dl = np.zeros_like(lam)
        dm = np.zeros_like(lam)
        dr = np.zeros_like(lam)
        s = self.m00
        dl[s] = -lam[s] * mu[s] * rho / tau[s]
        dm[s] = dl[s]
        dr[s] = -lam[s] * mu[s] / tau[s]
        s = self.m01
        dl[s] = lam[s] * rho / tau[s]
        dr[s] = lam[s] / tau[s]
        s = self.m10
        dm[s] = mu[s] * rho / tau[s]
        dr[s] = mu[s] / tau[s]
        s = self.m11
        dr[s] = -1.0 / tau[s]

        g_l = self.w * (self.th - lam + dl)      # d ll / d log lambda
        g_m = self.w * (self.ta - mu + dm)       # d ll / d log mu
        g_r = self.w * dr

        grad = np.empty_like(theta)
        grad[0] = -(g_l.sum() + g_m.sum())
        grad[1] = -g_l.sum()
        grad[2] = -g_r.sum()
        ga = np.bincount(self.hi, g_l, n) + np.bincount(self.ai, g_m, n)
        gd = np.bincount(self.ai, g_l, n) + np.bincount(self.hi, g_m, n)
        grad[3:3 + n] = -ga + self.inv_var * (att - self.pa)
        grad[3 + n:] = gd + self.inv_var * (dfn - self.pd)
        return f, grad


def fit_dixon_coles(matches: pd.DataFrame, ref_date, cfg: DCConfig,
                    current_teams: list[str] | None = None,
                    promoted: set[str] | None = None,
                    current_season: int | None = None,
                    x0: FittedDC | None = None,
                    laplace: bool = True) -> FittedDC:
    """Fit on matches played strictly before ref_date.

    current_teams  teams of the season being forecast (kept even with no data)
    promoted       teams that get the promoted-team prior mean
    """
    ref_date = pd.Timestamp(ref_date)
    df = matches[matches["date"] < ref_date]
    if current_season is not None:
        df = df[df["season"] >= current_season - cfg.seasons_back]
    df = df.reset_index(drop=True)

    teams = sorted(set(df["home"]) | set(df["away"]) | set(current_teams or []))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = df["home"].map(idx).values
    ai = df["away"].map(idx).values
    x = df["hg"].values.astype(int)
    y = df["ag"].values.astype(int)
    days = (ref_date - df["date"]).dt.days.values.astype(float)
    w = np.exp(-cfg.xi * days)

    if cfg.sot_k is not None:
        k = cfg.sot_k
    else:
        ok = df["hst"].notna() & df["ast"].notna()
        sot = (df.loc[ok, "hst"] + df.loc[ok, "ast"]).sum()
        k = float((df.loc[ok, "hg"] + df.loc[ok, "ag"]).sum() / sot) if sot > 0 else 0.0
    th, ta = _blend_targets(df, cfg, k)

    promoted = promoted or set()
    prior_a = np.array([cfg.promoted_attack if t in promoted else 0.0 for t in teams])
    prior_d = np.array([cfg.promoted_defence if t in promoted else 0.0 for t in teams])
    obj = _Objective(hi, ai, x, y, th, ta, w, prior_a, prior_d, cfg.prior_sd, n)

    if x0 is not None:
        old = x0.index
        att0 = np.array([x0.attack[old[t]] if t in old else prior_a[i] for i, t in enumerate(teams)])
        def0 = np.array([x0.defence[old[t]] if t in old else prior_d[i] for i, t in enumerate(teams)])
        start = np.concatenate([[x0.c, x0.h, x0.rho], att0, def0])
    else:
        mean_goals = max(0.5, (np.sum(w * (x + y)) / (2 * np.sum(w))) if len(df) else 1.3)
        start = np.concatenate([[np.log(mean_goals), 0.2, -0.05], prior_a, prior_d])

    bounds = [(None, None), (None, None), RHO_BOUNDS] + [(None, None)] * (2 * n)
    res = minimize(obj, start, jac=True, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-7})
    theta = res.x
    centre_idx = [idx[t] for t in (current_teams or teams)]
    fit = FittedDC(teams=teams, c=theta[0], h=theta[1], rho=theta[2],
                   attack=theta[3:3 + n].copy(), defence=theta[3 + n:].copy(),
                   info={"converged": bool(res.success), "message": str(res.message),
                         "n_matches": int(len(df)), "sot_k": k, "nll": float(res.fun),
                         "eff_matches": float(w.sum())},
                   scale=cfg.rating_scale,
                   center_a=float(theta[3:3 + n][centre_idx].mean()),
                   center_d=float(theta[3 + n:][centre_idx].mean()))
    if laplace:
        fit.cov = _laplace_cov(obj, theta)
    return fit


def _laplace_cov(obj: _Objective, theta: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Inverse Hessian at the optimum (numerical differentiation of the exact gradient)."""
    p = len(theta)
    hess = np.empty((p, p))
    for i in range(p):
        e = np.zeros(p)
        e[i] = eps
        hess[:, i] = (obj(theta + e)[1] - obj(theta - e)[1]) / (2 * eps)
    hess = 0.5 * (hess + hess.T)
    # tiny ridge for numerical safety, then invert
    vals, vecs = np.linalg.eigh(hess)
    vals = np.maximum(vals, 1e-8)
    return (vecs / vals) @ vecs.T
