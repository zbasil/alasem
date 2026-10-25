"""Points, tables and the official La Liga tie-breakers."""

import os

import numpy as np
import pandas as pd
import pytest

from zsc.standings import compute_table, league_table
from zsc.teams import canonical
from zsc.paths import RAW_OFFICIAL_TABLE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mk(rows):
    return pd.DataFrame(rows, columns=["home", "away", "hg", "ag"])


def double_round_robin(results):
    """results: dict (home, away) -> (hg, ag) covering every ordered pair."""
    return mk([(h, a, x, y) for (h, a), (x, y) in results.items()])


def test_points_and_goals():
    t = compute_table(mk([("A", "B", 2, 1), ("B", "C", 0, 0), ("C", "A", 3, 1)])).set_index("team")
    assert t.loc["A"].tolist() == [2, 1, 0, 1, 3, 4, -1, 3]
    assert t.loc["B"].tolist() == [2, 0, 1, 1, 1, 2, -1, 1]
    assert t.loc["C"].tolist() == [2, 1, 1, 0, 3, 1, 2, 4]


def test_two_teams_head_to_head_beats_goal_difference():
    # A and B finish level on points; B has the far better goal difference,
    # but A won the head-to-head on aggregate -> A must be above B.
    res = {("A", "B"): (1, 0), ("B", "A"): (1, 1),
           ("A", "C"): (0, 1), ("C", "A"): (1, 0),
           ("B", "C"): (5, 0), ("C", "B"): (1, 0)}
    t = league_table(double_round_robin(res)).set_index("team")
    assert t.loc["A", "Pts"] == t.loc["B", "Pts"] == 4
    assert t.loc["B", "GD"] > t.loc["A", "GD"]
    assert t.loc["A", "Pos"] < t.loc["B", "Pos"]


def test_two_teams_equal_head_to_head_falls_back_to_goal_difference():
    res = {("A", "B"): (1, 0), ("B", "A"): (1, 0),
           ("A", "C"): (3, 0), ("C", "A"): (0, 0),
           ("B", "C"): (1, 0), ("C", "B"): (0, 0)}
    t = league_table(double_round_robin(res)).set_index("team")
    assert t.loc["A", "Pts"] == t.loc["B", "Pts"]
    assert t.loc["A", "Pos"] < t.loc["B", "Pos"]          # better overall GD


def test_three_way_tie_uses_mini_league_points():
    # A, B, C level on 10 points. Mini-league: A 8, B 4, C 4; B and C are then
    # re-ranked on their own head-to-head (C won it 3-1 on aggregate).
    # Goal difference alone would give C (+4), A (+2), B (0).
    res = {
        ("A", "B"): (1, 0), ("B", "A"): (0, 0),
        ("A", "C"): (2, 1), ("C", "A"): (1, 1),
        ("B", "C"): (1, 0), ("C", "B"): (3, 0),
        ("A", "D"): (0, 0), ("D", "A"): (1, 1),
        ("B", "D"): (2, 0), ("D", "B"): (0, 1),
        ("C", "D"): (1, 0), ("D", "C"): (0, 2),
    }
    t = league_table(double_round_robin(res)).set_index("team")
    assert t.loc["A", "Pts"] == t.loc["B", "Pts"] == t.loc["C", "Pts"] == 10
    assert t.loc["C", "GD"] > t.loc["A", "GD"] > t.loc["B", "GD"]
    order = t.sort_values("Pos").index.tolist()
    assert order == ["A", "C", "B", "D"]


def test_mid_season_without_both_meetings_uses_goal_difference():
    # A beat B, but they have met only once -> head-to-head not yet applicable
    m = mk([("A", "B", 1, 0), ("B", "C", 4, 0), ("C", "A", 1, 0)])
    t = league_table(m).set_index("team")
    assert t.loc["A", "Pts"] == t.loc["B", "Pts"] == t.loc["C", "Pts"] == 3
    order = t.sort_values("Pos").index.tolist()
    assert order[0] == "B"                 # GD +3


def test_2006_07_real_madrid_champions_on_head_to_head(history):
    # Real Madrid and Barcelona both finished on 76 points; Barcelona had the
    # better goal difference, Real Madrid won the title on head-to-head.
    t = league_table(history[history["season"] == 2006])
    assert t.iloc[0]["team"] == "Real Madrid"
    assert t.iloc[1]["team"] == "Barcelona"
    assert t.iloc[0]["Pts"] == t.iloc[1]["Pts"] == 76


# Official final tables (Wikipedia), team order 1 -> 20 with points
OFFICIAL_2025_26 = [("Barcelona", 94), ("Real Madrid", 86), ("Villarreal", 72), ("Atlético Madrid", 69),
                    ("Real Betis", 60), ("Celta Vigo", 54), ("Getafe", 51), ("Rayo Vallecano", 50),
                    ("Valencia", 49), ("Real Sociedad", 46), ("Espanyol", 46), ("Athletic Bilbao", 45),
                    ("Sevilla", 43), ("Alavés", 43), ("Elche", 43), ("Levante", 42), ("Osasuna", 42),
                    ("Mallorca", 42), ("Girona", 41), ("Real Oviedo", 29)]
OFFICIAL_2024_25 = [("Barcelona", 88), ("Real Madrid", 84), ("Atlético Madrid", 76), ("Athletic Bilbao", 70),
                    ("Villarreal", 70), ("Real Betis", 60), ("Celta Vigo", 55), ("Rayo Vallecano", 52),
                    ("Osasuna", 52), ("Mallorca", 48), ("Real Sociedad", 46), ("Valencia", 46),
                    ("Getafe", 42), ("Espanyol", 42), ("Alavés", 42), ("Girona", 41), ("Sevilla", 41),
                    ("Leganes", 40), ("Las Palmas", 32), ("Valladolid", 16)]


@pytest.mark.parametrize("season,official", [(2025, OFFICIAL_2025_26), (2024, OFFICIAL_2024_25)])
def test_final_tables_match_official(history, season, official):
    t = league_table(history[history["season"] == season])
    got = list(zip(t["team"], t["Pts"]))
    exp = [(canonical(n), p) for n, p in official]
    assert got == exp


def test_current_season_matches_official_table(snapshot):
    cur = snapshot[(snapshot["season"] == 2026) & (snapshot["date"] <= "2026-10-21")]
    off = pd.read_csv(RAW_OFFICIAL_TABLE)
    off["team"] = off["team"].map(canonical)
    mine = compute_table(cur).set_index("team")
    for _, r in off.iterrows():
        assert mine.loc[r["team"], ["P", "W", "D", "L", "GF", "GA", "Pts"]].tolist() == \
            [r["P"], r["W"], r["D"], r["L"], r["GF"], r["GA"], r["Pts"]], r["team"]
