"""League tables and the official La Liga tie-breaking rules.

Teams level on points are separated as follows (RFEF / LaLiga rules):

  If every tied team has played every other tied team twice:
    * 2 teams      -> head-to-head goal difference (no away-goals rule)
    * 3+ teams     -> head-to-head points, then head-to-head goal difference,
                      using only the matches between the tied teams.
                      Teams still tied are re-ranked from the start among
                      themselves.
  Otherwise, or if still tied:
    * overall goal difference, then overall goals scored
    * then Fair Play, then a play-off match. Neither can be predicted, so the
      simulator breaks such ties at random and the table display by name.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_table(matches: pd.DataFrame, teams: list[str] | None = None) -> pd.DataFrame:
    """Points table (unordered) with P W D L GF GA GD Pts."""
    if teams is None:
        teams = sorted(set(matches["home"]) | set(matches["away"]))
    t = pd.DataFrame(0, index=teams, columns=["P", "W", "D", "L", "GF", "GA"])
    for h, a, x, y in zip(matches["home"], matches["away"], matches["hg"], matches["ag"]):
        t.loc[h, ["P", "GF", "GA"]] += [1, x, y]
        t.loc[a, ["P", "GF", "GA"]] += [1, y, x]
        if x > y:
            t.loc[h, "W"] += 1
            t.loc[a, "L"] += 1
        elif x < y:
            t.loc[a, "W"] += 1
            t.loc[h, "L"] += 1
        else:
            t.loc[h, "D"] += 1
            t.loc[a, "D"] += 1
    t["GD"] = t["GF"] - t["GA"]
    t["Pts"] = 3 * t["W"] + t["D"]
    return t.rename_axis("team").reset_index()


def h2h_matrices(matches: pd.DataFrame, teams: list[str]):
    """pts[i, j] = points i took from j, gf[i, j] = goals i scored v j,
    played[i, j] = meetings played."""
    idx = {t: k for k, t in enumerate(teams)}
    n = len(teams)
    pts = np.zeros((n, n), dtype=np.int64)
    gf = np.zeros((n, n), dtype=np.int64)
    played = np.zeros((n, n), dtype=np.int64)
    for h, a, x, y in zip(matches["home"], matches["away"], matches["hg"], matches["ag"]):
        i, j = idx[h], idx[a]
        gf[i, j] += x
        gf[j, i] += y
        played[i, j] += 1
        played[j, i] += 1
        if x > y:
            pts[i, j] += 3
        elif x < y:
            pts[j, i] += 3
        else:
            pts[i, j] += 1
            pts[j, i] += 1
    return pts, gf, played


def _split(group: list[int], values: np.ndarray) -> list[list[int]]:
    """Split a group into runs of equal value, best (highest) first."""
    order = sorted(group, key=lambda k: -values[k])
    parts, cur = [], [order[0]]
    for k in order[1:]:
        if values[k] == values[cur[-1]]:
            cur.append(k)
        else:
            parts.append(cur)
            cur = [k]
    parts.append(cur)
    return parts


class _Resolver:
    def __init__(self, gd, gf, h2h_pts, h2h_gf, h2h_played, final_key):
        self.gd, self.gf = gd, gf
        self.h2h_pts, self.h2h_gf, self.h2h_played = h2h_pts, h2h_gf, h2h_played
        self.final_key = final_key          # array: last resort ordering value

    def h2h_complete(self, g):
        sub = self.h2h_played[np.ix_(g, g)]
        off = ~np.eye(len(g), dtype=bool)
        return bool((sub[off] >= 2).all())

    def resolve(self, g: list[int]) -> list[int]:
        if len(g) == 1:
            return list(g)
        if self.h2h_complete(g):
            n = len(self.gd)
            if len(g) == 2:
                i, j = g
                d = self.h2h_gf[i, j] - self.h2h_gf[j, i]
                if d != 0:
                    return [i, j] if d > 0 else [j, i]
            else:
                ix = np.ix_(g, g)
                mini_pts = np.zeros(n)
                mini_gd = np.zeros(n)
                mini_pts[g] = self.h2h_pts[ix].sum(axis=1)
                mini_gd[g] = self.h2h_gf[ix].sum(axis=1) - self.h2h_gf[ix].sum(axis=0)
                for vals in (mini_pts, mini_gd):
                    parts = _split(g, vals)
                    if len(parts) > 1:
                        out = []
                        for p in parts:           # still-tied teams start again
                            out.extend(self.resolve(p))
                        return out
        return self.overall(g)

    def overall(self, g: list[int]) -> list[int]:
        for vals in (self.gd, self.gf, self.final_key):
            parts = _split(g, vals)
            if len(parts) > 1:
                out = []
                for p in parts:
                    out.extend(self.overall(p) if len(p) > 1 else p)
                return out
        return list(g)       # identical on every key (cannot happen with a strict final key)


def rank_order(pts, gd, gf, h2h_pts, h2h_gf, h2h_played, final_key) -> list[int]:
    """Indices of teams from 1st to last.

    final_key must be strictly ordered (e.g. random numbers, or a reversed
    alphabetical rank) - it stands in for Fair Play.
    """
    pts = np.asarray(pts)
    res = _Resolver(np.asarray(gd), np.asarray(gf), h2h_pts, h2h_gf, h2h_played, np.asarray(final_key))
    order = []
    for grp in _split(list(range(len(pts))), pts):
        order.extend(res.resolve(grp))
    return order


def league_table(matches: pd.DataFrame, teams: list[str] | None = None) -> pd.DataFrame:
    """Ordered table using the official rules (ties beyond goals: by name)."""
    t = compute_table(matches, teams)
    teams = t["team"].tolist()
    hp, hg, hpl = h2h_matrices(matches, teams)
    # alphabetical final key: earlier name = higher value
    name_rank = np.argsort(np.argsort(teams))
    final_key = -name_rank.astype(float)
    order = rank_order(t["Pts"].values, t["GD"].values, t["GF"].values, hp, hg, hpl, final_key)
    out = t.iloc[order].reset_index(drop=True)
    out.insert(0, "Pos", np.arange(1, len(out) + 1))
    return out
