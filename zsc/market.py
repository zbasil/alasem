"""Turning bookmaker odds into probabilities and expected goals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dixon_coles import outcome_probs, over_prob, score_matrix


def implied_1x2(odds_h, odds_d, odds_a) -> np.ndarray:
    """Margin-free probabilities (proportional method). Shape (n, 3)."""
    inv = 1.0 / np.column_stack([odds_h, odds_d, odds_a]).astype(float)
    return inv / inv.sum(axis=1, keepdims=True)


def implied_over(odds_over, odds_under) -> np.ndarray:
    inv_o = 1.0 / np.asarray(odds_over, dtype=float)
    inv_u = 1.0 / np.asarray(odds_under, dtype=float)
    return inv_o / (inv_o + inv_u)


def _model_probs(u, v, rho):
    m = score_matrix(np.exp(u), np.exp(v), rho)
    p = outcome_probs(m)
    return p[:, 0], p[:, 2], over_prob(m)


def implied_goals(p_home, p_away, p_over=None, rho: float = -0.05,
                  iters: int = 40, tol: float = 1e-10):
    """Solve for (lambda, mu) whose Dixon-Coles probabilities match the market.

    Least squares on P(home), P(away) and, when given, P(over 2.5).
    Vectorised Levenberg-Marquardt; returns (lambda, mu, max_abs_residual).
    """
    p_home = np.asarray(p_home, float)
    p_away = np.asarray(p_away, float)
    n = len(p_home)
    has_o = np.zeros(n, bool) if p_over is None else ~np.isnan(np.asarray(p_over, float))
    p_over = np.zeros(n) if p_over is None else np.nan_to_num(np.asarray(p_over, float))

    # starting point from the odds ratio
    u = np.log(1.35) + 0.6 * (p_home - p_away)
    v = np.log(1.10) - 0.6 * (p_home - p_away)
    damp = np.full(n, 1e-3)
    eps = 1e-5

    def resid(u_, v_):
        ph, pa, po = _model_probs(u_, v_, rho)
        r = np.stack([ph - p_home, pa - p_away, np.where(has_o, po - p_over, 0.0)], axis=1)
        return r

    r = resid(u, v)
    for _ in range(iters):
        ru = (resid(u + eps, v) - resid(u - eps, v)) / (2 * eps)
        rv = (resid(u, v + eps) - resid(u, v - eps)) / (2 * eps)
        # normal equations per match (2x2)
        a11 = (ru * ru).sum(1) + damp
        a22 = (rv * rv).sum(1) + damp
        a12 = (ru * rv).sum(1)
        b1 = -(ru * r).sum(1)
        b2 = -(rv * r).sum(1)
        det = a11 * a22 - a12 ** 2
        du = (a22 * b1 - a12 * b2) / det
        dv = (a11 * b2 - a12 * b1) / det
        du = np.clip(du, -0.5, 0.5)
        dv = np.clip(dv, -0.5, 0.5)
        r_new = resid(u + du, v + dv)
        better = (r_new ** 2).sum(1) <= (r ** 2).sum(1)
        u = np.where(better, u + du, u)
        v = np.where(better, v + dv, v)
        r = np.where(better[:, None], r_new, r)
        damp = np.where(better, damp * 0.3, damp * 10)
        if np.abs(r).max() < tol:
            break
    return np.exp(u), np.exp(v), np.abs(r).max(axis=1)


def add_market_goals(matches: pd.DataFrame, rho: float = -0.05) -> pd.DataFrame:
    """Add market-implied expected goals (mkt_lh, mkt_la) where odds exist."""
    out = matches.copy()
    out["mkt_lh"] = np.nan
    out["mkt_la"] = np.nan
    odds = out[["odds_h", "odds_d", "odds_a"]]
    ok = np.asarray(odds.notna().all(axis=1)) & np.asarray((odds.fillna(0) > 1.0).all(axis=1))
    if not ok.any():
        return out
    sub = out.loc[ok]
    p = implied_1x2(sub["odds_h"], sub["odds_d"], sub["odds_a"])
    po = np.full(len(sub), np.nan)
    has_ou = sub[["odds_o25", "odds_u25"]].notna().all(axis=1).values
    po[has_ou] = implied_over(sub.loc[has_ou, "odds_o25"], sub.loc[has_ou, "odds_u25"])
    lam, mu, err = implied_goals(p[:, 0], p[:, 2], po, rho=rho)
    out.loc[ok, "mkt_lh"] = lam
    out.loc[ok, "mkt_la"] = mu
    out.loc[ok, "mkt_err"] = err
    return out
