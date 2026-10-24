"""In-play model: time profile, probabilities, events."""

import os

import numpy as np
import pytest

from zsc.inplay import InPlayModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def model():
    return InPlayModel.load(os.path.join(ROOT, "outputs", "inplay_model.json"))


def test_time_profile(model):
    s = model.first_half_share
    assert np.isclose(model.remaining_share(0), 1.0)
    assert np.isclose(model.remaining_share(45, period=1), 1 - s)
    assert np.isclose(model.remaining_share(45 + 3, period=1), 1 - s)        # first-half stoppage
    assert np.isclose(model.remaining_share(90 + model.second_half_added, period=2), 0.0)
    assert model.remaining_share(90, period=2) > 0                              # stoppage still to come
    r = [model.remaining_share(t, period=1 if t <= 45 else 2) for t in range(0, 96)]
    assert all(a >= b for a, b in zip(r, r[1:]))                                # never increases
    # later minutes hold more goals: the second half carries more than the first
    assert s < 0.5


def test_probabilities_sum_to_one(model):
    for args in [(1.6, 1.1, 0, 0, 0), (1.6, 1.1, 30, 1, 0), (2.4, 0.7, 60, 0, 2), (1.2, 1.2, 80, 2, 2)]:
        p = model.probs(*args)
        assert np.isclose(sum(p), 1.0)
        assert all(0 <= x <= 1 for x in p)


def test_full_time_is_decided(model):
    assert model.probs(1.5, 1.2, 95, 2, 1, period=2) == pytest.approx((1.0, 0.0, 0.0), abs=1e-9)
    assert model.probs(1.5, 1.2, 95, 1, 1, period=2) == pytest.approx((0.0, 1.0, 0.0), abs=1e-9)


def test_goals_and_red_cards_move_probabilities_the_right_way(model):
    base = model.probs(1.5, 1.2, 30, 0, 0)
    after_goal = model.probs(1.5, 1.2, 30, 1, 0)
    assert after_goal[0] > base[0] and after_goal[2] < base[2]
    red_home = model.probs(1.5, 1.2, 30, 0, 0, red_home=1)
    assert red_home[0] < base[0] and red_home[2] > base[2]
    later = model.probs(1.5, 1.2, 75, 1, 0)
    assert later[0] > after_goal[0]                       # the same lead is safer later


def test_timeline_applies_events(model):
    tl = model.timeline(1.5, 1.2, [{"minute": 20, "team": "home", "kind": "goal"},
                                   {"minute": 70, "team": "away", "kind": "red"}], end_minute=95)
    assert tl[0]["hg"] == 0 and tl[25]["hg"] == 1 and tl[25]["ag"] == 0
    assert tl[-1]["p_home"] == pytest.approx(1.0, abs=1e-9)          # 1-0 at full time
    assert tl[30]["p_home"] > tl[10]["p_home"]


def test_json_round_trip(model):
    again = InPlayModel.from_json(model.to_json())
    assert again.probs(1.4, 1.0, 50, 1, 1) == pytest.approx(model.probs(1.4, 1.0, 50, 1, 1))


# ---- one model from kick-off to the final whistle (version 2) -------------

from dataclasses import replace  # noqa: E402

from zsc.dixon_coles import outcome_probs, score_matrix  # noqa: E402


@pytest.fixture(scope="module")
def v2(model):
    return replace(model, ramp=True, rho_mode="remaining")


@pytest.mark.parametrize("lam,mu,rho", [(2.148, 0.713, -0.091), (2.469, 1.671, -0.091), (1.144, 1.256, -0.05), (0.9, 2.2, 0.02)])
def test_minute_zero_equals_pre_match(v2, lam, mu, rho):
    pre = score_matrix(lam, mu, rho)[0]
    live = v2.final_score_matrix(lam, mu, 0, 0, 0, rho=rho)
    g = pre.shape[0]
    assert np.allclose(live[:g, :g], pre, atol=1e-12)
    assert np.allclose(v2.probs(lam, mu, 0, 0, 0, rho=rho), outcome_probs(pre[None])[0], atol=1e-12)


def test_score_effects_start_at_zero_and_reach_half_time_values(v2):
    assert v2.info_weight(0) == 0.0
    assert v2.info_weight(45, period=1) == pytest.approx(1.0)
    assert v2.info_weight(60, period=2) == 1.0
    w = [v2.info_weight(t, period=1) for t in range(0, 46)]
    assert all(a <= b for a, b in zip(w, w[1:]))
    # from half-time on the version-2 rates equal the fitted half-time multipliers
    old = replace(v2, ramp=False)
    assert v2.remaining_rates(1.5, 1.1, 45, 1, 0, period=1) == pytest.approx(old.remaining_rates(1.5, 1.1, 45, 1, 0, period=1))


def test_pre_match_to_live_to_full_time(v2):
    lam, mu, rho = 1.7, 1.1, -0.08
    tl = v2.timeline(lam, mu, [{"minute": 30, "team": "home", "kind": "goal"}], end_minute=95, rho=rho)
    pre = outcome_probs(score_matrix(lam, mu, rho))[0]
    assert (tl[0]["p_home"], tl[0]["p_draw"], tl[0]["p_away"]) == pytest.approx(tuple(pre), abs=1e-12)
    for r in tl:
        assert r["p_home"] + r["p_draw"] + r["p_away"] == pytest.approx(1.0, abs=1e-9)
    # no event in the first minutes: the forecast moves only slowly with the clock
    assert abs(tl[1]["p_home"] - tl[0]["p_home"]) < 0.01
    assert tl[31]["p_home"] > tl[30]["p_home"] + 0.1          # the goal (applied at the end of minute 30)
    assert tl[-1]["p_home"] == pytest.approx(1.0, abs=1e-9)  # 1-0 at the final whistle


def test_low_score_correction_fades_out(v2):
    assert v2.rho_remaining(-0.1, 0) == pytest.approx(-0.1)
    assert v2.rho_remaining(-0.1, 95, period=2) == pytest.approx(0.0)
    assert replace(v2, rho_mode="none").rho_remaining(-0.1, 0) == 0.0


def test_version_two_round_trip(v2):
    again = InPlayModel.from_json(v2.to_json())
    assert again.ramp and again.rho_mode == "remaining"
    assert again.probs(1.4, 1.0, 20, 1, 0, rho=-0.07) == pytest.approx(v2.probs(1.4, 1.0, 20, 1, 0, rho=-0.07))
