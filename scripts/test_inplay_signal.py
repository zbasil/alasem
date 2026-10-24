"""Does what happened in the first half (shots on target, xG) improve the half-time forecast?

    python scripts/test_inplay_signal.py

Data: La Liga 2015/16, the one full season with event data (StatsBomb Open Data; first-half shots, shots on target
and xG per team), joined by date and teams to the pre-match forecasts the market track made before each match
(outputs/eval/wf_market.csv, the same walk-forward predictions as the evaluation).

Baseline: the live model (outputs/models/inplay.json) at half-time from the pre-match lambda, mu, rho and the score.
Candidate: the same, with the second-half scoring rates multiplied by exp(+-beta * s), where s is a team's first-half
signal minus what was expected of it (expected = its pre-match rate x the first-half share), opponent subtracted.
Beta is fitted on the other folds only (5 folds by date), so every forecast is out of sample; the score state is
kept, so the goals already scored are not counted twice. Result: reports/inplay_signal_test.json.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.dixon_coles import score_matrix  # noqa: E402
from zsc.evaluate import outcome_index, rps  # noqa: E402
from zsc.evaluation import paired_diff as paired_bootstrap  # noqa: E402
from zsc.inplay import InPlayModel  # noqa: E402
from zsc.teams import canonical  # noqa: E402


def load():
    th = pd.read_csv(os.path.join(ROOT, "outputs", "archive", "sb_laliga1516_team_halves.csv.gz"))
    th = th[th["period"] == 1]
    rows = []
    for mid, g in th.groupby("match_id"):
        r0 = g.iloc[0]
        home, away = r0["home_team"], r0["away_team"]
        get = lambda team, k: float(g.loc[g["team"] == team, k].sum())
        rows.append({"sb_id": mid, "date": r0["date"], "home": canonical(home), "away": canonical(away),
                     "sot_h": get(home, "sot"), "sot_a": get(away, "sot"), "xg_h": get(home, "xg"), "xg_a": get(away, "xg"),
                     "sh_h": get(home, "shots"), "sh_a": get(away, "shots")})
    sb = pd.DataFrame(rows)
    wf = pd.read_csv(os.path.join(ROOT, "outputs", "eval", "wf_market.csv"))
    wf = wf[wf["season"] == 2015].copy()
    wf["date"] = pd.to_datetime(wf["date"]).dt.strftime("%Y-%m-%d")
    m = wf.merge(sb, on=["date", "home", "away"], how="inner")
    return m


def forecast(ip: InPlayModel, r, beta: float = 0.0, signal: str = "xg") -> np.ndarray:
    share1 = ip.first_half_share
    lam, mu, rho = r.xg_home, r.xg_away, r.rho
    hg, ag = int(r.hthg), int(r.htag)
    rl, rm = ip.remaining_rates(lam, mu, 45, hg, ag, 0, 0, period=1)
    if beta:
        if signal == "xg":
            s = (r.xg_h - lam * share1) - (r.xg_a - mu * share1)
        else:  # shots on target, scaled by the league's xG per shot on target (about 0.3) to a comparable unit
            s = 0.3 * ((r.sot_h - lam * share1 / 0.3 * 0.3) - (r.sot_a - mu * share1 / 0.3 * 0.3))
        rl, rm = rl * np.exp(beta * s), rm * np.exp(-beta * s)
    add = score_matrix(rl, rm, ip.rho_remaining(rho, 45, 1))[0]
    G = add.shape[0]
    full = np.zeros((G + hg, G + ag))
    full[hg:hg + G, ag:ag + G] = add
    i, j = np.indices(full.shape)
    return np.array([full[i > j].sum(), full[i == j].sum(), full[i < j].sum()])


def nll(ip, df, beta, signal):
    """Poisson log-likelihood of second-half goals (the fitting target)."""
    share1 = ip.first_half_share
    tot = 0.0
    for r in df.itertuples():
        rl, rm = ip.remaining_rates(r.xg_home, r.xg_away, 45, int(r.hthg), int(r.htag), 0, 0, period=1)
        s = (r.xg_h - r.xg_home * share1) - (r.xg_a - r.xg_away * share1) if signal == "xg" else \
            0.3 * ((r.sot_h - r.xg_home * share1) - (r.sot_a - r.xg_away * share1))
        lh, la = rl * np.exp(beta * s), rm * np.exp(-beta * s)
        yh, ya = r.hg - r.hthg, r.ag - r.htag
        tot += (lh - yh * np.log(lh)) + (la - ya * np.log(la))
    return tot


def main():
    ip = InPlayModel.load(os.path.join(ROOT, "outputs", "models", "inplay.json"))
    m = load().sort_values("date").reset_index(drop=True)
    y = outcome_index(m["hg"].astype(int), m["ag"].astype(int))
    folds = np.array_split(np.arange(len(m)), 5)
    base = np.array([forecast(ip, r) for r in m.itertuples()])
    out = {"data": "La Liga 2015/16, StatsBomb Open Data first halves + market-track pre-match forecasts",
           "n": int(len(m)), "baseline_rps": float(rps(base, y).mean()), "signals": {}}
    for signal in ("xg", "sot"):
        pred = np.zeros_like(base)
        betas = []
        for k, idx in enumerate(folds):
            train = m.drop(index=idx)
            res = minimize_scalar(lambda b: nll(ip, train, b, signal), bounds=(-1.0, 1.0), method="bounded")
            betas.append(float(res.x))
            for i in idx:
                pred[i] = forecast(ip, m.iloc[i], res.x, signal)
        cmp = paired_bootstrap(rps(pred, y), rps(base, y))
        out["signals"][signal] = {"beta_by_fold": [round(b, 3) for b in betas], "rps": float(rps(pred, y).mean()),
                                  "vs_baseline": cmp}
        print(f"{signal}: beta {np.round(betas, 3)} RPS {rps(pred, y).mean():.4f} vs baseline {rps(base, y).mean():.4f}; "
              f"diff {cmp['diff']:+.4f} [{cmp['ci_low']:+.4f}, {cmp['ci_high']:+.4f}] clear={cmp['clear']}")
    adopted = [s for s, v in out["signals"].items() if v["vs_baseline"]["clear"] and v["vs_baseline"]["diff"] < 0]
    out["decision"] = ("adopt " + ", ".join(adopted)) if adopted else \
        "not adopted: no clear improvement on 380 matches (one season of event data); re-test when more event data exist"
    out["decision_ar"] = ("ينضاف: " + "، ".join(adopted)) if adopted else \
        "ما ينضاف: ماكو تحسن واضح على 380 مباراة (موسم واحد بيانات أحداث)؛ ينعاد الاختبار لما تتوفر بيانات أكثر"
    with open(os.path.join(ROOT, "reports", "inplay_signal_test.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(out["decision"])


if __name__ == "__main__":
    main()
