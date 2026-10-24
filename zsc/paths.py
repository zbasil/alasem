"""Every file location in one place (all relative to the project root).

    data/raw/<source>/        files exactly as fetched, never edited (each folder has _source.json)
    data/standard/            unified tables rebuilt from raw by `python -m zsc data`
    data/model_inputs/        the exact training table of each data version (for reproducing a forecast)
    data/predictions/         append-only prediction logs
    data/live/                live match state written by the live runs
    outputs/                  fitted models, evaluation tables, cards
    app/                      the web app (app/data holds the current data snapshot)
    snapshots/                previous app data snapshots (backup / restore)
    reports/                  evaluation and test reports
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def p(*parts: str) -> str:
    return os.path.join(ROOT, *parts)


CONFIG = p("config", "settings.json")
RAW = p("data", "raw")
RAW_HISTORY = p("data", "raw", "football-data-mirror")
RAW_ODDS = p("data", "raw", "xgabora", "laliga_bet365_odds.csv")
RAW_OPENFOOTBALL = p("data", "raw", "openfootball", "es1_2026-27.json")
RAW_MANUAL = p("data", "raw", "manual", "results_2026_27.csv")
RAW_FD_EXTRACT = p("data", "raw", "football-data", "sp1_2026-27_extract.csv")
RAW_BETEXPLORER = p("data", "raw", "betexplorer", "results_2026_27.csv")
RAW_OFFICIAL_TABLE = p("data", "raw", "laliga", "official_table_2026-10-21.csv")
RAW_UPCOMING_FWP = p("data", "raw", "footballwebpages", "upcoming_fixtures_md10.csv")
RAW_SPORTRADAR = p("data", "raw", "sportradar")
RAW_SR_GAMES = p("data", "raw", "sportradar", "games")
RAW_STATSBOMB = p("data", "raw", "statsbomb")
SB_EXTRACT = p("data", "raw", "statsbomb", "sb1516_goals_reds.jsonl.gz")
STANDARD = p("data", "standard")
CURRENT_SEASON_TABLE = p("data", "standard", "season_2026_27.csv")
MATCHES = p("data", "standard", "matches.csv")
FIXTURES = p("data", "standard", "fixtures_2026_27.csv")
TEAMS = p("data", "standard", "teams.csv")
EXTERNAL_IDS = p("data", "standard", "external_ids.csv")
TEAM_STATS = p("data", "standard", "team_match_stats.csv")
CORRECTIONS = p("data", "standard", "corrections.csv")
MANIFEST = p("data", "standard", "manifest.json")
STATUS = p("data", "status.json")
MODEL_INPUTS = p("data", "model_inputs")
PREDICTIONS = p("data", "predictions")
PREMATCH_LOG = p("data", "predictions", "prematch_log.csv")
LIVE_LOG = p("data", "predictions", "live_log.csv")
LIVE = p("data", "live")
OUTPUTS = p("outputs")
MODELS = p("outputs", "models")
REGISTRY = p("outputs", "models", "registry.json")
APP = p("app")
APP_DATA = p("app", "data")
SNAPSHOTS = p("snapshots")
REPORTS = p("reports")
USERDATA = p("data", "userdata")          # audience challenge, saved stories (local server)
