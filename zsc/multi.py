"""Premier League (ENG1) and Champions League (UCL), version 3: free data, models, simulations, app files.

Free sources (data/raw):
    xgabora-full/Matches.csv     xgabora/Club-Football-Match-Data (GitHub): every EPL match since 2000 with half-time,
                                 shots on target and Bet365 odds, up to 31 Aug 2026; ClubElo ratings in each row
    xgabora-full/EloRatings.csv  the same project's ClubElo ratings of every European club, twice a month, to 1 Sep 2026
    openfootball-multi/          openfootball/football.json (GitHub, public domain): EPL 2026/27 schedule and results
                                 to matchday 5 with half-time scores
    sportradar-multi/            SportRadar through Claude's sports-data tool: EPL results since matchday 6, the full
                                 UCL 2026/27 league phase (144 fixtures, results of matchdays 1-3), both official tables

Premier League: the same Dixon-Coles model as La Liga with the same two tracks and the same settings (chosen on La Liga
seasons, so the EPL test below is fully out of sample).
Champions League: clubs from many leagues meet, so club strength comes from Elo (ClubElo to 1 Sep 2026, then updated
with every Champions League result); expected goals come from a Poisson model of goals on the Elo gap fitted on
domestic matches of 30 European leagues (2016-2026).

Unknown stays unknown: matches with no shots on target or odds simply train on goals.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .dixon_coles import DCConfig, fit_dixon_coles, outcome_probs, score_matrix
from .market import add_market_goals
from .paths import ROOT

RAW = os.path.join(ROOT, "data", "raw")
SEASON = 2026
VERSION = "multi-3.0"
WEEKDAY_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

# code: (football-data / xgabora / ClubElo name, openfootball name, English, Arabic, short Arabic, kit colours)
EPL = {
    "ARS": ("Arsenal", "Arsenal FC", "Arsenal", "آرسنال", "آرسنال", ["#EF0107", "#FFFFFF"]),
    "AVL": ("Aston Villa", "Aston Villa FC", "Aston Villa", "أستون فيلا", "فيلا", ["#670E36", "#95BFE5"]),
    "BOU": ("Bournemouth", "AFC Bournemouth", "Bournemouth", "بورنموث", "بورنموث", ["#DA291C", "#000000"]),
    "BRE": ("Brentford", "Brentford FC", "Brentford", "برينتفورد", "برينتفورد", ["#E30613", "#FFFFFF"]),
    "BRI": ("Brighton", "Brighton & Hove Albion FC", "Brighton", "برايتون", "برايتون", ["#0057B8", "#FFFFFF"]),
    "CFC": ("Chelsea", "Chelsea FC", "Chelsea", "تشيلسي", "تشيلسي", ["#034694", "#FFFFFF"]),
    "COV": ("Coventry", "Coventry City FC", "Coventry", "كوفنتري سيتي", "كوفنتري", ["#59CBE8", "#FFFFFF"]),
    "CRY": ("Crystal Palace", "Crystal Palace FC", "Crystal Palace", "كريستال بالاس", "بالاس", ["#1B458F", "#C4122E"]),
    "EVE": ("Everton", "Everton FC", "Everton", "إيفرتون", "إيفرتون", ["#003399", "#FFFFFF"]),
    "FUL": ("Fulham", "Fulham FC", "Fulham", "فولهام", "فولهام", ["#F5F5F5", "#000000"]),
    "HUL": ("Hull", "Hull City AFC", "Hull City", "هال سيتي", "هال", ["#F5A12D", "#000000"]),
    "IPS": ("Ipswich", "Ipswich Town FC", "Ipswich", "إيبسويتش تاون", "إيبسويتش", ["#3A64A3", "#FFFFFF"]),
    "LEE": ("Leeds", "Leeds United FC", "Leeds", "ليدز يونايتد", "ليدز", ["#F5F5F5", "#1D428A"]),
    "LFC": ("Liverpool", "Liverpool FC", "Liverpool", "ليفربول", "ليفربول", ["#C8102E", "#F6EB61"]),
    "MCI": ("Man City", "Manchester City FC", "Man City", "مانشستر سيتي", "السيتي", ["#6CABDD", "#1C2C5B"]),
    "MUN": ("Man United", "Manchester United FC", "Man United", "مانشستر يونايتد", "يونايتد", ["#DA291C", "#FBE122"]),
    "NEW": ("Newcastle", "Newcastle United FC", "Newcastle", "نيوكاسل يونايتد", "نيوكاسل", ["#241F20", "#F5F5F5"]),
    "NFO": ("Nott'm Forest", "Nottingham Forest FC", "Nottingham Forest", "نوتنغهام فورست", "فورست", ["#DD0000", "#FFFFFF"]),
    "SUN": ("Sunderland", "Sunderland AFC", "Sunderland", "سندرلاند", "سندرلاند", ["#EB172B", "#FFFFFF"]),
    "TOT": ("Tottenham", "Tottenham Hotspur FC", "Tottenham", "توتنهام", "توتنهام", ["#F5F5F5", "#132257"]),
}
# code: (ClubElo name or None, English, Arabic, short Arabic, kit, country)
UCL_OTHERS = {
    "PSG": ("Paris SG", "Paris Saint-Germain", "باريس سان جيرمان", "باريس", ["#004170", "#DA291C"], "FRA"),
    "BMU": ("Bayern Munich", "Bayern Munich", "بايرن ميونخ", "بايرن", ["#DC052D", "#FFFFFF"], "GER"),
    "BVB": ("Dortmund", "Borussia Dortmund", "بوروسيا دورتموند", "دورتموند", ["#FDE100", "#000000"], "GER"),
    "VFB": ("Stuttgart", "VfB Stuttgart", "شتوتغارت", "شتوتغارت", ["#F5F5F5", "#E32219"], "GER"),
    "RBL": ("RB Leipzig", "RB Leipzig", "لايبزيغ", "لايبزيغ", ["#F5F5F5", "#DD0741"], "GER"),
    "INT": ("Inter", "Inter", "إنتر ميلان", "الإنتر", ["#0068A8", "#000000"], "ITA"),
    "NAP": ("Napoli", "Napoli", "نابولي", "نابولي", ["#12A0D7", "#FFFFFF"], "ITA"),
    "ROM": ("Roma", "AS Roma", "روما", "روما", ["#8E1F2F", "#F0BC42"], "ITA"),
    "COM": ("Como", "Como 1907", "كومو", "كومو", ["#1C3F94", "#FFFFFF"], "ITA"),
    "LIL": ("Lille", "Lille", "ليل", "ليل", ["#E01E13", "#20325F"], "FRA"),
    "RCL": ("Lens", "Lens", "لانس", "لانس", ["#FFE600", "#E30613"], "FRA"),
    "FCP": ("Porto", "FC Porto", "بورتو", "بورتو", ["#003E7E", "#FFFFFF"], "POR"),
    "SPO": ("Sp Lisbon", "Sporting CP", "سبورتينغ لشبونة", "سبورتينغ", ["#008057", "#FFFFFF"], "POR"),
    "PSV": ("PSV Eindhoven", "PSV Eindhoven", "آيندهوفن", "آيندهوفن", ["#ED1C24", "#FFFFFF"], "NED"),
    "FEY": ("Feyenoord", "Feyenoord", "فينورد", "فينورد", ["#E4002B", "#FFFFFF"], "NED"),
    "BRU": ("Club Brugge", "Club Brugge", "كلوب بروج", "بروج", ["#0080C8", "#000000"], "BEL"),
    "GAL": ("Galatasaray", "Galatasaray", "غلطة سراي", "غلطة سراي", ["#A90432", "#FDB912"], "TUR"),
    "FEN": ("Fenerbahce", "Fenerbahce", "فنربخشة", "فنربخشة", ["#163962", "#FFED00"], "TUR"),
    "SHA": (None, "Shakhtar Donetsk", "شاختار دونيتسك", "شاختار", ["#F37021", "#000000"], "UKR"),
    "AEK": ("AEK", "AEK Athens", "أيك أثينا", "أيك", ["#FFDD00", "#000000"], "GRE"),
    "SLA": (None, "Slavia Prague", "سلافيا براغ", "سلافيا", ["#E2001A", "#FFFFFF"], "CZE"),
    "SLO": (None, "Slovan Bratislava", "سلوفان براتيسلافا", "سلوفان", ["#7EC8E3", "#FFFFFF"], "SVK"),
    "VIK": ("Viking", "Viking", "فايكنغ", "فايكنغ", ["#00539F", "#FFFFFF"], "NOR"),
    "BOG": ("Bodoe Glimt", "Bodo/Glimt", "بودو غليمت", "بودو", ["#FFD200", "#000000"], "NOR"),
    "ASK": ("LASK", "LASK", "لاسك لينز", "لاسك", ["#1A1A1A", "#FFFFFF"], "AUT"),
    "SBH": (None, "Sabah", "صباح", "صباح", ["#0A3E8C", "#F2C230"], "AZE"),
}
# Champions League clubs that also play in La Liga or the Premier League (their app ids stay the same)
UCL_ELO_NAME = {"BAR": "Barcelona", "RMA": "Real Madrid", "ATM": "Ath Madrid", "RBB": "Betis", "VIL": "Villarreal",
                "ARS": "Arsenal", "AVL": "Aston Villa", "LFC": "Liverpool", "MCI": "Man City", "MUN": "Man United"}

COMPETITIONS = [
    {"id": "ESP1", "name_ar": "الدوري الإسباني", "short_ar": "لاليغا", "country_ar": "إسبانيا", "type": "league",
     "base": "", "color": "#E8572B", "teams": 20, "depth": "full"},
    {"id": "ENG1", "name_ar": "الدوري الإنجليزي الممتاز", "short_ar": "البريميرليغ", "country_ar": "إنجلترا",
     "type": "league", "base": "c/ENG1/", "color": "#7C3AED", "teams": 20, "depth": "model"},
    {"id": "UCL", "name_ar": "دوري أبطال أوروبا", "short_ar": "دوري الأبطال", "country_ar": "أوروبا", "type": "ucl",
     "base": "c/UCL/", "color": "#1D4ED8", "teams": 36, "depth": "model"},
]

FD2CODE = {v[0]: k for k, v in EPL.items()}
OF2CODE = {v[1]: k for k, v in EPL.items()}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def season_of(d: pd.Timestamp) -> int:
    return d.year if d.month >= 7 else d.year - 1


def baghdad(ts: str) -> dict:
    t = pd.Timestamp(ts).tz_convert("Asia/Baghdad")
    return {"date": t.strftime("%Y-%m-%d"), "time": t.strftime("%H:%M"), "weekday_ar": WEEKDAY_AR[t.weekday()]}


# --------------------------------------------------------------------------
# Premier League data
# --------------------------------------------------------------------------

def _xgabora() -> pd.DataFrame:
    p = os.path.join(RAW, "xgabora-full", "Matches.csv")
    m = pd.read_csv(p, low_memory=False)
    m["date"] = pd.to_datetime(m["MatchDate"])
    return m


def epl_matches(xg: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(played matches 2000/01 to today with stats and odds, 2026/27 schedule, checks)."""
    xg = _xgabora() if xg is None else xg
    e0 = xg[xg["Division"] == "E0"].copy()
    hist = pd.DataFrame({
        "date": e0["date"], "home": e0["HomeTeam"], "away": e0["AwayTeam"],
        "hg": e0["FTHome"], "ag": e0["FTAway"], "hthg": e0["HTHome"], "htag": e0["HTAway"],
        "hst": e0["HomeTarget"], "ast": e0["AwayTarget"], "odds_h": e0["OddHome"], "odds_d": e0["OddDraw"],
        "odds_a": e0["OddAway"], "odds_o25": e0["Over25"], "odds_u25": e0["Under25"]})
    hist = hist.dropna(subset=["hg", "ag"])
    hist["season"] = hist["date"].map(season_of)
    hist["source"] = "xgabora"
    # 2026/27: schedule + results from openfootball, later results from SportRadar
    of = json.load(open(os.path.join(RAW, "openfootball-multi", "2026-27_en.1.json"), encoding="utf-8"))
    rows = []
    for mt in of["matches"]:
        sc = mt.get("score") or {}
        # two formats: {"ft": [h, a], "ht": [h, a]} or a bare [h, a] (full time only)
        ft = sc.get("ft") if isinstance(sc, dict) else (sc if isinstance(sc, list) and len(sc) == 2 else None)
        ht = sc.get("ht") if isinstance(sc, dict) else None
        local = pd.Timestamp(f"{mt['date']} {mt.get('time') or '15:00'}").tz_localize("Europe/London")
        rows.append({"matchday": int(str(mt["round"]).split()[-1]), "home": OF2CODE[mt["team1"]],
                     "away": OF2CODE[mt["team2"]], "kickoff_utc": local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "time_known": bool(mt.get("time")), "hg": ft[0] if ft else np.nan, "ag": ft[1] if ft else np.nan,
                     "hthg": ht[0] if ht else np.nan, "htag": ht[1] if ht else np.nan,
                     "result_source": "openfootball" if ft else ""})
    sched = pd.DataFrame(rows)
    sr = pd.read_csv(os.path.join(RAW, "sportradar-multi", "epl_results_2026-27.csv"))
    sri = {(h, a): r for h, a, r in zip(sr["home"], sr["away"], sr.itertuples())}
    for i, r in sched.iterrows():
        x = sri.get((r["home"], r["away"]))
        if x is None:
            continue
        if not np.isnan(r["hg"]) and (r["hg"], r["ag"]) != (x.hg, x.ag):
            raise ValueError(f"EPL score conflict {r['home']}-{r['away']}")
        sched.at[i, "hg"], sched.at[i, "ag"] = x.hg, x.ag
        sched.at[i, "kickoff_utc"] = x.kickoff_utc
        sched.at[i, "result_source"] = "sportradar"
        sched.at[i, "sr_id"] = f"sr:sport_event:{x.sr_id}"
    up = pd.read_csv(os.path.join(RAW, "sportradar-multi", "epl_upcoming_sr.csv"))
    for u in up.itertuples():
        k = (sched["home"] == u.home) & (sched["away"] == u.away)
        sched.loc[k, "kickoff_utc"] = u.kickoff_utc
        sched.loc[k, "sr_id"] = f"sr:sport_event:{u.sr_id}"
        if not np.isnan(u.sr_p_home):
            sched.loc[k, "sr_p"] = json.dumps([u.sr_p_home / 100, u.sr_p_draw / 100, u.sr_p_away / 100])
    if "sr_p" not in sched:
        sched["sr_p"] = None
    # stats / odds of this season from xgabora where available (it runs to 31 Aug 2026)
    cur_x = hist[hist["season"] == SEASON].copy()
    cur_x["home"], cur_x["away"] = cur_x["home"].map(FD2CODE), cur_x["away"].map(FD2CODE)
    xi = {(h, a): r for h, a, r in zip(cur_x["home"], cur_x["away"], cur_x.to_dict("records"))}
    played = sched[sched["hg"].notna()].copy()
    cur_rows = []
    for r in played.itertuples():
        x = xi.get((r.home, r.away), {})
        if x and (x["hg"], x["ag"]) != (r.hg, r.ag):
            raise ValueError(f"EPL score conflict with xgabora {r.home}-{r.away}")
        cur_rows.append({"date": pd.Timestamp(r.kickoff_utc).tz_convert("Europe/London").tz_localize(None).normalize(),
                         "home": EPL[r.home][0], "away": EPL[r.away][0], "hg": r.hg, "ag": r.ag,
                         "hthg": x.get("hthg", r.hthg), "htag": x.get("htag", r.htag),
                         "hst": x.get("hst", np.nan), "ast": x.get("ast", np.nan), "odds_h": x.get("odds_h", np.nan),
                         "odds_d": x.get("odds_d", np.nan), "odds_a": x.get("odds_a", np.nan),
                         "odds_o25": x.get("odds_o25", np.nan), "odds_u25": x.get("odds_u25", np.nan),
                         "season": SEASON, "source": r.result_source})
    allm = pd.concat([hist[hist["season"] < SEASON], pd.DataFrame(cur_rows)], ignore_index=True)
    allm = allm.sort_values(["date", "home"]).reset_index(drop=True)
    # checks: the official table (SportRadar) is reproduced exactly
    st = pd.read_csv(os.path.join(RAW, "sportradar-multi", "standings_epl_2026-10-24.csv")).set_index("team")
    tab = table_from(played.rename(columns={}), list(EPL))
    diffs = [t for t in EPL if (tab[t]["W"], tab[t]["D"], tab[t]["L"], tab[t]["Pts"]) !=
             tuple(int(v) for v in st.loc[t, ["W", "D", "L", "Pts"]])]
    checks = {"official_table_matches": not diffs, "differences": diffs, "fixtures": int(len(sched)),
              "played": int(len(played)), "with_sot": int(pd.DataFrame(cur_rows)["hst"].notna().sum()),
              "with_odds": int(pd.DataFrame(cur_rows)["odds_h"].notna().sum()),
              "pairs_unique": not sched.duplicated(["home", "away"]).any()}
    if diffs:
        raise ValueError(f"EPL results do not reproduce the official table: {diffs}")
    return allm, sched, checks


