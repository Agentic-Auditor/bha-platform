"""
narratives.py v2 — Pattern Library + Anthropic API integration.

Main entry point:
    get_narrative(dim, light, answers, context, db) -> dict

Pipeline:
    answers → detect_patterns() → get_pattern_hash()
           → check narrative_cache → (hit) return cached
           → (miss) build_ai_briefing() → call_anthropic() → store → return

Fallback:
    If ANTHROPIC_API_KEY is not set or API call fails, returns content
    from the static NARRATIVES dict (v1 content, always available).
"""

import hashlib
import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Dimension metadata
# ──────────────────────────────────────────────────────────────────

DIM_NAMES = {
    "D1": "การเงิน",
    "D2": "ลูกค้าและการตลาด",
    "D3": "ระบบงานและกระบวนการ",
    "D4": "ทีมและบุคลากร",
    "D5": "ซัพพลายเชน",
    "D6": "เทคโนโลยี",
    "D7": "ธรรมาภิบาลและการควบคุม",
}

# ──────────────────────────────────────────────────────────────────
# Pattern detection — all 7 dimensions
# ──────────────────────────────────────────────────────────────────

def detect_patterns(dim: str, answers: dict) -> list:
    """
    Detect 1-3 pattern codes for a dimension based on scored answers.
    Rules run in priority order; first match = primary code.
    Secondary codes are added if the condition is met and not already present.
    Returns list of up to 3 codes.
    """
    q = answers
    patterns = []

    if dim == "D1":
        if q.get("1.1", 0) == 0 and q.get("1.2", 0) == 0:
            # 1.1=ไม่รู้กำไร/ขาดทุน, 1.2=ไม่แยกเงินส่วนตัว/ธุรกิจ
            patterns.append("D1_CASH_CRISIS_NO_SYSTEM")
        elif q.get("1.1", 0) <= 1 and q.get("1.5", 0) == 0:
            patterns.append("D1_CASH_TIGHT_DECLINING")
        elif q.get("1.5", 0) >= 2 and q.get("1.3", 0) == 0:
            patterns.append("D1_GROWING_BUT_DEBT_TRAP")
        elif q.get("1.2", 0) >= 2 and q.get("1.6", 0) <= 1:
            patterns.append("D1_PROFITABLE_NO_RECURRING")
        elif q.get("1.5", 0) >= 2 and q.get("1.6", 0) >= 2 and q.get("1.1", 0) >= 2:
            patterns.append("D1_STRONG_RECURRING_BASE")
        else:
            patterns.append("D1_ACCOUNTING_GAP")
        if q.get("1.6", 0) <= 1 and "D1_PROFITABLE_NO_RECURRING" not in patterns:
            patterns.append("D1_PROFITABLE_NO_RECURRING")

    elif dim == "D2":
        if q.get("2.1", 0) == 0 and q.get("2.2", 0) == 0:
            # 2.1=customer concentration สูง, 2.2=ไม่รู้ว่าทำไมลูกค้าเลือก (value prop/differentiation)
            patterns.append("D2_NO_ICP_NO_DIFFERENTIATION")
        elif q.get("2.6", 0) <= 1 and q.get("2.5", 0) == 0:
            patterns.append("D2_PLATFORM_DEPENDENT")
        elif q.get("2.5", 0) <= 1 and q.get("2.2", 0) <= 1:
            patterns.append("D2_HIGH_CAC_LOW_RETENTION")
        elif q.get("2.1", 0) >= 2 and q.get("2.3", 0) <= 1:
            patterns.append("D2_KNOWS_CUSTOMER_CANT_REACH")
        elif q.get("2.6", 0) >= 2 and q.get("2.2", 0) >= 2 and q.get("2.1", 0) >= 2:
            patterns.append("D2_STRONG_OWNED_COMMUNITY")
        else:
            patterns.append("D2_VOLUME_WITHOUT_INSIGHT")
        if q.get("2.2", 0) <= 1 and "D2_HIGH_CAC_LOW_RETENTION" not in patterns:
            patterns.append("D2_HIGH_CAC_LOW_RETENTION")

    elif dim == "D3":
        if q.get("3.6", 0) == 0 and q.get("3.1", 0) == 0:
            patterns.append("D3_OWNER_IS_BOTTLENECK")
        elif q.get("3.2", 0) <= 1 and q.get("3.5", 0) == 0:
            patterns.append("D3_QUALITY_INCONSISTENT")
        elif q.get("3.3", 0) == 0 and q.get("3.4", 0) <= 1:
            patterns.append("D3_CAPACITY_MAXED_NO_TOOLS")
        elif q.get("3.1", 0) >= 2 and q.get("3.5", 0) <= 1:
            patterns.append("D3_SYSTEM_EXISTS_NO_CULTURE")
        elif q.get("3.6", 0) <= 1 and q.get("3.1", 0) >= 2:
            patterns.append("D3_DELEGATION_BLOCKED")
        elif q.get("3.6", 0) >= 2 and q.get("3.1", 0) >= 2 and q.get("3.5", 0) >= 2:
            patterns.append("D3_SYSTEMATIZED_SCALABLE")
        else:
            patterns.append("D3_OWNER_IS_BOTTLENECK")
        if (q.get("3.6", 0) <= 1
                and "D3_DELEGATION_BLOCKED" not in patterns
                and "D3_OWNER_IS_BOTTLENECK" not in patterns):
            patterns.append("D3_DELEGATION_BLOCKED")

    elif dim == "D4":
        if q.get("4.3", 0) == 0 and q.get("4.2", 0) <= 1:
            # 4.3=turnover rate สูงมาก (>50%), 4.2=พนักงานไม่รู้เป้าหมาย
            patterns.append("D4_HIGH_TURNOVER_CULTURE_ISSUE")
        elif q.get("4.4", 0) == 0 and q.get("4.5", 0) == 0:
            patterns.append("D4_KEY_PERSON_NO_BACKUP")
        elif q.get("4.1", 0) == 0 and q.get("4.5", 0) == 0:
            patterns.append("D4_SKILLS_GAP_NO_PLAN")
        elif q.get("4.2", 0) >= 2 and q.get("4.5", 0) == 0:
            patterns.append("D4_ENGAGED_STAGNANT")
        elif q.get("4.5", 0) >= 2 and q.get("4.3", 0) >= 2 and q.get("4.6", 0) >= 2:
            patterns.append("D4_GROWING_TEAM")
        else:
            patterns.append("D4_ACCOUNTABILITY_GAP")
        if q.get("4.4", 0) == 0 and "D4_KEY_PERSON_NO_BACKUP" not in patterns:
            patterns.append("D4_KEY_PERSON_NO_BACKUP")

    elif dim == "D5":
        if q.get("5.1", 0) == 0 and q.get("5.3", 0) == 0:
            # 5.1=มีซัพพลายเออร์รายเดียวและไม่มีทางออก, 5.3=ไม่รู้ล่วงหน้าเมื่อวัตถุดิบขาด/ราคาเปลี่ยน
            patterns.append("D5_SINGLE_SOURCE_ALREADY_FAILED")
        elif q.get("5.5", 0) == 0 and q.get("5.2", 0) == 0:
            patterns.append("D5_REACTIVE_STOCKOUT")
        elif q.get("5.3", 0) == 0 and q.get("5.1", 0) <= 1:
            patterns.append("D5_WEAK_BARGAINING")
        elif q.get("5.2", 0) == 0 and q.get("5.4", 0) == 0:
            patterns.append("D5_INVENTORY_BLIND")
        elif q.get("5.5", 0) >= 2 and q.get("5.1", 0) >= 2 and q.get("5.3", 0) >= 2:
            patterns.append("D5_PLANNED_PROCUREMENT")
        else:
            patterns.append("D5_QUALITY_RISK")
        if (q.get("5.4", 0) == 0
                and "D5_QUALITY_RISK" not in patterns
                and "D5_INVENTORY_BLIND" not in patterns):
            patterns.append("D5_QUALITY_RISK")

    elif dim == "D6":
        # Security red flag always added if triggered
        if q.get("6.2", 0) == 0:
            patterns.append("D6_SECURITY_EXPOSED")
        if q.get("6.1", 0) == 0 and q.get("6.5", 0) == 0 and q.get("6.6", 0) == 0:
            if "D6_SECURITY_EXPOSED" not in patterns:
                patterns.append("D6_COMPLETELY_MANUAL")
            else:
                patterns.append("D6_COMPLETELY_MANUAL")
        elif not patterns:
            if q.get("6.6", 0) == 0 and q.get("6.1", 0) <= 1:
                # 6.6=ตัดสินใจจากความรู้สึก ไม่ใช้ data, 6.1=ไม่มีเครื่องมือดิจิทัล
                patterns.append("D6_DATA_BLIND_DECISION")
            elif q.get("6.3", 0) == 0 and q.get("6.4", 0) == 0:
                patterns.append("D6_NO_ONLINE_PRESENCE")
            elif q.get("6.5", 0) >= 2 and q.get("6.6", 0) >= 2 and q.get("6.1", 0) >= 2:
                patterns.append("D6_DIGITAL_NATIVE")
            else:
                patterns.append("D6_PARTIAL_DIGITAL")
        if (q.get("6.3", 0) == 0 and q.get("6.4", 0) == 0
                and "D6_NO_ONLINE_PRESENCE" not in patterns):
            patterns.append("D6_NO_ONLINE_PRESENCE")

    elif dim == "D7":
        if q.get("7.1", 0) == 0 and q.get("7.2", 0) == 0:
            patterns.append("D7_DUAL_LEGAL_EXPOSURE")
        elif q.get("7.1", 0) >= 1 and q.get("7.5", 0) == 0 and q.get("7.3", 0) == 0:
            patterns.append("D7_LEGAL_BUT_UNPROTECTED")
        elif q.get("7.6", 0) == 0 and q.get("7.4", 0) == 0:
            patterns.append("D7_NO_EXTERNAL_PERSPECTIVE")
        elif q.get("7.3", 0) == 0 and q.get("7.2", 0) <= 1:
            patterns.append("D7_INFORMAL_OPERATIONS")
        elif q.get("7.4", 0) == 0 and q.get("7.5", 0) == 0:
            patterns.append("D7_CRISIS_UNREADY")
        elif (q.get("7.1", 0) >= 2 and q.get("7.2", 0) >= 2
              and q.get("7.3", 0) >= 2 and q.get("7.5", 0) >= 2):
            patterns.append("D7_GOVERNANCE_STRONG")
        else:
            patterns.append("D7_NO_EXTERNAL_PERSPECTIVE")
        if (q.get("7.4", 0) == 0 and q.get("7.5", 0) == 0
                and "D7_CRISIS_UNREADY" not in patterns):
            patterns.append("D7_CRISIS_UNREADY")

    return patterns[:3]


# ──────────────────────────────────────────────────────────────────
# Cache key
# ──────────────────────────────────────────────────────────────────

# Bump this whenever the narrative schema / prompt changes so that stale
# cached narratives (missing newer fields) are not served. v2 = added
# fact / principle_benefit / consequence and the fact-grounded prompt.
NARRATIVE_SCHEMA_VERSION = "v2"  # fact/principle/consequence + labels reconciled to constants.js


