"""Fitting and testing the in-play model on the inputs the app really uses.

The live app starts every match from the project's own pre-match expected
goals (lambda, mu) and Dixon-Coles rho. So the half-time -> full-time
multipliers are fitted, and tested, with exactly those inputs: the
walk-forward pre-match predictions of the displayed track (no market goals
sneak in unless the track itself uses them).
"""

from __future__ import annotations

import gzip
import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .dixon_coles import outcome_probs, score_matrix
from .inplay import InPlayModel, fit_state_multipliers, fit_state_strength


def with_inputs(pred: pd.DataFrame) -> pd.DataFrame:
    """Walk-forward predictions -> table with the in-play fitting columns (lambda, mu as mkt_* names
    because the fitting helpers read those columns)."""
    d = pred[pred["hthg"].notna() & pred["htag"].notna()].copy()
    d["mkt_lh"], d["mkt_la"] = d["xg_home"], d["xg_away"]
    return d


def first_half_share(tr: pd.DataFrame) -> float:
    return float((tr["hthg"].sum() + tr["htag"].sum()) / (tr["hg"].sum() + tr["ag"].sum()))


def candidate_models(tr: pd.DataFrame) -> dict[str, InPlayModel]:
    """All variants considered, fitted on the training seasons `tr`."""
    s = first_half_share(tr)
    kh, ka, _ = fit_state_multipliers(tr, s)
    ss = fit_state_strength(tr, s)
    out = {}
    for rho_mode in ("none", "remaining"):
        tag = "" if rho_mode == "none" else " + low-score correction"
        out["time profile" + tag] = InPlayModel(first_half_share=s, rho_mode=rho_mode)
        out["time profile + score" + tag] = InPlayModel(first_half_share=s, k_home=kh, k_away=ka, rho_mode=rho_mode)
        out["time profile + score x strength" + tag] = InPlayModel(
            first_half_share=s, k_home=ss["home"][0], b_home=ss["home"][1],
            k_away=ss["away"][0], b_away=ss["away"][1], rho_mode=rho_mode)
    return out


def ht_probs(model: InPlayModel, df: pd.DataFrame) -> np.ndarray:
    return np.array([model.probs(l, m, 45, int(h), int(a), period=1, rho=r)
                     for l, m, r, h, a in zip(df["mkt_lh"], df["mkt_la"], df["rho"], df["hthg"], df["htag"])])


def prematch_probs(df: pd.DataFrame) -> np.ndarray:
    return np.vstack([outcome_probs(score_matrix(l, m, r))[0] for l, m, r in zip(df["mkt_lh"], df["mkt_la"], df["rho"])])


def walk_forward_ht(d: pd.DataFrame, seasons, window: int = 8):
    """For each season T fit every variant on the `window` seasons before T and predict T's matches
    from their half-time score. Returns (rows of the predicted matches, {variant: probs})."""
    preds, frames = {}, []
    for T in seasons:
        tr = d[(d["season"] < T) & (d["season"] >= T - window)]
        val = d[d["season"] == T]
        if not len(val) or not len(tr):
            continue
        frames.append(val)
        preds.setdefault("pre-match only", []).append(prematch_probs(val))
        for k, mdl in candidate_models(tr).items():
            preds.setdefault(k, []).append(ht_probs(mdl, val))
    rows = pd.concat(frames, ignore_index=True)
    return rows, {k: np.vstack(v) for k, v in preds.items()}


# --------------------------------------------------------------------------
# StatsBomb 2015/16: goal-time profile and red cards (independent data)
# --------------------------------------------------------------------------

def load_statsbomb_extract(path: str) -> list[dict]:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def statsbomb_checks(rows: list[dict], s: float) -> dict:
    """Within-half goal-time profile (data vs model) and the red-card multipliers
    (within-match conditional likelihood, so team strength cancels out)."""
    ok = [r for r in rows if r["ev_home_goals"] == r["home_score"] and r["ev_away_goals"] == r["away_score"]]
    mdl = InPlayModel(first_half_share=s)
    eff = []
    for r in ok:
        for g in r["goals"]:
            if g["period"] in (1, 2):
                e = mdl.effective_minute(g["minute"] + g["second"] / 60, g["period"])
                eff.append(min(e, 44.999) if g["period"] == 1 else max(e, 45.0))
    eff = np.array(eff)
    edges = [0, 15, 30, 45, 60, 75, 90.0001]
    emp = np.histogram(eff, bins=edges)[0] / len(eff)
    mod = np.diff([mdl._cum(e) for e in [0, 15, 30, 45, 60, 75, 90]])

    team_rows = []
    for r in ok:
        if not r["reds"]:
            continue
        for team in (r["home"], r["away"]):
            def t_of(x):
                return mdl.effective_minute(x["minute"] + x["second"] / 60, x["period"])
            cuts = sorted(set([0.0, 90.0] + [t_of(x) for x in r["reds"]]))
            ints = []
            for a, b in zip(cuts[:-1], cuts[1:]):
                own = sum(1 for x in r["reds"] if x["team"] == team and t_of(x) <= a)
                opp = sum(1 for x in r["reds"] if x["team"] != team and t_of(x) <= a)
                n_goals = sum(1 for g in r["goals"] if g["team"] == team and g["period"] in (1, 2) and a < t_of(g) <= b)
                ints.append((mdl._cum(b) - mdl._cum(a), own, opp, n_goals))
            team_rows.append(ints)

    def nll(theta):
        lo, lp = theta
        tot = 0.0
        for ints in team_rows:
            w = np.array([sh * np.exp(lo * own + lp * opp) for sh, own, opp, _ in ints])
            g = np.array([n for *_, n in ints])
            if g.sum() == 0:
                continue
            p = w / w.sum()
            tot -= float((g * np.log(np.maximum(p, 1e-300))).sum())
        return tot

    res = minimize(nll, np.zeros(2), method="BFGS")
    se = np.sqrt(np.diag(res.hess_inv))
    lo, lp = res.x
    return {"matches": len(rows), "matches_used": len(ok), "goals": int(len(eff)),
            "first_half_share_statsbomb": float(np.mean(eff <= 45)),
            "per15_data": emp.tolist(), "per15_model": mod.tolist(),
            "red_matches": sum(1 for r in ok if r["reds"]),
            "red_own": float(np.exp(lo)), "red_opp": float(np.exp(lp)),
            "red_own_ci": [float(np.exp(lo - 1.96 * se[0])), float(np.exp(lo + 1.96 * se[0]))],
            "red_opp_ci": [float(np.exp(lp - 1.96 * se[1])), float(np.exp(lp + 1.96 * se[1]))]}
