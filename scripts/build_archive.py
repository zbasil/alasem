"""Deep analysis of the El Clásico archive (StatsBomb event data) -> app tables + story cards.

Player ratings use the position-relative formula (zsc/players.py, version 2) on the scale of La Liga 2015/16
(outputs/archive/sb_laliga1516_player_match.csv.gz, built by scripts/sb_players_1516.py); tactical match-ups come
from zsc/tactics.py.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import RAW_STATSBOMB  # noqa: E402

from zsc.cards import render_card  # noqa: E402
from zsc.deep import analyze_match  # noqa: E402
from zsc.inplay import InPlayModel  # noqa: E402
from zsc.pipeline import load_snapshot  # noqa: E402
from zsc import players as P, tactics as TAC  # noqa: E402
from zsc.events import short_name  # noqa: E402
import gzip, json  # noqa: E402,E401

MATCHES = [  # StatsBomb id, home, away, date
    ("69299", "Barcelona", "Real Madrid", "2010-11-29"),
    ("266424", "Real Madrid", "Barcelona", "2015-11-21"),
    ("267533", "Barcelona", "Real Madrid", "2016-04-02"),
]
TABLES = ["match", "stats", "insights", "players", "shots", "touches", "pass_nodes", "pass_edges", "timeline"]


def main():
    ip = InPlayModel.load(os.path.join(ROOT, "outputs", "models", "inplay.json"))
    ref_path = os.path.join(ROOT, "outputs", "archive", "sb_laliga1516_player_match.csv.gz")
    ref = pd.read_csv(ref_path) if os.path.exists(ref_path) else None
    tactics_out = {}
    snap = load_snapshot()
    out = {k: [] for k in TABLES}
    for sid, home, away, date in MATCHES:
        r = snap[(snap["date"] == date) & (snap["home"] == home) & (snap["away"] == away)].iloc[0]
        lam, mu = float(r["mkt_lh"]), float(r["mkt_la"])        # pre-match expectations from Bet365 odds
        res = analyze_match(os.path.join(RAW_STATSBOMB, f"events_{sid}.json.gz"), f"sb{sid}",
                            home, away, date, lam, mu, ip)
        assert (res["match"].iloc[0]["hg"], res["match"].iloc[0]["ag"]) == (r["hg"], r["ag"]), "score mismatch"
        events = json.load(gzip.open(os.path.join(RAW_STATSBOMB, f"events_{sid}.json.gz"), "rt", encoding="utf-8"))
        if ref is not None:
            rows, _ = P.match_rows(events, home, away)
            pmx = pd.DataFrame(rows)
            pmx["rating2"] = P.match_rating(pmx, ref)
            r2 = dict(zip(pmx["player"], pmx["rating2"]))
            grp = dict(zip(pmx["player"], pmx["group"]))
            pl = res["players"]
            pl["rating"] = pl["player"].map(r2).fillna(6.5)
            pl["group"] = pl["player"].map(grp)
            pl["group_ar"] = pl["group"].map(P.GROUP_AR)
            top = pl.sort_values("rating", ascending=False).iloc[0]
            ins = res["insights"]
            star = ins["row_id"].str.endswith("|star")
            ins.loc[star, "text"] = f"نجم المباراة حسب الحاسوب: {top['name_ar']} (تقييم {top['rating']:.1f} مقارنة بلاعبي مركزه)"
        tactics_out[f"sb{sid}"] = TAC.matchups(events, home, away, name=short_name)
        for k in TABLES:
            out[k].append(res[k])
        os.makedirs(os.path.join(ROOT, "outputs", "archive"), exist_ok=True)
        months = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر",
                  "نوفمبر", "ديسمبر"]
        y, mo, d = date.split("-")
        render_card(res["report"], os.path.join(ROOT, "outputs", "archive", f"clasico_{date}.png"),
                    data_credit="بيانات: StatsBomb (بيانات مفتوحة)",
                    subtitle=f"أرشيف الكلاسيكو · {int(d)} {months[int(mo) - 1]} {y}", pill="من الأرشيف")
        print(f"{date} {home} {r['hg']}-{r['ag']} {away}: ok")
    with open(os.path.join(ROOT, "outputs", "dashboard", "deep_tactics.json"), "w", encoding="utf-8") as f:
        json.dump(tactics_out, f, ensure_ascii=False, indent=1)
    names = {"match": "deep_matches", "stats": "deep_stats", "insights": "deep_insights", "players": "deep_players",
             "shots": "deep_shots", "touches": "deep_touches", "pass_nodes": "deep_pass_nodes",
             "pass_edges": "deep_pass_edges", "timeline": "deep_timeline"}
    for k in TABLES:
        df = pd.concat(out[k], ignore_index=True)
        p = os.path.join(ROOT, "outputs", "dashboard", f"{names[k]}.csv")
        df.to_csv(p, index=False)
        print(f"  {names[k]}.csv: {len(df)} rows, {os.path.getsize(p) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
