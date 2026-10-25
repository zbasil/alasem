"""Data integrity: complete seasons, two independent sources agree."""

import numpy as np

from zsc.data import validate_season
from zsc.pipeline import promoted_teams, season_teams
from zsc.paths import RAW_BETEXPLORER, RAW_ODDS  # noqa: E402


def test_every_historical_season_is_a_complete_double_round_robin(snapshot):
    for s in range(2000, 2026):
        df = snapshot[snapshot["season"] == s]
        assert validate_season(df, n_teams=20, complete=True) == [], s


def test_odds_and_shots_cover_the_tuning_and_test_seasons(snapshot):
    recent = snapshot[(snapshot["season"] >= 2012) & (snapshot["season"] <= 2025)]
    assert recent["odds_h"].notna().all()
    assert recent["mkt_lh"].notna().all()
    assert recent["hst"].notna().all()


def test_market_expected_goals_are_sane(snapshot):
    ok = snapshot["mkt_lh"].notna()
    assert np.isclose(snapshot.loc[ok, "mkt_lh"].mean(), snapshot.loc[ok, "hg"].mean(), atol=0.05)
    assert np.isclose(snapshot.loc[ok, "mkt_la"].mean(), snapshot.loc[ok, "ag"].mean(), atol=0.05)
    assert np.nanmedian(snapshot["mkt_err"]) < 0.01


def test_current_season_teams(snapshot):
    teams = season_teams(snapshot, 2026)
    assert len(teams) == 20
    assert promoted_teams(snapshot, 2026) == {"La Coruna", "Malaga", "Santander"}
    assert validate_season(snapshot[snapshot["season"] == 2026], n_teams=20) == []


def test_two_independent_sources_agree_on_every_score(history):
    import os
    import pandas as pd
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    odds = pd.read_csv(RAW_ODDS, parse_dates=["date"])
    h = history[history["season"] >= 2000]
    mg = h.merge(odds, on=["date", "home", "away"], how="inner", suffixes=("", "_o"))
    assert len(mg) >= 9000
    assert ((mg["hg"] == mg["hg_o"]) & (mg["ag"] == mg["ag_o"])).all()


def test_current_results_match_a_third_independent_list(snapshot):
    """betexplorer.com's results list (read 23 Oct 2026) agrees on all 89 scores."""
    import os
    import pandas as pd
    from zsc.teams import canonical
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    b = pd.read_csv(RAW_BETEXPLORER)
    names = {"Atl. Madrid": "Ath Madrid", "Dep. A Coruna": "La Coruna", "Real Sociedad": "Sociedad"}
    b["home"] = b["home"].map(lambda t: names.get(t, canonical(t)))
    b["away"] = b["away"].map(lambda t: names.get(t, canonical(t)))
    abandoned = b[b["score"].str.contains("ABN")]
    assert abandoned[["home", "away"]].values.tolist() == [["Vallecano", "Ath Bilbao"]]
    b = b[~b["score"].str.contains("ABN")]
    got = {(h, a): s for h, a, s in zip(b["home"], b["away"], b["score"])}
    cur = snapshot[(snapshot["season"] == 2026) & (snapshot["date"] <= "2026-10-21")]
    mine = {(h, a): f"{x}:{y}" for h, a, x, y in zip(cur["home"], cur["away"], cur["hg"], cur["ag"])}
    assert got == mine
