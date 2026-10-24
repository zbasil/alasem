"""Data layer: raw -> standard -> model inputs, with provenance and checks.

    fetch_all()   download sources into data/raw/<source>/ (retries, caching, never overwrites a good
                  file with a failed download; every file gets _source.json with url, time, sha256)
    build()       rebuild data/standard/ from data/raw only (offline, reproducible):
                    matches.csv          every played league match since 1993/94 with a stable match_id,
                                         goals, half-time goals, shots on target, Bet365 odds, and the
                                         source of each part
                    fixtures_2026_27.csv the full current-season schedule with kick-off (UTC + source),
                                         status (played / scheduled / postponed / abandoned) and ids
                    team_match_stats.csv per-team match stats from SportRadar game files (possession,
                                         shots, corners, cards ...), unknown values left empty
                    teams.csv, external_ids.csv, manifest.json (coverage + every check)
                  The build writes into a temporary folder and only replaces data/standard when every
                  check passes, so a bad source can never replace the last good data.
    model_table() the exact training table (with market-implied goals) of the current data version,
                  saved once per version in data/model_inputs/ so any forecast can be reproduced.

Unknown values stay empty (NaN): a missing shot count is never a zero.
"""

from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import shutil
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config
from .data import COLUMNS, attach_odds, load_history, standardise_football_data
from .paths import (MANIFEST, MODEL_INPUTS, RAW, RAW_BETEXPLORER, RAW_FD_EXTRACT, RAW_HISTORY, RAW_MANUAL,
                    RAW_ODDS, RAW_OFFICIAL_TABLE, RAW_OPENFOOTBALL, RAW_SR_GAMES, RAW_SPORTRADAR, STANDARD, STATUS)
from .registry import match_id, team_id, team_record, TEAMS
from .standings import compute_table
from .teams import canonical

SOURCE_LABELS = {
    "fd_mirror": "football-data.co.uk (GitHub mirror datasets/football-datasets)",
    "xgabora": "football-data.co.uk Bet365 odds + shots via xgabora/Club-Football-Match-Data",
    "openfootball": "openfootball/football.json",
    "manual": "results read from two public pages (data/raw/manual)",
    "football_data": "football-data.co.uk SP1 2026/27",
    "sportradar": "SportRadar (through Claude's sports-data tool)",
}
APPLIED_CORRECTIONS: list = []
STAT_COLS = ["possession", "shots_total", "shots_on_target", "shots_off_target", "shots_blocked", "corners",
             "fouls", "offsides", "yellow", "red", "saves"]
SR_STAT_KEYS = {"possession": "ball_possession", "shots_total": "shots_total", "shots_on_target": "shots_on_target",
                "shots_off_target": "shots_off_target", "shots_blocked": "shots_blocked", "corners": "corner_kicks",
                "fouls": "fouls", "offsides": "offsides", "yellow": "yellow_cards", "red": "red_cards",
                "saves": "shots_saved"}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


# --------------------------------------------------------------------------
# fetching (used by `python -m zsc update`; the build itself is offline)
# --------------------------------------------------------------------------

def _meta_path(path: str) -> str:
    return os.path.join(os.path.dirname(path), "_source.json")


def write_source_meta(path: str, url: str, extra: dict | None = None) -> None:
    mp = _meta_path(path)
    meta = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    name = os.path.basename(path)
    meta[name] = {"url": url, "fetched_at": now_utc(), "sha256": sha256_file(path),
                  "bytes": os.path.getsize(path), **(extra or {})}
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)