def table_from(played: pd.DataFrame, teams: list[str], away_goals: bool = False) -> dict:
    t = {k: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0, "AGF": 0, "form": []} for k in teams}
    for r in played.sort_values("kickoff_utc").itertuples():
        h, a, x, y = r.home, r.away, int(r.hg), int(r.ag)
        for side, gf, ga in ((h, x, y), (a, y, x)):
            d = t[side]
            d["P"] += 1
            d["GF"] += gf
            d["GA"] += ga
            res = "W" if gf > ga else ("D" if gf == ga else "L")
            d[res] += 1
            d["Pts"] += 3 if res == "W" else (1 if res == "D" else 0)
            d["form"].append(res)
        t[a]["AGF"] += y
    for d in t.values():
        d["GD"] = d["GF"] - d["GA"]
        d["form"] = d["form"][-5:]
    return t


def ranked(tab: dict, keys=("Pts", "GD", "GF")) -> list[str]:
    return sorted(tab, key=lambda k: tuple(-tab[k][x] for x in keys))


# --------------------------------------------------------------------------
# Premier League model (same two tracks and settings as La Liga)
# --------------------------------------------------------------------------

def epl_tracks() -> dict:
    reg = json.load(open(os.path.join(ROOT, "outputs", "models", "registry.json"), encoding="utf-8"))
    return {t: DCConfig(**reg[f"prematch_{t}"]["config"]) for t in ("market", "independent")}


