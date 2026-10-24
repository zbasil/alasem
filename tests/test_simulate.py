"""Season simulation: probabilities are coherent and match the model."""

import numpy as np
import pandas as pd
import pytest

from zsc.data import remaining_fixtures
from zsc.dixon_coles import DCConfig, fit_dixon_coles
from zsc.pipeline import promoted_teams, season_teams
from zsc.simulate import simulate_season
from zsc.standings import league_table


@pytest.fixture(scope="module")
def current(snapshot):
    teams = season_teams(snapshot, 2026)
    played = snapshot[snapshot["season"] == 2026]
    fit = fit_dixon_coles(snapshot, "2026-10-23", DCConfig(), current_teams=teams,
                          promoted=promoted_teams(snapshot, 2026), current_season=2026)
    return teams, played, fit


def test_probabilities_are_coherent(current):
    teams, played, fit = current
    sim = simulate_season(fit, played, teams, n_sims=2000, n_param_draws=50, seed=1)
    s = sim.summary()
    pos_cols = [f"pos_{k}" for k in range(1, 21)]
    assert np.allclose(s[pos_cols].sum(axis=1), 1.0)            # each team ends somewhere
    assert np.allclose(s[pos_cols].sum(axis=0), 1.0)            # each place has one team
    assert np.isclose(s["p_title"].sum(), 1.0)
    assert np.isclose(s["p_releg"].sum(), 3.0)
    assert np.isclose(s["p_top4"].sum(), 4.0)
    # nobody can lose points already won
    assert (sim.points >= sim.base_table.set_index("team").loc[sim.teams, "Pts"].values).all()
    # every team plays 38 games: max possible points
    left = 38 - sim.base_table.set_index("team").loc[sim.teams, "P"].values
    assert (sim.points <= sim.base_table.set_index("team").loc[sim.teams, "Pts"].values + 3 * left).all()


def test_expected_points_equal_model_expectation(current):
    # E[final points] = points now + sum over remaining games of 3 P(win) + P(draw)
    teams, played, fit = current
    sim = simulate_season(fit, played, teams, n_sims=20000, n_param_draws=1,
                          parameter_uncertainty=False, seed=3)
    rem = remaining_fixtures(played, teams)
    p = fit.predict(rem["home"], rem["away"])
    exp = sim.base_table.set_index("team").loc[sim.teams, "Pts"].astype(float)
    for _, r in p.iterrows():
        exp[r["home"]] += 3 * r["p_home"] + r["p_draw"]
        exp[r["away"]] += 3 * r["p_away"] + r["p_draw"]
    mean = pd.Series(sim.points.mean(0), index=sim.teams)
    se = pd.Series(sim.points.std(0) / np.sqrt(sim.points.shape[0]), index=sim.teams)
    assert ((mean - exp[sim.teams]).abs() < 4 * se + 1e-9).all()


def test_completed_season_reproduces_the_real_table(snapshot, history):
    # With no games left the simulator must return the real final table every time
    played = history[history["season"] == 2025]
    teams = sorted(set(played["home"]))
    fit = fit_dixon_coles(snapshot, "2026-06-01", DCConfig(), current_teams=teams, current_season=2025)
    sim = simulate_season(fit, played, teams, n_sims=50, n_param_draws=5, seed=0)
    real = league_table(played).set_index("team")["Pos"]
    for k, t in enumerate(sim.teams):
        assert (sim.positions[:, k] == real[t]).all(), t


def test_remaining_fixture_list(snapshot):
    played = snapshot[snapshot["season"] == 2026]
    teams = season_teams(snapshot, 2026)
    rem = remaining_fixtures(played, teams)
    assert len(played) >= 89 and len(played) + len(rem) == 380
    assert not set(zip(rem["home"], rem["away"])) & set(zip(played["home"], played["away"]))
    assert ("Vallecano", "Ath Bilbao") in set(zip(rem["home"], rem["away"]))   # abandoned 10 Oct


def test_market_overrides_are_used_for_those_fixtures(current):
    teams, played, fit = current
    # pretend the market makes Malaga overwhelming favourites at home to Barcelona
    ov = pd.DataFrame({"home": ["Malaga"], "away": ["Barcelona"], "mkt_lh": [25.0], "mkt_la": [0.01]})
    base = simulate_season(fit, played, teams, n_sims=1000, n_param_draws=20, seed=5)
    forced = simulate_season(fit, played, teams, n_sims=1000, n_param_draws=20, overrides=ov, seed=5)
    k_mal, k_bar = forced.teams.index("Malaga"), forced.teams.index("Barcelona")
    # Malaga now always takes those 3 points, so its average rises by about 3 minus what it got before
    gain = forced.points[:, k_mal].mean() - base.points[:, k_mal].mean()
    p_before = fit.predict(["Malaga"], ["Barcelona"]).iloc[0]
    expected_gain = 3 - (3 * p_before["p_home"] + p_before["p_draw"])
    assert abs(gain - expected_gain) < 0.25
    assert forced.points[:, k_bar].mean() < base.points[:, k_bar].mean()


def test_rating_scale_stretches_differences(snapshot):
    teams = season_teams(snapshot, 2026)
    a = fit_dixon_coles(snapshot, "2026-10-23", DCConfig(rating_scale=1.0), current_teams=teams,
                        current_season=2026, laplace=False)
    b = fit_dixon_coles(snapshot, "2026-10-23", DCConfig(rating_scale=1.2), current_teams=teams,
                        current_season=2026, laplace=False)
    la, ma = a.rates(["Barcelona"], ["Malaga"])
    lb, mb = b.rates(["Barcelona"], ["Malaga"])
    assert lb[0] > la[0] and mb[0] < ma[0]            # favourite stronger, underdog weaker
    # stretching is around the current-team mean, so the average team is unchanged
    att_a, _ = a.scaled()
    att_b, _ = b.scaled()
    idx = a.index
    ti = [idx[t] for t in teams]
    assert np.isclose(att_a[ti].mean(), att_b[ti].mean())