def fetch(url: str, dest: str, retries: int | None = None, timeout: int | None = None,
          min_age_minutes: float | None = None, log=print) -> dict:
    """Download url to dest with retries and exponential backoff.

    Cached: if dest was fetched less than min_age_minutes ago nothing is downloaded.
    Safe: the old file is only replaced after a complete, non-empty download.
    Returns {"status": "fresh" | "cached" | "unchanged" | "failed", ...}."""
    up = config.settings()["update"]
    retries = retries or up["retries"]
    timeout = timeout or up["timeout_seconds"]
    min_age = up["cache_minutes"] if min_age_minutes is None else min_age_minutes
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    meta_p = _meta_path(dest)
    meta = json.load(open(meta_p, encoding="utf-8")).get(os.path.basename(dest), {}) if os.path.exists(meta_p) else {}
    if os.path.exists(dest) and meta.get("fetched_at") and min_age > 0:
        age = (pd.Timestamp.now("UTC") - pd.Timestamp(meta["fetched_at"])).total_seconds() / 60
        if age < min_age:
            return {"status": "cached", "age_minutes": round(age, 1), "path": dest}
    err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Zahraa Football Supercomputer)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if not body:
                raise IOError("empty response")
            if os.path.exists(dest) and sha256_bytes(body) == sha256_file(dest):
                write_source_meta(dest, url, {"note": "unchanged"})
                return {"status": "unchanged", "path": dest}
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                f.write(body)
            os.replace(tmp, dest)
            write_source_meta(dest, url)
            return {"status": "fresh", "path": dest, "bytes": len(body)}
        except Exception as e:  # network errors, timeouts, HTTP errors
            err = e
            log(f"  fetch {url} attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(up["backoff_seconds"] * (2 ** attempt))
    return {"status": "failed", "error": str(err), "path": dest, "kept_previous": os.path.exists(dest)}


def fetch_all(log=print) -> dict:
    s = config.settings()["sources"]
    res = {"openfootball": fetch(s["openfootball"]["url"], RAW_OPENFOOTBALL, log=log),
           "football_data": fetch(s["football_data"]["url"],
                                  os.path.join(RAW, "football-data", "SP1_2627.csv"), log=log)}
    return res


# --------------------------------------------------------------------------
# reading raw sources
# --------------------------------------------------------------------------

def _openfootball() -> pd.DataFrame:
    js = json.load(open(RAW_OPENFOOTBALL, encoding="utf-8"))
    rows = []
    for mt in js["matches"]:
        sc = mt.get("score") or {}
        # two formats: {"ft": [h, a], "ht": [h, a]} or a bare [h, a] (full time only)
        ft = sc.get("ft") if isinstance(sc, dict) else (sc if isinstance(sc, list) and len(sc) == 2 else None)
        ht = sc.get("ht") if isinstance(sc, dict) else None
        if ht is None and ft is not None and list(ft) == [0, 0]:
            ht = [0, 0]                       # 0-0 at full time means 0-0 at half-time
        rows.append({"matchday": int(str(mt.get("round", "0")).split()[-1]), "date": mt["date"],
                     "time_local": mt.get("time") or "", "home": canonical(mt["team1"]), "away": canonical(mt["team2"]),
                     "hg": ft[0] if ft else np.nan, "ag": ft[1] if ft else np.nan,
                     "hthg": ht[0] if ht else np.nan, "htag": ht[1] if ht else np.nan})
    return pd.DataFrame(rows)


def _sportradar_games() -> dict:
    """(home, away) -> saved game_stats answer (normalised form), latest phase file wins (FT > HT)."""
    out = {}
    for path in sorted(glob.glob(os.path.join(RAW_SR_GAMES, "*.json"))):
        js = json.load(open(path, encoding="utf-8"))
        if "team_stats" not in js or "home" not in js:
            continue
        status = str(js.get("status", "")).lower()
        if status not in ("final", "closed", "ended", "complete", "ft"):
            continue
        key = (canonical(js["home"]), canonical(js["away"]))
        out[key] = {"path": path, **js}
    return out


def _sportradar_schedule() -> pd.DataFrame:
    """Every game seen in saved 'scores' answers (newest file wins): id, kick-off (UTC), status."""
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW_SPORTRADAR, "scores_*.json"))):
        js = json.load(open(path, encoding="utf-8"))
        for g in js.get("games", []):
            rows.append({"sr_id": g["id"], "home": canonical(g["home"]), "away": canonical(g["away"]),
                         "kickoff_utc": pd.Timestamp(g["start_time"]).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "sr_status": g.get("status", ""), "seen_at": js.get("fetched_at", ""),
                         "sr_p_home": (g.get("win_probability") or {}).get("home", np.nan),
                         "sr_p_draw": (g.get("win_probability") or {}).get("draw", np.nan),
                         "sr_p_away": (g.get("win_probability") or {}).get("away", np.nan)})
    if not rows:
        return pd.DataFrame(columns=["sr_id", "home", "away", "kickoff_utc", "sr_status", "seen_at"])
    df = pd.DataFrame(rows).sort_values("seen_at")
    return df.groupby(["home", "away"], as_index=False).last()