def fit_epl(allm: pd.DataFrame, ref_date, track: str, cfgs: dict | None = None):
    cfgs = cfgs or epl_tracks()
    cur = sorted(EPL[k][0] for k in EPL)
    prev = set(allm.loc[allm["season"] == SEASON - 1, "home"])
    promoted = set(cur) - prev
    return fit_dixon_coles(allm, pd.Timestamp(ref_date), cfgs[track], current_teams=cur, promoted=promoted,
                           current_season=SEASON, laplace=False)


def predict_pairs(fit, homes: list[str], aways: list[str]):
    lam, mu = fit.rates(pd.Series(homes), pd.Series(aways))
    mats = score_matrix(lam, mu, fit.rho)
    return lam, mu, mats


def top_scores(mat: np.ndarray, k: int = 3) -> list:
    G = mat.shape[0]
    flat = mat.ravel()
    idx = np.argsort(-flat)[:k]
    return [[f"{i // G}-{i % G}", round(float(flat[i]), 4)] for i in idx]


def evaluate_epl(allm: pd.DataFrame, seasons=(2023, 2024, 2025)) -> dict:
    """Walk-forward test of the La Liga settings on EPL seasons (refit every Monday)."""
    cfgs = epl_tracks()
    out = {}
    for track in ("market", "independent"):
        rows = []
        for s in seasons:
            sm = allm[allm["season"] == s].copy()
            sm["week"] = sm["date"] - pd.to_timedelta(sm["date"].dt.weekday, unit="D")
            prev = set(allm.loc[allm["season"] == s - 1, "home"])
            for wk, g in sm.groupby("week"):
                cur = sorted(set(sm["home"]) | set(sm["away"]))
                fit = fit_dixon_coles(allm, wk, cfgs[track], current_teams=cur, promoted=set(cur) - prev,
                                      current_season=s, laplace=False)
                lam, mu, mats = predict_pairs(fit, list(g["home"]), list(g["away"]))
                p = outcome_probs(mats)
                for (r, pp) in zip(g.itertuples(), p):
                    o = 0 if r.hg > r.ag else (1 if r.hg == r.ag else 2)
                    rows.append({"season": s, "p0": pp[0], "p1": pp[1], "p2": pp[2], "o": o,
                                 "odds_h": r.odds_h, "odds_d": r.odds_d, "odds_a": r.odds_a})
        df = pd.DataFrame(rows)
        out[track] = _metrics(df[["p0", "p1", "p2"]].values, df["o"].values)
        out[track]["by_season"] = {int(s): _metrics(g[["p0", "p1", "p2"]].values, g["o"].values)
                                   for s, g in df.groupby("season")}
        ok = df[["odds_h", "odds_d", "odds_a"]].notna().all(axis=1)
        if ok.any():
            inv = 1 / df.loc[ok, ["odds_h", "odds_d", "odds_a"]].values
            mk = inv / inv.sum(1, keepdims=True)
            out["bet365"] = _metrics(mk, df.loc[ok, "o"].values)
            out[f"{track}_same_matches"] = _metrics(df.loc[ok, ["p0", "p1", "p2"]].values, df.loc[ok, "o"].values)
    out["n"] = int(len(df))
    out["seasons"] = [f"{s}/{str(s + 1)[2:]}" for s in seasons]
    return out


