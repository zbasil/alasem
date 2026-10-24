# StatsBomb open data (event files)

Event data for three El Clásico matches from StatsBomb's free open-data release
(https://github.com/statsbomb/open-data), stored gzip-compressed and unchanged.

| file | match | date |
|---|---|---|
| events_69299.json.gz | Barcelona 5-0 Real Madrid | 2010-11-29 |
| events_266424.json.gz | Real Madrid 0-4 Barcelona | 2015-11-21 |
| events_267533.json.gz | Barcelona 1-2 Real Madrid | 2016-04-02 |

StatsBomb asks anyone publishing work based on this data to credit StatsBomb
as the data source. The app and the cards show "بيانات: StatsBomb".

`sb1516_goals_reds.jsonl.gz`: for each of the 1,517 matches of StatsBomb's free 2015/16 seasons
(La Liga, Premier League, Serie A, Ligue 1), the goals (minute, side, own goal), red cards and period
lengths, extracted by `scripts/sb_extract.py`. Used by `scripts/fit_inplay.py` for the goal-time
profile and the red-card effect.
