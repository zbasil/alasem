"""In-play (live) match probabilities.

Given the pre-match expected goals of both teams (lambda, mu for 90 minutes),
the current minute, the score and red cards, the goals still to come are
modelled as two Poisson counts:

    home: lambda * remaining_share(minute) * k_home(state) * red effects
    away: mu     * remaining_share(minute) * k_away(state) * red effects

remaining_share(): goals are not spread evenly over a match. The scoring rate
    rises roughly linearly through the game; its slope is set so that the
    first half holds `first_half_share` of the goals (44.3% in La Liga,
    2000/01-2025/26, 23,500+ goals). Second-half stoppage time is part of the
    second half: a reported 90' still leaves the added minutes to play.
state: the current goal difference (home minus away, capped at +-2). Teams
    that lead tend to score less and concede more; the multipliers are fitted
    on 20 seasons of half-time -> full-time results (scripts/fit_inplay.py).
red cards: each extra player a team is down multiplies its own scoring rate
    by red_own and the opponent's by red_opp (fitted on StatsBomb event data,
    see scripts/fit_inplay.py).

One model from kick-off to the final whistle (version 2):
    * the score effects grow with the share of the match's goals already
      'seen' (info_weight: 0 at kick-off, 1 from half-time on), because the
      multipliers were measured at half-time and a 0-0 after one minute says
      nothing yet;
    * the Dixon-Coles low-score correction is applied to the goals still to
      come, with rho scaled by the share of the match still to play.
  So at minute 0 with no events the final-score distribution is exactly the
  pre-match Dixon-Coles matrix built from the same lambda, mu and rho
  (tests/test_inplay.py::test_minute_zero_equals_pre_match).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import numpy as np

from .dixon_coles import MAX_GOALS, score_matrix

VERSION = "inplay-2.0"


@dataclass
class InPlayModel:
    first_half_share: float = 0.443
    second_half_added: float = 5.0          # expected 2nd-half stoppage minutes
    k_home: dict = field(default_factory=lambda: {d: 1.0 for d in range(-2, 3)})
    k_away: dict = field(default_factory=lambda: {d: 1.0 for d in range(-2, 3)})
    # how the state effect depends on pre-match strength: multiplier exp(b[d] * log(lambda/mu))
    b_home: dict = field(default_factory=lambda: {d: 0.0 for d in range(-2, 3)})
    b_away: dict = field(default_factory=lambda: {d: 0.0 for d in range(-2, 3)})
    red_own: float = 0.70
    red_opp: float = 1.30
    ramp: bool = True                       # score effects grow from 0 at kick-off to full at half-time
    rho_mode: str = "remaining"             # low-score correction on goals still to come: none | remaining | full
    version: str = VERSION

    # ---- time profile -------------------------------------------------
    @property
    def slope(self) -> float:
        """c in intensity(t) = 1 + c*t (t in effective minutes 0..90)."""
        s = self.first_half_share
        return (45 - 90 * s) / (4050 * s - 1012.5)

    def _cum(self, t_eff: float) -> float:
        c = self.slope
        t = min(max(t_eff, 0.0), 90.0)
        return (t + c * t * t / 2) / (90 + c * 4050)

    def effective_minute(self, minute: float, period: int | None = None) -> float:
        """Map a reported match minute to 0..90 effective minutes.

        First half: 0..45 (first-half stoppage counts as 45).
        Second half: 45 + (minute - 45) * 45 / (45 + added), so that 90+added -> 90.
        """
        if period is None:
            period = 1 if minute <= 45 else 2
        if period == 1:
            return min(minute, 45.0)
        a = self.second_half_added
        return 45 + max(0.0, min(minute, 90 + a) - 45) * 45 / (45 + a)

    def remaining_share(self, minute: float, period: int | None = None) -> float:
        return 1.0 - self._cum(self.effective_minute(minute, period))

    def info_weight(self, minute: float, period: int | None = None) -> float:
        """How much of the half-time score effect applies now: share of first-half goals already
        played (0 at kick-off, 1 from half-time on). 1 always when ramp is off."""
        if not self.ramp:
            return 1.0
        return min(1.0, self._cum(self.effective_minute(minute, period)) / self._cum(45.0))

    def rho_remaining(self, rho, minute: float, period: int | None = None) -> float:
        """Low-score correction for the goals still to come."""
        if rho is None or self.rho_mode == "none":
            return 0.0
        if self.rho_mode == "full":
            return float(rho)
        return float(rho) * self.remaining_share(minute, period)

    # ---- rates ----------------------------------------------------------
    def remaining_rates(self, lam, mu, minute, hg, ag, red_home=0, red_away=0, period=None):
        r = self.remaining_share(minute, period)
        w = self.info_weight(minute, period)
        d = int(np.clip(hg - ag, -2, 2))
        z = float(np.log(max(lam, 1e-9) / max(mu, 1e-9)))
        man_diff = red_home - red_away           # >0: home is down players
        rl = lam * r * (self.k_home[d] * np.exp(self.b_home[d] * z)) ** w
        rm = mu * r * (self.k_away[d] * np.exp(self.b_away[d] * z)) ** w
        if man_diff > 0:
            rl *= self.red_own ** man_diff
            rm *= self.red_opp ** man_diff
        elif man_diff < 0:
            rl *= self.red_opp ** (-man_diff)
            rm *= self.red_own ** (-man_diff)
        return rl, rm

    def final_score_matrix(self, lam, mu, minute, hg, ag, red_home=0, red_away=0, period=None, rho=None):
        """P(final home goals = i, final away goals = j); shape (G+1, G+1), offset by the current score.

        rho: the Dixon-Coles correlation of the pre-match model (None = no low-score correction)."""
        rl, rm = self.remaining_rates(lam, mu, minute, hg, ag, red_home, red_away, period)
        add = score_matrix(rl, rm, self.rho_remaining(rho, minute, period), max_goals=MAX_GOALS)[0]
        G = MAX_GOALS + max(hg, ag) + 1
        out = np.zeros((G, G))
        out[hg:hg + MAX_GOALS + 1, ag:ag + MAX_GOALS + 1] = add
        return out

    def probs(self, lam, mu, minute, hg, ag, red_home=0, red_away=0, period=None, rho=None):
        """(P home win, P draw, P away win) at full time."""
        m = self.final_score_matrix(lam, mu, minute, hg, ag, red_home, red_away, period, rho)
        return (float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum()))

    def most_likely_final(self, lam, mu, minute, hg, ag, red_home=0, red_away=0, period=None, rho=None):
        m = self.final_score_matrix(lam, mu, minute, hg, ag, red_home, red_away, period, rho)
        i, j = np.unravel_index(m.argmax(), m.shape)
        return int(i), int(j), float(m[i, j])

    def top_scores(self, lam, mu, minute, hg, ag, red_home=0, red_away=0, period=None, rho=None, k=3):
        """The k most likely final scores [(home, away, probability), ...]."""
        m = self.final_score_matrix(lam, mu, minute, hg, ag, red_home, red_away, period, rho)
        flat = np.argsort(m.ravel())[::-1][:k]
        return [(int(f // m.shape[1]), int(f % m.shape[1]), float(m.ravel()[f])) for f in flat]

    # ---- timeline -----------------------------------------------------
    def timeline(self, lam, mu, events, end_minute=95, rho=None):
        """Win probability minute by minute.

        events: list of dicts {minute, team ('home'|'away'), kind ('goal'|'red')},
        applied at the end of their minute. Row 0 is the pre-match prediction.
        """
        evs = sorted(events, key=lambda e: e["minute"])
        rows = []
        hg = ag = rh = ra = 0
        i = 0
        for t in range(0, int(end_minute) + 1):
            while i < len(evs) and evs[i]["minute"] < t:
                e = evs[i]
                if e["kind"] == "goal":
                    hg += e["team"] == "home"
                    ag += e["team"] == "away"
                elif e["kind"] == "red":
                    rh += e["team"] == "home"
                    ra += e["team"] == "away"
                i += 1
            ph, pd, pa = self.probs(lam, mu, t, hg, ag, rh, ra, period=1 if t <= 45 else 2, rho=rho)
            rows.append({"minute": t, "hg": hg, "ag": ag, "p_home": ph, "p_draw": pd, "p_away": pa})
        return rows

    # ---- io -------------------------------------------------------------
    def to_json(self) -> dict:
        d = asdict(self)
        for key in ("k_home", "k_away", "b_home", "b_away"):
            d[key] = {str(k): v for k, v in getattr(self, key).items()}
        return d

    @classmethod
    def from_json(cls, d: dict) -> "InPlayModel":
        d = dict(d)
        # files written before version 2 had no ramp / low-score correction
        d.setdefault("ramp", False)
        d.setdefault("rho_mode", "none")
        d.setdefault("version", "inplay-1.0")
        for key in ("k_home", "k_away", "b_home", "b_away"):
            if key in d:
                d[key] = {int(k): float(v) for k, v in d[key].items()}
        return cls(**d)

    @classmethod
    def load(cls, path: str) -> "InPlayModel":
        with open(path) as f:
            return cls.from_json(json.load(f))


# ---------------------------------------------------------------------------
# fitting helpers (half-time -> full-time)
# ---------------------------------------------------------------------------

def fit_state_multipliers(df, first_half_share: float):
    """Ratio estimates of the second-half scoring multipliers by half-time goal difference.

    df needs mkt_lh, mkt_la (pre-match expected goals), hthg, htag, hg, ag.
    """
    d = (df["hthg"] - df["htag"]).clip(-2, 2).astype(int)
    exp_h = df["mkt_lh"] * (1 - first_half_share)
    exp_a = df["mkt_la"] * (1 - first_half_share)
    act_h = df["hg"] - df["hthg"]
    act_a = df["ag"] - df["htag"]
    kh, ka, n = {}, {}, {}
    for s in range(-2, 3):
        sel = d == s
        kh[s] = float(act_h[sel].sum() / exp_h[sel].sum())
        ka[s] = float(act_a[sel].sum() / exp_a[sel].sum())
        n[s] = int(sel.sum())
    return kh, ka, n


def fit_state_strength(df, first_half_share: float, ridge: float = 2.0):
    """Poisson fit of second-half goals with a state x strength interaction.

    home 2H goals ~ Poisson(lambda (1-s) exp(a_h[d] + b_h[d] z)), z = log(lambda/mu),
    away 2H goals ~ Poisson(mu (1-s) exp(a_a[d] + b_a[d] z)), d = HT goal difference (home-away, +-2).
    A small ridge penalty keeps thinly populated states close to 'no effect'.
    """
    from scipy.optimize import minimize
    d = (df["hthg"] - df["htag"]).clip(-2, 2).astype(int).values + 2
    z = np.log(df["mkt_lh"].values / df["mkt_la"].values)
    out = {}
    for side, lamcol, act in (("home", "mkt_lh", df["hg"] - df["hthg"]), ("away", "mkt_la", df["ag"] - df["htag"])):
        E = df[lamcol].values * (1 - first_half_share)
        y = act.values.astype(float)

        def nll(th):
            a, b = th[:5], th[5:]
            eta = a[d] + b[d] * z
            mu_ = E * np.exp(eta)
            f = float((mu_ - y * eta).sum()) + ridge * float((a ** 2).sum() + (b ** 2).sum())
            g_eta = mu_ - y
            ga = np.bincount(d, g_eta, 5) + 2 * ridge * a
            gb = np.bincount(d, g_eta * z, 5) + 2 * ridge * b
            return f, np.concatenate([ga, gb])

        res = minimize(nll, np.zeros(10), jac=True, method="L-BFGS-B")
        out[side] = ({k - 2: float(np.exp(res.x[k])) for k in range(5)},
                     {k - 2: float(res.x[5 + k]) for k in range(5)})
    return out