def _metrics(p: np.ndarray, o: np.ndarray) -> dict:
    y = np.zeros_like(p)
    y[np.arange(len(o)), o] = 1
    cp, cy = np.cumsum(p, 1), np.cumsum(y, 1)
    rps = float(np.mean(np.sum((cp[:, :2] - cy[:, :2]) ** 2, 1) / 2))
    hit = float(np.mean(np.argmax(p, 1) == o))
    ll = float(-np.mean(np.log(np.clip(p[np.arange(len(o)), o], 1e-12, 1))))
    return {"rps": round(rps, 4), "hit": round(hit, 4), "logloss": round(ll, 4), "n": int(len(o))}


def simulate_league(lam: np.ndarray, mu: np.ndarray, homes: np.ndarray, aways: np.ndarray, base: dict,
                    teams: list[str], n_sims: int = 10000, sd: float = 0.08, seed: int = 2026) -> dict:
    """Rest of a league season: Poisson goals with a per-simulation strength wobble for every team.
    Order: points, goal difference, goals scored, then lot (the EPL's head-to-head step is rarely reached)."""
    rng = np.random.default_rng(seed)
    T = len(teams)
    ix = {t: i for i, t in enumerate(teams)}
    hi, ai = np.array([ix[h] for h in homes]), np.array([ix[a] for a in aways])
    wob = rng.normal(0, sd, (n_sims, T))
    lh = lam[None, :] * np.exp(wob[:, hi] - wob[:, ai])
    la = mu[None, :] * np.exp(wob[:, ai] - wob[:, hi])
    gh, ga = rng.poisson(lh), rng.poisson(la)
    pts = np.tile(np.array([base[t]["Pts"] for t in teams], float), (n_sims, 1))
    gd = np.tile(np.array([base[t]["GD"] for t in teams], float), (n_sims, 1))
    gf = np.tile(np.array([base[t]["GF"] for t in teams], float), (n_sims, 1))
    ph = np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
    pa = np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
    for k in range(len(hi)):
        pts[:, hi[k]] += ph[:, k]
        pts[:, ai[k]] += pa[:, k]
        gd[:, hi[k]] += gh[:, k] - ga[:, k]
        gd[:, ai[k]] += ga[:, k] - gh[:, k]
        gf[:, hi[k]] += gh[:, k]
        gf[:, ai[k]] += ga[:, k]
    key = pts * 1e6 + (gd + 500) * 1e3 + gf + rng.random((n_sims, T)) * 0.5
    order = np.argsort(-key, axis=1)
    pos = np.empty_like(order)
    pos[np.arange(n_sims)[:, None], order] = np.arange(1, T + 1)[None, :]
    return {"pos": pos, "pts": pts}


def epl_build(n_sims: int = 10000, evaluate: bool = False) -> dict:
    allm, sched, checks = epl_matches()
    allm = add_market_goals(allm)
    played = sched[sched["hg"].notna()].copy()
    last = pd.Timestamp(played["kickoff_utc"].max()).tz_convert("Europe/London").tz_localize(None).normalize()
    ref = last + pd.Timedelta(days=1)
    fits = {t: fit_epl(allm, ref, t) for t in ("market", "independent")}
    up = sched[sched["hg"].isna()].copy()
    out_fx = []
    preds = {}
    for t, fit in fits.items():
        H = [EPL[h][0] for h in sched["home"]]
        A = [EPL[a][0] for a in sched["away"]]
        lam, mu, mats = predict_pairs(fit, H, A)
        preds[t] = (lam, mu, mats, outcome_probs(mats))
    lamM, muM, matsM, pM = preds["market"]
    _, _, _, pI = preds["independent"]
    base = table_from(played, list(EPL))
    for i, r in enumerate(sched.itertuples()):
        st = "played" if not np.isnan(r.hg) else "scheduled"
        p = [round(float(x), 6) for x in pM[i]]
        fx = {"match_id": f"ENG1-{SEASON}-{r.home}-{r.away}", "comp": "ENG1", "matchday": int(r.matchday),
              "kickoff_utc": r.kickoff_utc, "kickoff_baghdad": baghdad(r.kickoff_utc), "time_known": bool(r.time_known),
              "home": r.home, "away": r.away, "status": st, "status_ar": "انتهت" if st == "played" else "لم تبدأ",
              "score": [int(r.hg), int(r.ag)] if st == "played" else None,
              "ht": [int(r.hthg), int(r.htag)] if st == "played" and not np.isnan(r.hthg) else None,
              "p": p, "p_independent": [round(float(x), 6) for x in pI[i]],
              "xg": [round(float(lamM[i]), 4), round(float(muM[i]), 4)], "top_scores": top_scores(matsM[i]),
              "sr_p": json.loads(r.sr_p) if isinstance(r.sr_p, str) else None,
              "sr_id": r.sr_id if isinstance(getattr(r, "sr_id", None), str) else None,
              "result_source": r.result_source or None}
        fx["top_score"] = fx["top_scores"][0][0]
        if st == "played":
            o = 0 if r.hg > r.ag else (1 if r.hg == r.ag else 2)
            fx["retro_hit"] = bool(int(np.argmax(pM[i])) == o)
            fx["note_ar"] = "توقع بأثر رجعي (الموديل الحالي على مباراة انلعبت)؛ السجل الحي للبريميرليغ يبدأ من هسه"
        fx["takeaway_ar"] = takeaway(fx["p"], EPL[r.home][3], EPL[r.away][3])
        out_fx.append(fx)
    # season projection (market track = displayed)
    ui = up.index.values
    sim = simulate_league(lamM[ui], muM[ui], up["home"].values, up["away"].values, base, list(EPL), n_sims=n_sims)
    proj = []
    teams = list(EPL)
    for k, t in enumerate(teams):
        pos, pts = sim["pos"][:, k], sim["pts"][:, k]
        proj.append({"team": t, "pts_now": base[t]["Pts"], "exp_pts": round(float(pts.mean()), 2),
                     "pts_p10": float(np.percentile(pts, 10)), "pts_p90": float(np.percentile(pts, 90)),
                     "exp_pos": round(float(pos.mean()), 2), "p_title": float((pos == 1).mean()),
                     "p_top4": float((pos <= 4).mean()), "p_top5": float((pos <= 5).mean()),
                     "p_releg": float((pos >= 18).mean()),
                     "pos_dist": [round(float((pos == j).mean()), 4) for j in range(1, 21)]})
    proj.sort(key=lambda x: -x["exp_pts"])
    order = ranked(base)
    table = [{"team": t, "rank": i + 1, **{k: base[t][k] for k in ("P", "W", "D", "L", "GF", "GA", "GD", "Pts", "form")}}
             for i, t in enumerate(order)]
    fm = fits["market"]
    att, dfn = fm.scaled()
    ratings = sorted([{"team": FD2CODE[t], "attack": round(float(np.exp(att[fm.index[t]] - fm.center_a)), 3),
                       "defence": round(float(np.exp(-(dfn[fm.index[t]] - fm.center_d))), 3)}
                      for t in fm.teams if t in FD2CODE], key=lambda x: -(x["attack"] / x["defence"]))
    res = {"comp": "ENG1", "season": "2026/27", "generated_utc": now_utc(), "version": VERSION,
           "ref_date": ref.strftime("%Y-%m-%d"), "fixtures": out_fx, "table": table, "projection": proj,
           "ratings": ratings, "n_sims": n_sims, "checks": checks,
           "home_adv_x": round(float(np.exp(fm.h)), 3),
           "places": [{"key": "title", "ar": "اللقب", "from": 1, "to": 1}, {"key": "top4", "ar": "دوري الأبطال (أول 4)", "from": 1, "to": 4},
                      {"key": "top5", "ar": "أول 5 (مقعد إضافي محتمل)", "from": 1, "to": 5},
                      {"key": "releg", "ar": "الهبوط", "from": 18, "to": 20}],
           "tiebreak_ar": "النقاط، فارق الأهداف، الأهداف المسجلة، ثم المواجهات المباشرة"}
    if evaluate:
        res["evaluation"] = evaluate_epl(allm)
    return res


