"""Scoring rules for probability forecasts (lower is better for all three)."""

from __future__ import annotations

import numpy as np


def outcome_index(hg, ag) -> np.ndarray:
    """0 = home win, 1 = draw, 2 = away win."""
    hg, ag = np.asarray(hg), np.asarray(ag)
    return np.where(hg > ag, 0, np.where(hg == ag, 1, 2))


def rps(probs: np.ndarray, outcome: np.ndarray) -> np.ndarray:
    """Ranked probability score per match (ordered outcomes H < D < A)."""
    probs = np.asarray(probs, float)
    obs = np.zeros_like(probs)
    obs[np.arange(len(outcome)), outcome] = 1.0
    cp = np.cumsum(probs, axis=1)[:, :2]
    co = np.cumsum(obs, axis=1)[:, :2]
    return ((cp - co) ** 2).sum(axis=1) / 2.0


def log_loss(probs: np.ndarray, outcome: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(probs, float)[np.arange(len(outcome)), outcome], 1e-12, 1.0)
    return -np.log(p)


def brier(probs: np.ndarray, outcome: np.ndarray) -> np.ndarray:
    probs = np.asarray(probs, float)
    obs = np.zeros_like(probs)
    obs[np.arange(len(outcome)), outcome] = 1.0
    return ((probs - obs) ** 2).sum(axis=1)


def calibration_table(probs: np.ndarray, outcome: np.ndarray, bins=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001)):
    """Rows: (bin low, bin high, n, mean forecast, observed frequency) over all 3 outcomes."""
    probs = np.asarray(probs, float)
    obs = np.zeros_like(probs)
    obs[np.arange(len(outcome)), outcome] = 1.0
    p, o = probs.ravel(), obs.ravel()
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum():
            rows.append((lo, min(hi, 1.0), int(m.sum()), float(p[m].mean()), float(o[m].mean())))
    return rows