def _betexplorer() -> pd.DataFrame:
    b = pd.read_csv(RAW_BETEXPLORER)
    b["home"] = b["home"].map(canonical)
    b["away"] = b["away"].map(canonical)
    return b


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def _current_season(season: int, problems: list, warnings: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Played matches and the full schedule of the current season."""
    src_cfg = config.settings()["sources"]
    of = _openfootball()
    trusted = src_cfg["openfootball"]["trusted_results_until"]
    of_res = of[of["hg"].notna() & (of["date"] <= trusted)].copy()
    of_res["result_source"] = "openfootball"
    manual = pd.read_csv(RAW_MANUAL)
    manual["home"], manual["away"] = manual["home"].map(canonical), manual["away"].map(canonical)
    manual["result_source"] = "manual: " + manual["source"].astype(str)
    cur = pd.concat([of_res[["date", "home", "away", "hg", "ag", "hthg", "htag", "result_source"]],
                     manual[["date", "home", "away", "hg", "ag", "result_source"]]], ignore_index=True)
    dup = cur.duplicated(["home", "away"], keep=False)
    if dup.any():
        problems.append("result listed twice: " + cur.loc[dup, ["date", "home", "away"]].to_string())
    cur["date"] = pd.to_datetime(cur["date"])
    cur["season"] = season
    for c in COLUMNS:
        if c not in cur:
            cur[c] = np.nan
    cur["hg"], cur["ag"] = cur["hg"].astype(int), cur["ag"].astype(int)
    rs = cur["result_source"].values
    ht_from_of = cur["hthg"].notna().values
    # odds, shots on target, half-time from football-data.co.uk (extract; full file if the updater fetched one)
    # settled extract first (two reads agreed; a third read settled 3 over/under pairs), then the two
    # pieces of the first full read for the matches the extract does not cover
    pieces = sorted(glob.glob(os.path.join(os.path.dirname(RAW_FD_EXTRACT), "fetch_pieces", "fetch[0-9A]*.csv")))
    fd_frames = [standardise_football_data(pd.read_csv(RAW_FD_EXTRACT), season)] + \
        [standardise_football_data(pd.read_csv(pth), season) for pth in pieces if "fetchB" not in pth]
    full_fd = os.path.join(RAW, "football-data", "SP1_2627.csv")
    if os.path.exists(full_fd):
        try:
            fd_frames.append(standardise_football_data(pd.read_csv(full_fd), season))
        except Exception as e:
            warnings.append(f"football-data SP1_2627.csv unreadable, extract used instead: {e}")
    fd = pd.concat(fd_frames, ignore_index=True)
    if len(fd_frames) > 1 + len(pieces) - sum("fetchB" in pth for pth in pieces):
        fd = pd.concat([fd_frames[-1], fd], ignore_index=True)        # a freshly fetched full file wins
    fd = fd.drop_duplicates(["home", "away"], keep="first")
    try:
        cur = attach_odds(cur[COLUMNS], fd)
    except ValueError as e:
        problems.append(f"score conflict with football-data.co.uk: {e}")
        cur = cur[COLUMNS]
    cur["result_source"] = rs
    # documented corrections of misread raw values (data/raw/football-data/corrections.csv)
    corr_p = os.path.join(os.path.dirname(RAW_FD_EXTRACT), "corrections.csv")
    if os.path.exists(corr_p):
        for c in pd.read_csv(corr_p).itertuples():
            sel = (cur["date"] == pd.Timestamp(c.date)) & (cur["home"] == canonical(c.home)) & (cur["away"] == canonical(c.away))
            if sel.sum() != 1:
                problems.append(f"correction does not match exactly one match: {c.date} {c.home} v {c.away}")
                continue
            cur.loc[sel, c.field] = float(c.value)
            APPLIED_CORRECTIONS.append({"date": c.date, "home": canonical(c.home), "away": canonical(c.away),
                                        "field": c.field, "value": c.value, "reason": c.reason})
    has_fd = cur.set_index(["home", "away"]).index.isin(fd.set_index(["home", "away"]).index)
    cur["odds_source"] = np.where(cur["odds_h"].notna(), "football_data", "")
    cur["stats_source"] = np.where(cur["hst"].notna(), "football_data", "")
    cur["ht_source"] = np.where(ht_from_of, "openfootball", np.where(cur["hthg"].notna() & has_fd, "football_data", ""))
    # shots on target / half-time from SportRadar game files where still missing
    sr = _sportradar_games()
    for i, r in cur.iterrows():
        g = sr.get((r["home"], r["away"]))
        if g is None:
            continue
        hs, as_ = g["team_stats"]["home"], g["team_stats"]["away"]
        if (int(g["score"]["home"]), int(g["score"]["away"])) != (r["hg"], r["ag"]):
            problems.append(f"SportRadar score differs for {r['home']} v {r['away']}: "
                            f"{g['score']} vs {r['hg']}-{r['ag']}")
            continue
        if pd.isna(r["hst"]) and hs.get("shots_on_target") is not None and as_.get("shots_on_target") is not None:
            cur.at[i, "hst"], cur.at[i, "ast"] = float(hs["shots_on_target"]), float(as_["shots_on_target"])
            cur.at[i, "stats_source"] = "sportradar"
        if pd.isna(r["hthg"]):
            ht = g.get("ht_score")
            if not ht and g.get("key_events"):
                hs_, as2 = 0, 0                       # running score after the last goal up to minute 45
                for e in g["key_events"]:
                    if e.get("type") == "score_change" and int(e.get("time") or 99) <= 45 and "home_score" in e:
                        hs_, as2 = int(e["home_score"]), int(e["away_score"])
                ht = {"home": hs_, "away": as2}
            if ht:
                cur.at[i, "hthg"], cur.at[i, "htag"] = ht["home"], ht["away"]
                cur.at[i, "ht_source"] = "sportradar"
    # schedule
    sched = of[["matchday", "date", "time_local", "home", "away"]].copy()
    tzl = config.settings()["competition"]["local_timezone"]

    def local_to_utc(d, t):
        if not t:
            return ""
        return pd.Timestamp(f"{d} {t}").tz_localize(tzl).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")

    sched["kickoff_utc"] = [local_to_utc(d, t) for d, t in zip(sched["date"], sched["time_local"])]
    sched["kickoff_source"] = np.where(sched["kickoff_utc"] != "", "openfootball", "")
    srs = _sportradar_schedule()
    if len(srs):
        sched = sched.merge(srs[["home", "away", "sr_id", "kickoff_utc", "sr_status"]].rename(
            columns={"kickoff_utc": "sr_kickoff"}), on=["home", "away"], how="left")
        use = sched["sr_kickoff"].notna() & (sched["sr_kickoff"] != "")
        sched.loc[use, "kickoff_utc"] = sched.loc[use, "sr_kickoff"]
        sched.loc[use, "kickoff_source"] = "sportradar"
        sched = sched.drop(columns=["sr_kickoff"])
    else:
        sched["sr_id"], sched["sr_status"] = np.nan, ""
    played_keys = set(zip(cur["home"], cur["away"]))
    be = _betexplorer()
    abandoned = set(zip(be.loc[be["score"].astype(str).str.contains("ABN"), "home"],
                        be.loc[be["score"].astype(str).str.contains("ABN"), "away"]))
    today = pd.Timestamp.now("UTC")
    status = []
    for r in sched.itertuples():
        if (r.home, r.away) in played_keys:
            status.append("played")
        elif (r.home, r.away) in abandoned:
            status.append("abandoned")
        elif r.kickoff_utc and pd.Timestamp(r.kickoff_utc) < today - pd.Timedelta(hours=3):
            status.append("result_pending")
        else:
            status.append("scheduled")
    sched["status"] = status
    # results date wins for played matches (openfootball dates can be the original, not the actual, date)
    rd = dict(zip(zip(cur["home"], cur["away"]), cur["date"].dt.strftime("%Y-%m-%d")))
    sched["played_date"] = [rd.get((h, a), "") for h, a in zip(sched["home"], sched["away"])]
    return cur, sched


def build(log=print) -> dict:
    """Rebuild data/standard from data/raw. Returns the manifest; raises if a check fails
    (the previous data/standard is then left untouched)."""
    cfg = config.settings()
    comp, season = cfg["competition"]["id"], int(cfg["competition"]["season"])
    problems, warnings = [], []
    APPLIED_CORRECTIONS.clear()
    t0 = time.time()

    hist = load_history(RAW_HISTORY, first_season=1993)
    odds = pd.read_csv(RAW_ODDS, parse_dates=["date"])
    try:
        hist = attach_odds(hist, odds)
    except ValueError as e:
        problems.append(f"history: score conflict between the two football-data copies: {e}")
    hist = hist[hist["season"] < season]
    hist["result_source"] = "fd_mirror"
    hist["odds_source"] = np.where(hist["odds_h"].notna(), "xgabora", "")
    hist["stats_source"] = np.where(hist["hst"].notna(), "xgabora", "")
    hist["ht_source"] = np.where(hist["hthg"].notna(), "fd_mirror", "")

    cur, sched = _current_season(season, problems, warnings)
    allm = pd.concat([hist, cur], ignore_index=True).sort_values(["date", "home"]).reset_index(drop=True)
    unknown = sorted((set(allm["home"]) | set(allm["away"])) - set(TEAMS))
    if unknown:
        problems.append(f"teams without an id: {unknown}")
        raise RuntimeError("; ".join(problems))
    allm.insert(0, "match_id", [match_id(comp, s, h, a) for s, h, a in zip(allm["season"], allm["home"], allm["away"])])
    allm.insert(1, "competition", comp)
    allm["home_id"] = allm["home"].map(team_id)
    allm["away_id"] = allm["away"].map(team_id)
    sched.insert(0, "match_id", [match_id(comp, season, h, a) for h, a in zip(sched["home"], sched["away"])])

    # ---- checks -------------------------------------------------------------
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            problems.append(f"{name}: {detail}")

    dup = allm["match_id"].duplicated(keep=False)
    check("no duplicate matches", not dup.any(), allm.loc[dup, "match_id"].tolist()[:10])
    check("no team plays itself", not (allm["home"] == allm["away"]).any())
    bad_goals = (allm[["hg", "ag"]] < 0).any(axis=1) | (allm[["hg", "ag"]] > 15).any(axis=1)
    check("goals between 0 and 15", not bad_goals.any(), allm.loc[bad_goals, "match_id"].tolist()[:10])
    ht = allm["hthg"].notna() & allm["htag"].notna()
    bad_ht = ht & ((allm["hthg"] > allm["hg"]) | (allm["htag"] > allm["ag"]))
    check("half-time goals never above full-time goals", not bad_ht.any(), allm.loc[bad_ht, "match_id"].tolist()[:10])
    sot = allm["hst"].notna()
    bad_sot = sot & ((allm["hst"] < 0) | (allm["ast"] < 0) | (allm["hst"] > 40) | (allm["ast"] > 40))
    check("shots on target between 0 and 40", not bad_sot.any(), allm.loc[bad_sot, "match_id"].tolist()[:10])
    oc = allm["odds_h"].notna()
    bad_odds = oc & ((allm[["odds_h", "odds_d", "odds_a"]] <= 1.0).any(axis=1))
    check("decimal odds above 1", not bad_odds.any(), allm.loc[bad_odds, "match_id"].tolist()[:10])
    margin = 1 / allm.loc[oc, "odds_h"] + 1 / allm.loc[oc, "odds_d"] + 1 / allm.loc[oc, "odds_a"]
    check("bookmaker margin between 0% and 25%", bool(((margin > 1.0) & (margin < 1.25)).all()),
          f"min {margin.min():.3f} max {margin.max():.3f}")
    ou = allm["odds_o25"].notna() & allm["odds_u25"].notna()
    ou_margin = 1 / allm.loc[ou, "odds_o25"] + 1 / allm.loc[ou, "odds_u25"]
    bad_ou = ou_margin[(ou_margin <= 1.0) | (ou_margin >= 1.2)]
    for i in bad_ou.index:                      # impossible pair: unknown, not a guess
        r = allm.loc[i]
        APPLIED_CORRECTIONS.append({"date": r["date"].strftime("%Y-%m-%d"), "home": r["home"], "away": r["away"],
                                    "field": "odds_o25+odds_u25",
                                    "value": f"blank (was {r['odds_o25']}/{r['odds_u25']})",
                                    "reason": "impossible over/under margin in the raw source; treated as unknown"})
        allm.loc[i, ["odds_o25", "odds_u25"]] = np.nan
    if len(bad_ou):
        warnings.append(f"{len(bad_ou)} over/under pairs with an impossible margin were set to unknown")
    high = int((margin > 1.15).sum())
    if high:
        warnings.append(f"{high} matches with a bookmaker margin above 15% (older seasons); kept, margin removed")
    for s_, g in allm.groupby("season"):
        n = len(set(g["home"]) | set(g["away"]))
        if s_ < season:
            check(f"season {s_}: complete double round robin", len(g) == n * (n - 1), f"{len(g)} matches, {n} teams")
    curm = allm[allm["season"] == season]
    check("current season: 20 teams", len(set(curm["home"]) | set(curm["away"])) == 20)
    check("current season: every played match is in the schedule",
          set(curm["match_id"]) <= set(sched["match_id"]), sorted(set(curm["match_id"]) - set(sched["match_id"]))[:5])
    check("schedule: 380 fixtures, each pair once", len(sched) == 380 and not sched["match_id"].duplicated().any())
    off = pd.read_csv(RAW_OFFICIAL_TABLE)
    off["team"] = off["team"].map(canonical)
    asof = os.path.basename(RAW_OFFICIAL_TABLE).split("_")[-1].replace(".csv", "")
    mine = compute_table(curm[curm["date"] <= asof]).set_index("team")
    diffs = []
    for _, r in off.iterrows():
        got = mine.loc[r["team"], ["P", "W", "D", "L", "GF", "GA", "Pts"]].tolist()
        exp = [r["P"], r["W"], r["D"], r["L"], r["GF"], r["GA"], r["Pts"]]
        if got != exp:
            diffs.append((r["team"], got, exp))
    check(f"results reproduce the official table of {asof}", not diffs, diffs[:3])
    be = _betexplorer()
    be = be[~be["score"].astype(str).str.contains("ABN")]
    be_sc = {(h, a): s for h, a, s in zip(be["home"], be["away"], be["score"])}
    mism = [(h, a, f"{x}-{y}", be_sc[(h, a)]) for h, a, x, y in zip(curm["home"], curm["away"], curm["hg"], curm["ag"])
            if (h, a) in be_sc and be_sc[(h, a)].replace(":", "-") != f"{x}-{y}"]
    check("current results agree with betexplorer's list", not mism, mism[:3])

    # ---- coverage (explicit gaps) -----------------------------------------------
    cov = []
    for s_, g in allm.groupby("season"):
        cov.append({"season": int(s_), "matches": int(len(g)), "with_odds": int(g["odds_h"].notna().sum()),
                    "with_shots_on_target": int(g["hst"].notna().sum()), "with_half_time": int(g["hthg"].notna().sum())})
    gaps = curm[curm["odds_h"].isna() | curm["hst"].isna() | curm["hthg"].isna()]
    gap_rows = [{"match_id": r.match_id, "date": r.date.strftime("%Y-%m-%d"), "home": r.home, "away": r.away,
                 "missing": [n for n, v in (("odds", r.odds_h), ("shots_on_target", r.hst), ("half_time", r.hthg))
                             if pd.isna(v)]} for r in gaps.itertuples()]

    if problems:
        _write_status({"last_build_attempt": now_utc(), "last_build_ok": False, "problems": problems})
        raise RuntimeError("data checks failed (previous data kept):\n- " + "\n- ".join(map(str, problems)))

    # ---- write atomically ------------------------------------------------------------
    tmp = STANDARD + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    cols = ["match_id", "competition", "season", "date", "home_id", "away_id", "home", "away", "hg", "ag", "hthg", "htag",
            "hst", "ast", "odds_h", "odds_d", "odds_a", "odds_o25", "odds_u25", "result_source", "ht_source",
            "stats_source", "odds_source"]
    allm[cols].to_csv(os.path.join(tmp, "matches.csv"), index=False)
    sched.to_csv(os.path.join(tmp, "fixtures_2026_27.csv"), index=False)
    pd.DataFrame([team_record(t) for t in sorted(TEAMS)]).assign(kit=lambda d: d["kit"].map(lambda k: "|".join(k))) \
        .to_csv(os.path.join(tmp, "teams.csv"), index=False)
    ext = sched[sched["sr_id"].notna()][["match_id", "sr_id"]].rename(columns={"sr_id": "external_id"})
    ext.insert(1, "source", "sportradar")
    ext.to_csv(os.path.join(tmp, "external_ids.csv"), index=False)
    team_stats_table().to_csv(os.path.join(tmp, "team_match_stats.csv"), index=False)
    pd.DataFrame(APPLIED_CORRECTIONS, columns=["date", "home", "away", "field", "value", "reason"]) \
        .to_csv(os.path.join(tmp, "corrections.csv"), index=False)
    fp = fingerprint(allm)
    manifest = {"built_at": now_utc(), "data_version": fp, "competition": comp, "season": season,
                "matches": int(len(allm)), "current_season_played": int(len(curm)),
                "fixtures": int(len(sched)), "fixture_status": sched["status"].value_counts().to_dict(),
                "coverage_by_season": cov, "current_season_gaps": gap_rows, "checks": checks, "warnings": warnings,
                "corrections": list(APPLIED_CORRECTIONS),
                "sources": {k: v for k, v in SOURCE_LABELS.items()},
                "raw_files": _raw_inventory(), "build_seconds": round(time.time() - t0, 1)}
    with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False, default=str)
    if os.path.isdir(STANDARD):
        backup = os.path.join(os.path.dirname(STANDARD), "backups", "standard-" + now_utc().replace(":", ""))
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        shutil.move(STANDARD, backup)
        _prune(os.path.dirname(backup), "standard-", keep=5)
    os.replace(tmp, STANDARD)
    _write_status({"last_build_attempt": manifest["built_at"], "last_build_ok": True,
                   "last_good_build": manifest["built_at"], "data_version": fp, "problems": []})
    log(f"standard data built: {len(allm)} matches, {len(curm)} this season, {len(gap_rows)} with gaps, "
        f"version {fp} ({manifest['build_seconds']}s)")
    return manifest


def team_stats_table() -> pd.DataFrame:
    rows = []
    for (h, a), g in _sportradar_games().items():
        for side, team, opp in (("home", h, a), ("away", a, h)):
            st = g["team_stats"][side]
            row = {"match_id": match_id(config.competition(), config.season(), h, a), "team_id": team_id(team),
                   "side": side, "source": "sportradar", "file": os.path.basename(g["path"])}
            for k, sk in SR_STAT_KEYS.items():
                v = st.get(sk)
                row[k] = float(v) if v is not None else np.nan      # unknown stays unknown
            rows.append(row)
    return pd.DataFrame(rows, columns=["match_id", "team_id", "side", "source", "file"] + STAT_COLS)


def _raw_inventory() -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(RAW, "**", "*"), recursive=True)):
        if os.path.isfile(path) and not path.endswith("_source.json"):
            out.append({"file": os.path.relpath(path, RAW), "bytes": os.path.getsize(path),
                        "modified_utc": datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    return out


def _prune(folder: str, prefix: str, keep: int) -> None:
    olds = sorted(d for d in os.listdir(folder) if d.startswith(prefix))
    for d in olds[:-keep]:
        shutil.rmtree(os.path.join(folder, d), ignore_errors=True)


def _write_status(update: dict) -> None:
    st = json.load(open(STATUS, encoding="utf-8")) if os.path.exists(STATUS) else {}
    st.update(update)
    tmp = STATUS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATUS)


def status() -> dict:
    return json.load(open(STATUS, encoding="utf-8")) if os.path.exists(STATUS) else {}


def fingerprint(m: pd.DataFrame) -> str:
    cols = ["date", "season", "home", "away", "hg", "ag", "hst", "ast", "odds_h", "odds_d", "odds_a", "odds_o25",
            "odds_u25", "hthg", "htag"]
    df = m[cols].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    blob = df.sort_values(["date", "home"]).to_csv(index=False, float_format="%.6g").encode()
    return hashlib.sha256(blob).hexdigest()[:12]


# --------------------------------------------------------------------------
# reading the standard layer
# --------------------------------------------------------------------------

def load_matches(first_season: int | None = None) -> pd.DataFrame:
    from .paths import MATCHES
    m = pd.read_csv(MATCHES, parse_dates=["date"], dtype={"result_source": str, "stats_source": str,
                                                          "odds_source": str, "ht_source": str})
    if first_season is not None:
        m = m[m["season"] >= first_season]
    return m.reset_index(drop=True)


def load_fixtures() -> pd.DataFrame:
    from .paths import FIXTURES
    return pd.read_csv(FIXTURES, dtype={"sr_id": str, "time_local": str, "kickoff_utc": str, "played_date": str,
                                        "sr_status": str, "kickoff_source": str})


def manifest() -> dict:
    return json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}


def model_table(first_season: int = 2000) -> pd.DataFrame:
    """Training table (standard matches + market-implied goals) for the current data version.
    Saved once per version in data/model_inputs/<version>.csv.gz."""
    from .market import add_market_goals
    m = load_matches(first_season)
    fp = manifest().get("data_version") or fingerprint(m)
    path = os.path.join(MODEL_INPUTS, f"{fp}.csv.gz")
    if os.path.exists(path):
        t = pd.read_csv(path, parse_dates=["date"], dtype={"result_source": str, "stats_source": str,
                                                          "odds_source": str, "ht_source": str})
    else:
        t = add_market_goals(m)
        os.makedirs(MODEL_INPUTS, exist_ok=True)
        t.to_csv(path, index=False, compression="gzip")
        _prune_files(MODEL_INPUTS, keep=20)
    t.attrs["data_version"] = fp
    return t


def _prune_files(folder: str, keep: int) -> None:
    files = sorted(glob.glob(os.path.join(folder, "*.csv.gz")), key=os.path.getmtime)
    for f in files[:-keep]:
        os.remove(f)