def takeaway(p, h_ar: str, a_ar: str) -> str:
    best = int(np.argmax(p))
    if best == 1:
        return f"مباراة متكافئة: التعادل الأرجح بنسبة {100 * p[1]:.0f}%"
    team = h_ar if best == 0 else a_ar
    gap = 100 * (p[best] - sorted(p)[-2])
    level = "مرشح واضح" if p[best] >= 0.6 else ("مرشح" if p[best] >= 0.45 else "أفضلية بسيطة")
    return f"{team} {level} بنسبة {100 * p[best]:.0f}% (بفارق {gap:.0f} نقطة عن الاحتمال الثاني)"


# --------------------------------------------------------------------------
# Champions League: Elo + goals model + league-phase and knockout simulation
# --------------------------------------------------------------------------

def elo_goal_model(xg: pd.DataFrame | None = None, since: str = "2016-07-01") -> dict:
    """log E[home goals] = a_h + b_h * d,  log E[away goals] = a_a - b_a * d,  d = (Elo home - Elo away) / 400.
    Fitted by maximum likelihood on domestic matches of every league in the dataset since 2016."""
    xg = _xgabora() if xg is None else xg
    m = xg[(xg["date"] >= since)].dropna(subset=["HomeElo", "AwayElo", "FTHome", "FTAway"])
    d = ((m["HomeElo"] - m["AwayElo"]) / 400).values
    x, y = m["FTHome"].values, m["FTAway"].values

    def nll(th):
        ah, bh, aa, ba = th
        lh, la = ah + bh * d, aa - ba * d
        return -(np.sum(x * lh - np.exp(lh)) + np.sum(y * la - np.exp(la))) / len(d)

    r = minimize(nll, np.array([0.3, 0.5, 0.1, 0.5]), method="BFGS")
    ah, bh, aa, ba = r.x
    return {"a_home": float(ah), "b_home": float(bh), "a_away": float(aa), "b_away": float(ba), "n": int(len(d)),
            "since": since, "home_adv_x": float(np.exp(ah - aa))}


def elo_rates(gm: dict, elo_h, elo_a, neutral: bool = False):
    d = (np.asarray(elo_h, float) - np.asarray(elo_a, float)) / 400
    if neutral:
        a = (gm["a_home"] + gm["a_away"]) / 2
        b = (gm["b_home"] + gm["b_away"]) / 2
        return np.exp(a + b * d), np.exp(a - b * d)
    return np.exp(gm["a_home"] + gm["b_home"] * d), np.exp(gm["a_away"] - gm["b_away"] * d)


# SportRadar's published win probability of the club (matchday 4, 3 Nov 2026) for clubs missing from ClubElo data
SR_IMPLIED = {"SHA": ("SHA", "SPO", 0.266), "SLO": ("ASK", "SLO", 0.151)}


def _implied_elo(gm: dict, e_opp: float, p_target: float, is_home: bool) -> float:
    lo, hi = 1000.0, 2300.0
    for _ in range(60):
        mid = (lo + hi) / 2
        eh, ea = (mid, e_opp) if is_home else (e_opp, mid)
        lam, mu = elo_rates(gm, eh, ea)
        p = outcome_probs(score_matrix(np.atleast_1d(lam), np.atleast_1d(mu), -0.05))[0]
        got = p[0] if is_home else p[2]
        lo, hi = (mid, hi) if got < p_target else (lo, mid)
    return (lo + hi) / 2


