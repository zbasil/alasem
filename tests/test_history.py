"""History files behind head-to-head and the claim lab: real results, no duplicates, this season included."""
import collections

import pytest

from zsc import history


@pytest.fixture(scope="module")
def docs():
    return history.build(write=False)


def test_known_clasicos(docs):
    rows = [r for r in docs["ESP1"]["rows"] if {r[1], r[2]} == {"BAR", "RMA"}]
    s2023 = [(r[0], r[1], r[3], r[4]) for r in rows if r[7] == 2023]
    assert s2023 == [(20231028, "BAR", 1, 2), (20240421, "RMA", 3, 2)]
    assert len(rows) == 2 * (2026 - 1993)          # two league meetings a season since 1993/94


def test_no_duplicates_and_full_seasons(docs):
    for comp, n in (("ESP1", 380), ("ENG1", 380)):
        rows = docs[comp]["rows"]
        keys = [(r[0], r[1], r[2]) for r in rows]
        assert len(keys) == len(set(keys))
        per = collections.Counter(r[7] for r in rows)
        # every finished season is complete (La Liga had 22 clubs, 462 matches, in 1995/96 and 1996/97)
        assert all(per[s] == (462 if comp == "ESP1" and s in (1995, 1996) else n) for s in per if s < 2026)


def test_scope_and_current_season(docs):
    for doc in docs.values():
        assert "الدوري فقط" in doc["scope_ar"]
        assert doc["coverage"]["seasons"][1] == 2026 and doc["coverage"]["n"] == len(doc["rows"])
    epl = docs["ENG1"]["rows"]
    assert any(r[1] == "ARS" and r[2] == "TOT" and r[0] == 20031108 and (r[3], r[4]) == (2, 1) for r in epl)
