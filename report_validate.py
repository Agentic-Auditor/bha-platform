"""
report_validate.py — invariant checker for BHA report `data` dicts.

Runs a set of structural / logical / content invariants over the data that
feeds pdf_report.generate_pdf(). Used by the QA harness and can be wired into
generation as a guard so regressions are caught automatically instead of by
manual visual review.

    validate_report(data) -> list[Issue]   # empty list == clean
"""

from collections import namedtuple

Issue = namedtuple("Issue", ["code", "severity", "detail"])

DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]

# words that only make sense for businesses with physical food/raw materials
_RESTAURANT_WORDS = ["วัตถุดิบ", "food cost", "Food Cost", "ครัว", "เมนู", "ของสด", "spoilage", "Waste / Spoilage"]
# business types that legitimately deal in physical inventory / materials
_PHYSICAL_TYPES = {"restaurant", "retail", "ecommerce", "oem", "brand", "health_beauty"}


def _band(pct):
    if pct <= 33.3:
        return "RED"
    if pct <= 66.7:
        return "YELLOW"
    return "GREEN"


def validate_report(data):
    issues = []

    def add(code, sev, detail):
        issues.append(Issue(code, sev, detail))

    bt = data.get("business_type", "")
    dim_pct = data.get("dim_pct", {})
    dim_light = data.get("dim_light", {})
    overall = data.get("overall_score")
    grade = data.get("overall_grade")

    # 1) weighted-score reconciliation against the weights actually used by scoring
    try:
        from scoring import BUSINESS_TYPE_WEIGHTS, DIM_WEIGHTS, _grade
        w = BUSINESS_TYPE_WEIGHTS.get(bt, DIM_WEIGHTS)
        if abs(sum(w.values()) - 1.0) > 0.001:
            add("WEIGHTS_NOT_100", "HIGH", f"weights for {bt} sum to {sum(w.values())}")
        calc = sum(dim_pct.get(d, 0) * w.get(d, 0) for d in DIMS)
        if overall is not None and abs(calc - overall) > 1.0:
            add("WEIGHT_RECONCILE", "HIGH", f"weighted={calc:.1f} vs overall={overall:.1f}")
        # grade consistency
        red_count = sum(1 for d in DIMS if dim_light.get(d) == "RED")
        if grade and _grade(overall, red_count) != grade:
            add("GRADE_MISMATCH", "HIGH", f"computed={_grade(overall, red_count)} vs shown={grade}")
    except Exception as e:
        add("SCORING_IMPORT", "MED", str(e))

    # 2) light vs pct band (RED may be force-set by a hard-floor red flag)
    for d in DIMS:
        pct = dim_pct.get(d)
        light = dim_light.get(d)
        if pct is None or light is None:
            add("MISSING_DIM", "HIGH", f"{d} missing pct/light")
            continue
        exp = _band(pct)
        if light != exp and not (light == "RED" and exp in ("YELLOW", "GREEN")):
            add("LIGHT_BAND", "HIGH", f"{d} pct={pct} band={exp} but light={light}")
        # 3) display-rounding contradiction: int(pct) shown but band differs at the edge
        if _band(float(int(pct))) != _band(pct) and light != "RED":
            add("DISPLAY_ROUNDING", "MED", f"{d} pct={pct} floors to {int(pct)} (band edge)")

    # 4) empty/!=expected sections
    rm = data.get("roadmap") or {}
    if not any(ph.get("items") for ph in rm.get("phases", [])):
        add("ROADMAP_EMPTY", "HIGH", "roadmap has no items in any phase")
    narr = data.get("narratives") or {}
    for d in DIMS:
        n = narr.get(d) or {}
        if not n.get("summary"):
            add("NARRATIVE_EMPTY", "MED", f"{d} summary empty")
        if not n.get("actions"):
            add("ACTIONS_EMPTY", "MED", f"{d} actions empty")
        if not n.get("fact"):
            add("FACT_EMPTY", "MED", f"{d} fact (ข้อเท็จจริง) empty")
        if not n.get("principle_benefit"):
            add("PRINCIPLE_EMPTY", "MED", f"{d} principle_benefit empty")
        if dim_light.get(d) != "GREEN" and not n.get("consequence"):
            add("CONSEQUENCE_EMPTY", "MED", f"{d} consequence empty (non-GREEN)")

    # 5) KPI completeness
    for g in (data.get("kpi_table") or []):
        if not g.get("rows"):
            add("KPI_EMPTY", "HIGH", f'{g.get("dim")} no KPI rows')
        for row in g.get("rows", []):
            if any((c is None or str(c).strip() == "") for c in row):
                add("KPI_BLANK_CELL", "MED", f'{g.get("dim")} blank cell in {row}')

    # 6) cross-industry language leakage
    if bt and bt not in {"restaurant"}:
        bench = data.get("benchmark") or {}
        for d in DIMS:
            n = narr.get(d) or {}
            blob = " ".join(n.get("actions", [])) + " " + str(n.get("summary", "")) + " " + str(n.get("current_state", ""))
            hits = [w for w in _RESTAURANT_WORDS if w in blob]
            if hits and bt not in _PHYSICAL_TYPES:
                add("LEAK_RESTAURANT_WORDS", "HIGH", f"{bt} {d} recommendation/narrative contains {hits}")
            bhits = [w for w in _RESTAURANT_WORDS if w in str(bench.get(d, ""))]
            if bhits and bt not in _PHYSICAL_TYPES:
                add("LEAK_BENCHMARK", "HIGH", f"{bt} {d} benchmark contains {bhits}")

    # 7) priority / 3-things consistency
    tops = data.get("top_risks", [])
    nongreen = [d for d in DIMS if dim_light.get(d) != "GREEN"]
    for d in tops:
        if nongreen and d not in nongreen:
            add("TOPRISK_GREEN", "MED", f"top_risk {d} is GREEN")
    prio = rm.get("priority_dims", [])
    if nongreen and prio and set(prio) != set(nongreen):
        add("PRIORITY_SET", "LOW", f"priority_dims {prio} != non-green {nongreen}")

    # 8) red-flag entries must be bare dimension codes (D1..D7), not display
    #    strings — guards the "flag D1" placeholder regression in the hard-floor
    #    box, where the renderer maps each code to a Thai dimension name + reason.
    for rf in (data.get("red_flags") or []):
        if rf not in DIMS:
            add("RED_FLAG_FORMAT", "LOW", f"red_flag {rf!r} is not a bare dim code (D1..D7)")

    return issues


class ReportValidationError(Exception):
    """Raised by assert_report_ok in strict mode when a HIGH invariant fails."""


def assert_report_ok(data, strict=False, log=None):
    """Generation-time guard around validate_report.

    Logs every issue via `log` (a callable taking one string; default no-op),
    and — when `strict` is True — raises ReportValidationError if any
    HIGH-severity issue is present. Returns the full issue list so callers can
    inspect or count them. Wire this in right before generate_pdf so invariant
    regressions are caught before a (paid) PDF is ever produced.
    """
    issues = validate_report(data)
    if log:
        for i in issues:
            log(f"[REPORT_VALIDATE] {i.severity} {i.code}: {i.detail}")
    highs = [i for i in issues if i.severity == "HIGH"]
    if strict and highs:
        raise ReportValidationError(
            f"{len(highs)} HIGH invariant violation(s): "
            + "; ".join(f"{i.code}:{i.detail}" for i in highs)
        )
    return issues