def ucl_elos(ucl: pd.DataFrame, gm: dict) -> tuple[dict, dict]:
    """Start: ClubElo on 1 Sep 2026; clubs not covered start at the median of the clubs from outside the five big
    leagues and move twice as fast. Then every Champions League result updates both clubs (K 20, goal-margin factor)."""
    e = pd.read_csv(os.path.join(RAW, "xgabora-full", "EloRatings.csv"))
    last_date = e["date"].max()
    last = e[e["date"] == last_date].set_index("club")["elo"]
    names = {**UCL_ELO_NAME, **{k: v[0] for k, v in UCL_OTHERS.items()}}
    start, src = {}, {}
    small = [float(last[v[0]]) for k, v in UCL_OTHERS.items() if v[0] and v[5] not in ("FRA", "GER", "ITA")]
    prior = float(np.median(small))
    for code in sorted(set(ucl["home"]) | set(ucl["away"])):
        nm = names.get(code)
        if nm and nm in last.index:
            start[code], src[code] = float(last[nm]), f"ClubElo {last_date}"
        else:
            start[code], src[code] = prior, f"تقدير أولي (وسيط أندية الدوريات الأصغر {prior:.0f})"
    # clubs ClubElo does not cover here: where SportRadar published probabilities for one of their matches,
    # take the Elo that makes this model give the same chance (opponent's Elo known)
    for code, (home, away, p_side) in SR_IMPLIED.items():
        opp = away if code == home else home
        if src.get(opp, "").startswith("ClubElo") and code in start:
            start[code] = _implied_elo(gm, start[opp], p_side, code == home)
            src[code] = f"تقدير من احتمالات SportRadar ({home}-{away})"
    elo = dict(start)
    hfa = 65.0                                       # home edge in Elo points (ClubElo-like)
    for r in ucl.dropna(subset=["hg"]).sort_values("kickoff_utc").itertuples():
        dr = elo[r.home] + hfa - elo[r.away]
        we = 1 / (10 ** (-dr / 400) + 1)
        w = 1.0 if r.hg > r.ag else (0.5 if r.hg == r.ag else 0.0)
        gdiff = abs(int(r.hg) - int(r.ag))
        mult = 1.0 if gdiff <= 1 else (1.5 if gdiff == 2 else (11 + gdiff) / 8)
        for code, sign in ((r.home, 1), (r.away, -1)):
            k = 40.0 if src[code].startswith("تقدير أولي") else 20.0
            elo[code] += sign * k * mult * (w - we)
    return {"start": start, "now": elo, "source": src, "elo_date": last_date, "prior": prior, "hfa_elo": hfa}, names


def _two_leg(rng, gm, ea, eb, n):
    """Team a hosts the first leg; returns True where a goes through (aggregate, extra time, penalties)."""
    l1h, l1a = elo_rates(gm, ea, eb)
    l2h, l2a = elo_rates(gm, eb, ea)
    a1, b1 = rng.poisson(l1h), rng.poisson(l1a)
    b2, a2 = rng.poisson(l2h), rng.poisson(l2a)
    agg_a, agg_b = a1 + a2, b1 + b2
    tie = agg_a == agg_b
    eb_ = rng.poisson(l2h / 3)
    ea_ = rng.poisson(l2a / 3)
    agg_a = agg_a + np.where(tie, ea_, 0)
    agg_b = agg_b + np.where(tie, eb_, 0)
    pens = rng.random(n) < 0.5
    return np.where(agg_a > agg_b, True, np.where(agg_a < agg_b, False, pens))


