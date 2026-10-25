"""Half-time / full-time live analysis for one match.

    python scripts/live_run.py --stats data/live/<id>/HT.json --phase HT --kickoff 2026-10-24T19:00:00Z
    python scripts/live_run.py --stats data/live/<id>/FT.json --phase FT --kickoff ... [--ht data/live/<id>/HT.json]

--stats is the sports-data tool's game_stats answer saved as JSON.
Writes data/live/<id>/report_<phase>.json (read by `python -m zsc export` for the app's match centre),
outputs/live/<id>_<phase>.md and .png (the chat report and card) and a row in data/predictions/live_log.csv.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.cards import render_card  # noqa: E402
from zsc.dixon_coles import fit_dixon_coles  # noqa: E402
from zsc.impact import IMPACT_SIMS, METRICS, league_impact  # noqa: E402
from zsc.inplay import InPlayModel  # noqa: E402
from zsc.live import (LiveContext, STAT_LABELS_AR, SHOWN_STATS, build_report, parse_game_stats,  # noqa: E402
                      report_markdown, save_json)
from zsc.pipeline import load_snapshot, promoted_teams, season_teams  # noqa: E402
from zsc import predlog  # noqa: E402
from zsc.config import competition  # noqa: E402
from zsc.paths import LIVE_LOG, PREMATCH_LOG  # noqa: E402
from zsc.predict import fit_track  # noqa: E402
from zsc.registry import match_id, team_id  # noqa: E402
from zsc.teams import arabic  # noqa: E402

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True)
    ap.add_argument("--phase", choices=["HT", "FT"], required=True)
    ap.add_argument("--kickoff", default="")
    ap.add_argument("--ht", default=None, help="half-time snapshot (for the second half in FT reports)")
    ap.add_argument("--event", default="")
    ap.add_argument("--sims", type=int, default=IMPACT_SIMS)
    ap.add_argument("--no-card", action="store_true")
    a = ap.parse_args()

    js = json.load(open(a.stats, encoding="utf-8"))
    snap = parse_game_stats(js, event_id=a.event)
    first = parse_game_stats(json.load(open(a.ht, encoding="utf-8"))) if a.ht else None
    event_id = a.event or snap.event_id or f"{snap.home}-{snap.away}"

    m = load_snapshot()
    reg = json.load(open(os.path.join(ROOT, "outputs", "models", "registry.json")))
    drift = float(reg["season"]["drift_sd"])
    mp = os.path.join(ROOT, "outputs", "models", "inplay.json")
    ip = InPlayModel.load(mp if os.path.exists(mp) else os.path.join(ROOT, "outputs", "inplay_model.json"))
    season = int(m["season"].max())
    teams = season_teams(m, season)
    # everything already played this season, except this match
    played = m[(m["season"] == season) & ~((m["home"] == snap.home) & (m["away"] == snap.away))]
    kickoff_day = pd.Timestamp(a.kickoff).tz_convert(None).normalize() if a.kickoff else played["date"].max() + pd.Timedelta(days=1)
    hist = m[~((m["season"] == season) & (m["home"] == snap.home) & (m["away"] == snap.away))]
    track = reg.get("displayed_track", "market")
    fit = fit_track(hist, track, kickoff_day, season)      # data strictly before the match day
    mid = match_id(competition(), season, snap.home, snap.away)
    # the pre-match forecast that was published (last pre-kick-off row of the displayed track) fixes
    # lambda, mu and rho, so minute 0 of the live forecast is exactly that forecast
    lam = mu = rho = None
    source = "refit at kick-off day"
    log = predlog.read(PREMATCH_LOG)
    if len(log):
        rows = log[(log["match_id"] == mid) & (log["track"] == track)]
        if a.kickoff:
            rows = rows[[pd.Timestamp(i) < pd.Timestamp(a.kickoff) for i in rows["issued_at"]]]
        rows = rows[rows["rho"].notna()]
        if len(rows):
            last = rows.sort_values("issued_at").iloc[-1]
            lam, mu, rho = float(last["xg_home"]), float(last["xg_away"]), float(last["rho"])
            source = f"prediction {last['prediction_id']} ({last['model_version']}, data {last['data_version']})"
    if lam is None:
        lamv, muv = fit.rates([snap.home], [snap.away])
        lam, mu, rho = float(lamv[0]), float(muv[0]), float(fit.rho)

    events = []
    from zsc.live import model_events
    events = model_events(snap)
    rh = sum(1 for e in events if e["kind"] == "red" and e["team"] == "home")
    ra = sum(1 for e in events if e["kind"] == "red" and e["team"] == "away")
    if a.phase == "HT":
        final = ip.final_score_matrix(lam, mu, 45, snap.hg, snap.ag, rh, ra, period=1, rho=rho)
    else:
        from zsc.impact import point_mass
        final = point_mass(snap.hg, snap.ag)
    impact = league_impact(fit, played, teams, snap.home, snap.away, final, n_sims=a.sims, drift_sd=drift)

    ctx = LiveContext(lam=lam, mu=mu, kickoff_utc=a.kickoff, impact=impact.to_dict("records"), rho=rho, source=source)
    rep = build_report(a.phase, snap, first, ctx, ip)
    rep["event_id"] = event_id
    rep["match_id"] = mid
    rep["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rep["impact_rows"] = [{"team": r["team"], **{f"{c}_{w}": float(r[f"{c}_{w}"]) for c, _ in METRICS for w in ("before", "now")}}
                          for r in impact.head(8).to_dict("records")]
    # the live forecast at this moment goes to the live log (never mixed with pre-match forecasts)
    minute = 45 if a.phase == "HT" else 95
    p_now = rep["now"]["p"]
    predlog.append(LIVE_LOG, pd.DataFrame([{
        "match_id": mid, "competition": competition(), "season": season, "id_source": "zsc", "external_id": event_id,
        "home_id": team_id(snap.home), "away_id": team_id(snap.away), "track": "live",
        "model_version": ip.version, "data_version": "sportradar-live", "data_fetched_at": js.get("fetched_at", ""),
        "issued_at": rep["generated_at"], "kickoff_utc": a.kickoff, "p_home": p_now[0], "p_draw": p_now[1], "p_away": p_now[2],
        "xg_home": lam, "xg_away": mu, "rho": rho, "minute": minute, "period": 1 if a.phase == "HT" else 2,
        "hg": snap.hg, "ag": snap.ag, "red_home": rh, "red_away": ra, "note": a.phase}]), kind="live")

    out_dir = os.path.join(ROOT, "data", "live", event_id.replace(":", "_"))
    os.makedirs(out_dir, exist_ok=True)
    save_json(rep, os.path.join(out_dir, f"report_{a.phase}.json"))
    impact.to_csv(os.path.join(out_dir, f"impact_{a.phase}.csv"), index=False)
    os.makedirs(os.path.join(ROOT, "outputs", "live"), exist_ok=True)
    base = os.path.join(ROOT, "outputs", "live", f"{event_id.replace(':', '_')}_{a.phase}")
    md = report_markdown(rep)
    open(base + ".md", "w", encoding="utf-8").write(md)
    if not a.no_card:
        render_card(rep, base + ".png")

    print(md)
    print()
    print("files:", base + ".md", base + ".png" if not a.no_card else "", sep="\n  ")


if __name__ == "__main__":
    main()
