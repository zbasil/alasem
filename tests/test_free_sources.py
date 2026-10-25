"""Parsers of the free sources (sample payloads shaped like the live ESPN / FPL / Understat / RSS responses)."""
import json
import os

import pytest

from zsc import free_sources as fs

FX = os.path.join(os.path.dirname(__file__), "fixtures", "free")


def load(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


def test_espn_scoreboard_live_and_pre():
    rows = fs.parse_espn_scoreboard(load("espn_scoreboard.json"))
    assert len(rows) == 2
    live, pre = rows
    assert live["state"] == "in" and live["clock"] == "49'"
    assert live["home"]["abbr"] == "CHE" and live["home"]["score"] == 1 and live["away"]["score"] == 0
    assert live["events"][0]["goal"] and live["events"][0]["players"] == ["Cole Palmer"]
    assert live["events"][1]["yellow"] and not live["events"][1]["goal"]
    assert pre["state"] == "pre" and pre["events"] == []


def test_espn_summary_lineups_unknown_stays_unknown():
    s = fs.parse_espn_summary(load("espn_summary.json"))
    assert s["has_lineups"]
    home = [l for l in s["lineups"] if l["side"] == "home"][0]
    assert home["formation"] == "4-2-3-1"
    assert sum(p["starter"] for p in home["players"]) == 2
    assert [p["name"] for p in home["players"] if p["subbed_in"]] == ["Bench Player"]
    assert s["stats"]["CHE"]["possessionPct"] == 58.2
    assert s["stats"]["TOT"]["shotsOnTarget"] is None          # blank is unknown, not 0


def test_fpl_availability_and_players():
    js = load("fpl_bootstrap.json")
    av = fs.parse_fpl_availability(js)
    assert [a["player"] for a in av] == ["Saliba", "Hincapie"]
    assert av[0]["status_ar"] == "مصاب" and av[1]["chance_next"] == 75
    pl = fs.parse_fpl_players(js)
    palmer = [p for p in pl if p["player"] == "Palmer"][0]
    assert palmer["team"] == "CHE" and palmer["xg"] == 5.1 and palmer["pos"] == "MID"
    assert all(p["minutes"] >= 1 for p in pl)


def test_rss_keeps_only_safe_links_and_sorts():
    items = fs.parse_rss(open(os.path.join(FX, "rss.xml"), encoding="utf-8").read(), "test")
    assert [i["title"] for i in items] == ["برشلونة يستعد لأستون فيلا", "Arsenal top the table"]
    assert items[0]["published"] == "2026-10-24T15:00:00Z"


def test_understat_embedded():
    html = open(os.path.join(FX, "understat_league.html"), encoding="utf-8").read()
    rows = fs.parse_understat_dates(fs.parse_understat_embedded(html, "datesData"))
    assert rows[0]["home"] == "Arsenal" and rows[0]["hg"] == 2 and rows[0]["xg_home"] == 1.84


def test_ntfy_needs_long_topic_and_keeps_arabic():
    with pytest.raises(ValueError):
        fs.ntfy_send("short", "t", "m", dry_run=True)
    r = fs.ntfy_send("zahraa-football-7f3k2q9x", "هدف لبرشلونة", "1-0 بالدقيقة 23", dry_run=True)
    assert r["body"]["title"] == "هدف لبرشلونة" and r["url"] == "https://ntfy.sh/"
