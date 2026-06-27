"""
Phase-2 regression tests:

 1. assert_report_ok — the generation-time invariant guard wired into
    app._build_pdf_bytes. Clean data passes (even in strict mode); a broken
    invariant is logged, and raises ReportValidationError ONLY in strict mode
    (fail-soft otherwise, so production paid delivery is never blocked by a
    stray issue).

 2. Live-light contract — mirrors build_report_model's phase-2 change: the
    report's traffic lights are derived LIVE from the answers via
    calculate_score (not read from frozen columns), so they can never drift
    and the assembled data carries no HIGH invariant violations.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scoring
import narratives as N
from narratives import detect_patterns, _static_fallback
from report_validate import validate_report, assert_report_ok, ReportValidationError

ALL_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
QIDS = [f"{d}.{q}" for d in range(1, 8) for q in range(1, 7)]


def _build(bt, answers):
    res = scoring.calculate_score(answers, bt)
    narr = {}
    for d in ALL_DIMS:
        light = res["dim_light"][d]
        narr[d] = _static_fallback(d, light, bt, patterns=detect_patterns(d, answers), answers=answers)
        N.apply_industry_overrides(narr[d], d, light, bt)
    non_green = [d for d in ALL_DIMS if res["dim_light"][d] != "GREEN"]
    return {
        "roadmap": N.get_roadmap(bt, res["dim_light"], res["dim_pct"]),
        "kpi_table": N.get_kpi_table(bt, res["dim_light"]),
        "benchmark": N.get_benchmark(bt, res["dim_light"], None),
        "business_name": f"Test {bt}", "email": "t@t.co", "business_type": bt,
        "overall_grade": res["grade"], "overall_score": res["overall"],
        "dim_light": res["dim_light"], "dim_pct": res["dim_pct"], "dim_raw": res["dim_raw"],
        "red_flags": list(res["red_flags"]),
        "top_risks": sorted(non_green, key=lambda d: res["dim_raw"][d])[:2],
        "narratives": narr,
    }


# ── 1. validation guard ──────────────────────────────────────────
def test_guard_passes_clean_even_in_strict():
    data = _build("general", {q: 3 for q in QIDS})
    issues = assert_report_ok(data, strict=True)  # must NOT raise
    assert not [i for i in issues if i.severity == "HIGH"]


def test_guard_raises_on_high_when_strict():
    data = _build("general", {q: 0 for q in QIDS})
    data["roadmap"] = {"phases": [], "priority_dims": []}  # -> ROADMAP_EMPTY (HIGH)
    with pytest.raises(ReportValidationError):
        assert_report_ok(data, strict=True)


def test_guard_fail_soft_logs_but_does_not_raise():
    data = _build("general", {q: 0 for q in QIDS})
    data["roadmap"] = {"phases": [], "priority_dims": []}
    logs = []
    issues = assert_report_ok(data, strict=False, log=logs.append)  # must NOT raise
    assert any(i.code == "ROADMAP_EMPTY" for i in issues)
    assert any("ROADMAP_EMPTY" in m for m in logs), "issue should be logged"


# ── 2. live-light contract (build_report_model phase-2) ──────────
_LIVE_CASES = [
    ("restaurant", {**{q: 0 for q in QIDS}, **{q: 1 for q in ["1.2", "2.6", "3.1", "4.3"]}}),
    ("ecommerce",  {q: __import__("random").Random(3).randint(0, 3) for q in QIDS}),
    ("service",    {**{q: 3 for q in QIDS}, **{q: 1 for q in ["5.2", "6.2"]}}),
    ("general",    {q: 2 for q in QIDS}),
]


@pytest.mark.parametrize("bt,answers", _LIVE_CASES, ids=[c[0] for c in _LIVE_CASES])
def test_lights_derived_live_from_answers(bt, answers):
    res = scoring.calculate_score(answers, bt)
    data = _build(bt, answers)
    for d in ALL_DIMS:
        assert data["dim_light"][d] == res["dim_light"][d], f"{d} light not live-derived"
        assert data["dim_pct"][d] == res["dim_pct"][d], f"{d} pct not live-derived"
    assert data["overall_grade"] == res["grade"]
    assert not [i for i in validate_report(data) if i.severity == "HIGH"]
