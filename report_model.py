"""
report_model.py — DB-free report assembly (the single source of truth).

`assemble_report_model` takes already-fetched rows (a `results` row dict, the
`assessment` dict, and the `answers` map) plus open DB handles for the narrative
cache / benchmark, and returns the one model dict that every consumer (summary,
full results, PDF, email) renders from. It contains the phase-2 behaviour:
scores / lights / grade are recomputed LIVE from the answers via
`calculate_score` (the frozen `results` columns are only a submit-time cache and
are used only as a fallback when answers are missing).

This module intentionally imports NO Flask / DB driver, so the assembly logic is
unit-testable anywhere (CI, sandbox) with a fake DB. `app.build_report_model`
does the DB fetch and delegates here.
"""
import json

from scoring import calculate_score, ALL_DIMENSIONS
from narratives import get_narrative, get_roadmap, get_kpi_table, get_benchmark


def assemble_report_model(result, assessment, answers, context,
                          assessment_id=None, narr_db=None, bmark_db=None):
    """Assemble the report model from already-fetched data.

    Args:
        result:     dict of the frozen `results` row (used only as fallback).
        assessment: dict with at least business_type / business_name / email.
        answers:    {question_id: score} — the authoritative input.
        context:    narrative context dict (age/revenue buckets, etc.).
        assessment_id: echoed into the model.
        narr_db:    open handle for the narrative cache (may be a no-op fake).
        bmark_db:   open handle for benchmark lookups (currently unused by
                    get_benchmark, kept for signature stability).

    Returns the model dict consumed by pdf_report / the API responses.
    """
    business_type = assessment.get("business_type", "")

    # Phase 2 — recompute LIVE from answers so the report can't drift from the
    # frozen results cache; fall back to the frozen columns only for legacy rows
    # that have no stored answers.
    if answers:
        live = calculate_score(answers, business_type)
        dim_lights = dict(live["dim_light"])
        dim_pcts   = dict(live["dim_pct"])
        dim_raws   = dict(live["dim_raw"])
        overall_score  = live["overall"]
        overall_grade  = live["grade"]
        red_flags      = live["red_flags"]
        red_flag_count = live["red_count"]
    else:
        dim_lights, dim_pcts, dim_raws = {}, {}, {}
        for d in ALL_DIMENSIONS:
            k = d.lower()
            dim_lights[d] = result[f"{k}_light"]
            dim_pcts[d]   = result[f"{k}_pct"]
            dim_raws[d]   = result[f"{k}_raw"]
        overall_score  = result["overall_score"]
        overall_grade  = result["overall_grade"]
        red_flags      = json.loads(result["red_flags"] or "[]")
        red_flag_count = result["red_flag_count"]

    # Narratives + their one-line summaries, built once for all 7 dimensions.
    narratives_out, summaries = {}, {}
    for d in ALL_DIMENSIONS:
        n = get_narrative(d, dim_lights[d], answers, context, narr_db)
        narratives_out[d] = n
        summaries[d]      = n.get("summary", "")

    non_green = [d for d in ALL_DIMENSIONS if dim_lights[d] != "GREEN"]
    top_risks = sorted(non_green, key=lambda d: dim_raws[d])[:2]

    roadmap_data   = get_roadmap(business_type, dim_lights, dim_pcts)
    kpi_data       = get_kpi_table(business_type, dim_lights)
    benchmark_data = get_benchmark(business_type, dim_lights, bmark_db)

    return {
        "assessment_id":  assessment_id,
        "overall_score":  overall_score,
        "overall_grade":  overall_grade,
        "red_flags":      red_flags,
        "red_flag_count": red_flag_count,
        "dim_light":      dim_lights,
        "dim_pct":        dim_pcts,
        "dim_raw":        dim_raws,
        "top_risks":      top_risks,
        "narratives":     narratives_out,
        "summaries":      summaries,
        "business_name":  assessment.get("business_name", ""),
        "business_type":  business_type,
        "email":          assessment.get("email", ""),
        "roadmap":        roadmap_data,
        "kpi_table":      kpi_data,
        "benchmark":      benchmark_data,
    }
