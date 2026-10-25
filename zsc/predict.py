"""Pre-match predictions for the current season, with explanations and logging.

Two tracks are fitted on the same data version:
    independent  Dixon-Coles on goals and shots on target only (no market input anywhere)
    market       the same model whose training targets also use market-implied goals of past
                 matches (it never needs odds for the match being predicted)
The displayed track is set in config/settings.json ("model.displayed_track").

Each prediction carries: the three outcome probabilities, both teams' expected goals, the three most
likely exact scores, the model inputs behind them (ratings, home advantage, rho) so a later version
can say exactly what changed, and the data and model versions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import numpy as np
import pandas as pd

from . import config
from .dixon_coles import DCConfig, FittedDC, fit_dixon_coles, outcome_probs, score_matrix
from .paths import REGISTRY
from .pipeline import promoted_teams, season_teams

TRACKS = ("market", "independent")
TRACK_AR = {"market": "مدعوم بالسوق", "independent": "مستقل (بدون السوق)", "sportradar": "SportRadar",
            "live": "مباشر", "scenario": "سيناريو"}


def registry() -> dict:
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def track_config(track: str) -> DCConfig:
    return DCConfig(**registry()[f"prematch_{track}"]["config"])


def model_version(track: str) -> str:
    return registry()[f"prematch_{track}"]["version"]


def config_hash(cfg: DCConfig) -> str:
    return hashlib.sha1(json.dumps(asdict(cfg), sort_keys=True).encode()).hexdigest()[:10]


def fit_track(m: pd.DataFrame, track: str, ref_date, season: int | None = None) -> FittedDC:
    """Fit one track on every match played strictly before ref_date (a calendar day)."""
    season = season or config.season()
    cfg = track_config(track)
    teams = season_teams(m, season)
    return fit_dixon_coles(m, pd.Timestamp(ref_date), cfg, current_teams=teams,
                           promoted=promoted_teams(m, season), current_season=season)


def team_factors(fit: FittedDC) -> pd.DataFrame:
    """Attack / defence of every team as multipliers of the league average (after rating_scale).
    attack 1.30 = scores 30% more than an average team would against the same opponent;
    defence 0.80 = concedes 20% less than average."""
    att, dfn = fit.scaled()
    ca, cd = fit.center_a, fit.center_d
    return pd.DataFrame({"team": fit.teams, "attack": np.exp(att - ca), "defence": np.exp(-(dfn - cd))})


def predict_matches(fit: FittedDC, fixtures: pd.DataFrame, k_scores: int = 3) -> pd.DataFrame:
    """fixtures: home, away (+ any columns to keep). Adds xg, probabilities, top scores, inputs."""
    if not len(fixtures):
        return fixtures.assign(p_home=[], p_draw=[], p_away=[])
    lam, mu = fit.rates(fixtures["home"], fixtures["away"])
    mats = score_matrix(lam, mu, fit.rho)
    p = outcome_probs(mats)
    G = mats.shape[1]
    out = fixtures.copy().reset_index(drop=True)
    out["xg_home"], out["xg_away"], out["rho"] = lam, mu, fit.rho
    out["p_home"], out["p_draw"], out["p_away"] = p[:, 0], p[:, 1], p[:, 2]
    flat = mats.reshape(len(out), -1)
    order = np.argsort(-flat, axis=1)[:, :k_scores]
    for k in range(k_scores):
        idx = order[:, k]
        out[f"score{k + 1}"] = [f"{i // G}-{i % G}" for i in idx]
        out[f"p_score{k + 1}"] = flat[np.arange(len(out)), idx]
    tf = team_factors(fit).set_index("team")
    att, dfn = fit.scaled()
    ix = fit.index
    out["inputs"] = [json.dumps({
        "c": round(float(fit.c), 5), "h": round(float(fit.h), 5), "rho": round(float(fit.rho), 5),
        "scale": fit.scale, "att_home": round(float(att[ix[h]]), 5), "def_home": round(float(dfn[ix[h]]), 5),
        "att_away": round(float(att[ix[a]]), 5), "def_away": round(float(dfn[ix[a]]), 5),
        "attack_home_x": round(float(tf.loc[h, "attack"]), 4), "defence_home_x": round(float(tf.loc[h, "defence"]), 4),
        "attack_away_x": round(float(tf.loc[a, "attack"]), 4), "defence_away_x": round(float(tf.loc[a, "defence"]), 4),
        "home_adv_x": round(float(np.exp(fit.h)), 4), "n_matches": fit.info.get("n_matches"),
    }) for h, a in zip(out["home"], out["away"])]
    return out


def explain(row: dict, names: dict) -> list[dict]:
    """Numeric reasons behind a prediction, straight from the model's inputs (largest effect first).

    Each reason: {key, text_ar, effect} where effect is the change in log expected goals it causes."""
    inp = json.loads(row["inputs"]) if isinstance(row["inputs"], str) else row["inputs"]
    h_ar, a_ar = names[row["home"]], names[row["away"]]
    rs = []

    def pct(x):
        return f"{100 * (x - 1):+.0f}٪"

    ah, dh, aa, da = inp["attack_home_x"], inp["defence_home_x"], inp["attack_away_x"], inp["defence_away_x"]
    rs.append({"key": "attack_home", "effect": float(np.log(ah)),
               "text_ar": f"هجوم {h_ar} {'أقوى' if ah >= 1 else 'أضعف'} من معدل الدوري ({pct(ah)} أهداف)"})
    rs.append({"key": "attack_away", "effect": -float(np.log(aa)),
               "text_ar": f"هجوم {a_ar} {'أقوى' if aa >= 1 else 'أضعف'} من معدل الدوري ({pct(aa)} أهداف)"})
    rs.append({"key": "defence_home", "effect": -float(np.log(dh)),
               "text_ar": f"دفاع {h_ar} {'يستقبل أقل' if dh <= 1 else 'يستقبل أكثر'} من المعدل ({pct(dh)} أهداف عليه)"})
    rs.append({"key": "defence_away", "effect": float(np.log(da)),
               "text_ar": f"دفاع {a_ar} {'يستقبل أقل' if da <= 1 else 'يستقبل أكثر'} من المعدل ({pct(da)} أهداف عليه)"})
    rs.append({"key": "home", "effect": float(np.log(inp["home_adv_x"])),
               "text_ar": f"ميزة الأرض (عامة بالدوري): ترفع أهداف {h_ar} المتوقعة {pct(inp['home_adv_x'])}"})
    for r in rs:
        r["size"] = abs(r["effect"])
        r["favours"] = "home" if r["effect"] > 0 else "away"
    rs.sort(key=lambda r: -r["size"])
    return rs


def favourite_line(row: dict, names: dict) -> str:
    p = {"home": row["p_home"], "draw": row["p_draw"], "away": row["p_away"]}
    best = max(p, key=p.get)
    if best == "draw":
        return f"المباراة متكافئة: التعادل الأرجح بنسبة {100 * p['draw']:.0f}٪"
    team = names[row[best]]
    team = team["ar"] if isinstance(team, dict) else team
    gap = 100 * (p[best] - max(v for k, v in p.items() if k != best))
    level = "مرشح واضح" if p[best] >= 0.6 else ("مرشح" if p[best] >= 0.45 else "أفضلية بسيطة")
    return f"{team} {level} بنسبة {100 * p[best]:.0f}٪ (بفارق {gap:.0f} نقطة عن الاحتمال الثاني)"
