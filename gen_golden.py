"""
gen_golden.py — (re)generate the frozen scoring baseline `tests/golden_samples.json`.

Run ONLY when a scoring change is INTENTIONAL, then review the JSON diff before
committing:

    cd BHA_Platform
    python gen_golden.py > tests/golden_samples.json

The baseline locks scoring.calculate_score: overall score, grade, red-flags and
every dimension's pct + traffic-light, for a deterministic matrix of
(business_type x answer-shape) cases. test_golden.py asserts the live code
reproduces it exactly.

Coverage: every business_type (so per-type weight tables are pinned) via a
seeded "mixed" profile + an all-strong profile, plus global extremes, plus the
three narrative samples used by gen_v2_samples.
"""
import json
import random

import scoring

ALL = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
QIDS = [f"{d}.{q}" for d in range(1, 8) for q in range(1, 7)]
TYPES = list(scoring.BUSINESS_TYPE_WEIGHTS.keys()) + ["general"]


def _seeded(bt):
    rng = random.Random(f"golden-{bt}")
    return {q: rng.randint(0, 3) for q in QIDS}


def _cases():
    for bt in TYPES:
        yield f"{bt}_mixed", bt, _seeded(bt)
    for bt in TYPES:
        yield f"{bt}_strong", bt, {q: 3 for q in QIDS}
    yield "allmin", "general", {q: 0 for q in QIDS}
    yield "allmid", "general", {q: 2 for q in QIDS}
    yield "nsample_restaurant_weak", "restaurant", {**{q: 0 for q in QIDS},
                                            **{q: 1 for q in ["1.2", "2.6", "3.1", "4.3"]}}
    yield "nsample_ecommerce_mixed", "ecommerce", {q: random.Random(3).randint(0, 3) for q in QIDS}
    yield "nsample_service_strong", "service", {**{q: 3 for q in QIDS},
                                        **{q: 1 for q in ["5.2", "6.2"]}}


def build():
    out = {
        "schema": "golden-v1",
        "note": "Frozen scoring baseline. Regenerate ONLY on an intentional "
                "scoring change (python gen_golden.py > tests/golden_samples.json) "
                "and review the diff.",
        "cases": [],
    }
    seen = set()
    for name, bt, answers in _cases():
        assert name not in seen, f"duplicate case name {name}"
        seen.add(name)
        answers = {q: int(answers[q]) for q in QIDS}
        r = scoring.calculate_score(answers, bt)
        out["cases"].append({
            "name": name,
            "business_type": bt,
            "answers": answers,
            "expected": {
                "overall_score": r["overall"],
                "overall_grade": r["grade"],
                "red_count": r["red_count"],
                "red_flags": sorted(r["red_flags"]),
                "dim_pct": r["dim_pct"],
                "dim_light": r["dim_light"],
            },
        })
    return out


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
