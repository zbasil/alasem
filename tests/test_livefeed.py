"""Live layer: tying ESPN games to our fixtures, stable event ids, corrections, unknown stays unknown."""
import copy
import json
import os

from zsc import free_sources as fs
from zsc import livefeed as lf

FX = os.path.join(os.path.dirname(__file__), "fixtures", "free")
TEAMS = {"CFC": {"en": "Chelsea"}, "TOT": {"en": "Tottenham"}, "LFC": {"en": "Liverpool"}, "BRI": {"en": "Brighton"},
         "MCI": {"en": "Man City"}, "MUN": {"en": "Man United"}}
FIXTURES = [
    {"match_id": "ENG1-2026-CFC-TOT", "home": "CFC", "away": "TOT", "kickoff_utc": "2026-10-24T16:30:00Z"},
    {"match_id": "ENG1-2026-LFC-BRI", "home": "LFC", "away": "BRI", "kickoff_utc": "2026-10-25T14:00:00Z"},
    {"match_id": "ENG1-2026-MCI-MUN", "home": "MCI", "away": "MUN", "kickoff_utc": "2026-10-25T16:30:00Z"},
]


def games():
    return fs.parse_espn_scoreboard(json.load(open(os.path.join(FX, "espn_scoreboard.json"), encoding="utf-8")))


def build(tmp_path, g, stamp="2026-10-24T17:20:00Z"):
    return lf.build_live({"ENG1": g}, stamp, fixtures={"ENG1": (FIXTURES, TEAMS)}, out_dirs=(str(tmp_path),))


def test_ties_games_by_name_not_abbreviation(tmp_path):
    doc = build(tmp_path, games())
    assert set(doc["matches"]) == {"ENG1-2026-CFC-TOT", "ENG1-2026-LFC-BRI"}   # ESPN says CHE/BHA, we say CFC/BRI
    assert doc["unmatched"] == [] and doc["n_live"] == 1
    live = doc["matches"]["ENG1-2026-CFC-TOT"]
    assert live["state"] == "live" and live["minute"] == 49 and live["score"] == [1, 0]
    assert [e["kind"] for e in live["events"]] == ["goal", "yellow"]
    assert live["events"][0]["side"] is None or live["events"][0]["side"] in ("home", "away")


def test_pre_match_score_is_unknown_not_zero(tmp_path):
    pre = build(tmp_path, games())["matches"]["ENG1-2026-LFC-BRI"]
    assert pre["state"] == "pre" and pre["score"] is None and pre["minute"] is None


def test_aliases_and_unknown_team_is_reported_not_guessed(tmp_path):
    g = copy.deepcopy(games()[1])
    g.update(espn_id="9", kickoff_utc="2026-10-25T16:30Z")
    g["home"] = {"name": "Manchester City", "abbr": "MNC", "score": 0}
    g["away"] = {"name": "Manchester United", "abbr": "MAN", "score": 0}
    odd = copy.deepcopy(g)
    odd.update(espn_id="10", kickoff_utc="2026-10-28T19:00Z")
    odd["home"], odd["away"] = {"name": "Unknown FC"}, {"name": "Nobody United"}
    doc = build(tmp_path, [g, odd])
    assert "ENG1-2026-MCI-MUN" in doc["matches"]
    assert [u["espn_id"] for u in doc["unmatched"]] == ["10"]


def test_stable_ids_and_var_retraction(tmp_path):
    g = games()
    first = build(tmp_path, g)["matches"]["ENG1-2026-CFC-TOT"]
    again = build(tmp_path, g, "2026-10-24T17:30:00Z")["matches"]["ENG1-2026-CFC-TOT"]
    assert [e["id"] for e in first["events"]] == [e["id"] for e in again["events"]]
    assert again["changed_utc"] == first["changed_utc"]            # nothing new: not marked as changed
    # the goal is ruled out: it leaves the feed and the score drops to 0-0
    g2 = copy.deepcopy(g)
    g2[0]["events"] = [e for e in g2[0]["events"] if not e["goal"]]
    g2[0]["home"]["score"] = 0
    after = build(tmp_path, g2, "2026-10-24T17:40:00Z")["matches"]["ENG1-2026-CFC-TOT"]
    assert after["score"] == [0, 0]
    assert [r["kind"] for r in after["retracted"]] == ["goal"]
    assert after["score_history"][-1] == {"score": [0, 0], "seen_utc": "2026-10-24T17:40:00Z", "correction": True}


def test_status_mapping_and_minutes():
    assert lf.minute_of("90'+4'") == 94 and lf.minute_of("HT") is None and lf.minute_of(None) is None
    g = games()[0]
    for name, state in [("STATUS_HALFTIME", "ht"), ("STATUS_POSTPONED", "postponed"), ("STATUS_FINAL_PEN", "ft")]:
        e = lf.live_entry(dict(g, status_name=name), None, "2026-10-24T17:00:00Z")
        assert e["state"] == state
        assert e["minute"] is None        # only a running match has a minute


def test_event_kinds():
    k = lf.event_kind
    assert k({"type": "Penalty - Scored", "goal": True}) == "penalty_goal"
    assert k({"type": "Own Goal", "goal": True}) == "own_goal"
    assert k({"type": "Red Card", "red": True}) == "red"
    assert k({"type": "Substitution"}) == "sub"


def test_summary_kept_between_runs(tmp_path):
    g = games()
    g[0]["summary"] = fs.parse_espn_summary(json.load(open(os.path.join(FX, "espn_summary.json"), encoding="utf-8")))
    m = build(tmp_path, g)["matches"]["ENG1-2026-CFC-TOT"]
    assert m["has_lineups"] and m["stats"]["home"]["possessionPct"] == 58.2 and m["stats"]["away"]["shotsOnTarget"] is None
    g2 = games()                       # the next run skips the summary call: lineups stay
    m2 = build(tmp_path, g2, "2026-10-24T17:30:00Z")["matches"]["ENG1-2026-CFC-TOT"]
    assert m2["has_lineups"] and m2["lineups"] == m["lineups"]
