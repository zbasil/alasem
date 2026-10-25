"""One-off: convert the version-1 prediction log (keyed by team names) to the version-2 log.

    python scripts/migrate_log_v1.py
The original file is kept unchanged in data/predictions/archive/log_v1.csv.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import RAW_SPORTRADAR  # noqa: E402

from zsc import predlog  # noqa: E402
from zsc.registry import match_id, team_id  # noqa: E402
from zsc.teams import canonical  # noqa: E402


def main():
    src = os.path.join(ROOT, "data", "predictions", "log.csv")
    arch = os.path.join(ROOT, "data", "predictions", "archive", "log_v1.csv")
    if not os.path.exists(arch):
        shutil.copy(src, arch)
    v1 = pd.read_csv(arch)
    sr = json.load(open(os.path.join(RAW_SPORTRADAR, "scores_2026-10-24T0838.json"), encoding="utf-8"))
    ext = {(canonical(g["home"]), canonical(g["away"])): g["id"] for g in sr["games"]}
    rows = []
    for r in v1.itertuples():
        mid = match_id("ESP1", 2026, r.home, r.away)
        track = "market" if r.source == "model" else "sportradar"
        rows.append({
            "match_id": mid, "competition": "ESP1", "season": 2026, "id_source": "zsc",
            "external_id": ext.get((r.home, r.away), ""), "home_id": team_id(r.home), "away_id": team_id(r.away),
            "track": track,
            "model_version": "prematch-market-1.0" if track == "market" else "sportradar-published",
            "config_hash": "", "data_version": "v1-2026-10-24", "data_fetched_at": sr["fetched_at"],
            "issued_at": r.logged_at, "kickoff_utc": r.kickoff_utc,
            "p_home": r.p_home, "p_draw": r.p_draw, "p_away": r.p_away,
            "xg_home": getattr(r, "xg_home", float("nan")), "xg_away": getattr(r, "xg_away", float("nan")),
            "note": "migrated from log v1",
        })
    df = pd.DataFrame(rows)
    out = os.path.join(ROOT, "data", "predictions", "prematch_log.csv")
    written = predlog.append(out, df, kind="prematch")
    print(f"migrated {len(written)} of {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
