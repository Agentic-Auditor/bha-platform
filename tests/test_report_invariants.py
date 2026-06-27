"""
Permanent regression guard for BHA report generation.

Builds a matrix of (business_type x score-profile) cases, asserts the report
`data` passes all invariants in report_validate, and that generate_pdf() does
not raise and produces a non-trivial PDF. Run with: pytest -q

This replaces case-by-case manual QA: any future change that reintroduces a
known class of bug (weight mismatch, colour-band drift, empty roadmap,
cross-industry language leakage, blank KPI cells, grade mismatch, render
crash) fails the suite automatically.
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scoring
import narratives as N
from narratives import detect_patterns, _static_fallback
import pdf_report
from report_validate import validate_report

ALL_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
QIDS = [f"{d}.{q}" for d in range(1, 8) for q in range(1, 7)]
TYPES = list(scoring.BUSINESS_TYPE_WEIGHTS.keys()) + ["general"]


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


def _profiles():
    yield "allmin", {q: 0 for q in QIDS}
    yield "allmax", {q: 3 for q in QIDS}
    yield "allmid", {q: 2 for q in QIDS}
    single = {q: 3 for q in QIDS}
    for q in [f"3.{i}" for i in range(1, 7)]:
        single[q] = 0
    yield "single_low", single
    for seed in range(6):
        rng = random.Random(seed)
        yield f"rand{seed}", {q: rng.randint(0, 3) for q in QIDS}


def test_no_high_severity_invariant_violations():
    failures = []
    for bt in TYPES:
        for label, answers in _profiles():
            data = _build(bt, answers)
            highs = [i for i in validate_report(data) if i.severity == "HIGH"]
            if highs:
                failures.append((bt, label, [(i.code, i.detail) for i in highs]))
    assert not failures, "HIGH-severity invariant violations:\n" + "\n".join(map(str, failures))


def test_generate_pdf_never_crashes():
    for bt in TYPES:
        for label, answers in _profiles():
            data = _build(bt, answers)
            buf = pdf_report.generate_pdf(data)
            blob = buf.read()
            assert len(blob) > 5000, f"{bt}/{label} produced a tiny/empty PDF ({len(blob)} bytes)"
