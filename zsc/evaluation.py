"""Scientific evaluation helpers.

Every number reported by the app comes from here: proper scoring rules,
paired bootstrap intervals for differences between models, calibration
tables and breakdowns. All functions work on plain arrays so the same code
scores pre-match, half-time and season forecasts.

Scores (lower is better except the hit rate):
    RPS        ranked probability score: distance between the forecast and the
               result on the ordered scale home win < draw < away win
    log loss   -log(probability given to what happened); punishes confident misses
    Brier      squared error of the three probabilities
    hit rate   share of matches where the most likely outcome happened
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluate import brier, log_loss, outcome_index, rps

EXPLAIN_AR = {
    "rps": "خطأ الاحتمالات المرتبة (RPS): يقيس بُعد التوقع عن النتيجة على سلّم فوز ← تعادل ← خسارة. كل ما أقل أحسن.",
    "logloss": "Log loss: يعاقب الثقة الزايدة بالتوقع الغلط. كل ما أقل أحسن.",
    "brier": "Brier: مربع الفرق بين الاحتمالات الثلاثة والنتيجة. كل ما أقل أحسن.",
    "hit": "نسبة الاختيار الصحيح: كم مرة صارت النتيجة الأرجح (فوز/تعادل/خسارة) فعلاً.",
    "exact_hit": "إصابة النتيجة الرقمية: كم مرة صارت النتيجة الأرجح بالأرقام (مثل 2-1) فعلاً.",
    "exact_logloss": "Log loss للنتيجة الرقمية: يقيس الاحتمال اللي انعطى للنتيجة الرقمية اللي صارت.",
}


def probs_matrix(df: pd.DataFrame, cols=("p_home", "p_draw", "p_away")) -> np.ndarray:
    return df[list(cols)].to_numpy(dtype=float)


def scores(p: np.ndarray, y: np.ndarray) -> dict:
    """Mean scores of a set of 1X2 forecasts."""
    p = np.asarray(p, float)
    return {"n": int(len(y)), "rps": float(rps(p, y).mean()), "logloss": float(log_loss(p, y).mean()),
            "brier": float(brier(p, y).mean()), "hit": float((p.argmax(1) == y).mean())}


def per_match(p: np.ndarray, y: np.ndarray) -> dict:
    return {"rps": rps(p, y), "logloss": log_loss(p, y), "brier": brier(p, y),
            "hit": (np.asarray(p).argmax(1) == y).astype(float)}


def paired_diff(a: np.ndarray, b: np.ndarray, n_boot: int = 2000, seed: int = 0) -> dict:
    """Mean of a - b with a 95% bootstrap interval (matches resampled in pairs)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    bs = d[idx].mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"diff": float(d.mean()), "ci_low": float(lo), "ci_high": float(hi), "n": int(len(d)),
            "clear": bool(lo > 0 or hi < 0)}


def compare(models: dict[str, np.ndarray], y: np.ndarray, pairs: list[tuple[str, str]],
            metrics=("rps", "logloss", "brier", "hit"), seed: int = 0) -> list[dict]:
    """Paired comparisons on the same matches."""
    pm = {k: per_match(v, y) for k, v in models.items()}
    out = []
    for a, b in pairs:
        row = {"a": a, "b": b}
        for m in metrics:
            row[m] = paired_diff(pm[a][m], pm[b][m], seed=seed)
        out.append(row)
    return out


def calibration(p: np.ndarray, y: np.ndarray, edges=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001),
                outcome: int | None = None) -> list[dict]:
    """Reliability table: forecasts grouped by probability, with the observed frequency and a
    95% interval for it (Wilson). outcome=None pools home, draw and away."""
    p = np.asarray(p, float)
    obs = np.zeros_like(p)
    obs[np.arange(len(y)), y] = 1.0
    if outcome is None:
        f, o = p.ravel(), obs.ravel()
    else:
        f, o = p[:, outcome], obs[:, outcome]
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (f >= lo) & (f < hi)
        n = int(m.sum())
        if not n:
            continue
        k = float(o[m].sum())
        ph = k / n
        z = 1.96
        den = 1 + z * z / n
        centre = (ph + z * z / (2 * n)) / den
        half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
        rows.append({"lo": float(lo), "hi": float(min(hi, 1.0)), "n": n, "forecast": float(f[m].mean()),
                     "observed": ph, "obs_low": float(centre - half), "obs_high": float(centre + half)})
    return rows


def calibration_error(rows: list[dict]) -> float:
    """Expected calibration error: sample-weighted |forecast - observed|."""
    n = sum(r["n"] for r in rows)
    return float(sum(r["n"] * abs(r["forecast"] - r["observed"]) for r in rows) / max(n, 1))


def exact_scores(df: pd.DataFrame) -> dict:
    """Exact-score forecasts: hit rate of the single most likely score and mean log score."""
    hit = ((df["likely_hg"] == df["hg"]) & (df["likely_ag"] == df["ag"])).astype(float)
    return {"n": int(len(df)), "exact_hit": float(hit.mean()),
            "exact_logloss": float(-np.log(np.clip(df["p_exact"].to_numpy(float), 1e-12, 1)).mean()),
            "mean_p_likely": float(df["p_likely"].mean())}


def favourite_band(p: np.ndarray) -> np.ndarray:
    m = np.asarray(p, float).max(1)
    return np.select([m < 0.45, m < 0.55, m < 0.65], ["<45%", "45-55%", "55-65%"], ">=65%")


def season_phase(df: pd.DataFrame) -> np.ndarray:
    """Matchday bucket from the order of matches within each season (10 matches per matchday)."""
    order = df.groupby("season")["date"].rank(method="first").to_numpy() - 1
    md = (order // 10 + 1).astype(int)
    return np.select([md <= 10, md <= 19, md <= 29], ["1-10", "11-19", "20-29"], "30-38")


def breakdown(df: pd.DataFrame, p_cols_by_model: dict[str, tuple], key: np.ndarray, name: str) -> list[dict]:
    """Scores of each model within each group of `key`."""
    y = outcome_index(df["hg"], df["ag"])
    rows = []
    for g in sorted(pd.unique(key)):
        m = key == g
        row = {"by": name, "group": str(g), "n": int(m.sum())}
        for model, cols in p_cols_by_model.items():
            s = scores(df.loc[m, list(cols)].to_numpy(float), y[m])
            row[f"{model}_rps"] = s["rps"]
            row[f"{model}_hit"] = s["hit"]
        rows.append(row)
    return rows


def team_breakdown(df: pd.DataFrame, cols: tuple, model: str) -> list[dict]:
    """Mean RPS of the matches each team played (home or away)."""
    y = outcome_index(df["hg"], df["ag"])
    r = rps(df[list(cols)].to_numpy(float), y)
    long = pd.concat([pd.DataFrame({"team": df["home"].values, "rps": r}),
                      pd.DataFrame({"team": df["away"].values, "rps": r})])
    g = long.groupby("team")["rps"].agg(["mean", "size"]).reset_index()
    return [{"team": t, "n": int(n), f"{model}_rps": float(v)} for t, v, n in zip(g["team"], g["mean"], g["size"])]