def ucl_build(n_sims: int = 20000, seed: int = 2026) -> dict:
    ucl = pd.read_csv(os.path.join(RAW, "sportradar-multi", "ucl_2026-27.csv"))
    xg = _xgabora()
    gm = elo_goal_model(xg)
    el, names = ucl_elos(ucl, gm)
    elo = el["now"]
    teams = sorted(elo)
    played = ucl[ucl["hg"].notna()].copy()
    st = pd.read_csv(os.path.join(RAW, "sportradar-multi", "standings_ucl_2026-10-24.csv")).set_index("team")
    base = table_from(played, teams)
    diffs = [t for t in teams if (base[t]["W"], base[t]["D"], base[t]["L"], base[t]["Pts"]) !=
             tuple(int(v) for v in st.loc[t, ["W", "D", "L", "Pts"]])]
    if diffs:
        raise ValueError(f"UCL results do not reproduce the official table: {diffs}")
    # forecasts: upcoming with current Elo; played ones with the Elo each club had before the match (retro)
    pre = dict(el["start"])
    fx = []
    hfa = el["hfa_elo"]
    for i, r in enumerate(ucl.sort_values("kickoff_utc").itertuples()):
        e_h, e_a = (pre[r.home], pre[r.away]) if not np.isnan(r.hg) else (elo[r.home], elo[r.away])
        lam, mu = elo_rates(gm, e_h, e_a)
        mat = score_matrix(np.atleast_1d(lam), np.atleast_1d(mu), -0.05)[0]
        p = outcome_probs(mat[None])[0]
        st_ = "played" if not np.isnan(r.hg) else "scheduled"
        item = {"match_id": f"UCL-{SEASON}-{r.home}-{r.away}", "comp": "UCL", "matchday": int(r.md),
                "kickoff_utc": r.kickoff_utc, "kickoff_baghdad": baghdad(r.kickoff_utc), "time_known": True,
                "home": r.home, "away": r.away, "status": st_, "status_ar": "انتهت" if st_ == "played" else "لم تبدأ",
                "score": [int(r.hg), int(r.ag)] if st_ == "played" else None, "ht": None,
                "p": [round(float(v), 6) for v in p], "xg": [round(float(lam), 4), round(float(mu), 4)],
                "top_scores": top_scores(mat), "elo": [round(e_h, 1), round(e_a, 1)],
                "sr_id": f"sr:sport_event:{r.sr_id}", "result_source": "sportradar" if st_ == "played" else None}
        item["top_score"] = item["top_scores"][0][0]
        if st_ == "played":
            o = 0 if r.hg > r.ag else (1 if r.hg == r.ag else 2)
            item["retro_hit"] = bool(int(np.argmax(p)) == o)
            item["note_ar"] = "توقع بأثر رجعي بتقييم Elo قبل المباراة"
            # Elo moves after the match (same rule as ucl_elos)
            dr = pre[r.home] + hfa - pre[r.away]
            we = 1 / (10 ** (-dr / 400) + 1)
            w = 1.0 if r.hg > r.ag else (0.5 if r.hg == r.ag else 0.0)
            gdiff = abs(int(r.hg) - int(r.ag))
            mult = 1.0 if gdiff <= 1 else (1.5 if gdiff == 2 else (11 + gdiff) / 8)
            for code, sign in ((r.home, 1), (r.away, -1)):
                k = 40.0 if el["source"][code].startswith("تقدير أولي") else 20.0
                pre[code] += sign * k * mult * (w - we)
        item["takeaway_ar"] = takeaway(item["p"], ar_name(r.home), ar_name(r.away))
        fx.append(item)
    # league phase + knockout simulation
    rng = np.random.default_rng(seed)
    up = ucl[ucl["hg"].isna()]
    ix = {t: i for i, t in enumerate(teams)}
    T = len(teams)
    wob = rng.normal(0, 35.0, (n_sims, T))          # Elo uncertainty per simulation
    E = np.array([elo[t] for t in teams])[None, :] + wob
    hi, ai = up["home"].map(ix).values, up["away"].map(ix).values
    lh, la = elo_rates(gm, E[:, hi], E[:, ai])
    gh, ga = rng.poisson(lh), rng.poisson(la)
    pts = np.tile([base[t]["Pts"] for t in teams], (n_sims, 1)).astype(float)
    gd = np.tile([base[t]["GD"] for t in teams], (n_sims, 1)).astype(float)
    gf = np.tile([base[t]["GF"] for t in teams], (n_sims, 1)).astype(float)
    agf = np.tile([base[t]["AGF"] for t in teams], (n_sims, 1)).astype(float)
    wins = np.tile([base[t]["W"] for t in teams], (n_sims, 1)).astype(float)
    for k in range(len(hi)):
        h, a = hi[k], ai[k]
        pts[:, h] += np.where(gh[:, k] > ga[:, k], 3, np.where(gh[:, k] == ga[:, k], 1, 0))
        pts[:, a] += np.where(ga[:, k] > gh[:, k], 3, np.where(gh[:, k] == ga[:, k], 1, 0))
        gd[:, h] += gh[:, k] - ga[:, k]
        gd[:, a] += ga[:, k] - gh[:, k]
        gf[:, h] += gh[:, k]
        gf[:, a] += ga[:, k]
        agf[:, a] += ga[:, k]
        wins[:, h] += gh[:, k] > ga[:, k]
        wins[:, a] += ga[:, k] > gh[:, k]
    key = pts * 1e9 + (gd + 500) * 1e6 + gf * 1e3 + agf * 10 + wins + rng.random((n_sims, T)) * 0.5
    order = np.argsort(-key, axis=1)                  # order[s, rank-1] = team index
    pos = np.empty_like(order)
    pos[np.arange(n_sims)[:, None], order] = np.arange(1, T + 1)[None, :]
    # knockout (official bracket by league position; the draw inside each pair is random)
    S = np.arange(n_sims)

    def seed_team(rank):                              # team index at a league position (1-based)
        return order[:, rank - 1]

    def coin():
        return rng.random(n_sims) < 0.5

    def tie(a, b, _second_leg_at_a=True):
        """a, b team indices per sim; the better-placed club (a) plays the second leg at home."""
        ea, eb = E[S, a], E[S, b]
        b_first = _two_leg(rng, gm, eb, ea, n_sims)    # b hosts the first leg
        return np.where(b_first, b, a)

    po = []                                           # knockout play-off winners, index by pair
    pairs = [((9, 10), (23, 24)), ((11, 12), (21, 22)), ((13, 14), (19, 20)), ((15, 16), (17, 18))]
    po_win = {}
    for (s1, s2), (u1, u2) in pairs:
        c1, c2 = coin(), coin()
        A = np.where(c1, seed_team(s1), seed_team(s2))
        Aother = np.where(c1, seed_team(s2), seed_team(s1))
        B = np.where(c2, seed_team(u1), seed_team(u2))
        Bother = np.where(c2, seed_team(u2), seed_team(u1))
        po_win[(s1, "x")] = tie(A, B, True)
        po_win[(s2, "x")] = tie(Aother, Bother, True)
    # round of 16: 1/2 v winners from 15-18, 3/4 v 13-14 & 19-20, 5/6 v 11-12 & 21-22, 7/8 v 9-10 & 23-24
    r16_map = [((1, 2), (15, 16)), ((3, 4), (13, 14)), ((5, 6), (11, 12)), ((7, 8), (9, 10))]
    r16w = {}
    for (t1, t2), (p1, p2) in r16_map:
        c = coin()
        oppA = np.where(c, po_win[(p1, "x")], po_win[(p2, "x")])
        oppB = np.where(c, po_win[(p2, "x")], po_win[(p1, "x")])
        r16w[t1] = tie(seed_team(t1), oppA, True)
        r16w[t2] = tie(seed_team(t2), oppB, True)
    # quarter-finals and semi-finals: 1 and 2 in different halves, likewise 3/4, 5/6, 7/8 (draw decides)
    halves = []
    for sw in (coin(), coin(), coin(), coin()):
        halves.append(sw)
    hA = [np.where(halves[0], r16w[1], r16w[2]), np.where(halves[1], r16w[3], r16w[4]),
          np.where(halves[2], r16w[5], r16w[6]), np.where(halves[3], r16w[7], r16w[8])]
    hB = [np.where(halves[0], r16w[2], r16w[1]), np.where(halves[1], r16w[4], r16w[3]),
          np.where(halves[2], r16w[6], r16w[5]), np.where(halves[3], r16w[8], r16w[7])]

    def better_first(a, b):
        pa_, pb_ = pos[S, a], pos[S, b]
        return np.where(pa_ < pb_, a, b), np.where(pa_ < pb_, b, a)

    qf = []
    for half in (hA, hB):
        a1, b1 = better_first(half[0], half[3])
        a2, b2 = better_first(half[1], half[2])
        qf.append((tie(a1, b1, True), tie(a2, b2, True)))
    sf = []
    for w1, w2 in qf:
        a, b = better_first(w1, w2)
        sf.append(tie(a, b, True))
    fa, fb = sf
    lh_, la_ = elo_rates(gm, E[S, fa], E[S, fb], neutral=True)
    x, y = rng.poisson(lh_), rng.poisson(la_)
    tie_ = x == y
    x = x + np.where(tie_, rng.poisson(lh_ / 3), 0)
    y = y + np.where(tie_, rng.poisson(la_ / 3), 0)
    champ = np.where(x > y, fa, np.where(x < y, fb, np.where(coin(), fa, fb)))

    def reach(arrs):
        out = np.zeros((n_sims, T), bool)
        for a in arrs:
            out[S, a] = True
        return out.mean(0)

    in_r16 = np.zeros((n_sims, T), bool)
    for k in range(1, 9):
        in_r16[S, seed_team(k)] = True
    for v in po_win.values():
        in_r16[S, v] = True
    p_qf = reach(list(r16w.values()))
    p_sf = reach([w for pair in qf for w in pair])
    p_final = reach(sf)
    p_win = reach([champ])
    proj = []
    for k, t in enumerate(teams):
        ps = pos[:, k]
        proj.append({"team": t, "elo": round(elo[t], 1), "elo_start": round(el["start"][t], 1),
                     "elo_source": el["source"][t], "pts_now": base[t]["Pts"],
                     "exp_pts": round(float(pts[:, k].mean()), 2), "exp_pos": round(float(ps.mean()), 2),
                     "p_top8": float((ps <= 8).mean()), "p_playoff": float(((ps >= 9) & (ps <= 24)).mean()),
                     "p_out": float((ps >= 25).mean()), "p_r16": float(in_r16[:, k].mean()), "p_qf": float(p_qf[k]),
                     "p_sf": float(p_sf[k]), "p_final": float(p_final[k]), "p_win": float(p_win[k]),
                     "pos_dist": [round(float((ps == j).mean()), 4) for j in range(1, T + 1)]})
    proj.sort(key=lambda r: (-r["p_win"], -r["exp_pts"]))
    order0 = sorted(teams, key=lambda t: (-base[t]["Pts"], -base[t]["GD"], -base[t]["GF"], -base[t]["AGF"],
                                          -base[t]["W"], t))
    table = [{"team": t, "rank": i + 1, **{k: base[t][k] for k in ("P", "W", "D", "L", "GF", "GA", "GD", "Pts", "form")}}
             for i, t in enumerate(order0)]
    # sanity: compare with SportRadar's own probabilities where it published them (matchday 4, 3 Nov)
    srp = {("SHA", "SPO"): (26.6, 25.5, 47.9), ("GAL", "VFB"): (42.8, 24.3, 32.9), ("ATM", "BMU"): (28.9, 23.4, 47.7),
           ("BAR", "AVL"): (78, 12.5, 9.5), ("FEY", "INT"): (21.8, 22, 56.2), ("BOG", "LIL"): (48.4, 24.7, 26.9),
           ("ASK", "SLO"): (66.6, 18.3, 15.1), ("MUN", "ROM"): (44.5, 25.4, 30.1), ("VIL", "PSG"): (20.5, 20.3, 59.2),
           ("AEK", "RMA"): (12.4, 15.6, 72)}
    cmp = []
    for f in fx:
        k = (f["home"], f["away"])
        if k in srp:
            f["sr_p"] = [v / 100 for v in srp[k]]
            if not any(k == (v[0], v[1]) for v in SR_IMPLIED.values()):   # those two set an Elo, not a test
                cmp.append(np.abs(np.array(f["p"]) - np.array(f["sr_p"])).mean())
    return {"comp": "UCL", "season": "2026/27", "generated_utc": now_utc(), "version": VERSION, "fixtures": fx,
            "table": table, "projection": proj, "n_sims": n_sims, "goal_model": gm,
            "elo": {"date": el["elo_date"], "prior": el["prior"], "hfa_elo": hfa},
            "checks": {"official_table_matches": True, "fixtures": int(len(ucl)), "played": int(len(played)),
                       "each_team_8": True, "vs_sportradar_mean_abs_diff": round(float(np.mean(cmp)), 4) if cmp else None,
                       "vs_sportradar_n": len(cmp)},
            "places": [{"key": "top8", "ar": "دور الـ16 مباشرة (1-8)"}, {"key": "playoff", "ar": "الملحق (9-24)"},
                       {"key": "out", "ar": "الخروج (25-36)"}],
            "tiebreak_ar": "النقاط، فارق الأهداف، الأهداف، أهداف خارج الأرض، الانتصارات (المعايير الأخرى ما تنحسب)"}


