"""
gen_v2_samples.py — smoke-test + sample generator for the v2 narrative schema
(Fact / Principle & Benefit / Consequence).

Run this AFTER closing the file in your editor and stopping the dev server,
so Python reads the real files (not a locked/stale copy):

    cd BHA_Platform
    python -B gen_v2_samples.py

It uses the static-fallback path (no ANTHROPIC_API_KEY needed) which now
produces fact / principle_benefit / consequence, builds 3 sample PDFs, and
checks report invariants. PDFs are written next to this script.
"""
import os
import sys
import random

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import narratives as N
import scoring
import pdf_report
from narratives import detect_patterns, _static_fallback, _fact_sentence
from report_validate import validate_report

ALL = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
QIDS = [f"{d}.{q}" for d in range(1, 8) for q in range(1, 7)]


def build(bt, answers):
    res = scoring.calculate_score(answers, bt)
    narr = {}
    for d in ALL:
        light = res["dim_light"][d]
        narr[d] = _static_fallback(d, light, bt,
                                   patterns=detect_patterns(d, answers), answers=answers)
        N.apply_industry_overrides(narr[d], d, light, bt)
    nong = [d for d in ALL if res["dim_light"][d] != "GREEN"]
    return {
        "roadmap": N.get_roadmap(bt, res["dim_light"], res["dim_pct"]),
        "kpi_table": N.get_kpi_table(bt, res["dim_light"]),
        "benchmark": N.get_benchmark(bt, res["dim_light"], None),
        "business_name": f"ตัวอย่าง {bt}", "email": "t@t.co", "business_type": bt,
        "overall_grade": res["grade"], "overall_score": res["overall"],
        "dim_light": res["dim_light"], "dim_pct": res["dim_pct"], "dim_raw": res["dim_raw"],
        "red_flags": list(res["red_flags"]),
        "top_risks": sorted(nong, key=lambda d: res["dim_raw"][d])[:2],
        "narratives": narr,
    }


PROFILES = {
    "restaurant_weak": ("restaurant", {**{q: 0 for q in QIDS},
                                       **{q: 1 for q in ["1.2", "2.6", "3.1", "4.3"]}}),
    "ecommerce_mixed": ("ecommerce", {q: random.Random(3).randint(0, 3) for q in QIDS}),
    "service_strong":  ("service",   {**{q: 3 for q in QIDS},
                                      **{q: 1 for q in ["5.2", "6.2"]}}),
}


def main():
    print("schema:", N.NARRATIVE_SCHEMA_VERSION)
    total_high = 0
    for name, (bt, ans) in PROFILES.items():
        data = build(bt, ans)
        issues = validate_report(data)
        highs = [i for i in issues if i.severity == "HIGH"]
        total_high += len(highs)
        d0 = data["top_risks"][0] if data["top_risks"] else "D1"
        n = data["narratives"][d0]
        print(f"\n=== {name} ({bt}) grade={data['overall_grade']} HIGH={len(highs)} sample_dim={d0} ===")
        for i in highs:
            print("   HIGH", i.code, i.detail)
        print("   fact:", n.get("fact"))
        print("   principle_benefit:", (n.get("principle_benefit") or "")[:90], "...")
        print("   consequence:", n.get("consequence"))
        pdf = pdf_report.generate_pdf(data)
        pdf = pdf.getvalue() if hasattr(pdf, "getvalue") else pdf
        out = os.path.join(HERE, f"BHA_v2_{name}.pdf")
        with open(out, "wb") as f:
            f.write(pdf)
        print(f"   PDF {len(pdf):,} bytes -> {os.path.basename(out)}")
    print("\nRESULT:", "PASS (0 HIGH issues)" if total_high == 0 else f"FAIL ({total_high} HIGH)")


if __name__ == "__main__":
    main()
