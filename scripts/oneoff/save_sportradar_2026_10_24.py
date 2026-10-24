"""Save the SportRadar answers read in the Claude session on 24 Oct 2026 (about 10:50 UTC) as raw files.

Values are copied from the sports-data tool's game_stats answers (team stats in the tool's key order,
key events with minute, side and running score). Lineups are not kept (they list the players who
played without marking the starting eleven).
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from zsc.paths import RAW_SR_GAMES, RAW_SPORTRADAR  # noqa: E402

FETCHED = "2026-10-24T10:50:00Z"
KEYS = ["ball_possession", "cards_given", "corner_kicks", "fouls", "free_kicks", "goal_kicks", "injuries", "offsides",
        "red_cards", "shots_blocked", "shots_off_target", "shots_on_target", "shots_saved", "shots_total",
        "substitutions", "throw_ins", "yellow_cards", "yellow_red_cards"]
TYPES = {"G": "score_change", "Y": "yellow_card", "R": "red_card", "S": "substitution", "YR": "yellow_red_card"}

GAMES = [
 ("sr:sport_event:72478608", "2026-10-11T16:30:00Z", "Real Betis Seville", "CA Osasuna", 5, 2,
  [55,2,8,11,12,4,0,0,0,5,3,9,3,17,5,17,2,0], [45,5,4,12,11,5,0,2,0,4,2,5,5,11,5,10,5,0],
  "G10h1-0 G31h2-0 Y41a Y45a Y45h S46a G48h3-0 G51a3-1 G56a3-2 S63a S63a Y64a G67h4-2 S73h S74h S74a S79a Y81h S81h S81h Y88a S90h G90h5-2 Y90a"),
 ("sr:sport_event:72478618", "2026-10-11T19:00:00Z", "Racing Santander", "Valencia CF", 2, 2,
  [54,3,8,15,9,8,0,0,0,2,4,11,1,17,5,20,3,0], [46,3,3,10,16,10,0,1,0,1,6,3,9,10,5,13,3,0],
  "G2a0-1 Y22h G32h1-1 Y45h Y45a Y45a S46a G47h2-1 S58a S58a S61h S61h G65a2-2 Y72a S75h S86a S86a S87h S87h Y90h"),
 ("sr:sport_event:72478624", "2026-10-11T14:15:00Z", "Real Sociedad San Sebastian", "RC Deportivo de A Coruna", 3, 2,
  [44,2,7,13,14,8,0,4,1,4,4,4,8,12,4,12,1,0], [56,3,10,13,13,7,0,0,1,5,4,10,1,19,5,15,2,0],
  "G29h1-0 G34h2-0 Y40a S46a G54h3-0 S56h S56h S57a S57a S57a G61a3-1 R66h G69a3-2 S70h Y71a S79a S88h R90a Y90h"),
 ("sr:sport_event:72478614", "2026-10-12T19:00:00Z", "Levante UD", "Sevilla FC", 3, 3,
  [56,2,5,7,15,8,1,0,0,1,0,6,0,7,5,23,2,0], [44,5,2,17,6,10,0,0,0,2,7,3,3,12,4,12,5,1],
  "G13a0-1 Y39h Y48a G54a0-2 S56h S56h G57h1-2 Y63a S68a S68a S68h S72a Y76h Y85a S88a S90h S90h Y90a G90h2-2 G90a2-3 Y90a G90h3-3"),
 ("sr:sport_event:72478630", "2026-10-16T19:00:00Z", "RC Deportivo de A Coruna", "Levante UD", 1, 1,
  [47,3,3,17,11,10,0,0,0,1,5,5,3,11,5,23,3,0], [53,2,5,12,18,5,0,0,0,1,4,4,4,9,4,21,2,0],
  "Y33a Y42h S62h S62h G63h1-0 S69a S69a S76a S80h S80h G82a1-1 S85h Y89a S90a Y90h Y90h"),
 ("sr:sport_event:72478626", "2026-10-17T16:30:00Z", "Real Betis Seville", "FC Barcelona", 2, 5,
  [42,4,2,10,10,8,0,1,1,1,0,5,5,6,5,18,3,0], [58,2,5,11,10,1,2,2,0,1,5,10,3,16,5,23,2,0],
  "G10a0-1 Y20a Y22h G27h1-1 G41a1-2 S46h S46a G51a1-3 Y53h G53h2-3 R54h Y55a Y61h S62a S62a G62a2-4 S64h S64h S70a S70h S70h S79a G81a2-5"),
 ("sr:sport_event:72478632", "2026-10-17T12:00:00Z", "Espanyol Barcelona", "Atletico Madrid", 0, 1,
  [28,2,4,10,9,11,0,0,0,2,3,2,5,7,5,14,2,0], [72,5,12,9,9,5,0,4,0,1,8,6,2,15,5,12,5,0],
  "Y22a Y43a S46a S46a S55a S62a S64h Y66a S67a Y68a S73h S73h Y79a Y81h S82h S82h Y87h G89a0-1"),
 ("sr:sport_event:72478642", "2026-10-17T19:00:00Z", "Valencia CF", "Athletic Bilbao", 0, 0,
  [37,3,2,14,14,11,0,2,0,3,6,4,2,13,5,15,3,0], [63,3,6,13,14,10,0,1,0,3,6,2,4,11,5,12,3,0],
  "Y19h Y38a Y42a S46a S54h S54h Y57a S63a S63a S63a S68a S74h S85h S86h Y87h Y90h"),
 ("sr:sport_event:72478644", "2026-10-17T14:15:00Z", "Villarreal CF", "Elche CF", 0, 0,
  [58,2,10,12,8,7,0,5,0,6,5,5,1,16,5,10,2,0], [42,4,5,7,13,9,0,0,0,1,3,1,5,5,5,16,4,0],
  "S28a Y38a S65a S65a S65a S66h S66h S66h Y71a Y75a S75h Y81h S83a S84h Y90h Y90a"),
 ("sr:sport_event:72478628", "2026-10-18T14:15:00Z", "RC Celta de Vigo", "Deportivo Alaves", 2, 1,
  [52,1,0,14,7,9,0,0,0,0,2,3,8,5,5,11,1,0], [48,1,4,17,5,4,0,0,0,3,6,9,1,18,5,22,1,0],
  "Y15h Y45a S46h S46h G53h1-0 S62a S62a S62a S70h S70h G71h2-0 S77h G87a2-1 S88a S88a"),
 ("sr:sport_event:72478636", "2026-10-18T16:30:00Z", "Malaga CF", "Real Sociedad San Sebastian", 2, 5,
  [47,1,4,4,6,5,0,2,0,1,7,5,5,13,5,18,1,0], [53,2,5,9,4,15,0,2,0,4,4,10,3,18,5,19,2,0],
  "G3a0-1 G26a0-2 Y37a S46h S46h G54h1-2 G59a1-3 S60a S60a Y62a S64h G66h2-3 Y67h G67a2-4 S68h S71a S71a G73a2-5 S79a S82h"),
 ("sr:sport_event:72478638", "2026-10-18T12:00:00Z", "CA Osasuna", "Racing Santander", 2, 0,
  [46,2,7,21,8,9,0,4,0,4,7,4,2,15,5,24,2,0], [54,3,4,8,21,13,1,2,0,1,5,2,2,8,5,24,3,0],
  "Y6a G9h1-0 Y28h S46a Y51a Y60h S67h S67h S69a S76h S76h Y80a S83a S83a G88h2-0 S90h S90a"),
 ("sr:sport_event:72478640", "2026-10-18T19:00:00Z", "Real Madrid", "Sevilla FC", 4, 1,
  [64,2,1,10,13,6,0,1,0,4,5,8,4,17,5,17,2,0], [36,2,2,13,10,11,1,0,0,2,4,5,4,11,5,15,2,0],
  "Y23h Y23a G30h1-0 G37h2-0 S46a S56a S56a G63h3-0 Y69a S70h S70h S72a S72a Y73h S78h G80a3-1 G82h4-1 S85h S85h"),
 ("sr:sport_event:72478634", "2026-10-19T19:00:00Z", "Getafe CF", "Rayo Vallecano", 1, 1,
  [31,7,8,12,8,10,0,0,1,4,4,3,4,11,5,13,6,0], [69,3,8,9,12,4,1,3,0,7,8,5,2,20,5,14,3,0],
  "Y1h G11a0-1 Y16h R28h S32h Y45a S46h S46h Y51h G56h1-1 S59a S59a S65a Y69a Y80h S81a S81a S81h Y84h S87h Y87h Y90a"),
 ("sr:sport_event:74801144", "2026-10-21T18:00:00Z", "Levante UD", "Athletic Bilbao", 3, 1,
  [43,3,3,12,12,10,1,0,0,3,2,6,3,11,5,11,3,0], [57,2,9,12,11,6,0,0,1,6,5,4,3,15,5,14,1,0],
  "G20h1-0 G22h2-0 S47a S47a G67a2-1 Y67h S72h S72h S72h R73a Y77h Y80h S81a S81a S81a S83h S86h Y90a G90h3-1"),
]

# scheduled games seen in the same answers (kick-off UTC, SportRadar's published win probabilities if any)
UPCOMING = [
 ("sr:sport_event:72478656", "2026-10-24T14:15:00+00:00", "Racing Santander", "Espanyol Barcelona", (41.5, 26.0, 32.5)),
 ("sr:sport_event:72478664", "2026-10-24T16:30:00+00:00", "Valencia CF", "Villarreal CF", (27.6, 26.4, 46.0)),
 ("sr:sport_event:72478648", "2026-10-25T13:00:00+00:00", "Athletic Bilbao", "Getafe CF", (61.1, 24.0, 14.9)),
 ("sr:sport_event:72478652", "2026-10-25T15:15:00+00:00", "RC Celta de Vigo", "Real Betis Seville", (31.4, 27.4, 41.2)),
 ("sr:sport_event:72478660", "2026-10-25T17:30:00+00:00", "Real Sociedad San Sebastian", "Levante UD", (60.0, 21.3, 18.7)),
 ("sr:sport_event:72478654", "2026-10-25T20:00:00+00:00", "FC Barcelona", "Real Madrid", (60.1, 16.1, 23.8)),
 ("sr:sport_event:72478684", "2026-10-30T20:00:00+00:00", "Villarreal CF", "Espanyol Barcelona", (61.2, 21.4, 17.4)),
 ("sr:sport_event:72478678", "2026-10-31T13:00:00+00:00", "Levante UD", "Atletico Madrid", None),
 ("sr:sport_event:72478682", "2026-10-31T15:15:00+00:00", "Rayo Vallecano", "RC Celta de Vigo", None),
 ("sr:sport_event:72478668", "2026-10-31T17:30:00+00:00", "Real Betis Seville", "Malaga CF", None),
 ("sr:sport_event:72478676", "2026-11-01T13:00:00+00:00", "Getafe CF", "Sevilla FC", None),
 ("sr:sport_event:72478680", "2026-11-01T15:15:00+00:00", "Racing Santander", "Real Madrid", None),
 ("sr:sport_event:72478672", "2026-11-01T17:30:00+00:00", "Elche CF", "Valencia CF", None),
 ("sr:sport_event:72478666", "2026-11-01T20:00:00+00:00", "Athletic Bilbao", "Real Sociedad San Sebastian", None),
 ("sr:sport_event:72478694", "2026-11-07T13:00:00+00:00", "Malaga CF", "Racing Santander", None),
 ("sr:sport_event:72478692", "2026-11-07T15:15:00+00:00", "Espanyol Barcelona", "RC Deportivo de A Coruna", None),
 ("sr:sport_event:72478702", "2026-11-07T20:00:00+00:00", "Valencia CF", "Real Madrid", None),
 ("sr:sport_event:72478690", "2026-11-08T13:00:00+00:00", "Elche CF", "Real Betis Seville", None),
 ("sr:sport_event:72478698", "2026-11-08T15:15:00+00:00", "Real Sociedad San Sebastian", "Rayo Vallecano", None),
 ("sr:sport_event:72478688", "2026-11-08T17:30:00+00:00", "RC Celta de Vigo", "Levante UD", None),
 ("sr:sport_event:72478704", "2026-11-08T17:30:00+00:00", "Villarreal CF", "Getafe CF", None),
]


def events(spec: str) -> list:
    out = []
    for tok in spec.split():
        code = "YR" if tok.startswith("YR") else tok[0]
        rest = tok[len(code):]
        side_i = next(i for i, ch in enumerate(rest) if ch in "ha")
        e = {"type": TYPES[code], "time": int(rest[:side_i]), "team": "home" if rest[side_i] == "h" else "away"}
        if code == "G":
            hs, as_ = rest[side_i + 1:].split("-")
            e["home_score"], e["away_score"] = int(hs), int(as_)
        out.append(e)
    return out


def main():
    os.makedirs(RAW_SR_GAMES, exist_ok=True)
    for gid, ko, home, away, hs, as_, sh, sa, ev in GAMES:
        evs = events(ev)
        ht = [0, 0]
        for e in evs:
            if e["type"] == "score_change" and e["time"] <= 45:
                ht = [e["home_score"], e["away_score"]]
        last = [e for e in evs if e["type"] == "score_change"]
        if last:
            assert [last[-1]["home_score"], last[-1]["away_score"]] == [hs, as_], gid
        js = {"fetched_at": FETCHED, "source": "SportRadar via fetch_sports_data (game_stats)", "id": gid,
              "kickoff_utc": ko, "home": home, "away": away, "status": "final", "score": {"home": hs, "away": as_},
              "ht_score": {"home": ht[0], "away": ht[1], "derived_from": "score_change events up to minute 45"},
              "team_stats": {"home": dict(zip(KEYS, sh)), "away": dict(zip(KEYS, sa))}, "key_events": evs}
        path = os.path.join(RAW_SR_GAMES, gid.replace(":", "_") + "_FT.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False, indent=0)
    games = []
    for gid, ko, home, away, wp in UPCOMING:
        g = {"id": gid, "status": "scheduled", "start_time": ko, "home": home, "away": away}
        if wp:
            g["win_probability"] = {"home": wp[0], "draw": wp[1], "away": wp[2]}
        games.append(g)
    for gid, ko, home, away, hs, as_, *_ in GAMES:
        games.append({"id": gid, "status": "final", "start_time": ko.replace("Z", "+00:00"), "home": home,
                      "away": away, "score": [hs, as_]})
    with open(os.path.join(RAW_SPORTRADAR, "scores_2026-10-24T1050.json"), "w", encoding="utf-8") as f:
        json.dump({"fetched_at": FETCHED, "source": "SportRadar via fetch_sports_data (scores, team queries)",
                   "games": games}, f, ensure_ascii=False, indent=0)
    print(f"saved {len(GAMES)} game files and {len(games)} schedule rows")


if __name__ == "__main__":
    main()
