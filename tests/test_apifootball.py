"""API-Football adapter: answers shaped like the documented v3 examples map to the project's ids."""

from zsc import apifootball as af


FIXTURES = {"response": [{"fixture": {"id": 1001, "date": "2026-10-25T20:00:00+00:00", "status": {"short": "NS"}},
                          "teams": {"home": {"id": 529, "name": "Barcelona"}, "away": {"id": 541, "name": "Real Madrid"}},
                          "goals": {"home": None, "away": None}}]}
LINEUPS = {"response": [
    {"team": {"id": 529, "name": "Barcelona"}, "formation": "4-3-3", "coach": {"id": 1, "name": "Coach A"},
     "startXI": [{"player": {"id": 1, "name": "Keeper One", "number": 1, "pos": "G", "grid": "1:1"}},
                 {"player": {"id": 2, "name": "Striker Nine", "number": 9, "pos": "F", "grid": "4:2"}}],
     "substitutes": [{"player": {"id": 3, "name": "Sub Twelve", "number": 12, "pos": "M", "grid": None}}]},
    {"team": {"id": 541, "name": "Real Madrid"}, "formation": "4-4-2", "coach": {"id": 2, "name": "Coach B"},
     "startXI": [{"player": {"id": 4, "name": "Keeper Two", "number": 13, "pos": "G", "grid": "1:1"}}], "substitutes": []}]}
INJURIES = {"response": [{"player": {"id": 7, "name": "Injured Player", "type": "Missing Fixture", "reason": "Knee Injury"},
                          "team": {"id": 541, "name": "Real Madrid"}, "fixture": {"id": 1001, "date": "2026-10-25T20:00:00+00:00"}}]}


def test_fixture_ids_map_to_stable_match_ids():
    ids = af.id_map(FIXTURES, 2026)
    assert ids == {1001: "ESP1-2026-BAR-RMA"}


def test_lineups_and_absences_rows():
    rows = af.lineup_rows(LINEUPS, "ESP1-2026-BAR-RMA")
    assert {r["team_id"] for r in rows} == {"BAR", "RMA"}
    assert sum(r["starter"] for r in rows) == 3 and rows[0]["formation"] == "4-3-3"
    ab = af.absence_rows(INJURIES, af.id_map(FIXTURES, 2026))
    assert ab[0]["match_id"] == "ESP1-2026-BAR-RMA" and ab[0]["team_id"] == "RMA" and ab[0]["reason"] == "Knee Injury"


def test_switched_off_without_a_key(monkeypatch):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    af.config._dotenv.cache_clear()
    assert not af.enabled()
    assert af.fetch()["status"] == "skipped"
