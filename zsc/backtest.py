"""Honest out-of-sample evaluation.

Walk-forward: for every week of a test season the model is refitted using
only matches played before that week, then it predicts that week's matches.
Nothing from the future is ever used. Bet365's pre-match odds (margin
removed) are scored on exactly the same matches as the benchmark.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .dixon_coles import DCConfig, fit_dixon_coles, score_matrix
from .evaluate import brier, log_loss, outcome_index, rps
from .market import implied_1x2
from .pipeline import promoted_teams, season_teams


def walk_forward(matches: pd.DataFrame, seasons, cfg: DCConfig) -> pd.DataFrame:
    rows = []
    for s in seasons:
        sm = matches[matches["season"] == s].sort_values("date")
        teams = season_teams(matches, s)
        prom = promoted_teams(matches, s)
        start = sm["date"].min()
        week = ((sm["date"] - start).dt.days // 7).values
        prev = None
        for wk in np.unique(week):
            g = sm[week == wk]
            ref = g["date"].min()
            fit = fit_dixon_coles(matches, ref, cfg, current_teams=teams, promoted=prom,
                                  current_season=s, x0=prev, laplace=False)
            prev = fit
            p = fit.predict(g["home"], g["away"])
            cols = ["date", "season", "home", "away", "hg", "ag", "odds_h", "odds_d", "odds_a"]
            cols += [c for c in ("hthg", "htag", "hst", "ast", "mkt_lh", "mkt_la") if c in g]
            out = g[cols].copy()
            out["p_home"], out["p_draw"], out["p_away"] = p["p_home"].values, p["p_draw"].values, p["p_away"].values
            out["xg_home"], out["xg_away"] = p["xg_home"].values, p["xg_away"].values
            out["rho"] = fit.rho
            mats = score_matrix(p["xg_home"].values, p["xg_away"].values, fit.rho)
            G = mats.shape[1]
            hg_, ag_ = np.minimum(g["hg"].values, G - 1), np.minimum(g["ag"].values, G - 1)
            out["p_exact"] = mats[np.arange(len(g)), hg_, ag_]
            best = mats.reshape(len(g), -1).argmax(1)
            out["likely_hg"], out["likely_ag"] = best // G, best % G
            out["p_likely"] = mats.reshape(len(g), -1).max(1)
            out["promoted_home"] = g["home"].isin(prom).values
            out["promoted_away"] = g["away"].isin(prom).values
            out["week"] = wk
            rows.append(out)
    return pd.concat(rows, ignore_index=True)


def prior_base_rates(matches: pd.DataFrame, season: int, n_seasons: int = 5) -> np.ndarray:
    """Home / draw / away frequencies of the n seasons before `season` (known before it starts)."""
    past = matches[(matches["season"] < season) & (matches["season"] >= season - n_seasons)]
    y = outcome_index(past["hg"], past["ag"])
    return np.bincount(y, minlength=3) / max(1, len(y))


def score(pred: pd.DataFrame) -> dict:
    y = outcome_index(pred["hg"], pred["ag"])
    pm = pred[["p_home", "p_draw", "p_away"]].values
    res = {"n": len(pred), "rps": rps(pm, y).mean(), "logloss": log_loss(pm, y).mean(), "brier": brier(pm, y).mean()}
    ok = pred[["odds_h", "odds_d", "odds_a"]].notna().all(axis=1).values
    if ok.any():
        pk = implied_1x2(pred.loc[ok, "odds_h"], pred.loc[ok, "odds_d"], pred.loc[ok, "odds_a"])
        res.update({"n_mkt": int(ok.sum()),
                    "rps_model_on_mkt": rps(pm[ok], y[ok]).mean(),
                    "rps_mkt": rps(pk, y[ok]).mean(),
                    "logloss_model_on_mkt": log_loss(pm[ok], y[ok]).mean(),
                    "logloss_mkt": log_loss(pk, y[ok]).mean()})
    # baseline known before each season: home/draw/away rates of the 5 seasons before it
    if "base_h" in pred:
        base = pred[["base_h", "base_d", "base_a"]].values
        res["rps_base_rates"] = rps(base, y).mean()
    return res


def tune(matches: pd.DataFrame, seasons, base: DCConfig, grid: dict, passes: int = 2, log=print):
    """Coordinate descent on mean RPS."""
    best = base
    cache = {}

    def run(cfg):
        key = tuple(sorted(cfg.__dict__.items()))
        if key not in cache:
            cache[key] = score(walk_forward(matches, seasons, cfg))["rps"]
        return cache[key]

    best_val = run(best)
    log(f"start rps={best_val:.5f} {best}")
    for _ in range(passes):
        for name, values in grid.items():
            for v in values:
                cand = replace(best, **{name: v})
                val = run(cand)
                if val < best_val - 1e-7:
                    best, best_val = cand, val
                    log(f"  improved rps={best_val:.5f} with {name}={v}")
    return best, best_val, cache
