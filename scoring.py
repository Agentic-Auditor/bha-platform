DIM_QUESTIONS = {
    "D1": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6"],
    "D2": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"],
    "D3": ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6"],
    "D4": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6"],
    "D5": ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6"],
    "D6": ["6.1", "6.2", "6.3", "6.4", "6.5", "6.6"],
    "D7": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6"],
}

DIM_MAX_RAW = 18  # 6 questions x max score 3

RED_FLAG_QUESTIONS = {
    "D1": ["1.1"],
    "D2": ["2.1"],
    "D3": ["3.1"],
    "D4": ["4.1"],
    "D5": ["5.1"],
    "D6": ["6.2"],
    "D7": ["7.1", "7.2"],
}

DIM_WEIGHTS = {
    "D1": 0.20, "D2": 0.15, "D3": 0.15,
    "D4": 0.10, "D5": 0.10, "D6": 0.10, "D7": 0.20,
}

BUSINESS_TYPE_WEIGHTS = {
    # D7 minimum 15% across all types -- AA signature dimension
    # sum must equal 1.00 per type
    "restaurant": {
        # D1 cash+food cost, D4 labor turnover
        "D1": 0.25, "D2": 0.15, "D3": 0.15,
        "D4": 0.15, "D5": 0.10, "D6": 0.05, "D7": 0.15,
    },
    "retail": {
        # D1 cash+inventory, D2 foot traffic, D5 supplier+stock
        "D1": 0.20, "D2": 0.20, "D3": 0.10,
        "D4": 0.10, "D5": 0.15, "D6": 0.10, "D7": 0.15,
    },
    "ecommerce": {
        # D2 marketing+ads, D6 digital/data, D1 ROAS cash flow
        "D1": 0.15, "D2": 0.25, "D3": 0.10,
        "D4": 0.05, "D5": 0.10, "D6": 0.20, "D7": 0.15,
    },
    "brand": {
        # D2 brand+channel, D5 supply chain+sourcing
        "D1": 0.20, "D2": 0.20, "D3": 0.10,
        "D4": 0.10, "D5": 0.15, "D6": 0.10, "D7": 0.15,
    },
    "service": {
        # D4 people = product, D2 retention+referral, D3 SOP
        "D1": 0.15, "D2": 0.20, "D3": 0.15,
        "D4": 0.20, "D5": 0.05, "D6": 0.10, "D7": 0.15,
    },
    "health_beauty": {
        # D2 retention+membership, D7 license+liability higher than min
        "D1": 0.20, "D2": 0.20, "D3": 0.10,
        "D4": 0.15, "D5": 0.05, "D6": 0.10, "D7": 0.20,
    },
    "oem": {
        # D3 production system, D5 supply chain
        "D1": 0.15, "D2": 0.20, "D3": 0.15,
        "D4": 0.10, "D5": 0.15, "D6": 0.10, "D7": 0.15,
    },
    "startup": {
        # D6 tech/data, D4 team, D1 runway
        "D1": 0.20, "D2": 0.15, "D3": 0.15,
        "D4": 0.15, "D5": 0.05, "D6": 0.15, "D7": 0.15,
    },
}

ALL_DIMENSIONS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]


def _get_weights(business_type):
    return BUSINESS_TYPE_WEIGHTS.get(business_type, DIM_WEIGHTS)


def _traffic_light(pct, flag_hit):
    """GREEN > 66%, YELLOW 34-66%, RED <= 33% (per spec v2 Section 5.5).
    pct is the percentage score (0-100) for a dimension.
    flag_hit forces RED regardless of pct.
    """
    if flag_hit:
        return "RED"
    if pct <= 33.3:
        return "RED"
    if pct <= 66.7:
        return "YELLOW"
    return "GREEN"


def _grade(overall, red_count):
    if red_count >= 3:
        return "WATCH" if overall >= 40 else "CRITICAL"
    if overall < 40:
        return "CRITICAL"
    if overall < 70:
        return "WATCH"
    if overall < 85:
        return "HEALTHY"
    return "STRONG"


def calculate_score(answers, business_type="general"):
    dim_raw = {}
    dim_pct = {}
    dim_light = {}
    red_flags = []

    for dim, questions in DIM_QUESTIONS.items():
        raw = sum(answers.get(q, 0) for q in questions)
        pct = (raw / DIM_MAX_RAW) * 100
        dim_raw[dim] = raw
        dim_pct[dim] = round(pct, 1)

        flag_hit = any(
            answers.get(q, 0) == 0
            for q in RED_FLAG_QUESTIONS.get(dim, [])
        )
        if flag_hit:
            red_flags.append(dim)

        dim_light[dim] = _traffic_light(dim_pct[dim], flag_hit)

    weights = _get_weights(business_type)
    overall = sum(dim_pct[d] * weights[d] for d in ALL_DIMENSIONS)

    red_count = sum(1 for d in ALL_DIMENSIONS if dim_light[d] == "RED")

    grade = _grade(overall, red_count)

    return {
        "dim_raw": dim_raw,
        "dim_pct": dim_pct,
        "dim_light": dim_light,
        "red_flags": red_flags,
        "red_count": red_count,
        "overall": round(overall, 1),
        "grade": grade,
    }
