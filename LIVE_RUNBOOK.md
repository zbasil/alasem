# Live run book (half-time, full-time, round close) — version 2 (valid for app v3)

Used by the scheduled check-ins in this Claude session. Project root: `/home/claude/zahraa-supercomputer`.

App (new, v2): https://claude.ai/artifact/33Js37q4BsirKiFPSsA4sx — one page `dist/web/index.html` plus its data files
`dist/web/data/...` (built from `app/` by `python scripts/build_app.py`). The old Dashboard artifact
(Y6aQg9z4MxgUrQRp5NvjRX) is retired: do not update it any more.

## Tracked matches (matchday 10)

| Match | SportRadar id | Kick-off (UTC) | Baghdad |
|---|---|---|---|
| Atlético Madrid – Deportivo | sr:sport_event:72478650 | 2026-10-24T19:00:00Z | Sat 22:00 |
| Barcelona – Real Madrid | sr:sport_event:72478654 | 2026-10-25T20:00:00Z | Sun 23:00 |

App v3 (24 Oct 2026): the same commands work. `python -m zsc export` now also copies the Premier League / Champions
League files (`outputs/multi`, built by `python -m zsc multi`) and free-source files (`outputs/free`) into every
snapshot, so nothing is lost; `build_app.py --plan` then lists them only when they changed. At round close, also refresh
EPL/UCL results (SportRadar `scores` with a team filter → `data/raw/sportradar-multi/*.csv`, then `python -m zsc multi`).

Live folder of a match: `data/live/sr_sport_event_<number>/` (HT.json, FT.json, report_HT.json, report_FT.json).

Scheduled check-ins (send_later into this session):
`trig_01ByXm5hZfoWUs8sgzg6wRTH` Atlético HT 19:49Z · `trig_01WvZVRYPLrdaEB7DEQ1FtEf` Atlético FT 20:56Z ·
`trig_01ViW8xTuqiyB5fayiwD5Awx` Clásico HT 25 Oct 20:49Z · `trig_01R5xJQ52sVr64YamVNFprVf` Clásico FT 21:56Z ·
`trig_01KrUNpz6QDxFgHgTcJ17tGX` round close 26 Oct 22:05Z.

Canonical team names for `data/raw/manual/results_2026_27.csv` (SportRadar name → name to write):
Atletico Madrid → Ath Madrid · Deportivo La Coruna → La Coruna · Rayo Vallecano → Vallecano · Elche CF → Elche ·
Racing Santander → Santander · Espanyol Barcelona → Espanol · Valencia CF → Valencia · Villarreal CF → Villarreal ·
Athletic Bilbao → Ath Bilbao · Getafe CF → Getafe · Celta Vigo → Celta · Real Betis → Betis · Real Sociedad → Sociedad ·
Levante UD → Levante · FC Barcelona → Barcelona · Real Madrid → Real Madrid · Sevilla FC → Sevilla · CA Osasuna → Osasuna ·
Deportivo Alaves → Alaves · Malaga CF → Malaga. (When unsure: `python -c "from zsc.teams import canonical; print(canonical('<name>'))"`.)

## Half-time (phase HT)

1. `fetch_sports_data` scores, league `la_liga`, team = home team. Find the event.
   * First half still running → `send_later` the same message 3 minutes later and stop.
   * Second half already under way (HT stats would be mixed with the second half) → skip HT, say nothing; FT still runs.
2. `fetch_sports_data` game_stats with the event id.
3. Write the normalised JSON to `data/live/sr_sport_event_<n>/HT.json`:
   `{"fetched_at", "source": "SportRadar via fetch_sports_data (game_stats)", "id", "home", "away", "status",
     "score": {"home", "away"}, "team_stats": {"home": {...}, "away": {...}},
     "key_events": [{"type", "time", "team", "home_score"?, "away_score"?}]}`
   Team names as SportRadar gives them; keep every stat key the tool returns and leave out (never invent or zero) any it
   does not return; key events: score_change, yellow_card, red_card, yellow_red_card, substitution with minute and side.
4. `python scripts/live_run.py --stats data/live/sr_sport_event_<n>/HT.json --phase HT --kickoff <kick-off ISO> --event <id>`
   (it takes lambda, mu and rho from the last pre-kick-off forecast in `data/predictions/prematch_log.csv`, so minute 0 of
   the live forecast is exactly the published forecast; it appends the live forecast to `data/predictions/live_log.csv`).
5. App: `python -m zsc export` → `python scripts/build_app.py --plan` → Artifact publish with
   `file_path` = `dist/web/index.html` (no `url` needed in this session; from another session use the app URL) and
   `files` = the plan's `files` map (only the changed data files) → `python scripts/build_app.py --record`.
6. Tell Zahraa: SendUserMessage with `outputs/live/sr_sport_event_<n>_HT.md` (Arabic, as is) plus one line that the app's
   match centre is updated; SendUserFile the `.png` card (status proactive); PushNotification (one Arabic line).

## Full-time (phase FT)

1. scores: not finished yet → `send_later` 4 minutes later and stop.
2. game_stats → `data/live/sr_sport_event_<n>/FT.json` (same shape) and a copy at
   `data/raw/sportradar/games/sr_sport_event_<n>_FT.json` (the data build reads shots on target and half-time from it).
3. `python scripts/live_run.py --stats data/live/sr_sport_event_<n>/FT.json --phase FT --kickoff <ISO> --event <id> --ht data/live/sr_sport_event_<n>/HT.json`
   (drop `--ht` if HT.json does not exist).
4. Results: append every La Liga match that has finished since the last update to `data/raw/manual/results_2026_27.csv`
   (`date` = match day in Spain, canonical names from the table above, `hg`, `ag`, `source` = "SportRadar final (...)",
   quoted). Save the scores answer as `data/raw/sportradar/scores_<YYYY-MM-DDTHHMM>.json`:
   `{"fetched_at", "source": "SportRadar via fetch_sports_data (scores)", "games": [{"id", "status", "start_time", "home",
   "away", "score": [h, a] if finished, "win_probability": {"home", "draw", "away"} if given}]}`.
   Also save game_stats of the other finished matches to `data/raw/sportradar/games/` when convenient (fills shots on target).
5. `python -m zsc update --offline` (rebuilds the standard data with its 45 checks, then the app data; it also logs the
   pre-match forecasts of every match kicking off in the next 10 days, both tracks plus SportRadar; never after kick-off).
   If the data build fails its checks, the previous data stay in place: read the error, fix the input row, run again.
6. App: as HT step 5 (`build_app.py --plan` → publish the changed files → `--record`).
7. Tell Zahraa as in HT step 6, adding what the result means for the season (the report's impact lines) and, once
   matches are scored, the track-record line from `app/data/accuracy.json` → `live_record`.

## Round close (no live report)

Full-time steps 4–6 for the last match of the round, then a short Arabic scorecard with SendUserMessage: how often
each source picked the right outcome on the same matches, RPS of each, the biggest surprise. No push notification.

## Never

* No push notification between 00:30 and 08:00 Baghdad unless it is the end of a match she is watching
  (the Clásico full-time just before 1 a.m. is fine; the Monday round close is not).
* Never type a number into the page by hand: every figure comes from the data files.
* Never log a pre-match prediction after kick-off (the log refuses it anyway).
* Never present the HT impact as "if the score stays": it is the model's distribution of final scores.
* A statistic SportRadar does not send stays missing, never 0.
