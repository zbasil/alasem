"""Central settings: config/settings.json plus the competition rules file."""

from __future__ import annotations

import json
import os
from functools import lru_cache

from .paths import CONFIG, ROOT


@lru_cache(maxsize=1)
def settings() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def rules(competition: str | None = None) -> dict:
    s = settings()
    path = s["competition"]["rules_file"]
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        r = json.load(f)
    if competition and r["id"] != competition:
        raise ValueError(f"no rules for {competition}")
    return r


def season_rules(season: int | None = None) -> dict:
    s = settings()
    season = season or s["competition"]["season"]
    return rules()["seasons"][str(season)]


def competition() -> str:
    return settings()["competition"]["id"]


def season() -> int:
    return int(settings()["competition"]["season"])


def tz() -> str:
    return settings()["timezone"]


@lru_cache(maxsize=1)
def _dotenv() -> dict:
    """KEY=value lines of the project's .env (if present); real environment variables always win."""
    out = {}
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _dotenv().get(name) or default
