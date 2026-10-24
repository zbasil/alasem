"""Fit and test the in-play model.

Part 1 (half-time -> full-time, La Liga 2005/06-2025/26 with market odds):
    tune on 2005/06-2017/18, test on 2018/19-2025/26.
Part 2 (StatsBomb 2015/16 event data, 1,517 matches in four leagues):
    goal-time profile within halves and the effect of red cards.
    Input: data/statsbomb/sb1516_goals_reds.jsonl.gz (made by scripts/sb_extract.py).

Writes outputs/inplay_model.json and outputs/inplay_report.json
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import SB_EXTRACT  # noqa: E402

from zsc.dixon_coles import outcome_probs, score_matrix  # noqa: E402
from zsc.evaluate import calibration_table, log_loss, outcome_index, rps  # noqa: E402
from zsc.inplay import InPlayModel, fit_state_multipliers, fit_state_strength  # noqa: E402
from zsc.pipeline import load_snapshot  # noqa: E402

TEST_WF = range(2016, 2026)     # walk-forward test seasons
WINDOW = 8                      # seasons of history used for each fit


def ht_probs(model: InPlayModel, df: pd.DataFrame) -> np.ndarray:
    return np.array([model.probs(l, m, 45, int(h), int(a), period=1)
                     for l, m, h, a in zip(df["mkt_lh"], df["mkt_la"], df["hthg"], df["htag"])])


def scores(p, y):
    return {"rps": float(rps(p, y).mean()), "logloss": float(log_loss(p, y).mean()),
            "hit": float((p.argmax(1) == y).mean())}


def build_models(tr: pd.DataFrame):
    s = float((tr["hthg"].sum() + tr["htag"].sum()) / (tr["hg"].sum() + tr["ag"].sum()))
    kh, ka, n = fit_state_multipliers(tr, s)
    ss = fit_state_strength(tr, s)
    return s, kh, ka, n, {
        "HT, even time, no state": InPlayModel(first_half_share=0.5),
        "HT, time profile": InPlayModel(first_half_share=s),
        "HT, time profile + state": InPlayModel(first_half_share=s, k_home=kh, k_away=ka),
        "HT, time profile + state x strength": InPlayModel(first_half_share=s, k_home=ss["home"][0], b_home=ss["home"][1],
                                                           k_away=ss["away"][0], b_away=ss["away"][1]),
    }


def part1(m: pd.DataFrame, log):
    """Walk-forward test: for each season T in 2016/17-2025/26, fit on the 8 seasons
    before T and predict the full-time result of every match of T from its half-time
    score. This is exactly how the model is used live (fit on the past, apply now)."""
    h = m[m["hthg"].notna() & m["mkt_lh"].notna()].copy()
    preds, ys = {}, []
    for T in TEST_WF:
        fit = h[(h["season"] < T) & (h["season"] >= T - WINDOW)]
        val = h[h["season"] == T]
        *_, models = build_models(fit)
        ys.append(outcome_index(val["hg"], val["ag"]))
        preds.setdefault("pre-match only", []).append(
            outcome_probs(score_matrix(val["mkt_lh"].values, val["mkt_la"].values, -0.05)))
        for k, mdl in models.items():
            preds.setdefault(k, []).append(ht_probs(mdl, val))
    y = np.concatenate(ys)
    preds = {k: np.concatenate(v) for k, v in preds.items()}
    res = {k: scores(p, y) for k, p in preds.items()}
    for k, r in res.items():
        log(f"WALK-FORWARD {k:38s} rps={r['rps']:.5f} logloss={r['logloss']:.5f} hit={r['hit']:.3f}")
    choice = min((k for k in res if k != "pre-match only"), key=lambda k: res[k]["rps"])
    rng = np.random.default_rng(0)
    d = rps(preds[choice], y) - rps(preds["HT, time profile"], y)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    log(f"chosen: {choice}; vs time profile only {d.mean():+.5f} "
        f"(95% CI {np.percentile(bs, 2.5):+.5f} to {np.percentile(bs, 97.5):+.5f}), n={len(y)}")
    cal = calibration_table(preds[choice], y)
    log("calibration at half-time (forecast -> observed): " +
        "; ".join(f"{lo:.1f}-{hi:.1f}: {f:.3f}->{o:.3f} (n={nn})" for lo, hi, nn, f, o in cal))

    # final model for live use: the most recent WINDOW seasons
    final_fit = h[h["season"] >= h["season"].max() - WINDOW + 1]
    s, kh, ka, n, models = build_models(final_fit)
    log(f"final fit on {final_fit['season'].min()}/{final_fit['season'].max()}: {len(final_fit)} matches, "
        f"first-half share {s:.4f}")
    mdl = models[choice]
    log("state multipliers at even strength (HT goal difference home-away): " +
        ", ".join(f"{dd:+d}: home x{mdl.k_home[dd]:.3f} away x{mdl.k_away[dd]:.3f}" for dd in range(-2, 3)))
    return s, mdl, choice, n, res, cal


def load_sb(path):
    import gzip
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def part2(sb_path, s, kh, ka, log):
    """Within-half time profile and red-card effects from StatsBomb 2015/16."""
    rows = load_sb(sb_path)
    ok = [r for r in rows if r["ev_home_goals"] == r["home_score"] and r["ev_away_goals"] == r["away_score"]]
    log(f"StatsBomb 2015/16: {len(rows)} matches, {len(ok)} with event goals matching the final score")

    # goal minutes in regulation (periods 1-2) on the effective clock
    mdl = InPlayModel(first_half_share=s)
    eff = []
    for r in ok:
        for g in r["goals"]:
            if g["period"] in (1, 2):
                t = g["minute"] + g["second"] / 60
                e = mdl.effective_minute(t, g["period"])
                # first-half stoppage goals sit at 45.0; keep them in the first half's bins
                eff.append(min(e, 44.999) if g["period"] == 1 else max(e, 45.0))
    eff = np.array(eff)
    # compare the empirical share of goals per 15-minute block with the model
    edges = [0, 15, 30, 45, 60, 75, 90.0001]
    emp = np.histogram(eff, bins=edges)[0] / len(eff)
    mod = np.diff([mdl._cum(e) for e in [0, 15, 30, 45, 60, 75, 90]])
    log(f"goals on the effective clock: {len(eff)}; first-half share {np.mean(eff <= 45):.4f}")
    log("share of goals per 15 min, data vs model: " +
        ", ".join(f"{a:.3f}/{b:.3f}" for a, b in zip(emp, mod)))

    # red cards: within-match conditional likelihood.
    # For each team-match with a red card, split its time into intervals of constant
    # (own reds, opponent reds); given the team's goal count, goal times are multinomial
    # over intervals with weight = expected-goal share * own^own_reds * opp^opp_reds.
    team_rows = []
    for r in ok:
        if not r["reds"]:
            continue
        for side, team in (("home", r["home"]), ("away", r["away"])):
            cuts = sorted(set([0.0, 90.0] + [mdl.effective_minute(x["minute"] + x["second"] / 60, x["period"])
                                               for x in r["reds"]]))
            ints = []
            for a, b in zip(cuts[:-1], cuts[1:]):
                own = sum(1 for x in r["reds"] if x["team"] == team
                          and mdl.effective_minute(x["minute"] + x["second"] / 60, x["period"]) <= a)
                opp = sum(1 for x in r["reds"] if x["team"] != team
                          and mdl.effective_minute(x["minute"] + x["second"] / 60, x["period"]) <= a)
                share = mdl._cum(b) - mdl._cum(a)
                n_goals = sum(1 for g in r["goals"] if g["team"] == team and g["period"] in (1, 2)
                              and a < mdl.effective_minute(g["minute"] + g["second"] / 60, g["period"]) <= b)
                ints.append((share, own, opp, n_goals))
            team_rows.append(ints)
    n_red_matches = sum(1 for r in ok if r["reds"])
    log(f"matches with a red card: {n_red_matches}; team-match units: {len(team_rows)}")

    def nll(theta):
        lo, lp = theta          # log multipliers
        tot = 0.0
        for ints in team_rows:
            w = np.array([sh * np.exp(lo * own + lp * opp) for sh, own, opp, _ in ints])
            g = np.array([n for *_, n in ints])
            if g.sum() == 0:
                continue
            p = w / w.sum()
            tot -= float((g * np.log(np.maximum(p, 1e-300))).sum())
        return tot

    from scipy.optimize import minimize
    res = minimize(nll, np.zeros(2), method="BFGS")
    lo, lp = res.x
    # standard errors from the inverse Hessian
    se = np.sqrt(np.diag(res.hess_inv)) if hasattr(res, "hess_inv") else np.array([np.nan, np.nan])
    own, opp = float(np.exp(lo)), float(np.exp(lp))
    ci_own = (float(np.exp(lo - 1.96 * se[0])), float(np.exp(lo + 1.96 * se[0])))
    ci_opp = (float(np.exp(lp - 1.96 * se[1])), float(np.exp(lp + 1.96 * se[1])))
    log(f"red card effect: own scoring x{own:.3f} (95% CI {ci_own[0]:.2f}-{ci_own[1]:.2f}), "
        f"opponent scoring x{opp:.3f} (95% CI {ci_opp[0]:.2f}-{ci_opp[1]:.2f})")
    block = {"goals": int(len(eff)), "first_half_share_sb": float(np.mean(eff <= 45)),
             "per15_data": emp.tolist(), "per15_model": mod.tolist(),
             "red_matches": n_red_matches, "red_own": own, "red_opp": opp,
             "red_own_ci": ci_own, "red_opp_ci": ci_opp}
    return block


def main():
    out_dir = os.path.join(ROOT, "outputs")
    lines = []

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    m = load_snapshot()
    s, model, choice, n, res, cal = part1(m, log)
    report = {"half_time_walk_forward": res, "chosen": choice, "window_seasons": WINDOW,
              "test_seasons": [min(TEST_WF), max(TEST_WF)], "first_half_share": s, "n_by_state": n,
              "model": model.to_json(),
              "calibration": [{"lo": lo, "hi": hi, "n": nn, "forecast": f, "observed": o} for lo, hi, nn, f, o in cal]}
    sb_path = sys.argv[1] if len(sys.argv) > 1 else SB_EXTRACT
    if sb_path and os.path.exists(sb_path):
        block = part2(sb_path, s, model.k_home, model.k_away, log)
        report["statsbomb"] = block
        model.red_own = round(block["red_own"], 3)
        model.red_opp = round(block["red_opp"], 3)
    with open(os.path.join(out_dir, "inplay_model.json"), "w") as f:
        json.dump(model.to_json(), f, indent=2)
    with open(os.path.join(out_dir, "inplay_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=float)
    with open(os.path.join(out_dir, "inplay_log.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
