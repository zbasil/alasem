import math
"""Live reports: parsing, own goals, second-half stats, Arabic texts, cards."""

import json
import os

import pytest

from zsc.cards import card_html
from zsc.inplay import InPlayModel
from zsc.live import (LiveContext, build_report, count_ar, model_events, parse_game_stats, phase_stats,
                      report_markdown, team_insights)
from zsc.paths import RAW_SR_GAMES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FT_PATH = os.path.join(RAW_SR_GAMES, "sr_sport_event_72478646_FT_original.json")


@pytest.fixture(scope="module")
def model():
    return InPlayModel.load(os.path.join(ROOT, "outputs", "inplay_model.json"))


RAW = {  # the sports tool's own shape (abbreviation keys)
    "home": "BAR", "away": "RMA",
    "teams": {"BAR": {"name": "FC Barcelona"}, "RMA": {"name": "Real Madrid"}},
    "score": {"BAR": 2, "RMA": 1},
    "team_stats": {"BAR": {"shots_total": 9, "shots_on_target": 4, "ball_possession": 61, "corner_kicks": 5},
                   "RMA": {"shots_total": 4, "shots_on_target": 2, "ball_possession": 39, "corner_kicks": 1}},
    "key_events": [
        {"type": "score_change", "time": 12, "team": "home", "home_score": 1, "away_score": 0},
        {"type": "score_change", "time": 30, "team": "home", "home_score": 1, "away_score": 1},   # own goal
        {"type": "red_card", "time": 40, "team": "away"},
        {"type": "score_change", "time": 44, "team": "home", "home_score": 2, "away_score": 1},
    ],
}


def test_parse_raw_tool_answer():
    s = parse_game_stats(RAW)
    assert (s.home, s.away, s.hg, s.ag) == ("Barcelona", "Real Madrid", 2, 1)
    assert s.stats["home"]["shots_total"] == 9
    # a statistic the source did not send stays unknown, never 0
    assert math.isnan(s.stats["away"]["fouls"])


def test_no_insight_is_claimed_from_missing_stats():
    from zsc.live import team_insights, phase_stats
    js = {"home": "Barcelona", "away": "Real Madrid", "score": {"home": 0, "away": 0},
          "team_stats": {"home": {"shots_total": 9}, "away": {"shots_total": 2}}, "key_events": []}
    st = phase_stats(parse_game_stats(js), None)["full"]
    pos, neg = team_insights(st["home"], st["away"], "برشلونة", "ريال مدريد", 1.0, [], "home")
    neg_a = team_insights(st["away"], st["home"], "ريال مدريد", "برشلونة", 1.0, [], "away")[1]
    text = " ".join(pos + neg + neg_a)
    # only shot volume is known: nothing about fouls, cards, corners, possession, accuracy or saves
    for word in ("أخطاء", "إنذار", "ركنيات", "استحواذ", "دقة", "الحارس", "انضباط"):
        assert word not in text, (word, text)
    assert "سيطرة هجومية" in text


def test_scorer_is_read_from_the_running_score():
    ev = model_events(parse_game_stats(RAW))
    goals = [(e["minute"], e["team"]) for e in ev if e["kind"] == "goal"]
    assert goals == [(12, "home"), (30, "away"), (44, "home")]      # the own goal counts for the away side
    assert [(e["minute"], e["team"]) for e in ev if e["kind"] == "red"] == [(40, "away")]


def test_second_half_is_full_minus_first():
    full = parse_game_stats(json.load(open(FT_PATH)))
    first = parse_game_stats(json.load(open(FT_PATH)))
    for k in ("shots_total", "corner_kicks", "fouls"):
        first.stats["home"][k] = full.stats["home"][k] - 3
    first.stats["home"]["ball_possession"] = 55
    first.hg, first.ag = 0, 1
    ps = phase_stats(full, first)
    assert ps["second_half"]["home"]["shots_total"] == 3
    assert ps["second_half"]["home"]["goals"] == 1 and ps["second_half"]["away"]["goals"] == 0
    # 51% over the match after 55% in the first half -> about 47% in the second
    assert ps["second_half"]["home"]["ball_possession"] == pytest.approx(47)


def test_reports_are_never_empty(model):
    snap = parse_game_stats(json.load(open(FT_PATH)))
    rep = build_report("FT", snap, None, LiveContext(lam=2.0, mu=1.0), model)
    for side in ("home", "away"):
        assert rep["insights"][side]["pos"] and rep["insights"][side]["neg"]
    assert rep["notes"]
    md = report_markdown(rep)
    assert "ألافيس" in md and "ملقة" in md
    assert rep["timeline"][-1]["p_draw"] == pytest.approx(1.0)


def test_half_time_report(model):
    rep = build_report("HT", parse_game_stats(RAW), None, LiveContext(lam=1.9, mu=1.3), model)
    assert sum(rep["now"]["p"]) == pytest.approx(1.0)
    assert rep["now"]["p"][0] > rep["pre_match"]["p"][0]                 # leading and opponent down to ten
    assert any("النتيجة الأرجح" in n for n in rep["notes"])
    html = card_html(rep)
    assert "برشلونة" in html and "@zahraatalksfootball94" in html and "<svg" in html


def test_insight_rules_point_the_right_way():
    st = {"shots_total": 12, "shots_on_target": 6, "goals": 2, "ball_possession": 62, "corner_kicks": 7,
          "fouls": 6, "yellow_cards": 0, "sent_off": 0, "offsides": 0, "shots_blocked": 2, "saves": 1}
    op = {"shots_total": 3, "shots_on_target": 1, "goals": 0, "ball_possession": 38, "corner_kicks": 1,
          "fouls": 12, "yellow_cards": 3, "sent_off": 0, "offsides": 1, "shots_blocked": 1, "saves": 4}
    pos, neg = team_insights(st, op, "أ", "ب", 1.0)
    assert any("سيطرة هجومية" in t for t in pos)
    pos2, neg2 = team_insights(op, st, "ب", "أ", 1.0)
    assert any("تحت الضغط" in t for t in neg2)
    assert any("الحارس" in t for t in pos2)


def test_arabic_counting():
    assert count_ar(1, "هدف", "هدفين", "أهداف") == "هدف"
    assert count_ar(2, "هدف", "هدفين", "أهداف") == "هدفين"
    assert count_ar(5, "هدف", "هدفين", "أهداف") == "5 أهداف"
    assert count_ar(12, "هدف", "هدفين", "أهداف", "هدف") == "12 هدف"