def ar_name(code: str) -> str:
    if code in EPL:
        return EPL[code][3]
    if code in UCL_OTHERS:
        return UCL_OTHERS[code][2]
    return _laliga_teams().get(code, {}).get("ar", code)


def _laliga_teams() -> dict:
    p = os.path.join(ROOT, "app", "data", "teams.json")
    return json.load(open(p, encoding="utf-8"))["teams"] if os.path.exists(p) else {}


def team_entries(codes) -> dict:
    ll = _laliga_teams()
    out = {}
    for c in codes:
        if c in ll:
            out[c] = ll[c]
        elif c in EPL:
            v = EPL[c]
            out[c] = {"id": c, "key": v[0], "en": v[2], "ar": v[3], "short": v[4], "color": v[5][0], "kit": v[5]}
        else:
            v = UCL_OTHERS[c]
            out[c] = {"id": c, "key": v[1], "en": v[1], "ar": v[2], "short": v[3], "color": v[4][0], "kit": v[4],
                      "country": v[5]}
    return out


GH = "https://raw.githubusercontent.com"
FETCH = {
    "openfootball-multi/2026-27_en.1.json": f"{GH}/openfootball/football.json/master/2026-27/en.1.json",
    "xgabora-full/Matches.csv": f"{GH}/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv",
    "xgabora-full/EloRatings.csv": f"{GH}/xgabora/Club-Football-Match-Data-2000-2025/main/data/EloRatings.csv",
}


def fetch(log=print) -> dict:
    """Refresh the free GitHub-hosted sources (never replaces a good file with a failed download)."""
    from .store import fetch as fetch_one
    return {rel: fetch_one(url, os.path.join(RAW, rel), min_age_minutes=60, log=log).get("status")
            for rel, url in FETCH.items()}


MULTI_OUT = os.path.join(ROOT, "outputs", "multi")


def stored_files() -> dict:
    """The last Premier League / Champions League app files (outputs/multi) and free-source files
    (outputs/free -> free/) and the live file (outputs/live -> live/), added to every app snapshot by zsc.export so a La Liga update never drops them."""
    out = {}
    for folder, prefix in ((MULTI_OUT, ""), (os.path.join(ROOT, "outputs", "free"), "free/"),
                           (os.path.join(ROOT, "outputs", "live"), "live/"),
                           (os.path.join(ROOT, "outputs", "history"), "history/")):
        for base, _, names in os.walk(folder):
            for n in names:
                # the raw ESPN dump stays out of the app: live/now.json is its normalised form
                if n.endswith(".json") and not n.startswith("_ntfy") and n != "espn_today.json":
                    path = os.path.join(base, n)
                    rel = prefix + os.path.relpath(path, folder).replace(os.sep, "/")
                    out[rel] = json.load(open(path, encoding="utf-8"))
    return out


def export(app_data: str | None = None, n_sims_epl: int = 10000, n_sims_ucl: int = 20000,
           evaluate: bool = False) -> dict:
    """Write c/ENG1/*.json, c/UCL/*.json and comps.json to outputs/multi (and straight into the app data
    folder when app_data is given, so no new La Liga snapshot is needed)."""
    epl = epl_build(n_sims_epl, evaluate=evaluate)
    ucl = ucl_build(n_sims_ucl)
    files = {}
    for res in (epl, ucl):
        cid = res["comp"]
        codes = sorted({f["home"] for f in res["fixtures"]} | {f["away"] for f in res["fixtures"]})
        files[f"c/{cid}/teams.json"] = {"teams": team_entries(codes), "current": codes}
        files[f"c/{cid}/fixtures.json"] = {"generated_utc": res["generated_utc"], "fixtures": res["fixtures"]}
        files[f"c/{cid}/season.json"] = {k: v for k, v in res.items() if k != "fixtures"}
    free_dir = os.path.join(ROOT, "outputs", "free")
    free = sorted(n for n in os.listdir(free_dir) if n.endswith(".json") and not n.startswith("_ntfy")) \
        if os.path.isdir(free_dir) else []
    files["comps.json"] = {"generated_utc": now_utc(), "version": VERSION, "competitions": COMPETITIONS, "free": free}
    if evaluate:
        files["c/ENG1/season.json"]["evaluation"] = epl["evaluation"]
    else:
        ev_p = os.path.join(ROOT, "reports", "epl_evaluation.json")
        if os.path.exists(ev_p):
            files["c/ENG1/season.json"]["evaluation"] = json.load(open(ev_p, encoding="utf-8"))
    for root_dir in [MULTI_OUT] + ([app_data] if app_data else []):
        for rel, obj in files.items():
            path = os.path.join(root_dir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), default=_js)
            os.replace(tmp, path)
    return {"files": sorted(files), "epl_checks": epl["checks"], "ucl_checks": ucl["checks"],
            "epl_eval": epl.get("evaluation")}


def _js(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))
