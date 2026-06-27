import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

pdfmetrics.registerFont(TTFont("Sarabun", os.path.join(FONTS_DIR, "Sarabun-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Sarabun-Bold", os.path.join(FONTS_DIR, "Sarabun-Bold.ttf")))
pdfmetrics.registerFontFamily("Sarabun", normal="Sarabun", bold="Sarabun-Bold")

LIGHT_COLORS = {
    "RED": colors.HexColor("#DC2626"),
    "YELLOW": colors.HexColor("#D97706"),
    "GREEN": colors.HexColor("#16A34A"),
}
LIGHT_BG = {
    "RED": colors.HexColor("#FEE2E2"),
    "YELLOW": colors.HexColor("#FEF3C7"),
    "GREEN": colors.HexColor("#DCFCE7"),
}
GRADE_COLORS = {
    "CRITICAL": colors.HexColor("#DC2626"),
    "WATCH": colors.HexColor("#D97706"),
    "HEALTHY": colors.HexColor("#16A34A"),
    "STRONG": colors.HexColor("#059669"),
}
GRADE_TH = {
    "CRITICAL": "วิกฤต",
    "WATCH": "ต้องระวัง",
    "HEALTHY": "สุขภาพดี",
    "STRONG": "แข็งแกร่ง",
}
DIM_NAMES = {
    "D1": "การเงินและสภาพคล่อง",
    "D2": "ลูกค้าและการตลาด",
    "D3": "ระบบงานและกระบวนการ",
    "D4": "ทีมและทรัพยากรมนุษย์",
    "D5": "ซัพพลายเชนและต้นทุน",
    "D6": "เทคโนโลยีและนวัตกรรม",
    "D7": "ธรรมาภิบาลและความเสี่ยง",
}
LIGHT_TH = {"RED": "แดง — เสี่ยงสูง", "YELLOW": "เหลือง — ควรปรับปรุง", "GREEN": "เขียว — ดี"}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ThTitle", fontName="Sarabun-Bold", fontSize=24, leading=30, alignment=TA_CENTER, textColor=colors.HexColor("#1E3A5F")))
    styles.add(ParagraphStyle("ThSubtitle", fontName="Sarabun", fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#6B7280")))
    styles.add(ParagraphStyle("ThH1", fontName="Sarabun-Bold", fontSize=18, leading=24, textColor=colors.HexColor("#1E3A5F"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle("ThH2", fontName="Sarabun-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#374151"), spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle("ThBody", fontName="Sarabun", fontSize=11, leading=16, textColor=colors.HexColor("#374151")))
    styles.add(ParagraphStyle("ThBodyCenter", fontName="Sarabun", fontSize=11, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#374151")))
    styles.add(ParagraphStyle("ThSmall", fontName="Sarabun", fontSize=9, leading=12, textColor=colors.HexColor("#9CA3AF")))
    styles.add(ParagraphStyle("ThSmallCenter", fontName="Sarabun", fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#9CA3AF")))
    styles.add(ParagraphStyle("ThAction", fontName="Sarabun", fontSize=11, leading=16, leftIndent=16, bulletIndent=0, textColor=colors.HexColor("#374151")))
    styles.add(ParagraphStyle("ThGrade", fontName="Sarabun-Bold", fontSize=36, leading=42, alignment=TA_CENTER))
    return styles


def _cover_page(story, styles, data):
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph("Business Health Assessment", styles["ThTitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("รายงานสุขภาพธุรกิจฉบับเต็ม", styles["ThSubtitle"]))
    story.append(Spacer(1, 20 * mm))

    grade = data["overall_grade"]
    grade_color = GRADE_COLORS.get(grade, colors.black)
    story.append(Paragraph(f'<font color="#{grade_color.hexval()[2:]}">{grade}</font>', styles["ThGrade"]))
    story.append(Paragraph(f'{GRADE_TH.get(grade, grade)} — คะแนนรวม {data["overall_score"]:.1f}%', styles["ThBodyCenter"]))
    story.append(Spacer(1, 15 * mm))

    biz_name = data.get("business_name") or "—"
    email = data.get("email") or "—"
    btype_th = {"restaurant": "ร้านอาหาร/คาเฟ่", "brand": "เจ้าของแบรนด์", "oem": "โรงงาน/OEM", "startup": "Startup"}
    info_data = [
        ["ชื่อธุรกิจ", biz_name],
        ["ประเภท", btype_th.get(data.get("business_type", ""), data.get("business_type", ""))],
        ["อีเมล", email],
        ["วันที่ออกรายงาน", datetime.utcnow().strftime("%d/%m/%Y")],
    ]
    info_table = Table(info_data, colWidths=[35 * mm, 80 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Sarabun-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Sarabun"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#374151")),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("โดย Northstar Corporation", styles["ThSmallCenter"]))
    story.append(PageBreak())


def _overview_page(story, styles, data):
    story.append(Paragraph("ภาพรวมสุขภาพธุรกิจ", styles["ThH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB")))
    story.append(Spacer(1, 4 * mm))

    dim_lights = data["dim_light"]
    dim_pcts = data["dim_pct"]

    table_data = [["มิติ", "สัญญาณ", "คะแนน"]]
    row_colors = []
    for d_key in ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]:
        light = dim_lights.get(d_key, "RED")
        pct = dim_pcts.get(d_key, 0)
        lc = LIGHT_COLORS[light]
        light_text = f'<font color="#{lc.hexval()[2:]}">{"●"}</font> {LIGHT_TH[light]}'
        table_data.append([DIM_NAMES[d_key], Paragraph(light_text, styles["ThBody"]), f"{pct:.0f}%"])
        row_colors.append(LIGHT_BG[light])

    t = Table(table_data, colWidths=[55 * mm, 60 * mm, 25 * mm])
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Sarabun-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Sarabun-Bold"),
        ("FONTNAME", (2, 1), (2, -1), "Sarabun"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#374151")),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#D1D5DB")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]
    for i, bg in enumerate(row_colors):
        style_cmds.append(("BACKGROUND", (0, i + 1), (-1, i + 1), bg))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    story.append(Spacer(1, 8 * mm))

    red_flags = data.get("red_flags", [])
    if red_flags:
        story.append(Paragraph("สัญญาณเตือน (Red Flags)", styles["ThH2"]))
        for flag in red_flags:
            story.append(Paragraph(f"⚠ {flag}", styles["ThBody"]))
        story.append(Spacer(1, 4 * mm))

    top_risks = data.get("top_risks", [])
    if top_risks:
        story.append(Paragraph("จุดเสี่ยงสำคัญ 2 อันดับแรก", styles["ThH2"]))
        for d in top_risks:
            story.append(Paragraph(f"• {DIM_NAMES.get(d, d)}", styles["ThBody"]))

    story.append(PageBreak())


def _dimension_pages(story, styles, data):
    narratives = data.get("narratives", {})
    dim_lights = data["dim_light"]
    dim_pcts = data["dim_pct"]
    dim_raws = data.get("dim_raw", {})

    for d_key in ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]:
        light = dim_lights.get(d_key, "RED")
        pct = dim_pcts.get(d_key, 0)
        raw = dim_raws.get(d_key, 0)
        lc = LIGHT_COLORS[light]
        narrative = narratives.get(d_key, {})

        story.append(Paragraph(f'{d_key} — {DIM_NAMES[d_key]}', styles["ThH1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=lc))
        story.append(Spacer(1, 3 * mm))

        status_text = f'<font color="#{lc.hexval()[2:]}">● {LIGHT_TH[light]}</font>  |  คะแนน {pct:.0f}% ({raw}/18)'
        story.append(Paragraph(status_text, styles["ThBody"]))
        story.append(Spacer(1, 4 * mm))

        summary = narrative.get("summary", "")
        if summary:
            story.append(Paragraph(summary, styles["ThBody"]))
            story.append(Spacer(1, 3 * mm))

        # current_state (v2) — also exposed as "detail" for backward compat
        detail = narrative.get("current_state") or narrative.get("detail", "")
        if detail:
            story.append(Paragraph("สถานการณ์ปัจจุบัน", styles["ThH2"]))
            story.append(Paragraph(detail, styles["ThBody"]))
            story.append(Spacer(1, 3 * mm))

        root_cause = narrative.get("root_cause", "")
        if root_cause:
            story.append(Paragraph("สาเหตุที่แท้จริง", styles["ThH2"]))
            story.append(Paragraph(root_cause, styles["ThBody"]))
            story.append(Spacer(1, 3 * mm))

        whats_working = narrative.get("whats_working", "")
        if whats_working:
            story.append(Paragraph("สิ่งที่ทำดีแล้ว", styles["ThH2"]))
            story.append(Paragraph(whats_working, styles["ThBody"]))
            story.append(Spacer(1, 3 * mm))

        actions = narrative.get("actions", [])
        if actions:
            story.append(Paragraph("สิ่งที่ควรทำ", styles["ThH2"]))
            for action in actions:
                story.append(Paragraph(f"✓ {action}", styles["ThAction"]))
            story.append(Spacer(1, 3 * mm))

        industry_context = narrative.get("industry_context", "")
        if industry_context:
            story.append(Paragraph("บริบทอุตสาหกรรม", styles["ThH2"]))
            story.append(Paragraph(industry_context, styles["ThBody"]))
            story.append(Spacer(1, 3 * mm))

        story.append(PageBreak())


def _cta_page(story, styles):
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph("ต้องการคำปรึกษาเชิงลึก?", styles["ThTitle"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Northstar SMEs Health Check", styles["ThH1"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "ทีมที่ปรึกษาของ Northstar พร้อมช่วยวิเคราะห์ปัญหาเชิงลึก "
        "วางแผนแก้ไข และติดตามผลอย่างเป็นระบบ",
        styles["ThBody"],
    ))
    story.append(Spacer(1, 8 * mm))

    services = [
        "วิเคราะห์ root cause ของปัญหาที่พบในแบบประเมิน",
        "วางแผนปรับปรุงระยะสั้น (Quick Wins) และระยะยาว",
        "ติดตามผลทุก 3 เดือนด้วย KPI ที่วัดได้",
        "เข้าถึงเครือข่ายผู้เชี่ยวชาญเฉพาะด้าน",
    ]
    for s in services:
        story.append(Paragraph(f"• {s}", styles["ThBody"]))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("ติดต่อเรา: contact@northstar.co.th", styles["ThBodyCenter"]))
    story.append(Paragraph("www.northstar.co.th", styles["ThBodyCenter"]))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sarabun", 8)
    canvas.setFillColor(colors.HexColor("#9CA3AF"))
    canvas.drawString(20 * mm, 10 * mm, "Business Health Assessment — Northstar Corporation")
    canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"หน้า {doc.page}")
    canvas.restoreState()


def generate_pdf(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )
    styles = _styles()
    story = []

    _cover_page(story, styles, data)
    _overview_page(story, styles, data)
    _dimension_pages(story, styles, data)
    _cta_page(story, styles)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf
