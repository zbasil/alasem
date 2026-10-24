"""The weekly notebook path: football-data.co.uk parsing, times, dashboard files."""

import io
import os

import numpy as np
import pandas as pd

from zsc.dashboard import dashboard_tables, uk_to_baghdad
from zsc.data import standardise_football_data
from zsc.dixon_coles import DCConfig
from zsc.forecast import run_forecast, to_json
from zsc.paths import RAW_UPCOMING_FWP  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAMPLE = """Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HST,AST,B365H,B365D,B365A,B365>2.5,B365<2.5
SP1,15/08/2026,19:30,Alaves,Getafe,3,0,H,8,2,2.35,2.8,3.75,3.2,1.36
SP1,16/08/26,17:00,Santander,Villarreal,2,2,D,3,7,3.2,3.6,2.15,1.8,2.0
SP1,23/08/2026,21:30,Elche,Barcelona,0,5,A,1,9,9.0,5.75,1.3,1.44,2.75
"""


def test_football_data_csv_is_parsed():
    df = standardise_football_data(pd.read_csv(io.StringIO(SAMPLE)), 2026)
    assert df["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-08-15", "2026-08-16", "2026-08-23"]
    assert df[["home", "away"]].values.tolist() == [["Alaves", "Getafe"], ["Santander", "Villarreal"],
                                                   ["Elche", "Barcelona"]]
    assert df["hg"].tolist() == [3, 2, 0] and df["ag"].tolist() == [0, 2, 5]
    assert df["odds_h"].tolist() == [2.35, 3.2, 9.0] and df["odds_o25"].tolist() == [3.2, 1.8, 1.44]
    assert (df["season"] == 2026).all()


def test_kick_off_times_follow_the_clock_change():
    assert uk_to_baghdad("2026-10-24", "20:00") == "22:00"     # UK summer time
    assert uk_to_baghdad("2026-10-25", "20:00") == "23:00"     # after clocks go back
    assert uk_to_baghdad("2026-10-25", "") == ""


def test_dashboard_files_are_consistent(snapshot):
    upcoming = pd.read_csv(RAW_UPCOMING_FWP)
    res = run_forecast(snapshot, 2026, "2026-10-23", DCConfig(rating_scale=1.1), 0.05,
                       upcoming=upcoming, n_sims=2000)
    t = dashboard_tables(to_json(res))
    f = t["forecast"]
    assert len(f) == 20 and set(f["team"]) == set(t["table_now"]["team"])
    assert abs(f["title_pct"].sum() - 100) < 1.0
    assert abs(f["releg_pct"].sum() - 300) < 1.5
    assert (f["pts_low"] <= f["exp_pts"]).all() and (f["exp_pts"] <= f["pts_high"]).all()
    assert (f["pts_now"] <= f["pts_low"]).all()
    pos = t["positions"]
    assert len(pos) == 400
    assert np.allclose(pos.groupby("team")["pct"].sum(), 100, atol=1.0)
    nr = t["next_round"]
    assert len(nr) == 10
    assert np.allclose(nr[["home_pct", "draw_pct", "away_pct"]].sum(axis=1), 100, atol=0.2)
    assert t["run_info"].loc[0, "matches_played"] == 89
    assert t["table_now"]["Pts"].tolist() == sorted(t["table_now"]["Pts"], reverse=True)


def test_merging_a_second_results_source():
    from zsc.online import merge_current, parse_extra_results
    base = parse_extra_results("2026-08-15, Alaves, Getafe, 3, 0\n2026-08-15, Sevilla, Vallecano, 2, 1", 2026)
    newer = parse_extra_results("2026-08-15, Alavés, Getafe, 3, 0\n2026-10-25, FC Barcelona, Real Madrid CF, 2, 1", 2026)
    out = merge_current(base, newer, log=lambda *_: None)
    assert len(out) == 3 and ("Barcelona", "Real Madrid") in set(zip(out["home"], out["away"]))
    # a disagreeing source is ignored completely
    wrong = parse_extra_results("2026-08-15, Alaves, Getafe, 1, 0\n2026-10-25, Barcelona, Real Madrid, 2, 1", 2026)
    assert len(merge_current(base, wrong, log=lambda *_: None)) == 2
