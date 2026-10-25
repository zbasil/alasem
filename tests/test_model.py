"""Probability maths, the likelihood gradient, parameter recovery, odds."""

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import check_grad
from scipy.stats import poisson

from zsc.dixon_coles import (DCConfig, FittedDC, _Objective, fit_dixon_coles,
                             outcome_probs, over_prob, score_matrix)
from zsc.evaluate import log_loss, outcome_index, rps
from zsc.market import implied_1x2, implied_goals, implied_over


def test_score_matrix_is_a_distribution():
    m = score_matrix([0.4, 1.3, 2.9], [0.6, 1.1, 0.3], -0.08)
    assert np.allclose(m.sum(axis=(1, 2)), 1.0)
    assert (m >= 0).all()
    p = outcome_probs(m)
    assert np.allclose(p.sum(1), 1.0)


def test_rho_zero_is_independent_poisson():
    lam, mu = 1.7, 0.9
    m = score_matrix(lam, mu, 0.0, max_goals=25)[0]
    exp = np.outer(poisson.pmf(np.arange(26), lam), poisson.pmf(np.arange(26), mu))
    assert np.allclose(m, exp, atol=1e-12)


def test_dixon_coles_correction_only_moves_low_scores():
    lam, mu, rho = 1.4, 1.1, -0.1
    a = score_matrix(lam, mu, rho, max_goals=30)[0]
    b = score_matrix(lam, mu, 0.0, max_goals=30)[0]
    diff = np.abs(a - b) > 1e-14
    assert diff[:2, :2].all() and not diff[2:, :].any() and not diff[:, 2:].any()
    assert a[0, 0] > b[0, 0] and a[1, 1] > b[1, 1]        # rho < 0 adds draws 0-0 / 1-1


def test_gradient_is_exact():
    rng = np.random.default_rng(1)
    n, k = 8, 300
    hi = rng.integers(0, n, k)
    ai = (hi + rng.integers(1, n, k)) % n
    x, y = rng.poisson(1.4, k), rng.poisson(1.1, k)
    th, ta = x + rng.uniform(-.4, .4, k), y + rng.uniform(-.4, .4, k)
    obj = _Objective(hi, ai, x, y, th, ta, rng.uniform(.1, 1, k),
                     rng.normal(0, .1, n), rng.normal(0, .1, n), 0.4, n)
    theta = np.concatenate([[0.1, 0.3, -0.07], rng.normal(0, .3, n), rng.normal(0, .3, n)])
    err = check_grad(lambda t: obj(t)[0], lambda t: obj(t)[1], theta)
    assert err / np.linalg.norm(obj(theta)[1]) < 1e-6


def test_recovers_known_team_strengths():
    rng = np.random.default_rng(7)
    teams = [f"T{i:02d}" for i in range(20)]
    att = rng.normal(0, 0.3, 20)
    dfn = rng.normal(0, 0.25, 20)
    c, h, rho = 0.1, 0.25, -0.06
    rows = []
    day = pd.Timestamp("2015-08-01")
    for season in range(6):
        for i in range(20):
            for j in range(20):
                if i == j:
                    continue
                lam = np.exp(c + h + att[i] - dfn[j])
                mu = np.exp(c + att[j] - dfn[i])
                pm = score_matrix(lam, mu, rho)[0].ravel()
                s = rng.choice(len(pm), p=pm)
                rows.append((day, 2015 + season, teams[i], teams[j], s // 11, s % 11))
                day += pd.Timedelta(hours=7)
    df = pd.DataFrame(rows, columns=["date", "season", "home", "away", "hg", "ag"])
    for col in ["hst", "ast", "mkt_lh", "mkt_la"]:
        df[col] = np.nan
    fit = fit_dixon_coles(df, day + pd.Timedelta(days=1), DCConfig(xi=0.0, prior_sd=3.0, seasons_back=10),
                          current_season=2020, laplace=True)
    idx = fit.index
    a_hat = np.array([fit.attack[idx[t]] for t in teams])
    d_hat = np.array([fit.defence[idx[t]] for t in teams])
    # ratings are identified up to a common shift
    assert np.corrcoef(a_hat, att)[0, 1] > 0.95
    assert np.corrcoef(d_hat, dfn)[0, 1] > 0.93
    assert abs(fit.h - h) < 0.06
    assert abs(fit.rho - rho) < 0.06
    # the reported uncertainty should cover the truth for most teams
    sd = np.sqrt(np.diag(fit.cov))[3:23]
    z = ((a_hat - a_hat.mean()) - (att - att.mean())) / sd
    assert np.mean(np.abs(z) < 2.5) >= 0.85


def test_market_conversion_round_trip():
    lam = np.array([0.6, 1.2, 1.5, 2.4, 3.1])
    mu = np.array([2.2, 1.4, 1.1, 0.7, 0.4])
    m = score_matrix(lam, mu, -0.05)
    p = outcome_probs(m)
    po = over_prob(m)
    l2, m2, err = implied_goals(p[:, 0], p[:, 2], po, rho=-0.05)
    assert np.allclose(l2, lam, atol=1e-5) and np.allclose(m2, mu, atol=1e-5)
    assert err.max() < 1e-8


def test_implied_probabilities_remove_margin():
    p = implied_1x2([2.0, 1.5], [3.4, 4.2], [3.9, 7.0])
    assert np.allclose(p.sum(1), 1.0)
    assert (p[:, 0] < 1 / np.array([2.0, 1.5])).all()      # margin removed
    po = implied_over([1.9], [1.9])
    assert np.allclose(po, 0.5)


def test_scoring_rules():
    probs = np.array([[1.0, 0, 0], [0.5, 0.3, 0.2]])
    y = outcome_index([2, 0], [0, 0])
    assert y.tolist() == [0, 1]
    r = rps(probs, y)
    assert r[0] == 0.0
    assert np.isclose(r[1], ((0.5 - 0) ** 2 + (0.8 - 1) ** 2) / 2)
    assert np.isclose(log_loss(probs, y)[1], -np.log(0.3))
