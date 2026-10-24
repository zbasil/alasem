"""Honest evaluation of every forecast the app shows (version 2).

Time separation
    training      everything played before each prediction (walk-forward refits every week)
    selection     2012/13-2022/23: every setting, variant and calibration is chosen here
    final test    2023/24-2025/26: looked at once, after all choices; never used to choose

Parts
    1. pre-match: two tracks (independent = no market inputs, market = market-implied goals in the
       training targets) against Bet365's pre-match odds and a base-rate baseline known before each season
    2. input ablations (selection seasons only) and a rest-days experiment
    3. in-play: half-time -> full-time with the production inputs (each track's own lambda, mu, rho)
    4. season: projections made after 100 matches, drift chosen on selection seasons, tested on the rest
    5. model registry with versions, configs and the data fingerprint

    python scripts/evaluate_all.py [--quick]

Writes reports/evaluation.json, reports/evaluation.md, outputs/models/*.json, outputs/eval/*.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import SB_EXTRACT  # noqa: E402

from zsc import evaluation as ev  # noqa: E402
from zsc.backtest import prior_base_rates, walk_forward  # noqa: E402
from zsc.dixon_coles import DCConfig, fit_dixon_coles  # noqa: E402
from zsc.evaluate import outcome_index, rps  # noqa: E402
from zsc.inplay import InPlayModel  # noqa: E402
from zsc.inplay_fit import (candidate_models, first_half_share, load_statsbomb_extract,  # noqa: E402
                            statsbomb_checks, walk_forward_ht, with_inputs)
from zsc.market import implied_1x2  # noqa: E402
from zsc.pipeline import load_snapshot, promoted_teams, season_teams  # noqa: E402
from zsc.simulate import simulate_season  # noqa: E402
from zsc.standings import compute_table, league_table  # noqa: E402

SELECTION = list(range(2012, 2023))
TEST = [2023, 2024, 2025]
WF_SEASONS = list(range(2008, 2026))      # in-play windows need pre-match predictions from 2008/09
INPLAY_SEL = list(range(2016, 2023))
WINDOW = 8
CUT_MATCHES = 100
DRIFTS = [0.0, 0.025, 0.05, 0.075, 0.1]
VERSION = "2.0"
OUT = os.path.join(ROOT, "outputs")
EVAL = os.path.join(OUT, "eval")
MODELS = os.path.join(OUT, "models")
REPORTS = os.path.join(ROOT, "reports")


def label(seasons):
    return f"{seasons[0]}/{(seasons[0] + 1) % 100:02d}-{seasons[-1]}/{(seasons[-1] + 1) % 100:02d}"


def data_fingerprint(m: pd.DataFrame) -> str:
    from zsc.store import fingerprint
    return fingerprint(m)


def load_cfg(track: str) -> DCConfig:
    with open(os.path.join(MODELS, f"config_{track}.json")) as f:
        return DCConfig(**json.load(f)["config"])


def wf_cached(m, track, cfg, seasons, log):
    path = os.path.join(EVAL, f"wf_{track}.csv")
    key = json.dumps(asdict(cfg), sort_keys=True)
    meta = path + ".key"
    if os.path.exists(path) and os.path.exists(meta) and open(meta).read() == key:
        df = pd.read_csv(path, parse_dates=["date"])
        if set(seasons) <= set(df["season"].unique()):
            return df
    t0 = time.time()
    df = walk_forward(m, seasons, cfg)
    for s in seasons:                                    # baseline known before each season
        b = prior_base_rates(m, s)
        sel = df["season"] == s
        df.loc[sel, "base_h"], df.loc[sel, "base_d"], df.loc[sel, "base_a"] = b
    df.to_csv(path, index=False)
    open(meta, "w").write(key)
    log(f"  walk-forward {track}: {len(df)} matches in {time.time() - t0:.0f}s")
    return df


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


# --------------------------------------------------------------------------
# 1. pre-match
# --------------------------------------------------------------------------

def prematch(wf: dict, log) -> dict:
    out = {}
    for split, seasons in (("selection", SELECTION), ("test", TEST)):
        mk = wf["market"][wf["market"]["season"].isin(seasons)].reset_index(drop=True)
        ind = wf["independent"][wf["independent"]["season"].isin(seasons)].reset_index(drop=True)
        assert (mk[["date", "home", "away"]].values == ind[["date", "home", "away"]].values).all()
        y = outcome_index(mk["hg"], mk["ag"])
        has_odds = mk[["odds_h", "odds_d", "odds_a"]].notna().all(axis=1).to_numpy()
        models = {"market": ev.probs_matrix(mk), "independent": ev.probs_matrix(ind),
                  "base_rates": mk[["base_h", "base_d", "base_a"]].to_numpy(float)}
        # Bet365 on the matches that have odds (all of them in these seasons)
        sub = has_odds
        p365 = implied_1x2(mk.loc[sub, "odds_h"], mk.loc[sub, "odds_d"], mk.loc[sub, "odds_a"])
        res = {"seasons": label(seasons), "n": int(len(y)), "n_with_odds": int(sub.sum()), "scores": {}}
        for k, p in models.items():
            res["scores"][k] = ev.scores(p[sub], y[sub])
        res["scores"]["bet365"] = ev.scores(p365, y[sub])
        res["scores"]["always_home"] = {"n": int(sub.sum()), "hit": float((y[sub] == 0).mean())}
        allm = {**{k: v[sub] for k, v in models.items()}, "bet365": p365}
        res["comparisons"] = ev.compare(allm, y[sub], [("market", "bet365"), ("independent", "bet365"),
                                                       ("market", "independent"), ("market", "base_rates"),
                                                       ("independent", "base_rates")])
        # share of the bookmaker's improvement over the baseline that each track achieves (RPS)
        sc = res["scores"]
        for k in ("market", "independent"):
            res[f"share_of_bet365_gain_{k}"] = (sc["base_rates"]["rps"] - sc[k]["rps"]) / (
                sc["base_rates"]["rps"] - sc["bet365"]["rps"])
        res["exact_scores"] = {"market": ev.exact_scores(mk), "independent": ev.exact_scores(ind)}
        # baseline for exact scores: the most frequent score of the 5 seasons before each season
        hits = []
        for s in seasons:
            hist = M[(M["season"] < s) & (M["season"] >= s - 5)]
            top = hist.groupby(["hg", "ag"]).size().idxmax()
            cur = mk[mk["season"] == s]
            hits.append(((cur["hg"] == top[0]) & (cur["ag"] == top[1])).to_numpy())
        res["exact_scores"]["most_common_score"] = {"exact_hit": float(np.concatenate(hits).mean())}
        if split == "test":
            res["calibration"] = {k: ev.calibration(p, y[sub]) for k, p in allm.items() if k != "base_rates"}
            res["calibration_by_outcome"] = {
                k: {name: ev.calibration(allm[k], y[sub], outcome=o)
                    for o, name in enumerate(("home", "draw", "away"))} for k in ("market", "independent", "bet365")}
            res["calibration_error"] = {k: ev.calibration_error(v) for k, v in res["calibration"].items()}
            both = {"market": ("p_home", "p_draw", "p_away")}
            mk2 = mk.copy()
            mk2[["i_home", "i_draw", "i_away"]] = models["independent"]
            mk2[["b_home", "b_draw", "b_away"]] = np.nan
            mk2.loc[sub, ["b_home", "b_draw", "b_away"]] = p365
            cols = {"market": ("p_home", "p_draw", "p_away"), "independent": ("i_home", "i_draw", "i_away"),
                    "bet365": ("b_home", "b_draw", "b_away")}
            res["breakdowns"] = {
                "season": ev.breakdown(mk2, cols, mk2["season"].to_numpy(), "season"),
                "phase": ev.breakdown(mk2, cols, ev.season_phase(mk2), "matchday"),
                "favourite": ev.breakdown(mk2, cols, ev.favourite_band(models["market"]), "favourite"),
                "data": ev.breakdown(mk2, cols, np.where(mk2["promoted_home"] | mk2["promoted_away"],
                                                         "promoted team (short history)", "established teams"), "data"),
                "team": ev.team_breakdown(mk2, cols["market"], "market"),
            }
            mk.to_csv(os.path.join(EVAL, "prematch_test_market.csv"), index=False)
            ind.to_csv(os.path.join(EVAL, "prematch_test_independent.csv"), index=False)
        out[split] = res
        s = res["scores"]
        log(f"  {split} {label(seasons)} n={res['n']}: RPS market {s['market']['rps']:.4f} independent "
            f"{s['independent']['rps']:.4f} bet365 {s['bet365']['rps']:.4f} base {s['base_rates']['rps']:.4f}; "
            f"hit {s['market']['hit']:.3f}/{s['independent']['hit']:.3f}/{s['bet365']['hit']:.3f}")
    return out


# --------------------------------------------------------------------------
# 2. ablations (selection seasons) and the rest-days experiment
# --------------------------------------------------------------------------

def ablations(m, cfg_ind, cfg_mkt, log) -> dict:
    variants = {
        "goals only": replace(cfg_ind, beta_sot=0.0, beta_mkt=0.0),
        "goals + shots on target": replace(cfg_ind, beta_mkt=0.0),
        "goals + shots + market": cfg_mkt,
        "independent without promoted-team prior": replace(cfg_ind, promoted_attack=0.0, promoted_defence=0.0),
        "independent without rating stretch": replace(cfg_ind, rating_scale=1.0),
        "independent without time decay": replace(cfg_ind, xi=0.0),
    }
    preds = {}
    for k, c in variants.items():
        t0 = time.time()
        preds[k] = walk_forward(m, SELECTION, c)
        log(f"  ablation '{k}' ({time.time() - t0:.0f}s)")
    y = outcome_index(preds["goals only"]["hg"], preds["goals only"]["ag"])
    pm = {k: ev.probs_matrix(v) for k, v in preds.items()}
    full = "goals + shots on target"           # = the tuned independent track
    pairs = [("goals + shots on target", "goals only"), ("goals + shots + market", full)] + \
            [(full, k) for k in pm if k.startswith("independent without")]
    labels = {("goals + shots on target", "goals only"): "shots on target",
              ("goals + shots + market", full): "market-implied goals",
              (full, "independent without promoted-team prior"): "promoted-team prior",
              (full, "independent without rating stretch"): "rating stretch",
              (full, "independent without time decay"): "time decay (recent matches weigh more)"}
    comps = ev.compare(pm, y, pairs)
    for c in comps:
        c["input"] = labels[(c["a"], c["b"])]
    res = {"seasons": label(SELECTION), "scores": {k: ev.scores(v, y) for k, v in pm.items()},
           "value_of_each_input": comps,
           "note": "negative RPS difference = the input improves the forecast (paired 95% bootstrap interval)"}
    return res, preds


def rest_days(m: pd.DataFrame, wf: pd.DataFrame, log) -> dict:
    """Does the gap since each team's previous league match add anything to the model's lambda/mu?
    Learned on the selection seasons, tested once on the test seasons. League matches only: cup and
    European fixtures are not in the data, so short gaps are under-counted (documented limitation)."""
    rows = []
    mm = m.sort_values("date")
    last = {}
    rest = {}
    for d, h, a in zip(mm["date"], mm["home"], mm["away"]):
        for t in (h, a):
            gap = (d - last[t]).days if t in last else np.nan
            rest[(d, t)] = min(gap, 14) if gap == gap else np.nan
            last[t] = d
    df = wf.copy()
    df["rest_h"] = [rest.get((d, h), np.nan) for d, h in zip(df["date"], df["home"])]
    df["rest_a"] = [rest.get((d, a), np.nan) for d, a in zip(df["date"], df["away"])]
    df = df.dropna(subset=["rest_h", "rest_a"])
    df["dr"] = (df["rest_h"] - df["rest_a"]) / 7.0
    from scipy.optimize import minimize_scalar

    tr = df[df["season"].isin(SELECTION)]

    def nll(g):
        lh = tr["xg_home"] * np.exp(g * tr["dr"])
        la = tr["xg_away"] * np.exp(-g * tr["dr"])
        return float((lh - tr["hg"] * np.log(lh) + la - tr["ag"] * np.log(la)).sum())

    g = minimize_scalar(nll, bounds=(-1, 1), method="bounded").x
    te = df[df["season"].isin(TEST)].reset_index(drop=True)
    from zsc.dixon_coles import outcome_probs, score_matrix
    adj = np.vstack([outcome_probs(score_matrix(l * np.exp(g * d), m_ * np.exp(-g * d), r))[0]
                     for l, m_, r, d in zip(te["xg_home"], te["xg_away"], te["rho"], te["dr"])])
    y = outcome_index(te["hg"], te["ag"])
    cmp = ev.compare({"with rest days": adj, "model": ev.probs_matrix(te)}, y, [("with rest days", "model")])
    log(f"  rest days: gamma={g:+.4f} per week of difference; test RPS change {cmp[0]['rps']['diff']:+.5f}")
    return {"gamma_per_week": float(g), "n_selection": int(len(tr)), "n_test": int(len(te)),
            "test_comparison": cmp[0], "adopted": bool(cmp[0]["rps"]["clear"] and cmp[0]["rps"]["diff"] < 0),
            "limitation": "league matches only (cup and European fixtures missing)"}


# --------------------------------------------------------------------------
# 3. in-play
# --------------------------------------------------------------------------

def inplay(wf: dict, log) -> dict:
    out = {}
    for track in ("market", "independent"):
        d = with_inputs(wf[track])
        rows, preds = walk_forward_ht(d, INPLAY_SEL + TEST, WINDOW)
        y = outcome_index(rows["hg"], rows["ag"])
        sel = rows["season"].isin(INPLAY_SEL).to_numpy()
        tst = rows["season"].isin(TEST).to_numpy()
        sel_scores = {k: ev.scores(p[sel], y[sel]) for k, p in preds.items()}
        best_any = min((k for k in preds if k != "pre-match only"), key=lambda k: sel_scores[k]["rps"])
        # constraint: at kick-off the live forecast must equal the pre-match one, which uses the Dixon-Coles
        # low-score correction, so only variants that keep it are eligible
        consistent = [k for k in preds if "low-score correction" in k]
        choice = min(consistent, key=lambda k: sel_scores[k]["rps"])
        constraint = ev.compare({"chosen": preds[choice][sel], "best": preds[best_any][sel]}, y[sel],
                                [("chosen", "best")])[0]
        test_scores = {k: ev.scores(p[tst], y[tst]) for k, p in preds.items()}
        res = {"selection_seasons": label(INPLAY_SEL), "test_seasons": label(TEST), "window_seasons": WINDOW,
               "selection_scores": sel_scores, "chosen": choice, "best_unconstrained": best_any,
               "constraint": "minute-0 forecast must equal the pre-match forecast (keeps the low-score correction)",
               "cost_of_constraint_selection": constraint, "test_scores": test_scores,
               "test_vs_prematch": ev.compare({"chosen": preds[choice][tst], "pre": preds["pre-match only"][tst]},
                                              y[tst], [("chosen", "pre")])[0],
               "test_vs_time_only": ev.compare({"chosen": preds[choice][tst], "time": preds["time profile"][tst]},
                                               y[tst], [("chosen", "time")])[0]}
        if track == "market":
            res["calibration_test"] = ev.calibration(preds[choice][tst], y[tst])
            res["calibration_error_test"] = ev.calibration_error(res["calibration_test"])
            # version 1 (market-implied inputs, no low-score correction) on the same test matches
            v1 = InPlayModel.load(os.path.join(OUT, "inplay_model.json"))
            t = rows[tst]
            res["v1_note"] = "v1 used market-implied goals as inputs; scored here with the market inputs it was built for"
            res["v1_test"] = ev.scores(np.array([v1.probs(l, m_, 45, int(h), int(a), period=1)
                                                 for l, m_, h, a in zip(t["mkt_lh_orig"], t["mkt_la_orig"], t["hthg"], t["htag"])])
                                       , y[tst]) if "mkt_lh_orig" in t else None
        out[track] = res
        log(f"  in-play {track}: chosen '{choice}' (selection RPS {sel_scores[choice]['rps']:.4f}); test RPS "
            f"{test_scores[choice]['rps']:.4f} vs pre-match {test_scores['pre-match only']['rps']:.4f}, hit "
            f"{test_scores[choice]['hit']:.3f}")
    return out


def final_inplay(wf_market: pd.DataFrame, choice: str, sb_block: dict) -> InPlayModel:
    d = with_inputs(wf_market)
    last = int(d["season"].max())
    tr = d[d["season"] >= last - WINDOW + 1]
    mdl = candidate_models(tr)[choice]
    mdl.red_own = round(sb_block["red_own"], 3)
    mdl.red_opp = round(sb_block["red_opp"], 3)
    return mdl


# --------------------------------------------------------------------------
# 4. season projections
# --------------------------------------------------------------------------

def season_run(m, cfg, drift, seasons, n_sims):
    rows = []
    for s in seasons:
        sm = m[m["season"] == s].sort_values(["date", "home"]).reset_index(drop=True)
        cut_date = sm.loc[CUT_MATCHES - 1, "date"]
        played = sm[sm["date"] <= cut_date]
        teams = season_teams(m, s)
        fit = fit_dixon_coles(m, cut_date + pd.Timedelta(days=1), cfg, current_teams=teams,
                              promoted=promoted_teams(m, s), current_season=s, laplace=False)
        sim = simulate_season(fit, played, teams, n_sims=n_sims, drift_sd=drift, parameter_uncertainty=False, seed=s)
        final = league_table(sm).set_index("team")
        now = compute_table(played, teams).set_index("team")
        for k, t in enumerate(sim.teams):
            pts, pos = sim.points[:, k], sim.positions[:, k]
            rows.append({"season": s, "team": t, "pts_at_cut": int(now.loc[t, "Pts"]), "pred_pts": pts.mean(),
                         "pred_sd": pts.std(), "p10": np.percentile(pts, 10), "p90": np.percentile(pts, 90),
                         "actual_pts": int(final.loc[t, "Pts"]), "actual_pos": int(final.loc[t, "Pos"]),
                         "p_title": (pos == 1).mean(), "p_top4": (pos <= 4).mean(), "p_releg": (pos >= 18).mean(),
                         "naive_pts": now.loc[t, "Pts"] / max(1, now.loc[t, "P"]) * 38})
    return pd.DataFrame(rows)


def season_metrics(df: pd.DataFrame) -> dict:
    err = df["actual_pts"] - df["pred_pts"]
    nerr = df["actual_pts"] - df["naive_pts"]
    out = {"teams": int(len(df)), "seasons": int(df["season"].nunique()),
           "points_MAE": float(err.abs().mean()), "points_RMSE": float(np.sqrt((err ** 2).mean())),
           "naive_points_MAE": float(nerr.abs().mean()),
           "mae_vs_naive": ev.paired_diff(err.abs().to_numpy(), nerr.abs().to_numpy()),
           "z_sd": float((err / df["pred_sd"]).std()),
           "coverage_80": float(((df["actual_pts"] >= df["p10"]) & (df["actual_pts"] <= df["p90"])).mean())}
    for evn, cond, base in (("title", df["actual_pos"] == 1, 1 / 20), ("top4", df["actual_pos"] <= 4, 4 / 20),
                            ("releg", df["actual_pos"] >= 18, 3 / 20)):
        p, yv = df[f"p_{evn}"].to_numpy(), cond.to_numpy(float)
        out[f"brier_{evn}"] = float(((p - yv) ** 2).mean())
        out[f"brier_{evn}_structural_base"] = float(((base - yv) ** 2).mean())
    return out


def season(m, cfg, quick, log) -> dict:
    n_sims = 1500 if quick else 4000
    sel_runs = {}
    for dsd in DRIFTS:
        t0 = time.time()
        sel_runs[dsd] = season_metrics(season_run(m, cfg, dsd, SELECTION, n_sims))
        log(f"  season selection drift={dsd}: MAE {sel_runs[dsd]['points_MAE']:.2f} coverage "
            f"{sel_runs[dsd]['coverage_80']:.3f} z_sd {sel_runs[dsd]['z_sd']:.3f} ({time.time() - t0:.0f}s)")
    chosen = min(DRIFTS, key=lambda d_: abs(sel_runs[d_]["coverage_80"] - 0.8) + abs(sel_runs[d_]["z_sd"] - 1) / 4)
    test_df = season_run(m, cfg, chosen, TEST, n_sims)
    test_df.to_csv(os.path.join(EVAL, "season_test_teams.csv"), index=False)
    test = season_metrics(test_df)
    log(f"  season test drift={chosen}: MAE {test['points_MAE']:.2f} (naive {test['naive_points_MAE']:.2f}), "
        f"coverage {test['coverage_80']:.3f}")
    return {"cut_after_matches": CUT_MATCHES, "selection_seasons": label(SELECTION), "test_seasons": label(TEST),
            "selection": {str(k): v for k, v in sel_runs.items()}, "chosen_drift_sd": chosen,
            "selection_rule": "coverage of the 80% points interval closest to 80% and spread (z sd) closest to 1",
            "test": test, "n_sims": n_sims}


# --------------------------------------------------------------------------

def main():
    global M
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer season simulations (for a smoke run)")
    a = ap.parse_args()
    for p in (EVAL, MODELS, REPORTS):
        os.makedirs(p, exist_ok=True)
    lines = []

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    t0 = time.time()
    M = load_snapshot()
    fp = data_fingerprint(M[M["season"] <= 2025])
    cfg = {"market": load_cfg("market"), "independent": load_cfg("independent")}
    log(f"data fingerprint (history to 2025/26): {fp}")

    wf = {k: wf_cached(M, k, c, WF_SEASONS, log) for k, c in cfg.items()}
    # keep the market-implied goals for the version-1 in-play comparison
    for k in wf:
        wf[k]["mkt_lh_orig"] = wf[k].get("mkt_lh")
        wf[k]["mkt_la_orig"] = wf[k].get("mkt_la")

    log("1. pre-match")
    pre = prematch(wf, log)
    log("2. ablations (selection seasons)")
    abl, _ = ablations(M, cfg["independent"], cfg["market"], log)
    rest = rest_days(M, wf["market"], log)
    log("3. in-play")
    ip = inplay(wf, log)
    sb = statsbomb_checks(load_statsbomb_extract(SB_EXTRACT),
                          first_half_share(with_inputs(wf["market"])))
    live = final_inplay(wf["market"], ip["market"]["chosen"], sb)
    log(f"  final live model: {ip['market']['chosen']}; first-half share {live.first_half_share:.4f}; red cards "
        f"own x{live.red_own} opponent x{live.red_opp}")
    log("4. season")
    sea = season(M, cfg["market"], a.quick, log)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    registry = {
        "created_utc": now, "data_fingerprint": fp, "platform_version": VERSION,
        "prematch_market": {"version": f"prematch-market-{VERSION}", "config": asdict(cfg["market"]),
                            "selection_seasons": label(SELECTION), "test_seasons": label(TEST)},
        "prematch_independent": {"version": f"prematch-independent-{VERSION}", "config": asdict(cfg["independent"]),
                                 "selection_seasons": label(SELECTION), "test_seasons": label(TEST)},
        "inplay": {"version": live.version, "variant": ip["market"]["chosen"], "inputs": "market track lambda, mu, rho",
                   "trained_seasons": f"{int(wf['market']['season'].max()) - WINDOW + 1}-{int(wf['market']['season'].max())}"},
        "season": {"version": f"season-{VERSION}", "drift_sd": sea["chosen_drift_sd"], "cut_after_matches": CUT_MATCHES},
        "displayed_track": "market",
    }
    with open(os.path.join(MODELS, "inplay.json"), "w") as f:
        json.dump(live.to_json(), f, indent=2)
    with open(os.path.join(MODELS, "registry.json"), "w") as f:
        json.dump(registry, f, indent=2)
    report = {"generated_utc": now, "registry": registry, "explain": ev.EXPLAIN_AR, "prematch": pre,
              "ablations": abl, "rest_days": rest, "inplay": ip, "statsbomb": sb, "season": sea,
              "runtime_s": round(time.time() - t0)}
    with open(os.path.join(REPORTS, "evaluation.json"), "w") as f:
        json.dump(report, f, indent=1, default=float, ensure_ascii=False)
    with open(os.path.join(REPORTS, "evaluation_log.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    log(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
