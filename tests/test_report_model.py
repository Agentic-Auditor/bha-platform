"""
Integration-ish test for report_model.assemble_report_model (the DB-free core
that app.build_report_model delegates to). Uses a fake DB so it runs in CI with
no Postgres / Flask. Proves the phase-2 contract end-to-end at the assembly
layer: lights/score/grade come LIVE from answers and OVERRIDE stale frozen
`results` columns; and that the frozen columns are used only as a fallback when
answers are missing.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scoring
from report_model import assemble_report_model

ALL_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
QIDS = [f"{d}.{q}" for d in range(1, 8) for q in range(1, 7)]


class _FakeCursor:
    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _FakeDB:
    """Minimal stand-in: every narrative_cache read misses, so get_narrative
    falls through to the deterministic static fallback (no API key needed)."""
    def execute(self, *a, **k):
        return _FakeCursor()

    def commit(self):
        pass

    def close(self):
        pass


def _frozen(light, pct, raw, overall, grade, red_flags="[]", rfc=0):
    row = {"overall_score": overall, "overall_grade": grade,
           "red_flags": red_flags, "red_flag_count": rfc}
    for d in ALL_DIMS:
        k = d.lower()
        row[f"{k}_light"] = light
        row[f"{k}_pct"] = pct
        row[f"{k}_raw"] = raw
    return row


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    # Force the static-fallback narrative path (no live Anthropic call).
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_live_recompute_overrides_stale_frozen_columns():
    # Frozen cache LIES: says everything GREEN / STRONG / 99.9.
    stale = _frozen(light="GREEN", pct=100.0, raw=18, overall=99.9, grade="STRONG")
    answers = {q: 0 for q in QIDS}  # ...but the real answers are all zero.
    assessment = {"business_type": "restaurant", "business_name": "X", "email": "x@x.co"}

    model = assemble_report_model(stale, assessment, answers, context={},
                                  assessment_id="A1", narr_db=_FakeDB(), bmark_db=_FakeDB())

    exp = scoring.calculate_score(answers, "restaurant")
    assert model["overall_score"] == exp["overall"] and model["overall_score"] != 99.9
    assert model["overall_grade"] == exp["grade"] == "CRITICAL"
    assert model["red_flag_count"] == exp["red_count"]
    for d in ALL_DIMS:
        assert model["dim_light"][d] == exp["dim_light"][d] == "RED"
        assert model["dim_pct"][d] == exp["dim_pct"][d]
    # narratives assembled for all dims
    assert all(model["narratives"][d].get("summary") for d in ALL_DIMS)
    assert model["kpi_table"] and model["roadmap"]["phases"]


def test_falls_back_to_frozen_columns_when_no_answers():
    frozen = _frozen(light="YELLOW", pct=55.0, raw=10, overall=58.0, grade="WATCH",
                     red_flags='["D1"]', rfc=1)
    assessment = {"business_type": "service", "business_name": "Y", "email": "y@y.co"}

    model = assemble_report_model(frozen, assessment, answers={}, context={},
                                  assessment_id="A2", narr_db=_FakeDB(), bmark_db=_FakeDB())

    assert model["overall_score"] == 58.0
    assert model["overall_grade"] == "WATCH"
    assert model["red_flags"] == ["D1"]
    for d in ALL_DIMS:
        assert model["dim_light"][d] == "YELLOW"
        assert model["dim_pct"][d] == 55.0
