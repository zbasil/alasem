"""The app's data snapshot and the browser ports of the models.

These tests read app/data (the current snapshot written by `python -m zsc export`) and run the JavaScript
checks with Node when Node is installed.
"""

import json
import os
import shutil
import subprocess

import numpy as np
import pytest

from zsc.paths import APP_DATA, ROOT


def load(rel):
    with open(os.path.join(APP_DATA, rel), encoding="utf-8") as f:
        return json.load(f)


pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(APP_DATA, "meta.json")), reason="no app snapshot yet")


def test_every_forecast_sums_to_one_and_minute_zero_matches():
    fx = load("fixtures.json")["fixtures"]
    assert len(fx) == 380
    for f in fx:
        if f.get("p"):
            assert abs(sum(f["p"]) - 1) < 2e-6, f["match_id"]      # numbers are stored with 6 decimals
    md = load("matches/md10.json")["matches"]
    for mid, m in md.items():
        for t in m["tracks"].values():
            assert abs(sum(t["p"]) - 1) < 2e-6
        si = m.get("scenario_inputs")
        if si and not m.get("score"):
            from zsc.dixon_coles import outcome_probs, score_matrix
            from zsc.inplay import InPlayModel
            ip = InPlayModel.from_json(si["inplay"])
            p0 = ip.probs(si["lam"], si["mu"], 0, 0, 0, rho=si["rho"])
            pre = outcome_probs(score_matrix(si["lam"], si["mu"], si["rho"]))[0]
            assert np.allclose(p0, pre, atol=1e-12)
            assert np.allclose(pre, m["tracks"][m["displayed_track"]]["p"], atol=2e-6)


def test_ids_are_stable_and_unique():
    fx = load("fixtures.json")["fixtures"]
    ids = [f["match_id"] for f in fx]
    assert len(set(ids)) == len(ids)
    assert all(i.startswith("ESP1-2026-") for i in ids)
    teams = load("teams.json")
    assert len(teams["current"]) == 20
    for f in fx:
        assert f["home"] in teams["teams"] and f["away"] in teams["teams"]


def test_played_matches_have_results_and_no_future_forecast():
    fx = load("fixtures.json")["fixtures"]
    for f in fx:
        if f.get("score"):
            assert f["status"] in ("played", "HT")
            if f.get("logged"):
                assert f["logged"]["issued_at"] < f["kickoff_utc"]


def test_season_projection_is_consistent():
    s = load("season.json")
    rows = s["projection"]
    assert len(rows) == 20
    assert abs(sum(r["p_title"] for r in rows) - 1) < 1e-5
    assert abs(sum(r["p_releg"] for r in rows) - 3) < 1e-5
    for r in rows:
        assert abs(sum(r["pos_dist"]) - 1) < 1e-5
        assert r["pts_p10"] <= r["exp_pts"] <= r["pts_p90"]
        assert r["exp_pts"] >= r["pts_now"]
    w = s["whatif"]
    assert len(w["fixtures"]) == 380 - sum(r["P"] for r in s["table"]) // 2


def test_accuracy_numbers_come_from_the_report():
    a = load("accuracy.json")
    with open(os.path.join(ROOT, "reports", "evaluation.json"), encoding="utf-8") as f:
        rep = json.load(f)
    for src, sc in rep["prematch"]["test"]["scores"].items():
        for k, v in sc.items():
            assert abs(a["prematch"]["test"]["scores"][src][k] - v) < 1e-6, (src, k)
    assert a["registry"]["displayed_track"] in ("market", "independent")


def test_meta_has_versions_and_feature_status():
    m = load("meta.json")
    for k in ("platform", "data", "prematch_market", "prematch_independent", "inplay", "season"):
        assert m["versions"][k]
    assert all(f["status"] in ("active", "partial", "active_local", "free_adapter", "needs_key", "needs_source") for f in m["features"])


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_javascript_ports_match_python():
    r = subprocess.run(["node", os.path.join(ROOT, "tests", "js", "test_models.js")], capture_output=True, text=True, cwd=ROOT, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_english_interface_translator():
    r = subprocess.run(["node", os.path.join(ROOT, "tests", "js", "test_i18n.js")], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
