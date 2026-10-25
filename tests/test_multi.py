"""Premier League and Champions League (version 3): data checks, model outputs, simulations, app files."""
import json
import os

import numpy as np
import pytest

from zsc import multi
from zsc.paths import ROOT

MULTI = os.path.join(ROOT, "outputs", "multi")
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(MULTI, "comps.json")),
                                reason="run `python -m zsc multi` first")


def load(rel):
    return json.load(open(os.path.join(MULTI, rel), encoding="utf-8"))


def test_comps_list():
    c = load("comps.json")["competitions"]
    assert [x["id"] for x in c] == ["ESP1", "ENG1", "UCL"]


def test_epl_files():
    fx = load("c/ENG1/fixtures.json")["fixtures"]
    assert len(fx) == 380 and len({f["match_id"] for f in fx}) == 380
    for f in fx:
        assert abs(sum(f["p"]) - 1) < 1e-4 and all(0 <= v <= 1 for v in f["p"])
    s = load("c/ENG1/season.json")
    assert s["checks"]["official_table_matches"]
    assert abs(sum(r["p_title"] for r in s["projection"]) - 1) < 1e-6
    assert abs(sum(r["p_releg"] for r in s["projection"]) - 3) < 1e-6
    played = [f for f in fx if f["status"] == "played"]
    assert len(played) == s["checks"]["played"]
    assert sum(r["P"] for r in s["table"]) == 2 * len(played)


def test_ucl_files():
    fx = load("c/UCL/fixtures.json")["fixtures"]
    assert len(fx) == 144
    teams = {}
    for f in fx:
        teams[f["home"]] = teams.get(f["home"], 0) + 1
        teams[f["away"]] = teams.get(f["away"], 0) + 1
    assert len(teams) == 36 and set(teams.values()) == {8}
    s = load("c/UCL/season.json")
    pr = s["projection"]
    assert abs(sum(r["p_win"] for r in pr) - 1) < 1e-6
    assert abs(sum(r["p_top8"] for r in pr) - 8) < 1e-6
    assert abs(sum(r["p_r16"] for r in pr) - 16) < 1e-6
    for r in pr:   # reaching a later round is never likelier than an earlier one
        assert r["p_r16"] + 1e-9 >= r["p_qf"] >= r["p_sf"] - 1e-9 >= r["p_final"] - 2e-9 >= r["p_win"] - 3e-9


def test_elo_goal_model_monotone():
    gm = {"a_home": 0.37, "b_home": 0.74, "a_away": 0.14, "b_away": 0.74}
    lam, mu = multi.elo_rates(gm, [1900, 1800, 1700], [1700, 1800, 1900])
    assert lam[0] > lam[1] > lam[2] and mu[0] < mu[1] < mu[2]
    ln, mn = multi.elo_rates(gm, 1800, 1800, neutral=True)
    assert np.isclose(ln, mn)


def test_table_from_and_ranking():
    import pandas as pd
    played = pd.DataFrame({"home": ["A", "B", "C"], "away": ["B", "C", "A"], "hg": [2, 1, 0], "ag": [0, 1, 3],
                           "kickoff_utc": ["2026-01-01", "2026-01-02", "2026-01-03"]})
    t = multi.table_from(played, ["A", "B", "C"])
    assert t["A"]["Pts"] == 6 and t["A"]["GD"] == 5 and t["A"]["AGF"] == 3
    assert multi.ranked(t)[0] == "A"
