"""
Golden-sample regression test — freezes the verified scoring baseline.

For a fixed set of canonical (business_type x answer) profiles, asserts that
scoring.calculate_score reproduces EXACTLY the frozen overall score, grade,
red-flags and every dimension's pct + traffic-light. Any future change that
shifts a number or a light fails here loudly.

It also asserts the v2 narrative contract (fact / principle_benefit /
consequence) holds on the deterministic static-fallback path.

If a scoring change is INTENTIONAL, regenerate the baseline with gen_golden.py
and review the diff before committing.

Run: pytest -q tests/test_golden.py
"""
import os
import sys
import json

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scoring
import narratives as N
from narratives import detect_patterns, _static_fallback

ALL_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]

_GOLDEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_samples.json")
with open(_GOLDEN_PATH, encoding="utf-8") as _f:
    _GOLDEN = json.load(_f)
_CASES = _GOLDEN["cases"]
_IDS = [c["name"] for c in _CASES]


@pytest.mark.parametrize("case", _CASES, ids=_IDS)
def test_scoring_matches_golden(case):
    bt = case["business_type"]
    answers = {k: int(v) for k, v in case["answers"].items()}
    exp = case["expected"]
    res = scoring.calculate_score(answers, bt)

    assert res["overall"] == exp["overall_score"], f"overall drift: {res['overall']} != {exp['overall_score']}"
    assert res["grade"] == exp["overall_grade"], f"grade drift: {res['grade']} != {exp['overall_grade']}"
    assert res["red_count"] == exp["red_count"]
    assert sorted(res["red_flags"]) == exp["red_flags"], "red-flag set drift"
    for d in ALL_DIMS:
        assert res["dim_pct"][d] == exp["dim_pct"][d], f"{d} pct drift: {res['dim_pct'][d]} != {exp['dim_pct'][d]}"
        assert res["dim_light"][d] == exp["dim_light"][d], f"{d} light drift: {res['dim_light'][d]} != {exp['dim_light'][d]}"


@pytest.mark.parametrize("case", _CASES, ids=_IDS)
def test_v2_narrative_contract(case):
    """Every dimension narrative on the static-fallback path must carry the v2
    fields: a deterministic `fact`, a `principle_benefit`, and (for non-GREEN)
    a `consequence`, plus the base summary/actions."""
    bt = case["business_type"]
    answers = {k: int(v) for k, v in case["answers"].items()}
    res = scoring.calculate_score(answers, bt)
    for d in ALL_DIMS:
        light = res["dim_light"][d]
        n = _static_fallback(d, light, bt, patterns=detect_patterns(d, answers), answers=answers)
        N.apply_industry_overrides(n, d, light, bt)
        assert n.get("summary"), f"{case['name']} {d} summary empty"
        assert n.get("actions"), f"{case['name']} {d} actions empty"
        assert n.get("fact"), f"{case['name']} {d} fact (ข้อเท็จจริง) empty"
        assert n.get("principle_benefit"), f"{case['name']} {d} principle_benefit empty"
        if light != "GREEN":
            assert n.get("consequence"), f"{case['name']} {d} consequence empty (non-GREEN)"