def get_pattern_hash(dim, patterns, business_type, age_bucket, revenue_bucket, light=""):
    """Deterministic 16-char hash used as narrative_cache lookup key.

    `light` is part of the key: narrative text is written for a specific
    traffic-light level, so two assessments that share a pattern set but land
    on different lights (common near the 33%/67% borders) must NOT collide —
    otherwise the cached paragraph can contradict the badge shown.
    """
    key = json.dumps({
        "schema": NARRATIVE_SCHEMA_VERSION,
        "dim": dim,
        "patterns": sorted(patterns),
        "btype": business_type or "general",
        "age": age_bucket or "",
        "revenue": revenue_bucket or "",
        "light": light or "",
    }, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────────
# AI briefing builder
# ──────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────
# Industry profiles — injected into AI prompt for business-type-
# specific actions and benchmarks.
# ──────────────────────────────────────────────────────────────────

INDUSTRY_PROFILES = {
    "restaurant": {
        "label": "ร้านอาหาร / F&B",
        "context": (
            "ธุรกิจ F&B มี Food Cost เป้าหมาย 28–35% และ Labor Cost 25–30% ของรายได้ "
            "รายได้ขึ้นกับ foot traffic และ delivery platform (Grab Food, Foodpanda, Wongnai) "
            "ความท้าทายหลัก: Turnover พนักงานสูง, waste จากวัตถุดิบ, ช่วง peak vs off-peak"
        ),
        "tools": "POS system (Wongnai POS, Square), LINE OA, Grab/Foodpanda Merchant Portal, Google Maps",
        "kpis": "Food Cost %, Labor Cost %, Table Turnover Rate, Average Check, สัดส่วน Delivery:Dine-in",
    },
    "brand": {
        "label": "แบรนด์สินค้า / D2C Brand",
        "context": (
            "แบรนด์แข่งขันด้าน Brand Equity, Packaging, และ Channel mix "
            "รายได้มาจาก Retail margin, Online D2C, และ Distribution network "
            "ความท้าทายหลัก: Channel conflict, SKU proliferation, Shelf space, Brand building cost"
        ),
        "tools": "Shopee/Lazada Seller Center, Meta Ads, LINE OA, Shopify, 3PL logistics, TikTok Shop",
        "kpis": "Sell-through Rate, Channel Margin, ROAS, Customer LTV, Brand Awareness Score",
    },
    "retail": {
        "label": "ค้าปลีก / ร้านค้า",
        "context": (
            "ค้าปลีกแข่งขันด้าน Inventory turnover และ Gross margin per sqm "
            "รายได้ขึ้นกับ foot traffic, location, และ product mix "
            "ความท้าทายหลัก: Dead stock, margin บีบจาก supplier, cash จมในสต็อก, สู้ online ไม่ได้"
        ),
        "tools": "POS (Loyverse, Square), LINE OA, บัญชี FlowAccount, Stock management app",
        "kpis": "Inventory Turnover, Gross Margin %, Shrinkage Rate, Revenue per sqm, Sell-through Rate",
    },
    "ecommerce": {
        "label": "ขายออนไลน์ / E-commerce",
        "context": (
            "E-commerce seller แข่งด้าน ROAS, Conversion rate, และ Logistics cost per order "
            "รายได้ขึ้นกับ platform algorithm, ads spend, และ review rating "
            "ความท้าทายหลัก: Platform fee สูง 15-25%, price war, return rate, ads cost เพิ่มขึ้นทุกปี"
        ),
        "tools": "Shopee/Lazada Seller Center, TikTok Shop, Meta/Google Ads, LINE OA, 3PL/Flash/J&T",
        "kpis": "ROAS, CAC, Conversion Rate, Return Rate, Net Margin after fees, GMV Growth",
    },
    "service": {
        "label": "ธุรกิจบริการ",
        "context": (
            "ธุรกิจบริการมีรายได้ขึ้นกับ Revenue per hour/session และ Utilization rate "
            "คนคือสินค้าหลัก ความท้าทายหลัก: Key person risk, ขยาย scale ยาก, "
            "pricing pressure, ลูกค้าไม่กลับมาถ้า service ไม่สม่ำเสมอ"
        ),
        "tools": "LINE OA, Google Calendar/Booking, Notion, Google Business Profile, ระบบนัดออนไลน์",
        "kpis": "Revenue per Staff, Utilization Rate %, Repeat Booking Rate, NPS, Average Job Value",
    },
    "health_beauty": {
        "label": "สุขภาพ / ความงาม",
        "context": (
            "Health & Beauty มีรายได้จาก Treatment revenue per chair/bed และ Membership/package "
            "ความท้าทายหลัก: License/ใบอนุญาต, liability, therapist turnover สูง, "
            "ลูกค้าซื้อ package แล้วไม่มาใช้ (ghost member), สต็อก consumables"
        ),
        "tools": "ระบบนัด (Fresha, Line Booking), LINE OA, POS clinic/spa, Google Reviews",
        "kpis": "Revenue per Chair/Bed, Package Redemption Rate, Client Retention Rate, Treatment Margin %",
    },
    "oem": {
        "label": "รับจ้างผลิต / OEM / โรงงาน",
        "context": (
            "OEM มีรายได้ขึ้นกับ Volume Contract จากลูกค้าไม่กี่ราย margin บางและแข่งด้านราคา "
            "ความท้าทายหลัก: Customer concentration สูง, MOQ/lead time, Labor efficiency, QC reject rate"
        ),
        "tools": "ERP/MRP, Production schedule, QC checklist, ISO documentation, B2B sourcing platform",
        "kpis": "Capacity Utilization %, Defect/Reject Rate, OTD (On-Time Delivery), Cost per Unit, Customer HHI",
    },
    "startup": {
        "label": "Startup / ธุรกิจเทคโนโลยี",
        "context": (
            "Startup วัด Traction ด้วย MRR/ARR, CAC, LTV, และ Churn Rate "
            "Runway และ Burn Rate เป็น KPI ชีวิตรอด "
            "ความท้าทายหลัก: Product-market fit, Unit economics, Fundraising, Scaling team"
        ),
        "tools": "Notion/Linear (PM), Mixpanel/GA4 (analytics), Stripe/Omise, Slack, AWS/GCP, Figma",
        "kpis": "MRR/ARR Growth %, CAC Payback Period, Net Revenue Retention, Runway (months), Churn Rate",
    },
    "general": {
        "label": "ธุรกิจ SME ทั่วไป",
        "context": "SME ที่ต้องการสร้างระบบและขยายธุรกิจอย่างยั่งยืน มีความท้าทายด้านการจัดการและการเงินที่หลากหลาย",
        "tools": "Excel, LINE OA, Google Workspace, บัญชี FlowAccount",
        "kpis": "Revenue Growth, Gross Margin %, Customer Retention Rate, Cash Reserve",
    },
}


def _fact_base_block(dim, answers):
    """Render the answer-derived fact base as prompt text. This is the ONLY
    factual ground the model is allowed to use about this business."""
    facts = build_fact_base(dim, answers)
    if not facts:
        return "(ไม่มีข้อมูลคำตอบรายข้อ — ห้ามคาดเดาตัวเลขหรือสถานการณ์ใดๆ)"
    lines = [f"- {label}: {score}/{SCORE_MAX} ({level})"
             for (_qid, label, score, level) in facts]
    return "\n".join(lines)


def build_ai_briefing(dim, light, patterns, context, answers=None):
    """Build the prompt sent to Anthropic API.

    The prompt is grounded on a Fact base built from the user's actual answers
    (see _fact_base_block). The model is instructed to use ONLY those facts and
    the supplied industry context, and to never invent numbers or benchmarks —
    this is the core anti-hallucination guard.
    """
    btype     = context.get("business_type", "general")
    age       = context.get("age_bucket", "ไม่ระบุ")
    revenue   = context.get("revenue_bucket", "ไม่ระบุ")
    employees = context.get("employee_bucket", "ไม่ระบุ")
    biz_name  = context.get("business_name", "")
    goal      = context.get("goal_bucket", "")  # C4: เป้าหมาย 12 เดือน

    profile     = INDUSTRY_PROFILES.get(btype, INDUSTRY_PROFILES["general"])
    btype_label = profile["label"]
    ind_context = profile["context"]
    ind_tools   = profile["tools"]
    ind_kpis    = profile["kpis"]

    light_label = {"RED": "ต้องแก้ด่วน", "YELLOW": "ต้องพัฒนา", "GREEN": "แข็งแกร่ง"}.get(light, light)
    goal_line   = f"\n- เป้าหมาย 12 เดือน: {goal}" if goal else ""
    fact_block  = _fact_base_block(dim, answers)

    # GREEN dimensions: frame the "consequence" field as opportunity-cost.
    consequence_spec = (
        "1-2 ประโยค — ถ้า 'ไม่ต่อยอด' จุดแข็งนี้ จะเสียโอกาส/ความได้เปรียบอะไรให้คู่แข่ง"
        if light == "GREEN"
        else "1-2 ประโยค — ถ้า 'ไม่ปรับปรุง' จุดนี้ จะเกิดผลเสียอะไรต่อธุรกิจอย่างเป็นรูปธรรม (เชื่อมกับข้อเท็จจริงด้านบน)"
    )

    return f"""คุณเป็นที่ปรึกษาด้านบริหารความเสี่ยงและกลยุทธ์ธุรกิจ SME เขียน narrative สำหรับรายงาน Business Health Assessment เป็นภาษาไทย

## บริบทธุรกิจ
- ประเภท: {btype_label}{(" — " + biz_name) if biz_name else ""}
- อายุกิจการ: {age} | รายรับ: {revenue} | พนักงาน: {employees}{goal_line}
- บริบทอุตสาหกรรม: {ind_context}
- เครื่องมือที่ใช้ทั่วไปในธุรกิจนี้: {ind_tools}
- KPI หลักของธุรกิจนี้: {ind_kpis}

## มิติที่วิเคราะห์: {DIM_NAMES.get(dim, dim)}
- ระดับผลประเมิน: {light} ({light_label})
- รูปแบบความเสี่ยงที่ระบบตรวจพบ (pattern): {", ".join(patterns) if patterns else "ไม่มี"}

## ข้อเท็จจริงจากคำตอบของผู้ใช้ (Fact base — ฐานข้อมูลจริงเพียงชุดเดียวที่ใช้ได้)
แต่ละข้อคือคะแนนจริงที่ผู้ใช้ตอบ (0 = ยังไม่มี, 3 = แข็งแกร่ง):
{fact_block}

## สิ่งที่คุณต้องเขียน (ตอบเป็น JSON เท่านั้น ไม่มีข้อความอื่น)

{{
  "summary": "1 ประโยค — ข้อค้นพบหลักของมิตินี้ คมชัด อิงข้อเท็จจริงด้านบน",
  "current_state": "2-3 ประโยค — สถานการณ์ปัจจุบัน อ้างอิงเฉพาะข้อที่ผู้ใช้ตอบ (ระบุชื่อหัวข้อที่อ่อน/แข็ง) ด้วยภาษาที่ตรงกับ {btype_label}",
  "root_cause": "2-3 ประโยค — สาเหตุที่แท้จริงเบื้องหลังข้อที่ได้คะแนนต่ำ เชื่อมกับลักษณะของ {btype_label}",
  "whats_working": "1-2 ประโยค — สิ่งที่ทำได้ดีแล้ว อ้างเฉพาะข้อที่ได้คะแนน 2-3 เท่านั้น (ถ้าไม่มี ให้เว้นว่าง)",
  "principle_benefit": "2 ประโยค — หลักการบริหารที่ว่าทำไมมิตินี้สำคัญ และประโยชน์ที่ธุรกิจจะได้หากทำได้ดี",
  "consequence": "{consequence_spec}",
  "actions": [
    "[สัปดาห์ 1] สิ่งที่ทำได้ทันที — ระบุเครื่องมือหรือวิธีที่เหมาะกับ {btype_label}",
    "[เดือน 1] การปรับปรุงระยะกลาง — สอดคล้องกับ KPI ของ {btype_label}",
    "[ไตรมาส 1] การยกระดับเชิงกลยุทธ์{(' — เชื่อมกับเป้าหมาย: ' + goal) if goal else ''}"
  ],
  "industry_context": "1 ประโยค — เทียบกับ {btype_label} ทั่วไปในเชิงคุณภาพ (ห้ามอ้างตัวเลข/เปอร์เซ็นต์ที่ไม่ได้ให้ไว้)"
}}

## กฎการเขียน (สำคัญมาก)
- โทน: มืออาชีพ น่าเชื่อถือ กระชับ แต่เจ้าของ SME อ่านเข้าใจ — เลี่ยงศัพท์เทคนิคที่ไม่จำเป็น และอธิบายศัพท์อังกฤษสั้นๆ เมื่อจำเป็นต้องใช้
- อ้างอิงข้อเท็จจริง: ทุกประโยคต้องอิงจาก Fact base หรือบริบทอุตสาหกรรมที่ให้ไว้เท่านั้น
- ห้ามสร้างตัวเลข เปอร์เซ็นต์ จำนวนเงิน หรือสถิติใดๆ ที่ไม่ได้ระบุไว้ใน prompt นี้โดยเด็ดขาด
- ห้ามอ้างเหตุการณ์หรือรายละเอียดที่ผู้ใช้ไม่ได้ให้ (เช่น ชื่อซัพพลายเออร์ จำนวนพนักงานจริง) — ถ้าไม่รู้ ให้พูดเชิงหลักการแทน
- ห้ามใช้คำเชื่อมฟุ่มเฟือย: "อย่างไรก็ตาม", "นอกจากนี้", "ในทำนองเดียวกัน"
- ถ้า light=GREEN ให้เน้นการต่อยอดสู่ระดับถัดไป ไม่ใช่แค่ชม"""


# ──────────────────────────────────────────────────────────────────
# Anthropic API call
# ──────────────────────────────────────────────────────────────────

def call_anthropic(prompt: str) -> dict:
    """
    Call claude-haiku-4-5 and parse JSON response.
    Raises on API error or JSON parse failure — caller handles fallback.
    """
    try:
        import anthropic as _anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed — run: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = _anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(text)


# ──────────────────────────────────────────────────────────────────
# Cache-first orchestrator
# ──────────────────────────────────────────────────────────────────

def get_or_generate_narrative(dim, light, patterns, context, db, answers=None):
    """
    Returns AI narrative dict for a dimension.
    Checks SQLite cache first; generates via API on miss; stores result.
    On any error falls back to static NARRATIVES dict.
    """
    age_bucket     = context.get("age_bucket", "")
    revenue_bucket = context.get("revenue_bucket", "")
    business_type  = context.get("business_type", "general")

    hash_key = get_pattern_hash(dim, patterns, business_type, age_bucket, revenue_bucket, light)

    # Cache hit
    try:
        cached = db.execute(
            "SELECT narrative FROM narrative_cache WHERE pattern_hash = ?",
            (hash_key,),
        ).fetchone()
        if cached:
            db.execute(
                "UPDATE narrative_cache SET hit_count = hit_count + 1, last_hit_at = ? WHERE pattern_hash = ?",
                (datetime.utcnow().isoformat(), hash_key),
            )
            db.commit()
            return json.loads(cached["narrative"])
    except Exception as e:
        log.warning("narrative_cache read error: %s", e)

    # Cache miss — call API
    try:
        prompt    = build_ai_briefing(dim, light, patterns, context, answers=answers)
        narrative = call_anthropic(prompt)

        # Ensure required keys exist with defaults
        narrative.setdefault("summary", "")
        narrative.setdefault("current_state", "")
        narrative.setdefault("root_cause", "")
        narrative.setdefault("whats_working", "")
        narrative.setdefault("principle_benefit", "")
        narrative.setdefault("consequence", "")
        narrative.setdefault("actions", [])
        narrative.setdefault("industry_context", "")

        # Fact field is ALWAYS computed deterministically from the answers,
        # overriding anything the model might have produced — guarantees the
        # "ข้อเท็จจริง" section can never be hallucinated.
        narrative["fact"] = _fact_sentence(dim, answers)

        # For GREEN, consequence is opportunity-cost; for RED/YELLOW it is the
        # downside of inaction. If the model returned nothing, fall back to the
        # deterministic pattern-based consequence.
        if not narrative.get("consequence") and light != "GREEN":
            narrative["consequence"] = _consequence_text(patterns, light)
        if not narrative.get("principle_benefit"):
            narrative["principle_benefit"] = DIM_PRINCIPLES.get(dim, "")

        # Add computed fields for backward compat
        narrative["detail"]   = narrative.get("current_state", "")
        narrative["cta_flag"] = (light == "RED")

        try:
            db.execute(
                """INSERT OR IGNORE INTO narrative_cache
                   (pattern_hash, dim, patterns, business_type, age_bucket,
                    revenue_bucket, narrative, model, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    hash_key, dim, json.dumps(patterns), business_type,
                    age_bucket, revenue_bucket,
                    json.dumps(narrative), "claude-haiku-4-5",
                    datetime.utcnow().isoformat(),
                ),
            )
            db.commit()
        except Exception as e:
            log.warning("narrative_cache write error: %s", e)

        return narrative

    except Exception as e:
        log.warning("Anthropic API error for %s/%s: %s — using static fallback", dim, light, e)
        return _static_fallback(dim, light, business_type, patterns=patterns, answers=answers)


# ──────────────────────────────────────────────────────────────────
# Lookup tables for rich static fallback
# ──────────────────────────────────────────────────────────────────

PATTERN_ROOT_CAUSES = {
    # D1
    "D1_CASH_CRISIS_NO_SYSTEM":    "ไม่มีระบบบัญชีแยกระหว่างเงินส่วนตัวและเงินธุรกิจ ทำให้มองไม่เห็นกระแสเงินสดจริง และตัดสินใจได้ช้าเมื่อมีวิกฤต",
    "D1_CASH_TIGHT_DECLINING":     "รายได้ไม่เพียงพอครอบคลุมต้นทุนคงที่ และแนวโน้มกำไรลดลงต่อเนื่อง บ่งบอกว่า Model ธุรกิจยังไม่ยั่งยืน",
    "D1_GROWING_BUT_DEBT_TRAP":    "รายได้เติบโตแต่ใช้หนี้เป็นเชื้อเพลิงหลัก ทำให้ภาระดอกเบี้ยกัดกินกำไรและสร้างความเปราะบางต่อดอกเบี้ยขาขึ้น",
    "D1_PROFITABLE_NO_RECURRING":  "กำไรดีแต่รายได้ไม่สม่ำเสมอ ขึ้นกับออเดอร์ใหม่ทุกเดือน ทำให้วางแผนการเงินระยะยาวได้ยาก",
    "D1_STRONG_RECURRING_BASE":    "ฐานรายได้ประจำมั่นคงแล้ว แต่ยังมีโอกาสเพิ่ม Margin ด้วยการปรับ Pricing หรือลด Cost",
    "D1_ACCOUNTING_GAP":           "ขาดระบบติดตามตัวเลขที่แม่นยำ ทำให้ตัดสินใจจากความรู้สึกมากกว่าข้อมูล และพลาดโอกาสลดรายจ่าย",
    # D2
    "D2_NO_ICP_NO_DIFFERENTIATION": "ไม่รู้ว่าลูกค้าอุดมคติคือใคร และยังไม่มีจุดต่างที่ชัดเจนในตลาด ทำให้แข่งด้วยราคาอย่างเดียว",
    "D2_PLATFORM_DEPENDENT":        "รายได้ผูกกับแพลตฟอร์มบุคคลที่สาม ซึ่งสามารถปรับค่าธรรมเนียมหรือกฎได้ตลอดเวลาโดยไม่ต้องขออนุญาต",
    "D2_HIGH_CAC_LOW_RETENTION":    "ต้นทุนหาลูกค้าใหม่สูง แต่ลูกค้าเก่าไม่กลับมาซื้อซ้ำ ทำให้ต้องวิ่งหาลูกค้าใหม่ตลอดเวลา",
    "D2_KNOWS_CUSTOMER_CANT_REACH": "รู้จักลูกค้าดีแต่ยังหาช่องทางเข้าถึงที่มีประสิทธิภาพไม่ได้ ทำให้ตัวเองเป็นที่รู้จักได้ช้า",
    "D2_STRONG_OWNED_COMMUNITY":    "มีฐานลูกค้าประจำแข็งแกร่ง แต่ยังขยายฐานลูกค้าใหม่ได้ช้าเพราะพึ่ง Word-of-mouth เป็นหลัก",
    "D2_VOLUME_WITHOUT_INSIGHT":    "มีลูกค้าจำนวนมากแต่ไม่มีข้อมูลเชิงลึกว่าใครคือลูกค้าที่ทำกำไรจริง ทำให้ทรัพยากรกระจายผิดจุด",
    # D3
    "D3_OWNER_IS_BOTTLENECK":       "เจ้าของอยู่ในทุกการตัดสินใจ ทำให้ระบบงานขยายตัวไม่ได้และธุรกิจเติบโตถึงจุดอิ่มตัวของเวลาเจ้าของ",
    "D3_QUALITY_INCONSISTENT":      "ไม่มีมาตรฐานการทำงานที่เป็นลายลักษณ์อักษร ทำให้คุณภาพขึ้นกับคนทำในแต่ละวันและยากจะรักษาความสม่ำเสมอ",
    "D3_CAPACITY_MAXED_NO_TOOLS":   "ระบบปัจจุบันทำงานเต็มกำลังแล้ว แต่ยังไม่มีเครื่องมือเพิ่มประสิทธิภาพหรือ Automate งานซ้ำ",
    "D3_SYSTEM_EXISTS_NO_CULTURE":  "มีระบบบนกระดาษแต่ทีมไม่ทำตาม ขาดวัฒนธรรมองค์กรที่สนับสนุนการทำตาม SOP",
    "D3_DELEGATION_BLOCKED":        "มีระบบงานบ้างแต่การมอบหมายงานยังติดขัด ทำให้เจ้าของยังต้องตัดสินใจมากเกินไปในงานประจำ",
    "D3_SYSTEMATIZED_SCALABLE":     "ระบบงานดีแต่ยังมีโอกาส Automate งานซ้ำๆ เพิ่มเติมเพื่อลดต้นทุนและลดความเสี่ยงจากความผิดพลาดของคน",
    # D4
    "D4_HIGH_TURNOVER_CULTURE_ISSUE": "อัตราการลาออกสูงบ่งบอกปัญหาวัฒนธรรมองค์กร ความไม่ชัดเจนด้านเป้าหมาย หรือค่าตอบแทนไม่แข่งขัน",
    "D4_KEY_PERSON_NO_BACKUP":        "มีบุคคลสำคัญที่ขาดไม่ได้ แต่ไม่มีแผนสำรองเมื่อเขาลาออกหรือป่วยกะทันหัน ทำให้งานหยุดชะงักทันที",
    "D4_SKILLS_GAP_NO_PLAN":          "ทีมขาดทักษะที่จำเป็นสำหรับการเติบโต และไม่มีแผนพัฒนาที่ชัดเจน ทำให้ช่องว่างทักษะขยายตัวเรื่อยๆ",
    "D4_ENGAGED_STAGNANT":            "ทีม Engage ดีแต่ไม่เติบโต ขาดโปรแกรมพัฒนาทักษะใหม่ ทำให้คนเก่งอาจออกเพื่อหาความท้าทาย",
    "D4_GROWING_TEAM":                "ทีมเติบโตดีแต่ยังต้องรักษา Culture และ Alignment เมื่อจำนวนคนเพิ่มขึ้น",
    "D4_ACCOUNTABILITY_GAP":          "ขาดระบบ Accountability ที่ชัดเจน ทำให้งานตกหล่นและไม่รู้ว่าใครรับผิดชอบส่วนไหน",
    # D5
    "D5_SINGLE_SOURCE_ALREADY_FAILED": "พึ่งพาซัพพลายเออร์รายเดียวและเคยมีปัญหาส่งของล่าช้าหรือหยุดส่งแล้ว แสดงว่าความเสี่ยงนี้เป็นจริง",
    "D5_REACTIVE_STOCKOUT":            "ไม่มีระบบพยากรณ์ความต้องการ ทำให้สินค้าหมดแบบกะทันหันเป็นประจำและสูญเสียโอกาสขาย",
    "D5_WEAK_BARGAINING":              "ซื้อแบบ Spot price ไม่มีสัญญาล็อกราคา ทำให้ต้นทุนผันผวนตามตลาดและไม่สามารถวางแผนกำไรได้แม่นยำ",
    "D5_INVENTORY_BLIND":              "ไม่รู้ว่ามีสต็อกเท่าไหร่จริงๆ ทำให้สั่งซื้อเกินหรือขาดแคลนโดยไม่รู้ตัว และเงินจมอยู่ในสต็อก",
    "D5_PLANNED_PROCUREMENT":          "ระบบจัดซื้อดีแต่ยังมีโอกาสลดต้นทุนด้วย Strategic sourcing และ Volume discount",
    "D5_QUALITY_RISK":                 "ขาดระบบตรวจสอบคุณภาพปัจจัยนำเข้าก่อนรับเข้า ทำให้ความเสี่ยงด้านคุณภาพส่งผ่านถึงสินค้าและบริการ",
    # D6
    "D6_SECURITY_EXPOSED":     "ไม่มีระบบรักษาความปลอดภัยข้อมูล ทำให้เสี่ยงต่อการถูก Hack รั่วไหลของข้อมูลลูกค้า หรือเรียกค่าไถ่",
    "D6_COMPLETELY_MANUAL":    "ทุกกระบวนการทำมือ ทำให้ Scale ยาก เสียเวลาพนักงานกับงาน routine และเกิดข้อผิดพลาดจากคนได้ง่าย",
    "D6_DATA_BLIND_DECISION":  "ตัดสินใจจากความรู้สึกมากกว่าข้อมูล ทำให้พลาดโอกาสและเสียทรัพยากรกับทิศทางที่ไม่ได้ผล",
    "D6_NO_ONLINE_PRESENCE":   "ไม่มีตัวตนออนไลน์ ทำให้ลูกค้าใหม่หาไม่พบและเสียโอกาสในตลาด Digital ที่คู่แข่งครองอยู่",
    "D6_DIGITAL_NATIVE":       "ใช้ Digital เก่งแต่ยังมีโอกาสใช้ AI เพิ่ม ROI และ Automate งาน Decision-making",
    "D6_PARTIAL_DIGITAL":      "ใช้เครื่องมือดิจิทัลบางส่วนแต่ยังไม่เชื่อมต่อกัน ทำให้ข้อมูลกระจัดกระจายและต้องทำงานซ้ำซ้อน",
    # D7
    # D7 root causes aligned ONLY to actual questions asked (7.1–7.6):
    # 7.1=financial controls, 7.2=fraud/loss, 7.3=legal/tax/license,
    # 7.4=BCP/emergency plan, 7.5=contract management, 7.6=risk assessment
    "D7_DUAL_LEGAL_EXPOSURE":       "ไม่มีระบบตรวจสอบการเข้าถึงเงิน (7.1) และมีประวัติสูญเสียทรัพย์สินที่หาสาเหตุไม่ได้ (7.2) ทำให้ความเสี่ยงทุจริตอยู่ในระดับสูงมาก",
    "D7_LEGAL_BUT_UNPROTECTED":     "มีการควบคุมการเงินบ้าง แต่ยังมีความเสี่ยงด้านกฎหมาย/ภาษี/ใบอนุญาตค้างอยู่ (7.3) และสัญญาสำคัญยังไม่เป็นระบบ (7.5)",
    "D7_NO_EXTERNAL_PERSPECTIVE":   "ไม่มีการประเมินความเสี่ยงเป็นระบบ (7.6) และไม่มีแผนรับมือเหตุฉุกเฉิน (7.4) ทำให้ blind spot สะสมโดยไม่รู้ตัว",
    "D7_INFORMAL_OPERATIONS":       "มีความเสี่ยงด้านกฎหมาย/ภาษีค้างอยู่ (7.3) และระบบควบคุมการเงินยังไม่เข้มงวด (7.2) ทำให้ข้อพิพาทยุ่งยากและขอสินเชื่อยาก",
    "D7_CRISIS_UNREADY":            "ไม่มีแผนรับมือเหตุฉุกเฉิน (7.4) และสัญญา/เอกสารสำคัญยังไม่เป็นระบบ (7.5) ทำให้เมื่อเกิดวิกฤตจะไม่มีฐานทางกฎหมายช่วยปกป้อง",
    "D7_GOVERNANCE_STRONG":         "ระบบควบคุมและธรรมาภิบาลแข็งแกร่งในทุกมิติ ยังมีโอกาสพัฒนาสู่มาตรฐานสากลเพื่อรองรับการตรวจสอบจากนักลงทุนหรือสถาบันการเงิน",
}

# Labels reconciled against the real questionnaire (frontend/lib/constants.js
# QUESTIONS_STEP1). The previous labels predated the current question set and
# were misaligned across ALL dimensions — corrected June 2026 so the `fact`
# and `whats_working` fields name the right item per question id.
QUESTION_LABELS = {
    # D1 — การเงินและสภาพคล่อง
    "1.1": "การรู้กำไร-ขาดทุนรายเดือน", "1.2": "การแยกเงินส่วนตัว-ธุรกิจ",
    "1.3": "เงินสำรองฉุกเฉิน",          "1.4": "การรู้ต้นทุนที่แท้จริง",
    "1.5": "แนวโน้มรายได้",             "1.6": "รายได้ประจำ (Recurring)",
    # D2 — ลูกค้าและการตลาด
    "2.1": "การกระจุกตัวของลูกค้า",     "2.2": "การรู้จุดต่าง/คุณค่า",
    "2.3": "อัตราซื้อซ้ำ",              "2.4": "ช่องทางขายสำรอง",
    "2.5": "ต้นทุนหาลูกค้าใหม่ (CAC)",  "2.6": "ระบบรับ Feedback ลูกค้า",
    # D3 — ระบบงานและกระบวนการ
    "3.1": "การพึ่งพาเจ้าของ",          "3.2": "ระบบ SOP/คู่มืองาน",
    "3.3": "ระบบติดตามงาน",             "3.4": "ตัวชี้วัดคุณภาพ",
    "3.5": "ระบบควบคุมคุณภาพ (QC)",     "3.6": "ความพร้อมรองรับการเติบโต",
    # D4 — ทีมและทรัพยากรมนุษย์
    "4.1": "ความเสี่ยง Key Person",     "4.2": "ความชัดเจนของเป้าหมายงาน",
    "4.3": "อัตราการลาออก",             "4.4": "ความสามารถปรับตัวของทีม",
    "4.5": "การสรรหาและ Onboard",       "4.6": "การพัฒนาทักษะพนักงาน",
    # D5 — ซัพพลายเชนและต้นทุน
    "5.1": "การพึ่งซัพพลายเออร์รายเดียว","5.2": "อำนาจต่อรองกับซัพพลายเออร์",
    "5.3": "การคาดการณ์ล่วงหน้า",       "5.4": "ความผันผวนของต้นทุน",
    "5.5": "ระบบจัดการสต็อก",           "5.6": "ความพยายามลดต้นทุน",
    # D6 — เทคโนโลยีและนวัตกรรม
    "6.1": "การใช้เครื่องมือดิจิทัล",   "6.2": "ความปลอดภัยและ Backup ข้อมูล",
    "6.3": "การเตรียมรับมือ AI",        "6.4": "ช่องทางออนไลน์ 24 ชม.",
    "6.5": "Automation งานซ้ำ",          "6.6": "การใช้ข้อมูลตัดสินใจ",
    # D7 — ธรรมาภิบาล การควบคุมภายใน และความเสี่ยง
    "7.1": "การควบคุมการเข้าถึงเงิน",   "7.2": "การป้องกันการทุจริต",
    "7.3": "ความเสี่ยงกฎหมาย/ภาษี",     "7.4": "แผนรับมือเหตุฉุกเฉิน",
    "7.5": "การจัดการสัญญา/เอกสาร",     "7.6": "การประเมินความเสี่ยง",
}


# ──────────────────────────────────────────────────────────────────
# Fact base — deterministic facts pulled straight from the user's
# answers. Used both to (a) ground the AI prompt and (b) build the
# "ข้อเท็จจริงจากการประเมิน" field shown in the report. Nothing here is
# inferred or generated, so it can never be hallucinated.
# ──────────────────────────────────────────────────────────────────

SCORE_MAX = 3
SCORE_LEVELS = {0: "ยังไม่มี", 1: "เริ่มมีบ้าง", 2: "ทำได้ดี", 3: "แข็งแกร่ง"}


def build_fact_base(dim, answers):
    """Return [(qid, label, score, level_word), …] for the 6 questions in
    `dim`, ordered by question number. 100% derived from `answers`."""
    answers = answers or {}
    dim_num = dim[1]
    facts = []
    for qid in sorted(QUESTION_LABELS):
        if not qid.startswith(dim_num + "."):
            continue
        if qid not in answers:
            continue
        try:
            score = int(answers.get(qid, 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(SCORE_MAX, score))
        facts.append((qid, QUESTION_LABELS.get(qid, qid), score, SCORE_LEVELS.get(score, "")))
    return facts


def _fact_sentence(dim, answers):
    """A factual one-liner built ONLY from the user's actual answers — names
    the weak items (score ≤ 1) and the strong items (score ≥ 2) with counts."""
    facts = build_fact_base(dim, answers)
    if not facts:
        return ""
    total = len(facts)
    weak   = [lbl for (_q, lbl, s, _l) in facts if s <= 1]
    strong = [lbl for (_q, lbl, s, _l) in facts if s >= 2]
    parts = []
    if weak:
        parts.append(f"จุดที่ยังเป็นช่องโหว่ ({len(weak)}/{total} ข้อ): "
                     + ", ".join(weak[:3]) + ("…" if len(weak) > 3 else ""))
    if strong:
        parts.append(f"จุดที่ทำได้ดีแล้ว ({len(strong)}/{total} ข้อ): "
                     + ", ".join(strong[:3]) + ("…" if len(strong) > 3 else ""))
    if not parts:
        return ""
    return "จากคำตอบของคุณ — " + "  |  ".join(parts)


# ──────────────────────────────────────────────────────────────────
# Consequence of inaction — one concrete downside per pattern code,
# parallel to PATTERN_ROOT_CAUSES. Professional, business-specific tone.
# ──────────────────────────────────────────────────────────────────

PATTERN_CONSEQUENCES = {
    # D1
    "D1_CASH_CRISIS_NO_SYSTEM":   "หากปล่อยไว้ ธุรกิจอาจขาดสภาพคล่องกะทันหันโดยไม่มีสัญญาณเตือน และตัดสินใจพลาดเพราะมองไม่เห็นกำไรที่แท้จริง",
    "D1_CASH_TIGHT_DECLINING":    "หากไม่ปรับโครงสร้างต้นทุนหรือราคา กำไรที่ลดลงต่อเนื่องจะกัดกินเงินทุนสำรองจนถึงจุดที่ฟื้นตัวได้ยาก",
    "D1_GROWING_BUT_DEBT_TRAP":   "หากดอกเบี้ยปรับขึ้นหรือยอดขายสะดุด ภาระหนี้จะกลายเป็นกับดักสภาพคล่องทันที",
    "D1_PROFITABLE_NO_RECURRING": "หากไม่สร้างรายได้ประจำ ธุรกิจต้องเริ่มนับหนึ่งหายอดขายใหม่ทุกเดือน วางแผนและขอสินเชื่อได้ยาก",
    "D1_STRONG_RECURRING_BASE":   "หากไม่ต่อยอดเพิ่ม margin คู่แข่งที่บริหารต้นทุนและราคาได้ดีกว่าจะค่อยๆ แย่งความได้เปรียบไป",
    "D1_ACCOUNTING_GAP":          "หากยังตัดสินใจโดยไม่มีตัวเลขแม่นยำ จะมองไม่เห็นรายจ่ายที่รั่วไหลและพลาดโอกาสเพิ่มกำไร",
    # D2
    "D2_NO_ICP_NO_DIFFERENTIATION": "หากยังไม่มีจุดต่าง ธุรกิจจะถูกบีบให้แข่งด้วยราคาเพียงอย่างเดียว ซึ่งกัดกำไรและไม่ยั่งยืน",
    "D2_PLATFORM_DEPENDENT":        "หากแพลตฟอร์มปรับค่าธรรมเนียมหรือกฎ รายได้อาจหายเป็นสัดส่วนมากโดยที่คุณควบคุมไม่ได้",
    "D2_HIGH_CAC_LOW_RETENTION":    "หากลูกค้าเก่าไม่กลับมา ต้นทุนการตลาดจะสูงขึ้นเรื่อยๆ จนกำไรต่อออเดอร์หดตัว",
    "D2_KNOWS_CUSTOMER_CANT_REACH": "หากยังเข้าถึงลูกค้าได้ช้า คู่แข่งที่สื่อสารเก่งกว่าจะครองพื้นที่ในใจลูกค้ากลุ่มเดียวกันไปก่อน",
    "D2_STRONG_OWNED_COMMUNITY":    "หากพึ่ง word-of-mouth อย่างเดียว การเติบโตจะถึงเพดานเมื่อฐานลูกค้าเดิมอิ่มตัว",
    "D2_VOLUME_WITHOUT_INSIGHT":    "หากไม่รู้ว่าใครคือลูกค้าที่ทำกำไร ทรัพยากรการตลาดจะกระจายผิดจุดและได้ผลตอบแทนต่ำกว่าที่ควร",
    # D3
    "D3_OWNER_IS_BOTTLENECK":      "หากทุกการตัดสินใจยังผ่านเจ้าของ ธุรกิจจะโตได้เท่าที่เวลาเจ้าของมี และหยุดชะงักทันทีเมื่อเจ้าของไม่อยู่",
    "D3_QUALITY_INCONSISTENT":     "หากไม่มีมาตรฐาน คุณภาพจะแกว่งตามคนทำในแต่ละวัน ทำให้ลูกค้าไม่มั่นใจและรักษาฐานลูกค้าได้ยาก",
    "D3_CAPACITY_MAXED_NO_TOOLS":  "หากไม่เพิ่มเครื่องมือหรือ automation กำลังการผลิตที่เต็มแล้วจะกลายเป็นเพดานรายได้และพนักงานหมดไฟ",
    "D3_SYSTEM_EXISTS_NO_CULTURE": "หากทีมไม่ทำตามระบบ SOP บนกระดาษจะไร้ผล และความผิดพลาดเดิมๆ จะเกิดซ้ำ",
    "D3_DELEGATION_BLOCKED":       "หากมอบหมายงานไม่ได้ เจ้าของจะจมอยู่กับงานประจำจนไม่มีเวลาคิดเรื่องการเติบโต",
    "D3_SYSTEMATIZED_SCALABLE":    "หากไม่ต่อยอด automation ต้นทุนต่อหน่วยจะลดช้ากว่าคู่แข่งที่ลงทุนระบบมากกว่า",
    # D4
    "D4_HIGH_TURNOVER_CULTURE_ISSUE": "หากการลาออกยังสูง ต้นทุนสรรหาและฝึกคนใหม่จะกัดกำไร และความรู้ในองค์กรจะรั่วไหลออกไปเรื่อยๆ",
    "D4_KEY_PERSON_NO_BACKUP":        "หากบุคคลสำคัญลาออกหรือป่วยกะทันหัน งานหลักอาจหยุดชะงักทันทีโดยไม่มีคนทดแทน",
    "D4_SKILLS_GAP_NO_PLAN":          "หากไม่มีแผนพัฒนาคน ช่องว่างทักษะจะกว้างขึ้นจนทีมตามการเติบโตของธุรกิจไม่ทัน",
    "D4_ENGAGED_STAGNANT":            "หากไม่เปิดโอกาสพัฒนา คนเก่งอาจลาออกเพื่อหาความท้าทายใหม่ที่อื่น",
    "D4_GROWING_TEAM":                "หากไม่รักษา culture และทิศทางร่วมเมื่อทีมโต ความเร็วในการตัดสินใจและคุณภาพงานจะลดลง",
    "D4_ACCOUNTABILITY_GAP":          "หากไม่มีระบบความรับผิดชอบที่ชัดเจน งานจะตกหล่นและปัญหาจะถูกโยนไปมาโดยไม่มีใครแก้",
    # D5
    "D5_SINGLE_SOURCE_ALREADY_FAILED": "หากซัพพลายเออร์รายเดียวมีปัญหาอีกครั้ง การผลิตหรือส่งมอบอาจหยุดทันทีและเสียลูกค้าให้คู่แข่ง",
    "D5_REACTIVE_STOCKOUT":            "หากของหมดกะทันหันต่อไป จะสูญเสียยอดขายและความน่าเชื่อถือกับลูกค้าซ้ำๆ",
    "D5_WEAK_BARGAINING":              "หากต้นทุนผันผวนตามตลาด จะวางแผนกำไรไม่ได้และเสียเปรียบคู่แข่งที่ล็อกราคาได้",
    "D5_INVENTORY_BLIND":              "หากไม่รู้สต็อกจริง เงินจะจมในของค้างหรือขาดของขายโดยไม่รู้ตัว กระทบทั้งกำไรและสภาพคล่อง",
    "D5_PLANNED_PROCUREMENT":          "หากไม่ต่อยอดสู่ strategic sourcing จะเสียโอกาสลดต้นทุนที่คู่แข่งรายใหญ่ได้เปรียบ",
    "D5_QUALITY_RISK":                 "หากไม่ตรวจคุณภาพปัจจัยนำเข้า ปัญหาจะส่งผ่านถึงสินค้าและบริการ กลายเป็นการคืนสินค้าและคำร้องเรียน",
    # D6
    "D6_SECURITY_EXPOSED":    "หากไม่มีระบบความปลอดภัยข้อมูล ความเสี่ยงข้อมูลรั่วหรือถูกเรียกค่าไถ่อาจสร้างความเสียหายและความรับผิดทางกฎหมาย",
    "D6_COMPLETELY_MANUAL":   "หากยังทำมือทุกขั้นตอน การขยายธุรกิจจะติดขัดและความผิดพลาดจากคนจะเพิ่มตามปริมาณงาน",
    "D6_DATA_BLIND_DECISION": "หากตัดสินใจโดยไม่มีข้อมูล จะลงทุนผิดทางและเสียทรัพยากรกับสิ่งที่วัดผลไม่ได้",
    "D6_NO_ONLINE_PRESENCE":  "หากไม่มีตัวตนออนไลน์ ลูกค้าใหม่จะหาไม่เจอ และคู่แข่งจะครองตลาดดิจิทัลไปก่อน",
    "D6_DIGITAL_NATIVE":      "หากไม่ต่อยอด AI และ automation จะเสียความได้เปรียบด้านต้นทุนและความเร็วให้คู่แข่งที่ลงทุนก่อน",
    "D6_PARTIAL_DIGITAL":     "หากเครื่องมือยังไม่เชื่อมต่อกัน ข้อมูลจะกระจัดกระจายและทีมต้องทำงานซ้ำซ้อนเสียเวลา",
    # D7
    "D7_DUAL_LEGAL_EXPOSURE":     "หากไม่มีระบบควบคุมการเข้าถึงเงินและตรวจสอบการสูญเสีย ความเสี่ยงทุจริตอาจสร้างความเสียหายร้ายแรงโดยไม่รู้ตัว",
    "D7_LEGAL_BUT_UNPROTECTED":   "หากความเสี่ยงด้านกฎหมาย ภาษี ใบอนุญาต และสัญญายังค้างอยู่ อาจเกิดค่าปรับหรือข้อพิพาทที่กระทบเงินทุนและชื่อเสียง",
    "D7_NO_EXTERNAL_PERSPECTIVE": "หากไม่มีการประเมินความเสี่ยงและแผนฉุกเฉิน จุดบอดจะสะสมจนกลายเป็นวิกฤตที่รับมือไม่ทัน",
    "D7_INFORMAL_OPERATIONS":     "หากระบบยังไม่เป็นทางการ การขอสินเชื่อหรือดึงนักลงทุนจะยาก และข้อพิพาทจะยุ่งยากเพราะไม่มีเอกสารรองรับ",
    "D7_CRISIS_UNREADY":          "หากไม่มีแผนรับมือและเอกสารสำคัญไม่เป็นระบบ เมื่อเกิดวิกฤตจะไม่มีฐานทางกฎหมายและข้อมูลช่วยปกป้องธุรกิจ",
    "D7_GOVERNANCE_STRONG":       "หากไม่ยกระดับสู่มาตรฐานสากล อาจเสียโอกาสจากนักลงทุนหรือสถาบันการเงินที่ต้องการธรรมาภิบาลระดับสูง",
}


# ──────────────────────────────────────────────────────────────────
# Principle & benefit — one statement per dimension explaining WHY the
# dimension matters (the principle) and the upside of doing it well.
# Dimension-level and light-independent.
# ──────────────────────────────────────────────────────────────────

DIM_PRINCIPLES = {
    "D1": "หลักการ: ธุรกิจที่ยั่งยืนต้องแยกเงินส่วนตัวออกจากเงินธุรกิจ และตัดสินใจจากตัวเลขจริงไม่ใช่ความรู้สึก เมื่อระบบการเงินแม่นยำ คุณจะเห็นกำไรที่แท้จริง คุมกระแสเงินสดได้ และวางแผนเติบโตได้อย่างมั่นใจ",
    "D2": "หลักการ: รายได้ที่มั่นคงมาจากการรู้จักลูกค้าที่ใช่ มีจุดต่างที่ชัดเจน และทำให้ลูกค้ากลับมาซื้อซ้ำ เมื่อทำได้ ต้นทุนการตลาดจะลดลงและรายได้จะคาดการณ์ได้แม่นยำขึ้น",
    "D3": "หลักการ: ธุรกิจจะขยายได้ก็ต่อเมื่อระบบงานไม่ผูกกับตัวเจ้าของ และมีมาตรฐานที่ทำซ้ำได้ เมื่อมีระบบ คุณภาพจะสม่ำเสมอและส่งมอบงานได้มากขึ้นโดยไม่เพิ่มภาระเจ้าของ",
    "D4": "หลักการ: คนคือสินทรัพย์ที่สร้างผลงาน ธุรกิจที่ดีต้องรักษาคนเก่ง พัฒนาทักษะ และมีแผนสำรองตำแหน่งสำคัญ เมื่อทีมมั่นคง ผลงานจะต่อเนื่องและความรู้จะอยู่กับองค์กร",
    "D5": "หลักการ: ห่วงโซ่อุปทานที่ดีต้องไม่พึ่งซัพพลายเออร์รายเดียว มองเห็นสต็อกจริง และวางแผนจัดซื้อล่วงหน้า เมื่อทำได้ ต้นทุนจะควบคุมได้และลดความเสี่ยงการหยุดชะงัก",
    "D6": "หลักการ: เทคโนโลยีและข้อมูลช่วยให้ตัดสินใจแม่นยำขึ้นและลดงานซ้ำซ้อน ธุรกิจยุคใหม่ต้องมีตัวตนออนไลน์และปกป้องข้อมูล เมื่อทำได้ คุณจะแข่งขันได้เร็วขึ้นด้วยต้นทุนที่ต่ำลง",
    "D7": "หลักการ: ธรรมาภิบาลและการควบคุมภายในคือเกราะป้องกันธุรกิจจากการทุจริต ข้อพิพาท และวิกฤต เมื่อมีระบบควบคุมที่ดี ธุรกิจจะน่าเชื่อถือต่อคู่ค้า นักลงทุน และสถาบันการเงิน",
}


def _consequence_text(patterns, light):
    """Pick the most relevant consequence(s) from detected patterns.
    Returns "" for GREEN (handled as upside elsewhere)."""
    if not patterns:
        return ""
    chosen = [PATTERN_CONSEQUENCES[p] for p in patterns if PATTERN_CONSEQUENCES.get(p)]
    if not chosen:
        return ""
    return chosen[0]


def _static_fallback(dim, light, business_type, patterns=None, answers=None):
    """
    Return content from static NARRATIVES dict, enhanced with pattern- and
    answer-driven root_cause and whats_working sections.
    """
    btype_narrative = NARRATIVES.get(dim, {}).get(light, {}).get(business_type)
    if not btype_narrative:
        btype_narrative = NARRATIVES.get(dim, {}).get(light, {}).get("general", {})
    if not btype_narrative:
        btype_narrative = {}

    # ── root_cause: built from detected pattern codes ──────────────
    root_cause = ""
    if patterns:
        _CONFLICT = {
            "D1_CASH_TIGHT_DECLINING": {"D1_PROFITABLE_NO_RECURRING", "D1_STRONG_RECURRING_BASE"},
            "D1_CASH_CRISIS_NO_SYSTEM": {"D1_PROFITABLE_NO_RECURRING", "D1_STRONG_RECURRING_BASE"},
            "D1_GROWING_BUT_DEBT_TRAP": {"D1_PROFITABLE_NO_RECURRING", "D1_STRONG_RECURRING_BASE"},
        }
        chosen = []
        for p in patterns:
            if not PATTERN_ROOT_CAUSES.get(p):
                continue
            if any(p in _CONFLICT.get(c, set()) or c in _CONFLICT.get(p, set()) for c in chosen):
                continue  # skip a cause that contradicts one already chosen
            chosen.append(p)
        causes = [PATTERN_ROOT_CAUSES[p] for p in chosen]
        if causes:
            root_cause = "  ".join(causes[:2])

    # ── whats_working: highest-scoring questions in this dimension ──
    whats_working = ""
    if answers:
        dim_num = dim[1]  # "1" for D1, "2" for D2, …
        good_qs = {
            qid: score
            for qid, score in answers.items()
            if qid.startswith(dim_num + ".") and score >= 2
        }
        if good_qs:
            top = sorted(good_qs.items(), key=lambda x: x[1], reverse=True)[:2]
            labels = [QUESTION_LABELS.get(qid, qid) for qid, _ in top]
            whats_working = (
                f"ในมิตินี้มีสิ่งที่ทำได้ดีแล้ว ได้แก่ {' และ '.join(labels)} "
                f"ซึ่งเป็นรากฐานที่ดีสำหรับการพัฒนาต่อยอด"
            )
        elif not good_qs and light == "RED":
            whats_working = "การที่คุณทำแบบประเมินนี้ถือเป็นจุดเริ่มต้นที่ดี — การรู้ปัญหาก่อนคือก้าวแรกของการแก้ไข"

    # ── principle & benefit: dimension-level, light-aware framing ──
    principle_benefit = DIM_PRINCIPLES.get(dim, "")

    # ── consequence: downside of inaction (RED/YELLOW); upside for GREEN ──
    if light == "GREEN":
        consequence = ""
    else:
        consequence = _consequence_text(patterns or [], light)

    return {
        "summary":           btype_narrative.get("summary", ""),
        "current_state":     btype_narrative.get("detail", ""),
        "detail":            btype_narrative.get("detail", ""),
        "fact":              _fact_sentence(dim, answers),
        "root_cause":        root_cause,
        "whats_working":     whats_working,
        "principle_benefit": principle_benefit,
        "consequence":       consequence,
        "actions":           btype_narrative.get("actions", []),
        "industry_context":  "",
        "cta_flag":          btype_narrative.get("cta_flag", light == "RED"),
        "_source":           "static_fallback",
    }


# ──────────────────────────────────────────────────────────────────
# Main entry point — called from app.py
# ──────────────────────────────────────────────────────────────────

def get_narrative(dim, light, answers, context, db):
    """
    Public API. Returns narrative dict for one dimension.

    Args:
        dim:     "D1" … "D7"
        light:   "RED" / "YELLOW" / "GREEN"
        answers: full {question_id: score} dict for the assessment
        context: {"business_type", "age_bucket", "revenue_bucket",
                  "employee_bucket", "business_name"}
        db:      open SQLite connection (from get_db())

    Returns dict with keys:
        summary, current_state, detail, root_cause,
        whats_working, actions, industry_context, cta_flag
    """
    patterns = detect_patterns(dim, answers)
    narr = get_or_generate_narrative(dim, light, patterns, context, db, answers=answers)
    return apply_industry_overrides(narr, dim, light, context.get("business_type", ""))


def get_all_narratives(all_dims_light, answers, context, db):
    """
    Convenience: generate narratives for all 7 dimensions.
    Returns {"D1": {...}, "D2": {...}, ...}
    """
    return {
        dim: get_narrative(dim, light, answers, context, db)
        for dim, light in all_dims_light.items()
    }


# ──────────────────────────────────────────────────────────────────
# Static fallback — v1 content (Thai, all dims)
# ──────────────────────────────────────────────────────────────────

NARRATIVES = {
    "D1": {
        "RED": {
            "general": {
                "summary": "ระบบการเงินของคุณมีช่องโหว่ร้ายแรงที่อาจทำให้ธุรกิจล้มได้ก่อนที่คุณจะรู้ตัว",
                "detail": "ปัญหาหลักที่พบคือการขาดระบบบัญชีที่แยกชัดเจนระหว่างเงินส่วนตัวและเงินธุรกิจ ทำให้ไม่สามารถวัดกำไร-ขาดทุนที่แท้จริงได้ เมื่อรวมกับสภาพคล่องที่ต่ำและต้นทุนที่ไม่ชัดเจน ธุรกิจเสี่ยงต่อการขาดเงินสดกะทันหัน",
                "actions": [
                    "[สัปดาห์ 1] เปิดบัญชีธนาคารแยกสำหรับธุรกิจโดยเฉพาะ",
                    "[สัปดาห์ 2] บันทึกรายรับ-รายจ่ายทุกวันด้วย Excel หรือ FlowAccount",
                    "[เดือน 1] คำนวณ Gross Margin ของสินค้า/บริการแต่ละรายการ",
                    "[เดือน 2] ตั้งเป้า Cash Reserve ให้ครอบคลุมค่าใช้จ่ายคงที่ 2–3 เดือน",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "ระบบการเงินของคุณเริ่มมีโครงสร้าง แต่ยังมีช่องโหว่ที่ต้องอุดก่อนที่จะขยายธุรกิจ",
                "detail": "คุณมีพื้นฐานที่ดีในการแยกบัญชี แต่ยังขาดการติดตามสม่ำเสมอและการวิเคราะห์ต้นทุนเชิงลึก",
                "actions": [
                    "[ทันที] ทำ P&L Statement รายเดือนด้วย Excel",
                    "[เดือน 1] ทำ Cash Flow Forecast ล่วงหน้า 3 เดือน",
                    "[เดือน 2] พิจารณาใช้ซอฟต์แวร์บัญชีเพื่อลดเวลาและเพิ่มความแม่นยำ",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "ระบบการเงินของคุณแข็งแกร่ง — คุณรู้ตัวเลขและวางแผนได้จากข้อมูลจริง",
                "detail": "ธุรกิจของคุณมีระบบบัญชีและการติดตามสภาพคล่องที่ดี ซึ่งถือเป็นรากฐานสำคัญสำหรับการเติบโต",
                "actions": [
                    "[ทันที] เริ่มทำ Budget vs. Actual ทุกเดือน",
                    "[ไตรมาส 1] วางแผนภาษีเชิงรุกและตรวจสอบสิทธิ์ประโยชน์ SME",
                ],
                "cta_flag": False,
            },
        },
    },
    "D2": {
        "RED": {
            "general": {
                "summary": "ฐานลูกค้ายังไม่กลับมาซ้ำอย่างสม่ำเสมอ — รายได้จึงพึ่งลูกค้าใหม่และยอดขายรายวันมากเกินไป",
                "detail": "ยังไม่มีระบบติดตามว่าลูกค้ากลับมาซื้อซ้ำมากน้อยแค่ไหน หรือมาจากช่องทางใด ทำให้คาดเดารายได้และวางแผนการตลาดได้ยาก",
                "actions": [
                    "[สัปดาห์ 1] ทำรายชื่อลูกค้า Top 10 และวิเคราะห์สัดส่วนรายได้",
                    "[สัปดาห์ 2] สอบถามลูกค้า 5 ราย ว่าทำไมเลือกซื้อจากคุณ",
                    "[เดือน 1] เปิดช่องทางขายสำรองอย่างน้อย 1 ช่องทาง",
                    "[เดือน 2] เริ่มติดตาม Repeat Purchase Rate",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "คุณมีฐานลูกค้าพอสมควร แต่ยังขาดข้อมูลเชิงลึกและระบบรักษาลูกค้า",
                "detail": "คุณเริ่มมีการกระจายลูกค้าบ้าง แต่ยังขาดระบบติดตามความพึงพอใจและ Retention rate",
                "actions": [
                    "[ทันที] เริ่มเก็บข้อมูลลูกค้าอย่างเป็นระบบ",
                    "[เดือน 1] สร้าง Loyalty program หรือระบบ Follow-up",
                    "[เดือน 2] วิเคราะห์ช่องทางขายที่ให้ ROI สูงสุด",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "ฐานลูกค้าของคุณกระจายดีและมีระบบติดตาม — พร้อมขยายตลาดได้อย่างมั่นใจ",
                "detail": "คุณมีฐานลูกค้าที่กระจายดี มีข้อมูลยืนยัน และมีช่องทางสำรอง",
                "actions": [
                    "[ทันที] วิเคราะห์ CLV ของลูกค้าแต่ละ segment",
                    "[ไตรมาส 1] ทดลอง Referral program",
                ],
                "cta_flag": False,
            },
        },
    },
    "D3": {
        "RED": {
            "general": {
                "summary": "ธุรกิจพึ่งพาตัวคุณมากเกินไป — ถ้าคุณหายไป ธุรกิจจะหยุดชะงักทันที",
                "detail": "ไม่มีเอกสารขั้นตอนการทำงาน ไม่มีระบบติดตามสถานะงาน และไม่มี KPI ที่ชัดเจน",
                "actions": [
                    "[สัปดาห์ 1] เขียน SOP ของงานสำคัญ 3 อย่างแรก",
                    "[สัปดาห์ 2] มอบหมายงาน 1 อย่างให้คนอื่นรับผิดชอบเต็มตัว",
                    "[เดือน 1] ตั้ง KPI อย่างน้อย 3 ตัวที่วัดสุขภาพธุรกิจรายเดือน",
                    "[เดือน 2] ทดลองไม่เข้ามาดูแลงาน 1 วัน เพื่อทดสอบระบบ",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "มีระบบงานบ้าง แต่ยังไม่ครบถ้วนพอที่จะให้ธุรกิจเดินได้โดยไม่ต้องพึ่งคุณตลอด",
                "detail": "คุณเริ่มมีการจัดระบบ แต่ยังมีงานสำคัญหลายอย่างที่อยู่ในหัว",
                "actions": [
                    "[ทันที] จัดทำ Checklist สำหรับงาน routine ที่ทำซ้ำ",
                    "[เดือน 1] ใช้เครื่องมือ Task management เช่น Trello หรือ Notion",
                    "[เดือน 2] ตรวจสอบว่าทุกตำแหน่งมีคนสำรองอย่างน้อย 1 คน",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "ระบบงานของคุณเข้มแข็ง — ธุรกิจเดินได้แม้คุณไม่อยู่",
                "detail": "มี SOP ชัดเจน มีระบบติดตามงาน และมี KPI ที่วัดได้",
                "actions": [
                    "[ไตรมาส 1] ทำ Process audit เพื่อหา bottleneck และ waste",
                    "[ไตรมาส 1] พิจารณา Automate งาน routine ที่ทำซ้ำ",
                ],
                "cta_flag": False,
            },
        },
    },
    "D4": {
        "RED": {
            "general": {
                "summary": "ทีมของคุณมีความเสี่ยง Key Person สูง — การลาออกของคนเดียวอาจทำให้ธุรกิจวิกฤต",
                "detail": "มีบุคคลสำคัญที่ขาดไม่ได้ ไม่มีเป้าหมายชัดเจน และอัตราการลาออกสูง",
                "actions": [
                    "[สัปดาห์ 1] ระบุ Key Person ทุกตำแหน่งและเริ่มวางแผน Backup",
                    "[เดือน 1] กำหนด Role & Responsibility ชัดเจนสำหรับทุกตำแหน่ง",
                    "[เดือน 1] สอบถามทีมเรื่อง Pain point หลักที่ทำให้อยากลาออก",
                    "[เดือน 2] เริ่มโปรแกรม Cross-training",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "ทีมพอเดินได้ แต่ยังขาดระบบพัฒนาคนและรักษาคนอย่างเป็นระบบ",
                "detail": "มีทีมที่ทำงานได้ แต่ยังไม่มีเป้าหมายชัดเจนหรือระบบประเมินผล",
                "actions": [
                    "[ทันที] ตั้งเป้าหมายรายเดือนสำหรับพนักงานทุกคน",
                    "[เดือน 1] จัดประชุม 1-on-1 รายเดือนกับพนักงานหลัก",
                    "[ไตรมาส 1] วางแผน Career path สำหรับตำแหน่งสำคัญ",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "ทีมของคุณมีเสถียรภาพดีและพร้อมเติบโต",
                "detail": "มีระบบเป้าหมาย การประเมิน และ Backup ที่ดี อัตราการลาออกต่ำ",
                "actions": [
                    "[ไตรมาส 1] พัฒนาโปรแกรม Leadership สำหรับ High potential",
                    "[ปีนี้] สร้างวัฒนธรรมการเรียนรู้ด้วย Training budget ประจำปี",
                ],
                "cta_flag": False,
            },
        },
    },
    "D5": {
        "RED": {
            "general": {
                "summary": "ซัพพลายเชนของคุณเปราะบาง — การหยุดส่งสินค้าจากซัพพลายเออร์รายเดียวอาจทำให้ธุรกิจหยุดชะงัก",
                "detail": "พึ่งพาซัพพลายเออร์รายเดียว ไม่มีอำนาจต่อรอง และไม่รู้ล่วงหน้าเมื่อราคาจะเปลี่ยน",
                "actions": [
                    "[สัปดาห์ 1] ระบุสินค้า/บริการที่พึ่งซัพพลายเออร์หรือผู้ให้บริการรายเดียว",
                    "[เดือน 1] ติดต่อซัพพลายเออร์สำรองอย่างน้อย 1 รายสำหรับทุกรายการสำคัญ",
                    "[เดือน 1] เจรจาเงื่อนไขกับซัพพลายเออร์ปัจจุบัน",
                    "[เดือน 2] สร้างระบบแจ้งเตือนเมื่อสต็อกต่ำกว่าจุดสั่งซื้อ",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "มีซัพพลายเออร์บ้าง แต่ยังไม่มีแผนสำรองที่เพียงพอ",
                "detail": "มีทางเลือกบ้างแต่ยังไม่ได้ทดสอบ และยังไม่มีระบบติดตามราคาอย่างเป็นระบบ",
                "actions": [
                    "[ทันที] ทำรายงานต้นทุนจัดซื้อ/ผู้ให้บริการย้อนหลัง 6 เดือน",
                    "[เดือน 1] ทดสอบซัพพลายเออร์สำรองด้วยออเดอร์เล็ก",
                    "[เดือน 2] เจรจาสัญญาล็อกราคา 3-6 เดือนกับซัพพลายเออร์หลัก",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "ซัพพลายเชนของคุณมั่นคง — มีทางเลือกและอำนาจต่อรองที่ดี",
                "detail": "มีซัพพลายเออร์สำรอง มีอำนาจต่อรอง และรู้ล่วงหน้าเมื่อมีการเปลี่ยนแปลง",
                "actions": [
                    "[ไตรมาส 1] พิจารณา Strategic partnership กับซัพพลายเออร์หลัก",
                    "[ปีนี้] ทำ Total Cost of Ownership analysis",
                ],
                "cta_flag": False,
            },
        },
    },
    "D6": {
        "RED": {
            "general": {
                "summary": "ธุรกิจของคุณยังไม่ได้ใช้เทคโนโลยีเลย — เสี่ยงต่อการถูก disrupt",
                "detail": "ทุกอย่างยังทำมือ ข้อมูลสำคัญอยู่ในหัวหรือกระดาษ ไม่มี Backup",
                "actions": [
                    "[สัปดาห์ 1] สำรองข้อมูลสำคัญทั้งหมดขึ้น Cloud ทันที",
                    "[สัปดาห์ 2] เริ่มใช้เครื่องมือดิจิทัลพื้นฐาน เช่น Google Sheets, LINE OA",
                    "[เดือน 1] สำรวจว่า AI/Automation ตัวไหนช่วยลดงานซ้ำๆ ได้",
                    "[เดือน 2] เปิดช่องทางออนไลน์ให้ลูกค้าติดต่อ/สั่งซื้อได้ตลอด",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "คุณเริ่มใช้เทคโนโลยีบ้าง แต่ยังไม่เชื่อมต่อกันและข้อมูลยังไม่พร้อมใช้งาน",
                "detail": "มีเครื่องมือบางตัวแต่ข้อมูลกระจัดกระจาย ยังไม่มี Backup ที่น่าเชื่อถือ",
                "actions": [
                    "[ทันที] ตั้งระบบ Backup อัตโนมัติสำหรับข้อมูลสำคัญ",
                    "[เดือน 1] รวมข้อมูลลูกค้าเข้าระบบเดียว",
                    "[เดือน 2] ทดลองใช้ AI tool อย่างน้อย 1 ตัวในงาน routine",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "คุณใช้เทคโนโลยีได้ดีและข้อมูลพร้อมใช้งาน — พร้อมก้าวไปอีกขั้น",
                "detail": "มีระบบครบ เชื่อมต่อกัน มี Backup และเริ่มใช้ AI/Automation แล้ว",
                "actions": [
                    "[ไตรมาส 1] ใช้ข้อมูลลูกค้าทำ Personalized marketing",
                    "[ปีนี้] สำรวจ AI use cases ที่ให้ ROI สูงสุด",
                ],
                "cta_flag": False,
            },
        },
    },
    "D7": {
        "RED": {
            "general": {
                "summary": "ธุรกิจของคุณมีความเสี่ยงด้านการควบคุมภายในในระดับที่อันตราย",
                "detail": "ระบบควบคุมภายในที่อ่อนแอหรือไม่มีเลยถือเป็นความเสี่ยงสูงสุด โดยเฉพาะเมื่อมีคนมากกว่า 1 คนเข้าถึงเงินโดยไม่มีระบบตรวจสอบ",
                "actions": [
                    "[ภายใน 48 ชม.] ตรวจสอบสิทธิ์การเข้าถึงบัญชีธนาคาร ถอนสิทธิ์ที่ไม่จำเป็น",
                    "[สัปดาห์ 1] ตั้งระบบ Dual Authorization — การจ่ายเงินเกิน X บาท ต้องผ่าน 2 คน",
                    "[สัปดาห์ 2] ทำ Cash Count และ Stock Count ทันที",
                    "[เดือน 1] กำหนดนโยบายค่าใช้จ่ายชัดเจน",
                    "[เดือน 2] ปรึกษาผู้เชี่ยวชาญด้านการควบคุมภายใน",
                ],
                "cta_flag": True,
            },
        },
        "YELLOW": {
            "general": {
                "summary": "มีระบบควบคุมบางส่วนแล้ว แต่ยังมีช่องโหว่ที่ต้องปิด",
                "detail": "คุณเริ่มมีการแบ่งหน้าที่และตรวจสอบ แต่ยังไม่ครอบคลุม การอุดช่องโหว่ที่เหลือจะลดความเสี่ยงได้มาก",
                "actions": [
                    "[เดือน 1] ทบทวนสิทธิ์การเข้าถึงบัญชีและระบบทุกตัว",
                    "[เดือน 1] ตั้ง Alert ธนาคาร ทุกธุรกรรม",
                    "[เดือน 2] จัดทำ Business Continuity Plan เบื้องต้น",
                    "[เดือน 3] ทำ Risk Assessment ประจำปี",
                ],
                "cta_flag": False,
            },
        },
        "GREEN": {
            "general": {
                "summary": "ระบบควบคุมภายในของคุณแข็งแกร่ง — ธุรกิจมีความยั่งยืนสูง",
                "detail": "มีการแบ่งหน้าที่ชัดเจน มีระบบตรวจสอบ มีแผนรับมือเหตุฉุกเฉิน และมีการประเมินความเสี่ยงสม่ำเสมอ ซึ่งเป็นรากฐานของธุรกิจที่ยั่งยืน",
                "actions": [
                    "[ไตรมาส 1] Review และ Update นโยบายควบคุมภายใน",
                    "[ปีนี้] พิจารณาจ้าง Internal Auditor หรือใช้บริการ Outsource",
                    "[ปีนี้] ทำ Scenario Planning สำหรับความเสี่ยงใหม่",
                ],
                "cta_flag": False,
            },
        },
    },
}


# ══════════════════════════════════════════════════════════════════
# Roadmap · KPI Control System · Benchmark
# Re-derived generators (consumed by pdf_report.generate_pdf and app.py)
# ══════════════════════════════════════════════════════════════════

import re as _re

# Full dimension display names (kept local so this module is self-contained)
DIM_FULL_NAMES = {
    "D1": "การเงินและสภาพคล่อง",
    "D2": "ลูกค้าและการตลาด",
    "D3": "ระบบงานและกระบวนการ",
    "D4": "ทีมและทรัพยากรมนุษย์",
    "D5": "ซัพพลายเชนและต้นทุน",
    "D6": "เทคโนโลยีและนวัตกรรม",
    "D7": "ธรรมาภิบาลและความเสี่ยง",
}
DIM_SHORT_NAMES = {
    "D1": "การเงิน", "D2": "การตลาด", "D3": "ระบบงาน", "D4": "ทีมงาน",
    "D5": "ซัพพลายเชน", "D6": "เทคโนโลยี", "D7": "ธรรมาภิบาล",
}
ALL_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]

OWNER_BY_DIM = {
    "D1": "เจ้าของ / ฝ่ายบัญชี", "D2": "เจ้าของ / การตลาด", "D3": "เจ้าของ / ผู้จัดการ",
    "D4": "เจ้าของ / HR", "D5": "เจ้าของ / จัดซื้อ", "D6": "เจ้าของ / IT", "D7": "เจ้าของ / ผู้บริหาร",
}

# Map an action time-prefix to a 90-day roadmap phase index (0..2)
_PHASE_OF_PREFIX = {
    "ทันที": 0, "สัปดาห์ 1": 0, "สัปดาห์ 2": 0, "สัปดาห์": 0,
    "เดือน 1": 1,
    "เดือน 2": 2, "เดือน 3": 2, "ไตรมาส 1": 2, "ไตรมาส": 2, "ปีนี้": 2,
}

ROADMAP_PHASES = [
    {"label": "สัปดาห์ 1–2", "tag": "Quick Wins"},
    {"label": "เดือนที่ 1",   "tag": "Foundation Fixes"},
    {"label": "เดือนที่ 2–3", "tag": "System Building"},
]


def _split_action_prefix(action):
    """'[สัปดาห์ 1] เปิดบัญชี...' -> ('สัปดาห์ 1', 'เปิดบัญชี...')"""
    m = _re.match(r"\s*\[([^\]]+)\]\s*(.*)", action or "")
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", (action or "").strip()


def _phase_index(prefix):
    if prefix in _PHASE_OF_PREFIX:
        return _PHASE_OF_PREFIX[prefix]
    # fuzzy: match leading keyword
    for key, idx in _PHASE_OF_PREFIX.items():
        if prefix.startswith(key):
            return idx
    return 1  # default to Foundation


import json as _json
import os as _os

_IB_PATH = _os.path.join(_os.path.dirname(__file__), "industry_benchmarks.json")
try:
    with open(_IB_PATH, encoding="utf-8") as _f:
        INDUSTRY_CONFIG = _json.load(_f)
except Exception as _e:
    log.warning("industry_benchmarks.json load failed: %s", _e)
    INDUSTRY_CONFIG = {"profiles": {"default": {"dimensions": {}}}}


def _merged_profile(business_type):
    """Return {dim: dimension_config} merging the industry profile over default."""
    profs = INDUSTRY_CONFIG.get("profiles", {})
    base_dims = profs.get("default", {}).get("dimensions", {})
    ind_dims = profs.get(business_type, {}).get("dimensions", {})
    return {d: (ind_dims.get(d) or base_dims.get(d) or {}) for d in ALL_DIMS}


def get_actions(dim, light, business_type):
    """Industry-specific recommendations from JSON if present, else generic static actions."""
    prof = _merged_profile(business_type)
    recs = (prof.get(dim, {}).get("recommendations") or {}).get(light)
    if recs:
        return list(recs)
    return list(NARRATIVES.get(dim, {}).get(light, {}).get("general", {}).get("actions", []))


def apply_industry_overrides(narr, dim, light, business_type):
    """Overlay industry-specific narrative text and recommendations onto a narrative dict."""
    prof = _merged_profile(business_type)
    dd = prof.get(dim, {})
    nov = (dd.get("narrative") or {}).get(light)
    if nov:
        for k in ("summary", "current_state", "root_cause", "whats_working"):
            if nov.get(k):
                narr[k] = nov[k]
        if nov.get("current_state"):
            narr["detail"] = nov["current_state"]
    recs = (dd.get("recommendations") or {}).get(light)
    if recs:
        narr["actions"] = list(recs)
    return narr


def get_roadmap(business_type, dim_lights, dim_pct=None):
    """
    Build a 90-day action roadmap from the static action library.
    Only RED/YELLOW dimensions are included (these need fixing first),
    RED before YELLOW. Actions are bucketed into 3 phases by their
    time-prefix. Returns a dict consumed by pdf_report.

    Returns:
        {
          "title": "แผนปฏิบัติ 90 วัน",
          "subtitle": "...",
          "priority_dims": ["D1","D5",...],   # ordered chips for header
          "phases": [
             {"label","tag","items":[{"dim","dim_name","text"}, ...]}, ...
          ]
        }
    """
    nongreen = [d for d in ALL_DIMS if dim_lights.get(d) != "GREEN"]
    if dim_pct:
        # most urgent first (lowest score), keeps roadmap / exec-summary / conclusion consistent
        order = sorted(nongreen, key=lambda d: (dim_pct.get(d, 0), ALL_DIMS.index(d)))
    else:
        order = ([d for d in ALL_DIMS if dim_lights.get(d) == "RED"]
                 + [d for d in ALL_DIMS if dim_lights.get(d) == "YELLOW"])

    all_green = not order
    if all_green:
        # business is healthy across the board -> a sustain / optimize roadmap
        order = sorted(ALL_DIMS, key=lambda d: ((dim_pct or {}).get(d, 0), ALL_DIMS.index(d)), reverse=True)
    subtitle = ("ธุรกิจอยู่ในเกณฑ์ดีทุกมิติ — แผนรักษามาตรฐานและต่อยอด"
                if all_green else "เรียงลำดับความสำคัญจากมิติที่มีความเสี่ยงสูงสุดก่อน")

    phases = [{"label": p["label"], "tag": p["tag"], "items": []} for p in ROADMAP_PHASES]

    for d in order:
        light = dim_lights.get(d)
        actions = get_actions(d, light, business_type)
        for a in actions:
            prefix, text = _split_action_prefix(a)
            idx = _phase_index(prefix)
            phases[idx]["items"].append({
                "dim": d,
                "dim_name": DIM_SHORT_NAMES.get(d, d),
                "text": text,
            })

    return {
        "title": "แผนปฏิบัติ 90 วัน",
        "subtitle": subtitle,
        "priority_dims": order,
        "all_green": all_green,
        "phases": phases,
    }


# ── KPI Control System ────────────────────────────────────────────
# rows: (KPI, target, warning, frequency)
KPI_LIBRARY = {
    "D1": [
        ("Cash Runway", "> 90 วัน", "< 60 วัน", "รายสัปดาห์"),
        ("Gross Margin", "> 50%", "< 30%", "รายเดือน"),
        ("Revenue MoM Growth", "> 5%", "< 0% ติดต่อกัน 2 เดือน", "รายเดือน"),
    ],
    "D2": [
        ("Repeat Purchase Rate", "> 30%", "< 15%", "รายเดือน"),
        ("Customer Concentration", "Top 1 < 30% ของรายได้", "Top 1 > 50%", "รายไตรมาส"),
        ("NPS / Review Score", "> 4.5/5", "< 4.0/5", "รายเดือน"),
    ],
    "D3": [
        ("SOP Coverage", "> 80% ของงาน routine", "< 50%", "ราย 3 เดือน"),
        ("Error / Rework Rate", "< 2%", "> 5%", "รายสัปดาห์"),
        ("Owner Decision Dependency", "< 30% ของ decisions", "> 60%", "ราย 3 เดือน"),
    ],
    "D4": [
        ("Employee Turnover Rate", "< 15%/ปี", "> 30%/ปี", "รายไตรมาส"),
        ("Key Person Backup Coverage", "100% ของ key roles", "< 50%", "ราย 6 เดือน"),
        ("Employee Engagement Score", "> 70%", "< 50%", "รายไตรมาส"),
    ],
    "D5": [
        ("Supplier Concentration", "Top 1 < 40%", "Top 1 > 70%", "รายไตรมาส"),
        ("Stockout Incidents", "0 ครั้ง/เดือน", "> 2 ครั้ง/เดือน", "รายเดือน"),
        ("Inventory Days", "15-30 วัน", "> 60 วัน หรือ < 7 วัน", "รายเดือน"),
    ],
    "D6": [
        ("Digital Tool Adoption", "POS + บัญชี + CRM ครบ", "ไม่มีเครื่องมือดิจิทัลเลย", "ราย 6 เดือน"),
        ("Data Backup Status", "Backup อัตโนมัติทุกวัน", "ไม่มี Backup", "รายสัปดาห์"),
        ("Online Revenue %", "> 20% ของยอดขาย", "0%", "รายเดือน"),
    ],
    "D7": [
        ("Legal & Tax Compliance", "ไม่มีเอกสารค้าง", "มีเอกสาร/ภาษีค้าง", "ราย 6 เดือน"),
        ("Contract Coverage", "ลูกค้า/ซัพพลายเออร์หลักมีสัญญา 100%", "< 50%", "ราย 6 เดือน"),
        ("BCP Readiness", "มีแผนฉุกเฉิน 3 สถานการณ์", "ไม่มีแผนเลย", "รายปี"),
    ],
}

# Business-type specific KPI tweaks (replace a row by KPI name)
KPI_OVERRIDES = {
    "restaurant": {
        "Gross Margin": ("Gross Margin (Food Cost)", "Food Cost < 35%", "Food Cost > 50%", "รายเดือน"),
    },
    "ecommerce": {
        "Gross Margin": ("Net Margin after fees", "> 15%", "< 5%", "รายเดือน"),
    },
    "startup": {
        "Cash Runway": ("Runway (months)", "> 12 เดือน", "< 6 เดือน", "รายเดือน"),
        "Supplier Concentration": ("Vendor Concentration", "เจ้าหลัก < 40%", "> 70%", "รายไตรมาส"),
        "Stockout Incidents": ("Cloud/Infra Cost % รายได้", "< 15%", "> 30%", "รายเดือน"),
        "Inventory Days": ("Gross Margin", "> 70%", "< 50%", "รายเดือน"),
    },
    "ecommerce_extra_placeholder": {},
}


# ── KPI tracking start-date (auto-derived from traffic light) ─────
import datetime as _dt

_TH_MONTHS_ABBR = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
                   "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def _fmt_thai_date(d):
    """Thai-style short date with Buddhist year, e.g. 24 มิ.ย. 2569."""
    return f"{d.day} {_TH_MONTHS_ABBR[d.month]} {d.year + 543}"


# Days from report date to when tracking each KPI should begin, by light.
# RED needs immediate monitoring; GREEN can wait until the optimise phase.
_KPI_START_OFFSET = {
    "RED":    (0,  "ทันที (สัปดาห์นี้)"),
    "YELLOW": (30, "ภายใน 1 เดือน"),
    "GREEN":  (90, "ภายในไตรมาสนี้"),
}


def kpi_start_for_light(light, base=None):
    """Return (start_date_str, start_iso, start_label) for a dimension light."""
    base = base or _dt.date.today()
    offset, label = _KPI_START_OFFSET.get(light, _KPI_START_OFFSET["RED"])
    d = base + _dt.timedelta(days=offset)
    return _fmt_thai_date(d), d.isoformat(), label


def get_kpi_table(business_type, dim_lights, start_base=None):
    """
    Return per-dimension KPI control rows, ordered so that RED/YELLOW
    dimensions come first (these must be tracked most closely), then GREEN.

    Returns:
        [
          {"dim","dim_name","light","rows":[(kpi,target,warning,freq),...]},
          ...
        ]
    """
    prof = _merged_profile(business_type)
    rank = {"RED": 0, "YELLOW": 1, "GREEN": 2}
    order = sorted(ALL_DIMS, key=lambda d: (rank.get(dim_lights.get(d, "RED"), 0), ALL_DIMS.index(d)))

    out = []
    for d in order:
        rules = prof.get(d, {}).get("kpi_rules", [])
        rows = [(r.get("kpi_name", ""), r.get("target_condition", ""),
                 r.get("warning_condition", ""), r.get("tracking_frequency", "")) for r in rules]
        _light = dim_lights.get(d, "RED")
        _sdate, _siso, _slabel = kpi_start_for_light(_light, start_base)
        out.append({
            "dim": d,
            "dim_name": DIM_FULL_NAMES.get(d, d),
            "light": _light,
            "owner": OWNER_BY_DIM.get(d, "เจ้าของ"),
            "rows": rows,
            "start_date": _sdate,
            "start_iso": _siso,
            "start_label": _slabel,
        })
    return out


# ── Benchmark / industry context ──────────────────────────────────
BENCHMARK_BASE = {
    "D1": "ธุรกิจขนาดเล็กถือเงินสดสำรองมัธยฐานเพียง ~27 วัน ขณะที่กลุ่มแข็งแรงสุด 25% ถือไว้ 62 วันขึ้นไป — ควรตั้งเป้าสำรองค่าใช้จ่ายคงที่ 2–3 เดือน (ที่มา: JPMorgan Chase Institute)",
    "D2": "อัตราซื้อซ้ำเฉลี่ยอยู่ที่ ~28% (เกณฑ์ดี 20–40%) และการหาลูกค้าใหม่มีต้นทุนสูงกว่าการรักษาลูกค้าเดิม 5–25 เท่า การเพิ่ม retention เพียง 5% สามารถเพิ่มกำไรได้ 25–95% (ที่มา: Bain & Company; LoyaltyLion)",
    "D3": "ผลิตภาพรวม (TFP) ของ SME ไทยปี 2024 ติดลบ −0.27 สะท้อนว่าหลายธุรกิจใช้ทรัพยากรมากขึ้นแต่ผลิตได้น้อยลง — การวาง SOP และลดการพึ่งเจ้าของช่วยยกระดับผลิตภาพ (ที่มา: สสว./OSMEP)",
    "D4": "อัตราการลาออกโดยสมัครใจเฉลี่ยอยู่ที่ ~13% ต่อปี (Mercer 2024–25) โดยระดับที่ถือว่าสุขภาพดีคือต่ำกว่า 10% ต่อปี (ที่มา: Mercer; Gallup)",
    "D5": "ธุรกิจที่ทนทานมักไม่พึ่งซัพพลายเออร์/ผู้ให้บริการรายเดียวเกิน 40% ของยอดซื้อ และคุมต้นทุนผันแปรให้สมดุลกับรายได้",
    "D6": "ธุรกิจขนาดเล็กในไทยใช้คอมพิวเตอร์ราว 65% และเข้าถึงอินเทอร์เน็ต ~70% แต่มีเพียง ~13% ที่มีบุคลากรสายไอที — การปิดช่องว่างดิจิทัลจึงเป็นโอกาสสร้างความได้เปรียบ (ที่มา: ASEAN SME Policy Index 2024)",
    "D7": "ธุรกิจขนาดเล็ก 1 ใน 4 มีเงินสดสำรองไม่ถึง 13 วัน จึงเปราะบางมากต่อเหตุไม่คาดฝัน การมีแผนรับมือฉุกเฉิน (BCP) และระบบควบคุมภายในที่ดีช่วยลดความเสี่ยงนี้อย่างมีนัยสำคัญ (ที่มา: JPMorgan Chase Institute)",
}

# Industry-specific benchmark overrides (only where the generic line would be wrong)
BENCHMARK_OVERRIDES = {
    "restaurant": {
        "D1": "ธุรกิจขนาดเล็กถือเงินสดสำรองมัธยฐาน ~27 วัน แต่ร้านอาหารถือเฉลี่ยเพียง ~16 วัน — ควรตั้งเป้าสำรองค่าใช้จ่ายคงที่อย่างน้อย 2 เดือน (ที่มา: JPMorgan Chase Institute)",
        "D5": "สำหรับร้านอาหาร ต้นทุนหลัก (วัตถุดิบ+แรงงาน) ควรคุมไว้ที่ 55–65% ของยอดขาย และไม่พึ่งซัพพลายเออร์วัตถุดิบสดรายเดียวเกิน 40% (ที่มา: National Restaurant Association, 2024)",
    },
    "startup": {
        "D1": "สตาร์ทอัพควรรักษา Runway ให้มากกว่า 12–18 เดือน และรู้ Burn Rate รายเดือนเสมอ กิจการที่แข็งแรงมักมีสภาพคล่องสำรองสูงกว่าค่ามัธยฐานของ SME ทั่วไป (ที่มา: JPMorgan Chase Institute; แนวปฏิบัติ VC)",
        "D5": "สำหรับธุรกิจเทค ต้นทุนหลักคือโครงสร้างพื้นฐาน/บริการคลาวด์และค่าธรรมเนียมแพลตฟอร์ม ควรคุม Cloud Cost ให้สัมพันธ์กับรายได้ และไม่พึ่งผู้ให้บริการรายเดียวมากเกินไป",
        "D6": "สำหรับสตาร์ทอัพ เทคโนโลยีและข้อมูลคือแกนหลักของธุรกิจ ควรมีระบบสำรองข้อมูลอัตโนมัติและความปลอดภัยไซเบอร์ที่ได้มาตรฐานตั้งแต่ต้น",
    },
    "ecommerce": {
        "D5": "สำหรับ E-commerce ควรคุมต้นทุนสินค้าและค่าโลจิสติกส์/ค่าธรรมเนียมแพลตฟอร์ม และไม่พึ่งซัพพลายเออร์หรือช่องทางขายรายเดียวเกิน 40%",
    },
}


def get_benchmark(business_type, dim_lights, db=None):
    """Industry-aware benchmark line per dimension, read from industry_benchmarks.json."""
    prof = _merged_profile(business_type)
    res = {}
    for d in ALL_DIMS:
        dd = prof.get(d, {})
        ctx = dd.get("benchmark_context", "")
        src = dd.get("source_ref", "")
        res[d] = f"{ctx} (ที่มา: {src})" if (ctx and src) else ctx
    return res


BENCHMARK_SOURCES = [
    ("JPMorgan Chase Institute", "Cash is King: Flows, Balances, and Buffer Days (งานวิจัยธุรกิจขนาดเล็ก 597,000 ราย)", "jpmorganchase.com/institute"),
    ("National Restaurant Association", "Restaurant Economic Insights / Operations Data, 2024 — เกณฑ์ต้นทุนอาหารและแรงงาน", "restaurant.org"),
    ("สสว. (OSMEP)", "รายงานสถานการณ์วิสาหกิจขนาดกลางและขนาดย่อม และผลิตภาพรวม (TFP), 2024", "sme.go.th"),
    ("ASEAN SME Policy Index 2024 (OECD/ERIA)", "Enabling Sustainable Growth and Digitalisation of SMEs", "asean.org"),
    ("Mercer / Gallup", "Turnover Survey 2024–25; Gallup State of the Global Workplace — engagement & turnover", "gallup.com"),
    ("Bain & Company / LoyaltyLion", "Customer retention economics & repeat-purchase benchmarks", "bain.com"),
    ("NIST", "Small Business Cybersecurity Corner — MFA, access control, data & cloud protection, 2026", "nist.gov"),
    ("AICPA", "AT-C Section 215 Agreed-Upon Procedures — แนวทางหากต้องการภาคผนวกตรวจรับโดยบุคคลที่สาม", "aicpa-cima.com"),
]


def get_benchmark_sources():
    return list(BENCHMARK_SOURCES)


# ══════════════════════════════════════════════════════════════════
# Hard-floor (red-flag) one-liners — single source of truth, shared by
# the paid PDF's "สัญญาณอันตราย" box and the FREE results danger box.
# dim -> (dimension name, plain-language reason). Reasons map to the
# scoring.RED_FLAG_QUESTIONS that force a dimension RED.
# ══════════════════════════════════════════════════════════════════
HARD_FLOOR_LABELS = {
    "D1": ("การเงินและสภาพคล่อง", "ยังไม่รู้กำไร–ขาดทุนรายเดือน จึงมองไม่เห็นสุขภาพการเงินที่แท้จริง"),
    "D2": ("ลูกค้าและการตลาด", "รายได้กระจุกตัวอยู่กับลูกค้าน้อยราย เสี่ยงสูงหากเสียลูกค้าหลัก"),
    "D3": ("ระบบงานและกระบวนการ", "ธุรกิจพึ่งพาเจ้าของเกือบทั้งหมด หยุดชะงักทันทีหากเจ้าของไม่อยู่"),
    "D4": ("ทีมและทรัพยากรมนุษย์", "มีบุคคลสำคัญที่ขาดไม่ได้และยังไม่มีคนสำรอง (Key Person Risk)"),
    "D5": ("ซัพพลายเชนและต้นทุน", "พึ่งซัพพลายเออร์/ผู้ให้บริการรายเดียวโดยไม่มีทางเลือกสำรอง"),
    "D6": ("เทคโนโลยีและนวัตกรรม", "ไม่มีระบบสำรองข้อมูล/ความปลอดภัย เสี่ยงข้อมูลสูญหายหรือรั่วไหล"),
    "D7": ("ธรรมาภิบาลและความเสี่ยง", "ยังไม่มีการควบคุมการเข้าถึงเงินหรือป้องกันการทุจริตอย่างเพียงพอ"),
}


def hard_floor_items(red_flags, limit=2):
    """Return up to `limit` readable hard-floor warnings for the danger box.

    `red_flags` is the list from scoring (bare dim codes like ["D1","D5"], but
    tolerant of strings that merely contain a code). Returns
    [{"dim","name","reason"}, …] de-duplicated and capped at `limit`.
    """
    out = []
    seen = set()
    for code in (red_flags or []):
        dim = next((d for d in HARD_FLOOR_LABELS if d in str(code)), None)
        if not dim or dim in seen:
            continue
        seen.add(dim)
        name, reason = HARD_FLOOR_LABELS[dim]
        out.append({"dim": dim, "name": name, "reason": reason})
        if len(out) >= limit:
            break
    return out
