"""Prediction log v2: refuses late forecasts, versions every change, scores by match id."""

import pandas as pd
import pytest

from zsc import predlog


def row(mid="ESP1-2026-ATM-DEP", track="market", issued="2026-10-24T11:00:00Z", ko="2026-10-24T19:00:00Z",
        p=(0.7, 0.2, 0.1), data="d1", model="prematch-market-2.0", **kw):
    return {"match_id": mid, "competition": "ESP1", "season": 2026, "id_source": "zsc", "home_id": "ATM",
            "away_id": "DEP", "track": track, "model_version": model, "data_version": data,
            "issued_at": issued, "kickoff_utc": ko, "p_home": p[0], "p_draw": p[1], "p_away": p[2],
            "score1": "2-0", **kw}


def test_refuses_forecast_issued_at_or_after_kickoff(tmp_path):
    path = str(tmp_path / "log.csv")
    with pytest.raises(ValueError, match="after kick-off"):
        predlog.append(path, pd.DataFrame([row(issued="2026-10-24T19:00:00Z")]))
    with pytest.raises(ValueError, match="after kick-off"):
        predlog.append(path, pd.DataFrame([row(issued="2026-10-24T19:30:00Z")]))


def test_refuses_probabilities_that_do_not_sum_to_one(tmp_path):
    with pytest.raises(ValueError, match="sum to 1"):
        predlog.append(str(tmp_path / "log.csv"), pd.DataFrame([row(p=(0.7, 0.2, 0.2))]))


def test_identical_forecast_is_not_logged_twice_and_changes_are_versioned(tmp_path):
    path = str(tmp_path / "log.csv")
    first = predlog.append(path, pd.DataFrame([row()]))
    assert len(first) == 1
    again = predlog.append(path, pd.DataFrame([row(issued="2026-10-24T12:00:00Z")]))
    assert len(again) == 0                                   # same numbers, same versions: skipped
    changed = predlog.append(path, pd.DataFrame([row(issued="2026-10-24T13:00:00Z", p=(0.6, 0.25, 0.15), data="d2")]))
    assert len(changed) == 1
    log = predlog.read(path)
    assert len(log) == 2
    assert log.iloc[1]["supersedes"] == log.iloc[0]["prediction_id"]


def test_outside_source_reading_is_new_only_when_its_numbers_change(tmp_path):
    path = str(tmp_path / "log.csv")
    sr = dict(track="sportradar", model="sportradar-published", data="sportradar", p=(0.763, 0.148, 0.089))
    assert len(predlog.append(path, pd.DataFrame([row(**sr)]))) == 1
    assert len(predlog.append(path, pd.DataFrame([row(issued="2026-10-24T15:00:00Z", **sr)]))) == 0


def test_scoring_uses_the_last_forecast_before_the_real_kickoff_and_match_ids(tmp_path):
    path = str(tmp_path / "log.csv")
    predlog.append(path, pd.DataFrame([row(p=(0.5, 0.3, 0.2))]))
    predlog.append(path, pd.DataFrame([row(issued="2026-10-24T18:00:00Z", p=(0.7, 0.2, 0.1), data="d2")]))
    log = predlog.read(path)
    results = pd.DataFrame([{"match_id": "ESP1-2026-ATM-DEP", "hg": 2, "ag": 0}])
    per, summ = predlog.score(log, results)
    assert len(per) == 1 and abs(per.iloc[0]["p_home"] - 0.7) < 1e-9 and per.iloc[0]["hit"] == 1
    # the match was moved earlier: the 18:00 forecast came after the real kick-off and no longer counts
    per2, _ = predlog.score(log, results, kickoffs={"ESP1-2026-ATM-DEP": "2026-10-24T17:00:00Z"})
    assert abs(per2.iloc[0]["p_home"] - 0.5) < 1e-9
    # a corrected result is re-scored automatically (scoring always reads the current results)
    per3, _ = predlog.score(log, pd.DataFrame([{"match_id": "ESP1-2026-ATM-DEP", "hg": 0, "ag": 1}]))
    assert per3.iloc[0]["hit"] == 0


def test_live_rows_go_to_their_own_log(tmp_path):
    path = str(tmp_path / "live.csv")
    r = row(track="live", issued="2026-10-24T19:50:00Z", minute=45, period=1, hg=1, ag=0, red_home=0, red_away=0)
    new = predlog.append(path, pd.DataFrame([r]), kind="live")       # live rows may be issued after kick-off
    assert len(new) == 1
    assert "minute" in predlog.read(path, predlog.LIVE_COLS).columns
