"""
pdf_report.py  v2 — AA · Agentic Auditor edition.
Editorial Business-Health-Assessment report generator (Thai).
Public API:  generate_pdf(data) -> io.BytesIO
"""

import io
import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as _canvas
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Flowable, Image,
)
from reportlab.graphics.shapes import Drawing, Wedge, Circle, String

BRAND_NAME      = os.environ.get("BHA_BRAND_NAME", "AA · Agentic-Auditor")
BRAND_MONO      = "AA"
BRAND_FULL      = "Agentic Auditor"
REPORT_RUNHEAD  = "AA · Business Health Assessment"
CONTACT_EMAIL   = os.environ.get("BHA_CONTACT_EMAIL", "agenticauditor24@gmail.com")
CONTACT_WEB     = os.environ.get("BHA_CONTACT_WEB", "www.agentic-auditor.com/bha")
EDITION_LABEL   = f"VOL. I · EDITION {datetime.utcnow().strftime('%Y.%m')}"
LOGO_PATH       = os.environ.get(
    "BHA_LOGO_PATH",
    os.path.join(os.path.dirname(__file__), "assets", "logo_aa_mark.png"),
)
# Aspect ratio (w/h) of the logo, read once so we can place it without
# distortion in both the cover masthead and the per-page header.
try:
    from reportlab.lib.utils import ImageReader as _ImageReader
    _logo_w0, _logo_h0 = _ImageReader(LOGO_PATH).getSize()
    LOGO_ASPECT = (_logo_w0 / _logo_h0) if _logo_h0 else 1.0
except Exception:
    LOGO_ASPECT = 1.0

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
pdfmetrics.registerFont(TTFont("Sarabun", os.path.join(FONTS_DIR, "Sarabun-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Sarabun-Bold", os.path.join(FONTS_DIR, "Sarabun-Bold.ttf")))
pdfmetrics.registerFontFamily("Sarabun", normal="Sarabun", bold="Sarabun-Bold")
F  = "Sarabun"
FB = "Sarabun-Bold"

# ── Thai tone-mark stacking fix ──────────────────────────────────
# ReportLab does not apply OpenType GPOS, so a tone mark following an
# upper vowel (ั ิ ี ึ ื) lands on top of the vowel. We raise such tone
# marks with setRise so they sit correctly above the vowel.
import reportlab.pdfgen.textobject as _textobj
_TH_UPPER = set("ัิีึื")
_TH_TONE = set("่้๊๋์")
_rl_textOut = getattr(_textobj.PDFTextObject, "_rl_orig_textOut", _textobj.PDFTextObject._textOut)
_textobj.PDFTextObject._rl_orig_textOut = _rl_textOut

def _thai_textOut(self, text, TStar=0):
    if not any(c in _TH_TONE for c in text):
        return _rl_textOut(self, text, TStar)
    fs = getattr(self, "_fontsize", 10) or 10
    rise = fs * 0.15
    base = getattr(self, "_rise", 0) or 0
    n = len(text); buf = ""; i = 0
    while i < n:
        ch = text[i]; last = (i == n - 1)
        if ch in _TH_TONE and i > 0 and text[i - 1] in _TH_UPPER:
            if buf:
                _rl_textOut(self, buf, 0); buf = ""
            self.setRise(base + rise); _rl_textOut(self, ch, 0); self.setRise(base)
            if last and TStar:
                self._code.append("T*")
        else:
            buf += ch
            if last:
                _rl_textOut(self, buf, TStar); buf = ""
        i += 1
    if buf:
        _rl_textOut(self, buf, 0)

_textobj.PDFTextObject._textOut = _thai_textOut
# ─────────────────────────────────────────────────────────────────

INK      = HexColor("#1B2A4A")
INK_SOFT = HexColor("#3C4A63")
GOLD     = HexColor("#B08338")
GOLD_DK  = HexColor("#8A6526")
CREAM    = HexColor("#FBF8F2")
LINE     = HexColor("#E4DED2")
GREY     = HexColor("#6B7280")
GREY_LT  = HexColor("#9CA3AF")
BODY     = HexColor("#374151")

LIGHT_COLORS = {"RED": HexColor("#D64545"), "YELLOW": HexColor("#C98A1B"), "GREEN": HexColor("#2E8B57")}
LIGHT_TRACK  = HexColor("#ECE7DC")
LIGHT_BG     = {"RED": HexColor("#FBEAEA"), "YELLOW": HexColor("#FBF1DC"), "GREEN": HexColor("#E6F1EA")}
LIGHT_TH     = {"RED": "แดง · เสี่ยงสูง", "YELLOW": "เหลือง · ควรปรับปรุง", "GREEN": "เขียว · ดี"}
PHASE_COLORS = [HexColor("#B23B3B"), GOLD_DK, HexColor("#256B45")]

GRADE_COLORS = {"CRITICAL": HexColor("#D64545"), "WATCH": HexColor("#C98A1B"),
                "HEALTHY": HexColor("#2E8B57"), "STRONG": HexColor("#1E7A47")}
GRADE_TH = {"CRITICAL": "วิกฤต", "WATCH": "ต้องระวัง", "HEALTHY": "สุขภาพดี", "STRONG": "แข็งแกร่ง"}

DIM_NAMES = {
    "D1": "การเงินและสภาพคล่อง", "D2": "ลูกค้าและการตลาด",
    "D3": "ระบบงานและกระบวนการ", "D4": "ทีมและทรัพยากรมนุษย์",
    "D5": "ซัพพลายเชนและต้นทุน", "D6": "เทคโนโลยีและนวัตกรรม",
    "D7": "ธรรมาภิบาลและความเสี่ยง",
}
DIM_EN = {
    "D1": "Finance & Liquidity", "D2": "Customer & Marketing",
    "D3": "Operations & Process", "D4": "Team & Human Resources",
    "D5": "Supply Chain & Cost", "D6": "Technology & Innovation",
    "D7": "Governance & Risk",
}
DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
BTYPE_TH = {"restaurant": "ร้านอาหาร / คาเฟ่", "brand": "เจ้าของแบรนด์", "oem": "โรงงาน / OEM",
            "startup": "Startup", "ecommerce": "E-commerce", "retail": "ค้าปลีก",
            "service": "ธุรกิจบริการ", "health_beauty": "สุขภาพ & ความงาม"}

PAGE_W, PAGE_H = A4
LM = RM = 18 * mm
TM = 22 * mm
BM = 18 * mm
_S = None


def _hex(c):
    return c.hexval()[2:]


def _split_prefix(action):
    m = re.match(r"\s*\[([^\]]+)\]\s*(.*)", action or "")
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", (action or "").strip()


def _phase_style(prefix):
    p = prefix or ""
    if p.startswith("ทันที") or p.startswith("สัปดาห์"):
        return LIGHT_BG["RED"], HexColor("#B23B3B")
    if p.startswith("เดือน 1") or p == "เดือน":
        return LIGHT_BG["YELLOW"], GOLD_DK
    return LIGHT_BG["GREEN"], HexColor("#256B45")


def _count_lights(dl):
    r = sum(1 for v in dl.values() if v == "RED")
    y = sum(1 for v in dl.values() if v == "YELLOW")
    g = sum(1 for v in dl.values() if v == "GREEN")
    return r, y, g


def _first_quick_wins(data, n=1):
    rm = data.get("roadmap") or {}
    for ph in rm.get("phases", []):
        if ph["items"]:
            return ph["items"][:n]
    return []


def _priority_actions(data, n=3):
    """One earliest-phase action per dimension, in the report's priority order
    (most-urgent dim first) so the callout matches the stated top risks."""
    rm = data.get("roadmap") or {}
    order = rm.get("priority_dims") or []
    by_dim = {}
    for ph in rm.get("phases", []):
        for it in ph["items"]:
            by_dim.setdefault(it["dim"], it)
    out = [by_dim[d] for d in order if d in by_dim]
    if len(out) < n:
        seen = {id(x) for x in out}
        for ph in rm.get("phases", []):
            for it in ph["items"]:
                if id(it) not in seen:
                    out.append(it); seen.add(id(it))
    return out[:n]


_VERDICT = {
    "CRITICAL": "อยู่ในภาวะที่ต้องเร่งแก้ไข มีความเสี่ยงต่อความอยู่รอดของธุรกิจหากไม่ลงมือ",
    "WATCH": "พอเดินได้ แต่มีจุดเปราะบางที่ควรจัดการให้เรียบร้อยก่อนขยายธุรกิจ",
    "HEALTHY": "อยู่ในเกณฑ์ดี มีพื้นฐานมั่นคงและพร้อมต่อยอดสู่การเติบโต",
    "STRONG": "แข็งแกร่ง พร้อมเติบโตและขยายตัวได้อย่างมั่นใจ",
}


def _exec_summary_text(data):
    grade = data["overall_grade"]; score = data["overall_score"]
    gth = GRADE_TH.get(grade, grade)
    r, y, g = _count_lights(data["dim_light"])
    tops = data.get("top_risks", [])
    top_names = " และ ".join(DIM_NAMES.get(d, d) for d in tops) if tops else "—"
    qw = _first_quick_wins(data, 1)
    s1 = (f'<font name="{FB}" color="#{_hex(INK)}">ภาพรวม:</font> ธุรกิจอยู่ในระดับ '
          f'<font name="{FB}" color="#{_hex(GRADE_COLORS.get(grade, INK))}">{grade} · {gth} ({score:.1f}%)</font> '
          f'— {_VERDICT.get(grade, "")}')
    s2 = (f'<font name="{FB}" color="#{_hex(INK)}">จุดที่ต้องโฟกัส:</font> จาก 7 มิติ พบระดับเสี่ยงสูง {r} มิติ '
          f'และควรปรับปรุง {y} มิติ โดยควรจัดการก่อนคือ {top_names}')
    if qw:
        s3 = (f'<font name="{FB}" color="#{_hex(INK)}">ก้าวแรก:</font> เริ่มจาก “{qw[0]["text"]}” '
              f'(ด้าน{qw[0]["dim_name"]}) ภายในสัปดาห์นี้ แล้วทำตามแผนปฏิบัติ 90 วันในรายงาน')
    else:
        s3 = (f'<font name="{FB}" color="#{_hex(INK)}">ก้าวแรก:</font> รักษามาตรฐานที่ดีไว้ '
              f'และทำตามแผนต่อยอดในรายงานเพื่อยกระดับสู่ระดับแข็งแกร่ง')
    return [s1, s2, s3]


def _conclusion_text(data):
    grade = data["overall_grade"]; score = data["overall_score"]
    r, y, g = _count_lights(data["dim_light"])
    tops = data.get("top_risks", [])
    top_names = " และ ".join(DIM_NAMES.get(d, d) for d in tops) if tops else "จุดที่ระบุในรายงาน"
    gth = GRADE_TH.get(grade, grade)
    if grade == "CRITICAL":
        p1 = (f"ภาพรวมสะท้อนว่าธุรกิจยังอยู่ในภาวะเปราะบาง (คะแนนรวม {score:.1f}% · {gth}) "
              f"มีมิติเสี่ยงสูงถึง {r} ด้าน จำเป็นต้องเร่งแก้ระบบพื้นฐาน — โดยเฉพาะการเงิน การควบคุม และความต่อเนื่องของการดำเนินงาน "
              f"ให้มั่นคงก่อนคิดเรื่องการเติบโต")
    elif grade == "WATCH":
        p1 = (f"ธุรกิจยังเดินต่อได้ (คะแนนรวม {score:.1f}% · {gth}) แต่มีความเปราะบางเชิงระบบ "
              f"({r} ด้านเสี่ยงสูง, {y} ด้านควรปรับปรุง) ที่เริ่มกระทบความสามารถในการเติบโตและการควบคุมความเสี่ยง "
              f"จึงต้องจัดลำดับความสำคัญและกำหนดผู้รับผิดชอบให้ชัด")
    else:
        p1 = (f"ภาพรวมอยู่ในเกณฑ์ควบคุมได้ดี (คะแนนรวม {score:.1f}% · {gth}) มีมิติที่แข็งแรง {g} ด้าน "
              f"และยังมีบางจุดที่ควรปรับเพื่อเพิ่มความพร้อมต่อการเติบโต")
    if tops:
        p2 = (f"ลำดับความสำคัญเชิงกลยุทธ์คือการจัดการ {top_names} ก่อน เพราะเป็นมิติที่ส่งผลต่อ "
              f"เสถียรภาพและความสามารถในการเติบโตมากที่สุด การลงมือในจุดนี้จะให้ผลตอบแทนต่อความพยายามสูงสุด")
    else:
        p2 = ("ไม่มีมิติที่อยู่ในระดับเสี่ยง — ลำดับความสำคัญจึงเป็นการรักษามาตรฐานที่ดีไว้ "
              "และต่อยอดมิติที่ยังมีช่องว่างพัฒนา เพื่อเตรียมความพร้อมสำหรับการเติบโตและการขยายธุรกิจ")
    p3 = ("ทุกข้อเสนอแนะในรายงานมีผู้รับผิดชอบและ KPI กำกับ หากดำเนินการตามแผน 90 วันและติดตามผลตามรอบ "
          "คาดว่าจะเห็นสัญญาณการปรับตัวที่ดีขึ้นภายใน 1 ไตรมาส")
    return [p1, p2, p3]




def _styles():
    s = getSampleStyleSheet()

    def add(name, **kw):
        s.add(ParagraphStyle(name, **kw))

    add("Kicker", fontName=FB, fontSize=9, leading=12, textColor=GOLD_DK, spaceAfter=2)
    add("H1", fontName=FB, fontSize=22, leading=26, textColor=INK, spaceAfter=2)
    add("H2", fontName=FB, fontSize=13, leading=17, textColor=INK, spaceBefore=6, spaceAfter=3)
    add("ColHead", fontName=FB, fontSize=10, leading=13, textColor=GOLD_DK, spaceAfter=2)
    add("Body", fontName=F, fontSize=10.5, leading=15.5, textColor=BODY)
    add("BodyC", fontName=F, fontSize=10.5, leading=15.5, textColor=BODY, alignment=TA_CENTER)
    add("Lead", fontName=F, fontSize=12, leading=17, textColor=INK_SOFT)
    add("Small", fontName=F, fontSize=8.5, leading=11.5, textColor=GREY)
    add("SmallC", fontName=F, fontSize=8.5, leading=11.5, textColor=GREY, alignment=TA_CENTER)
    add("RecNum", fontName=FB, fontSize=12, leading=14, textColor=GOLD, alignment=TA_CENTER)
    add("RecText", fontName=F, fontSize=10, leading=14, textColor=BODY)
    add("RoadText", fontName=F, fontSize=9.5, leading=12.5, textColor=BODY)
    add("Badge", fontName=FB, fontSize=8, leading=10, alignment=TA_CENTER)
    add("KpiHdr", fontName=FB, fontSize=8.5, leading=11, textColor=white)
    add("KpiCell", fontName=F, fontSize=8.5, leading=11.5, textColor=BODY)
    add("KpiName", fontName=FB, fontSize=8.5, leading=11.5, textColor=INK)
    add("CoverScore", fontName=FB, fontSize=64, leading=64, textColor=INK)
    add("CoverTitle", fontName=FB, fontSize=34, leading=40, textColor=INK)
    return s


def _donut(pct, ring_color, size=32 * mm, center_big=None, center_small=None,
           big_size=15, small_size=8):
    d = Drawing(size, size)
    cx = cy = size / 2.0
    r = size / 2.0
    pct = max(0.0, min(100.0, float(pct)))
    d.add(Wedge(cx, cy, r, 0, 360, fillColor=LIGHT_TRACK, strokeColor=None))
    if pct > 0:
        sweep = 360.0 * pct / 100.0
        d.add(Wedge(cx, cy, r, 90 - sweep, 90, fillColor=ring_color, strokeColor=None))
    d.add(Circle(cx, cy, r * 0.66, fillColor=white, strokeColor=None))
    if center_big is not None:
        d.add(String(cx, cy - big_size * 0.18, str(center_big), fontName=FB,
                     fontSize=big_size, fillColor=ring_color, textAnchor="middle"))
    if center_small is not None:
        d.add(String(cx, cy - big_size * 0.95, str(center_small), fontName=F,
                     fontSize=small_size, fillColor=GREY, textAnchor="middle"))
    return d


class HBar(Flowable):
    def __init__(self, pct, color, width, height=5):
        super().__init__()
        self.pct = max(0, min(100, pct))
        self.color = color
        self.width = width
        self.height = height

    def wrap(self, *a):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(LIGHT_TRACK)
        c.roundRect(0, 0, self.width, self.height, self.height / 2, fill=1, stroke=0)
        w = self.width * self.pct / 100.0
        if w > 0:
            c.setFillColor(self.color)
            c.roundRect(0, 0, max(w, self.height), self.height, self.height / 2, fill=1, stroke=0)


def _badge(prefix):
    bg, fg = _phase_style(prefix)
    t = Table([[Paragraph(f'<font color="#{_hex(fg)}">{prefix}</font>', _S["Badge"])]],
              colWidths=[26 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [5, 5, 5, 5]),
    ]))
    return t


class NumberedCanvas(_canvas.Canvas):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for st in self._saved:
            self.__dict__.update(st)
            self._furniture(total)
            super().showPage()
        super().save()

    def _furniture(self, total):
        pn = self._pageNumber
        self.saveState()
        if pn > 1:
            # Gold shield mark + brand name rendered as dark text (so it reads
            # on the white page); page number on the right.
            _hx = LM
            if os.path.exists(LOGO_PATH):
                try:
                    _lsz = 6 * mm
                    self.drawImage(LOGO_PATH, LM, PAGE_H - 15.0 * mm,
                                   width=_lsz, height=_lsz, mask="auto",
                                   preserveAspectRatio=True)
                    _hx = LM + _lsz + 2.5 * mm
                except Exception:
                    _hx = LM
            _by = PAGE_H - 12.8 * mm
            self.setFont(FB, 8.5)
            self.setFillColor(INK)
            self.drawString(_hx, _by, "AA")
            self.setFont(F, 8.5)
            self.setFillColor(GREY)
            self.drawString(_hx + self.stringWidth("AA", FB, 8.5), _by, "  |  Agentic-Auditor")
            self.setFont(F, 8)
            self.setFillColor(GREY_LT)
            self.drawRightString(PAGE_W - RM, PAGE_H - 13 * mm, f"{pn:02d} / {total}")
            self.setStrokeColor(LINE)
            self.setLineWidth(0.5)
            self.line(LM, PAGE_H - 15 * mm, PAGE_W - RM, PAGE_H - 15 * mm)
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(LM, BM - 4 * mm, PAGE_W - RM, BM - 4 * mm)
        self.setFont(F, 7.5)
        self.setFillColor(GREY_LT)
        self.drawString(LM, BM - 8 * mm, BRAND_NAME)
        self.drawCentredString(PAGE_W / 2, BM - 8 * mm, f"{pn:02d}")
        self.drawRightString(PAGE_W - RM, BM - 8 * mm, "Business Health Assessment")
        self.restoreState()


def _logo_mark(size):
    """Brand mark: real logo image if assets/logo_aa.png exists, else a navy AA tile."""
    if os.path.exists(LOGO_PATH):
        return Image(LOGO_PATH, width=size, height=size)
    t = Table([[Paragraph(BRAND_MONO, ParagraphStyle(
        "m", fontName=FB, fontSize=15, textColor=white, alignment=TA_CENTER))]],
        colWidths=[size], rowHeights=[size])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ROUNDEDCORNERS", [3, 3, 3, 3])]))
    return t


def _cover(story, data):
    grade = data["overall_grade"]
    gcol = GRADE_COLORS.get(grade, INK)
    score = data["overall_score"]
    cw = PAGE_W - LM - RM
    # Cover masthead: gold shield + brand name rendered as dark text (reads on
    # white), tagline beneath the name, edition label on the right.
    mono = _logo_mark(13 * mm)
    wm = Table([[mono,
                 Paragraph(f'<font name="{FB}" size="13" color="#{_hex(INK)}">AA</font>'
                           f'<font name="{F}" size="13" color="#{_hex(GREY)}">  |  Agentic-Auditor</font><br/>'
                           f'<font name="{F}" size="7.5" color="#{_hex(GREY)}">AI-ASSISTED RISK &amp; HEALTH DIAGNOSTICS</font>',
                           _S["Body"]),
                 Paragraph(f'<font color="#{_hex(GREY_LT)}">{EDITION_LABEL}</font>',
                           ParagraphStyle("e", fontName=F, fontSize=8.5, alignment=TA_RIGHT))]],
                colWidths=[16 * mm, 96 * mm, cw - 112 * mm])
    wm.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (1, 0), (1, 0), 10)]))
    story.append(wm)
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=INK))
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("BUSINESS HEALTH ASSESSMENT · รายงานฉบับเต็ม", _S["Kicker"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("รายงานสุขภาพ<br/>ธุรกิจของคุณ", _S["CoverTitle"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("วินิจฉัยด้วยตัวเลข — และอธิบายด้วยภาษาที่ลงมือต่อได้จริง", _S["Lead"]))
    story.append(Spacer(1, 18 * mm))
    left = [
        Paragraph("OVERALL HEALTH SCORE", _S["Kicker"]),
        Spacer(1, 1 * mm),
        Paragraph(f'<font color="#{_hex(gcol)}">{score:.1f}%</font>', _S["CoverScore"]),
        Spacer(1, 1 * mm),
        Paragraph(f'<font name="{FB}" size="13" color="#{_hex(gcol)}">{grade} — {GRADE_TH.get(grade, grade)}</font>', _S["Body"]),
    ]
    info_rows = [
        ["ชื่อธุรกิจ", data.get("business_name") or "—"],
        ["ประเภทธุรกิจ", BTYPE_TH.get(data.get("business_type", ""), data.get("business_type") or "—")],
        ["อีเมล", data.get("email") or "—"],
        ["วันที่ออกรายงาน", datetime.utcnow().strftime("%d / %m / %Y")],
        ["จัดทำโดย", BRAND_NAME],
    ]
    info = Table([[Paragraph(k, _S["Small"]), Paragraph(f'<b>{v}</b>', _S["Body"])] for k, v in info_rows],
                 colWidths=[30 * mm, 52 * mm])
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
    ]))
    block = Table([[left, info]], colWidths=[cw * 0.46, cw * 0.54])
    block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(block)
    story.append(Spacer(1, 22 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("CONFIDENTIAL · จัดทำเพื่อผู้รับที่ระบุชื่อเท่านั้น", _S["SmallC"]))
    story.append(PageBreak())


def _exec_snapshot(story, data):
    dl, dp = data["dim_light"], data["dim_pct"]
    grade = data["overall_grade"]
    gcol = GRADE_COLORS.get(grade, INK)
    cw = PAGE_W - LM - RM
    story.append(Paragraph("EXECUTIVE SUMMARY", _S["Kicker"]))
    story.append(Paragraph("ภาพรวมสุขภาพธุรกิจ", _S["H1"]))
    story.append(Paragraph("เจ็ดมิติ · หนึ่งคะแนนรวม · สามสัญญาณสี — แดง เหลือง เขียว", _S["Small"]))
    story.append(Spacer(1, 5 * mm))

    # SCQA executive narrative (answer-first)
    summ = _exec_summary_text(data)
    sbox = Table([[Paragraph(p, _S["Body"])] for p in summ], colWidths=[PAGE_W - LM - RM])
    sbox.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM),
                              ("LINEBEFORE", (0, 0), (0, -1), 2, GOLD),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                              ("TOPPADDING", (0, 0), (0, 0), 8), ("BOTTOMPADDING", (0, -1), (0, -1), 8),
                              ("TOPPADDING", (0, 1), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -2), 2)]))
    story.append(sbox)
    story.append(Spacer(1, 6 * mm))
    barw = 36 * mm
    rows = []
    for i, d in enumerate(DIMS, 1):
        col = LIGHT_COLORS[dl.get(d, "RED")]
        name = Paragraph(f'<font name="{FB}" color="#{_hex(INK)}">{DIM_NAMES[d]}</font><br/>'
                         f'<font name="{F}" size="8" color="#{_hex(GREY_LT)}">{DIM_EN[d]}</font>', _S["Body"])
        num = Paragraph(f'<font color="#{_hex(GOLD)}">{i:02d}</font>', _S["RecNum"])
        bar = HBar(dp.get(d, 0), col, barw)
        pctp = Paragraph(f'<font name="{FB}" color="#{_hex(col)}">{dp.get(d, 0):.0f}%</font>', _S["Body"])
        rows.append([num, name, bar, pctp])
    dimtbl = Table(rows, colWidths=[8 * mm, 52 * mm, barw + 2 * mm, 14 * mm])
    sty = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
           ("ALIGN", (3, 0), (3, -1), "RIGHT"),
           ("LEFTPADDING", (0, 0), (0, -1), 1), ("RIGHTPADDING", (0, 0), (0, -1), 1)]
    for i in range(len(rows)):
        sty.append(("LINEBELOW", (0, i), (-1, i), 0.5, LINE))
    dimtbl.setStyle(TableStyle(sty))
    donut = _donut(data["overall_score"], gcol, size=46 * mm,
                   center_big=f"{data['overall_score']:.1f}%",
                   center_small=GRADE_TH.get(grade, grade), big_size=18, small_size=9)
    right = Table([[donut],
                   [Paragraph(f'<font name="{FB}" color="#{_hex(gcol)}">{grade}</font>'
                              f'<br/><font size="8" color="#{_hex(GREY)}">OVERALL · คะแนนรวม</font>', _S["BodyC"])]],
                  colWidths=[cw * 0.34 - 4 * mm])
    right.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 1), (0, 1), 4)]))
    snap = Table([[dimtbl, right]], colWidths=[cw * 0.66, cw * 0.34])
    snap.setStyle(TableStyle([("VALIGN", (0, 0), (0, 0), "TOP"), ("VALIGN", (1, 0), (1, 0), "MIDDLE")]))
    story.append(snap)
    story.append(Spacer(1, 6 * mm))

    # Hard-floor alerts (red flags) — controls so critical that the dimension cannot be green
    rfs = data.get("red_flags") or []
    if rfs:
        # Map a red-flag entry to a readable Thai line. data["red_flags"] holds
        # dimension codes ("D1".."D7") from build_report_model; we render the
        # dimension name + the specific hard-floor reason. Falls back to the raw
        # value if no known code is present (backward compatible).
        from narratives import HARD_FLOOR_LABELS as _HF  # single source of truth

        def _fmt_rf(flag):
            code = next((c for c in _HF if c in str(flag)), None)
            if code:
                name, reason = _HF[code]
                return f'<font name="{FB}" color="#{_hex(INK)}">{name}:</font>  {reason}'
            return str(flag)

        rhead = Paragraph(f'<font name="{FB}" color="#{_hex(LIGHT_COLORS["RED"])}">สัญญาณอันตราย (Hard-floor) — ต้องแก้ทันที</font>',
                          _S["ColHead"])
        ritems = [[Paragraph(f'<font color="#{_hex(LIGHT_COLORS["RED"])}">●</font>', _S["Body"]),
                   Paragraph(_fmt_rf(flag), _S["Body"])] for flag in rfs]
        rtbl = Table(ritems, colWidths=[6 * mm, (PAGE_W - LM - RM) - 6 * mm - 20])
        rtbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 2),
                                  ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        rbox = Table([[rhead], [rtbl]], colWidths=[PAGE_W - LM - RM])
        rbox.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG["RED"]),
                                  ("LINEBEFORE", (0, 0), (0, -1), 2.5, LIGHT_COLORS["RED"]),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                  ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        story.append(rbox)
        story.append(Spacer(1, 6 * mm))

    firsts = _priority_actions(data, 3)
    if firsts:
        _norisk = not data.get("top_risks")
        head = Paragraph("แนะนำให้ต่อยอด 3 เรื่องนี้" if _norisk
                         else "เริ่มทำ 3 อย่างนี้ก่อน — ภายในสัปดาห์นี้", _S["ColHead"])
        items = []
        for i, it in enumerate(firsts, 1):
            items.append([Paragraph(f'<font color="#{_hex(GOLD)}">{i:02d}</font>', _S["RecNum"]),
                          Paragraph(f'<font name="{FB}" color="#{_hex(INK)}">{it["dim_name"]}</font> — {it["text"]}',
                                    _S["RecText"])])
        itbl = Table(items, colWidths=[8 * mm, cw - 8 * mm - 20])
        itbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (0, -1), 1), ("RIGHTPADDING", (0, 0), (0, -1), 1),
                                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        box = Table([[head], [itbl]], colWidths=[cw])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CREAM),
            ("BOX", (0, 0), (-1, -1), 0.5, GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [5, 5, 5, 5]),
        ]))
        story.append(box)
    story.append(PageBreak())


def _dimension(story, data, d):
    dl, dp, dr = data["dim_light"], data["dim_pct"], data.get("dim_raw", {})
    light = dl.get(d, "RED")
    col = LIGHT_COLORS[light]
    n = data.get("narratives", {}).get(d, {})
    bench = (data.get("benchmark") or {}).get(d, "")
    cw = PAGE_W - LM - RM
    strong = light == "GREEN"
    kicker = f"มิติที่ {d[1:].zfill(2)} · " + ("ด้านที่มีความแข็งแกร่ง" if strong else "ด้านที่ควรพัฒนา")
    story.append(Paragraph(kicker, _S["Kicker"]))
    title_cell = [Paragraph(DIM_NAMES[d], _S["H1"]),
                  Paragraph(f'<font name="{FB}" color="#{_hex(col)}">{LIGHT_TH[light]}</font>'
                            f'  <font size="9" color="#{_hex(GREY_LT)}">{DIM_EN[d]}</font>', _S["Body"])]
    donut = _donut(dp.get(d, 0), col, size=30 * mm,
                   center_big=f"{dp.get(d, 0):.0f}%", center_small=f"{dr.get(d, 0)} / 18",
                   big_size=14, small_size=7.5)
    head = Table([[title_cell, donut]], colWidths=[cw - 34 * mm, 34 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (0, 0), "MIDDLE"), ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                              ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.append(head)
    story.append(HRFlowable(width="100%", thickness=1.2, color=col, spaceBefore=4, spaceAfter=6))
    if n.get("summary"):
        story.append(Paragraph(n["summary"], _S["Lead"]))
        story.append(Spacer(1, 3 * mm))
    # Fact base — answer-derived facts (never hallucinated)
    if n.get("fact"):
        fact_tbl = Table([[Paragraph(
            f'<font name="{FB}" color="#{_hex(INK)}">ข้อเท็จจริงจากการประเมิน</font>  '
            f'<font color="#{_hex(INK_SOFT)}">{n["fact"]}</font>', _S["Small"])]], colWidths=[cw])
        fact_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F2F4F7")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, INK)]))
        story.append(fact_tbl)
        story.append(Spacer(1, 3 * mm))
    detail = n.get("current_state") or n.get("detail")
    left_html = (f'<font name="{FB}" color="#{_hex(INK)}">สถานการณ์ปัจจุบัน</font><br/>{detail}' if detail else "")
    right_html = ""
    if n.get("root_cause"):
        right_html = f'<font name="{FB}" color="#{_hex(INK)}">สาเหตุที่แท้จริง</font><br/>{n["root_cause"]}'
    elif n.get("whats_working"):
        right_html = f'<font name="{FB}" color="#{_hex(INK)}">สิ่งที่ทำดีแล้ว</font><br/>{n["whats_working"]}'
    if left_html or right_html:
        two = Table([[Paragraph(left_html, _S["Body"]), Paragraph(right_html, _S["Body"])]],
                    colWidths=[cw / 2 - 4 * mm, cw / 2 - 4 * mm])
        two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("RIGHTPADDING", (0, 0), (0, 0), 8), ("LEFTPADDING", (1, 0), (1, 0), 8)]))
        story.append(two)
        story.append(Spacer(1, 3 * mm))
    if n.get("root_cause") and n.get("whats_working"):
        story.append(Paragraph(f'<font name="{FB}" color="#{_hex(INK)}">สิ่งที่ทำดีแล้ว</font>  {n["whats_working"]}', _S["Body"]))
        story.append(Spacer(1, 2 * mm))
    # Principle & benefit  +  Consequence of inaction
    pb   = n.get("principle_benefit")
    cons = n.get("consequence")
    cons_label = "โอกาสที่จะเสียไปหากไม่ต่อยอด" if strong else "ผลกระทบหากไม่ปรับปรุง"
    cons_col   = LIGHT_COLORS["GREEN"] if strong else LIGHT_COLORS[light]
    cons_bg    = LIGHT_BG["GREEN"] if strong else LIGHT_BG[light]
    if pb and cons:
        lcell = Paragraph(f'<font name="{FB}" color="#{_hex(GOLD_DK)}">ทำไมเรื่องนี้สำคัญ</font><br/>{pb}', _S["Small"])
        rcell = Paragraph(f'<font name="{FB}" color="#{_hex(cons_col)}">{cons_label}</font><br/>{cons}', _S["Small"])
        strip = Table([[lcell, Paragraph("", _S["Small"]), rcell]],
                      colWidths=[cw / 2 - 3 * mm, 6 * mm, cw / 2 - 3 * mm])
        strip.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, 0), CREAM), ("BACKGROUND", (2, 0), (2, 0), cons_bg),
            ("LEFTPADDING", (0, 0), (0, 0), 9), ("RIGHTPADDING", (0, 0), (0, 0), 9),
            ("LEFTPADDING", (2, 0), (2, 0), 9), ("RIGHTPADDING", (2, 0), (2, 0), 9),
            ("LEFTPADDING", (1, 0), (1, 0), 0), ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBEFORE", (0, 0), (0, 0), 2.5, GOLD), ("LINEBEFORE", (2, 0), (2, 0), 2.5, cons_col)]))
        story.append(strip)
        story.append(Spacer(1, 4 * mm))
    elif pb or cons:
        if cons:
            box_html = f'<font name="{FB}" color="#{_hex(cons_col)}">{cons_label}</font>  {cons}'
            box_bg, box_line = cons_bg, cons_col
        else:
            box_html = f'<font name="{FB}" color="#{_hex(GOLD_DK)}">ทำไมเรื่องนี้สำคัญ</font>  {pb}'
            box_bg, box_line = CREAM, GOLD
        b = Table([[Paragraph(box_html, _S["Small"])]], colWidths=[cw])
        b.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), box_bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, box_line)]))
        story.append(b)
        story.append(Spacer(1, 4 * mm))
    if bench:
        bt = Table([[Paragraph(f'<font name="{FB}" color="#{_hex(GOLD_DK)}">เทียบกับธุรกิจทั่วไป</font>  '
                               f'<font color="#{_hex(INK_SOFT)}">{bench}</font>', _S["Body"])]], colWidths=[cw])
        bt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM),
                                ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                ("LINEBEFORE", (0, 0), (0, -1), 2, GOLD)]))
        story.append(bt)
        story.append(Spacer(1, 4 * mm))
    actions = n.get("actions", [])
    if actions:
        story.append(Paragraph("สิ่งที่ควรทำ · Recommendations", _S["ColHead"]))
        rec_rows = []
        for i, a in enumerate(actions, 1):
            prefix, text = _split_prefix(a)
            rec_rows.append([Paragraph(f"{i:02d}", _S["RecNum"]),
                             Paragraph(text, _S["RecText"]),
                             _badge(prefix) if prefix else Paragraph("", _S["RecText"])])
        rt = Table(rec_rows, colWidths=[9 * mm, cw - 9 * mm - 30 * mm, 30 * mm])
        rsty = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (0, -1), 1), ("RIGHTPADDING", (0, 0), (0, -1), 1),
                ("ALIGN", (2, 0), (2, -1), "RIGHT")]
        for i in range(len(rec_rows)):
            rsty.append(("LINEBELOW", (0, i), (-1, i), 0.5, LINE))
        rt.setStyle(TableStyle(rsty))
        story.append(rt)
    story.append(PageBreak())


def _roadmap(story, data):
    rm = data.get("roadmap") or {}
    cw = PAGE_W - LM - RM
    story.append(Paragraph("ROADMAP", _S["Kicker"]))
    story.append(Paragraph(rm.get("title", "แผนปฏิบัติ 90 วัน"), _S["H1"]))
    story.append(Paragraph(rm.get("subtitle", ""), _S["Small"]))
    if data.get("overall_grade") == "CRITICAL":
        story.append(Paragraph(f'<font color="#{_hex(LIGHT_COLORS["RED"])}">ในภาวะวิกฤต ให้ทำกลุ่ม Must-do ให้ครบก่อน '
                               f'แล้วค่อยขยับไป Should-do และ Later</font>', _S["Small"]))
    story.append(Spacer(1, 2 * mm))
    chips = rm.get("priority_dims", [])
    if chips:
        cells = []
        for d in chips:
            col = LIGHT_COLORS[data["dim_light"].get(d, "RED")]
            cells.append(Paragraph(f'<font name="{FB}" color="#{_hex(col)}">● </font>'
                                   f'<font color="#{_hex(INK)}">{DIM_NAMES[d]}</font>', _S["Small"]))
        chiptbl = Table([cells], colWidths=[cw / len(cells)] * len(cells))
        chiptbl.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(chiptbl)
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=6))
    for pi, ph in enumerate(rm.get("phases", [])):
        items = ph["items"]
        if not items:
            continue
        tagcol = PHASE_COLORS[pi] if pi < len(PHASE_COLORS) else GOLD_DK
        _prio = ["Must-do", "Should-do", "Later"][pi] if pi < 3 else ""
        ph_head = Table([[Paragraph(f'<font name="{FB}" color="#FFFFFF">{ph["label"]}</font>'
                                    f'  <font size="9" color="#FFFFFF">{ph["tag"]}</font>'
                                    f'  <font size="9" color="#FFFFFF">· {_prio}</font>', _S["H2"])]],
                        colWidths=[cw])
        ph_head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), tagcol),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 10),
                                     ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                     ("ROUNDEDCORNERS", [4, 4, 4, 4])]))
        # single-column chronological checklist; each item tagged with its dimension
        def _pill(it):
            lt = data["dim_light"].get(it["dim"], "RED")
            col = LIGHT_COLORS[lt]; bg = LIGHT_BG[lt]
            t = Table([[Paragraph(f'<font color="#{_hex(col)}">\u25cf {it["dim_name"]}</font>', _S["Badge"])]],
                      colWidths=[26 * mm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                   ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
            return t

        rows = [[_pill(it), Paragraph(it["text"], _S["RoadText"])] for it in items]

        def _rowstyle(nrows):
            st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                  ("LEFTPADDING", (0, 0), (0, -1), 0), ("LEFTPADDING", (1, 0), (1, -1), 8)]
            for ri in range(nrows):
                st.append(("LINEBELOW", (0, ri), (-1, ri), 0.4, LINE))
            return TableStyle(st)

        colw = [28 * mm, cw - 28 * mm]
        first_tbl = Table(rows[:1], colWidths=colw); first_tbl.setStyle(_rowstyle(1))
        story.append(KeepTogether([ph_head, Spacer(1, 2 * mm), first_tbl]))
        if len(rows) > 1:
            rest_tbl = Table(rows[1:], colWidths=colw); rest_tbl.setStyle(_rowstyle(len(rows) - 1))
            story.append(rest_tbl)
        story.append(Spacer(1, 2 * mm))
    story.append(PageBreak())


def _kpi_pages(story, data):
    kpi = data.get("kpi_table") or []
    if not kpi:
        return
    cw = PAGE_W - LM - RM
    per_page = 4
    pages = [kpi[i:i + per_page] for i in range(0, len(kpi), per_page)]
    nparts = len(pages)
    for pidx, groups in enumerate(pages, 1):
        story.append(Paragraph(f"CONTROL SYSTEM · PART {pidx} / {nparts}", _S["Kicker"]))
        story.append(Paragraph("ระบบควบคุม & ตัวชี้วัด รายมิติ", _S["H1"]))
        story.append(Paragraph("มิติที่ต้องติดตามใกล้ชิดก่อน (แดง/เหลือง)" if pidx == 1 else "มิติที่เหลือ", _S["Small"]))
        story.append(Spacer(1, 4 * mm))
        for g in groups:
            col = LIGHT_COLORS[g["light"]]
            _sd = g.get("start_date", "")
            _sl = g.get("start_label", "")
            _start_line = (f'<br/><font name="{F}" size="8.5" color="#{_hex(GOLD_DK)}">'
                           f'เริ่มติดตาม: {_sd} · {_sl}</font>') if _sd else ""
            gh = Paragraph(f'<font name="{FB}" color="#{_hex(col)}">●</font>  '
                           f'<font name="{FB}" color="#{_hex(INK)}">{g["dim_name"]}</font>'
                           f'<font name="{F}" size="9" color="#{_hex(GREY)}">    ผู้รับผิดชอบ (แนะนำ): {g.get("owner","เจ้าของ")}</font>'
                           f'{_start_line}', _S["H2"])
            header = [Paragraph("KPI", _S["KpiHdr"]), Paragraph("เป้าหมาย", _S["KpiHdr"]),
                      Paragraph("เกณฑ์เตือน", _S["KpiHdr"]), Paragraph("ความถี่", _S["KpiHdr"])]
            tbl_body = [header]
            for (k, tgt, warn, freq) in g["rows"]:
                tbl_body.append([Paragraph(k, _S["KpiName"]), Paragraph(tgt, _S["KpiCell"]),
                                 Paragraph(warn, _S["KpiCell"]), Paragraph(freq, _S["KpiCell"])])
            kt = Table(tbl_body, colWidths=[cw * 0.30, cw * 0.26, cw * 0.28, cw * 0.16])
            ksty = [("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE)]
            for ri in range(1, len(tbl_body)):
                if ri % 2 == 0:
                    ksty.append(("BACKGROUND", (0, ri), (-1, ri), CREAM))
            kt.setStyle(TableStyle(ksty))
            story.append(KeepTogether([gh, Spacer(1, 1 * mm), kt, Spacer(1, 5 * mm)]))
        if pidx == nparts:
            story.append(Spacer(1, 2 * mm))
            story.append(_kpi_note())
        story.append(PageBreak())
    return


def _kpi_note():
    cw = PAGE_W - LM - RM
    note = Table([[Paragraph(f'<font name="{FB}" color="#{_hex(GOLD_DK)}">วิธีอ่านตาราง</font><br/>'
                             f'<font color="#{_hex(INK_SOFT)}">“เป้าหมาย” คือสภาวะที่ดี ควรพยายามรักษาให้อยู่ในเกณฑ์นี้ '
                             f'— ส่วน “เกณฑ์เตือน” คือสัญญาณว่าธุรกิจต้องลงมือแก้ไขทันที<br/>'
                             f'“เริ่มติดตาม” คือกำหนดเริ่มเฝ้าระวัง KPI ของมิตินั้น ตั้งตามระดับความเร่งด่วน (แดงเริ่มทันที)</font>', _S["Body"])]],
                 colWidths=[cw])
    note.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                              ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                              ("LINEBEFORE", (0, 0), (0, -1), 2, GOLD)]))
    return note


def _cta(story):
    cw = PAGE_W - LM - RM
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("TAKE THE NEXT STEP", _S["Kicker"]))
    story.append(Paragraph("ต้องการคำปรึกษาเชิงลึก?", _S["CoverTitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("บริการเสริม · SMEs Health Check Consultation", _S["H2"]))
    story.append(Paragraph(
        f'<font color="#{_hex(GREY)}">รายงานฉบับนี้คือผลิตภัณฑ์ Business Health Assessment โดย {BRAND_NAME} '
        f'(เครื่องมือวินิจฉัย ไม่ใช่ความเห็นผู้สอบบัญชี) — หากต้องการลงมือแก้ไขเชิงลึก '
        f'SMEs Health Check Consultation เป็นบริการให้คำปรึกษาเสริมแยกต่างหาก</font>', _S["Body"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("ทีมที่ปรึกษาพร้อมช่วยวิเคราะห์ปัญหาเชิงลึก วางแผนแก้ไข และติดตามผลอย่างเป็นระบบ", _S["Body"]))
    story.append(Spacer(1, 6 * mm))
    svc = [
        ("01", "วิเคราะห์สาเหตุที่แท้จริงของปัญหาที่พบในแบบประเมิน"),
        ("02", "วางแผนปรับปรุงระยะสั้น (Quick Wins) และระยะยาว"),
        ("03", "ติดตามผลทุก 3 เดือนด้วย KPI ที่วัดได้"),
        ("04", "เข้าถึงเครือข่ายผู้เชี่ยวชาญเฉพาะด้าน"),
    ]
    rows = []
    for i in range(0, 4, 2):
        rows.append([Paragraph(f'<font color="#{_hex(GOLD)}">{svc[i][0]}</font>  {svc[i][1]}', _S["Body"]),
                     Paragraph(f'<font color="#{_hex(GOLD)}">{svc[i+1][0]}</font>  {svc[i+1][1]}', _S["Body"])])
    st = Table(rows, colWidths=[cw / 2 - 4 * mm, cw / 2 - 4 * mm])
    st.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (0, -1), 10), ("LEFTPADDING", (1, 0), (1, -1), 10)]))
    story.append(st)
    story.append(Spacer(1, 12 * mm))
    contact = Table([[Paragraph(f'<font name="{F}" size="8" color="#{_hex(GREY_LT)}">EMAIL</font><br/>'
                                f'<font name="{FB}" color="#{_hex(INK)}">{CONTACT_EMAIL}</font>', _S["BodyC"]),
                      Paragraph(f'<font name="{F}" size="8" color="#{_hex(GREY_LT)}">WEB</font><br/>'
                                f'<font name="{FB}" color="#{_hex(INK)}">{CONTACT_WEB}</font>', _S["BodyC"])]],
                    colWidths=[cw / 2, cw / 2])
    contact.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                                 ("LINEABOVE", (0, 0), (-1, 0), 0.5, LINE)]))
    story.append(contact)
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("— End of Report —", _S["SmallC"]))


def _about_page(story, data):
    cw = PAGE_W - LM - RM
    story.append(Paragraph("ABOUT THIS REPORT", _S["Kicker"]))
    story.append(Paragraph("เกี่ยวกับรายงานฉบับนี้", _S["H1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=4, spaceAfter=8))

    # left: methodology | right: table of contents
    method = (
        f'<font name="{FB}" color="#{_hex(INK)}">วิธีการประเมิน</font><br/>'
        f'รายงานนี้ประเมินสุขภาพธุรกิจครอบคลุม 7 มิติหลัก มิติละ 6 คำถาม '
        f'ให้คะแนนข้อละ 0–3 (เต็ม 18 คะแนนต่อมิติ) แล้วแปลงเป็นเปอร์เซ็นต์ '
        f'จัดระดับด้วยสัญญาณไฟจราจร และสรุปเป็นเกรดรวมของธุรกิจ '
        f'<font color="#{_hex(GREY)}">โดยคะแนนรวมเป็นค่าเฉลี่ยถ่วงน้ำหนักของแต่ละมิติตามประเภทธุรกิจ จึงอาจต่างจากค่าเฉลี่ยอย่างง่าย</font><br/><br/>'
        f'<font name="{FB}" color="#{_hex(INK)}">กรอบอ้างอิงเบื้องหลัง</font><br/>'
        f'สังเคราะห์จากกรอบบริหารจัดการสากล (Balanced Scorecard, McKinsey 7S, '
        f'5C of Credit และ PESTLE) เพื่อให้ครอบคลุมทั้งภายในและปัจจัยแวดล้อม'
    )
    toc_items = [
        "บทสรุปผู้บริหาร", "ภาพรวมสุขภาพธุรกิจ 7 มิติ", "วิเคราะห์เจาะลึกรายมิติ",
        "แผนปฏิบัติการ 90 วัน", "ระบบ KPI ควบคุมและติดตามผล", "ข้อสรุปและก้าวต่อไป",
        "แหล่งอ้างอิงและระเบียบวิธี",
    ]
    toc_html = f'<font name="{FB}" color="#{_hex(INK)}">ในเล่มนี้</font><br/>' + "<br/>".join(
        f'<font color="#{_hex(GOLD_DK)}">{i:02d}</font>  {t}' for i, t in enumerate(toc_items, 1))
    two = Table([[Paragraph(method, _S["Body"]), Paragraph(toc_html, _S["Body"])]],
                colWidths=[cw * 0.58, cw * 0.42])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("RIGHTPADDING", (0, 0), (0, 0), 12), ("LEFTPADDING", (1, 0), (1, 0), 12)]))
    story.append(two)
    story.append(Spacer(1, 8 * mm))

    # scoring legend
    story.append(Paragraph("วิธีอ่านสัญญาณและเกรด", _S["ColHead"]))
    legend = [
        [Paragraph(f'<font name="{FB}" color="#{_hex(LIGHT_COLORS["GREEN"])}">● เขียว</font>', _S["Body"]),
         Paragraph("67% ขึ้นไป — อยู่ในเกณฑ์ดี (Healthy)", _S["Body"]),
         Paragraph(f'<font name="{FB}" color="#{_hex(GRADE_COLORS["STRONG"])}">STRONG</font> / '
                   f'<font name="{FB}" color="#{_hex(GRADE_COLORS["HEALTHY"])}">HEALTHY</font>', _S["Body"]),
         Paragraph("ภาพรวมแข็งแรง / ดี", _S["Body"])],
        [Paragraph(f'<font name="{FB}" color="#{_hex(LIGHT_COLORS["YELLOW"])}">● เหลือง</font>', _S["Body"]),
         Paragraph("34–66% — ควรปรับปรุง (At-risk)", _S["Body"]),
         Paragraph(f'<font name="{FB}" color="#{_hex(GRADE_COLORS["WATCH"])}">WATCH</font>', _S["Body"]),
         Paragraph("ต้องระวัง มีจุดเปราะบาง", _S["Body"])],
        [Paragraph(f'<font name="{FB}" color="#{_hex(LIGHT_COLORS["RED"])}">● แดง</font>', _S["Body"]),
         Paragraph("0–33% — เสี่ยงสูง (Critical)", _S["Body"]),
         Paragraph(f'<font name="{FB}" color="#{_hex(GRADE_COLORS["CRITICAL"])}">CRITICAL</font>', _S["Body"]),
         Paragraph("วิกฤต ต้องเร่งแก้ไข", _S["Body"])],
    ]
    lt = Table(legend, colWidths=[cw * 0.16, cw * 0.34, cw * 0.20, cw * 0.30])
    lsty = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, -1), CREAM),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, 1), 0.5, LINE)]
    lt.setStyle(TableStyle(lsty))
    story.append(lt)
    story.append(Spacer(1, 7 * mm))

    # weight table for this business type (transparency of the weighted score)
    try:
        from scoring import BUSINESS_TYPE_WEIGHTS, DIM_WEIGHTS
        _w = BUSINESS_TYPE_WEIGHTS.get(data.get("business_type", ""), DIM_WEIGHTS)
    except Exception:
        _w = {}
    if _w:
        story.append(Paragraph("น้ำหนักแต่ละมิติสำหรับธุรกิจประเภทนี้ (ใช้คำนวณคะแนนรวมแบบถ่วงน้ำหนัก)", _S["ColHead"]))
        hdr = [Paragraph(f'<font name="{FB}" color="#FFFFFF">{DIM_NAMES[d].split("และ")[0]}</font>', _S["KpiHdr"]) for d in DIMS]
        valrow = [Paragraph(f'<font name="{FB}" color="#{_hex(INK)}">{int(round(_w.get(d,0)*100))}%</font>', _S["BodyC"]) for d in DIMS]
        wt = Table([hdr, valrow], colWidths=[(cw)/7]*7)
        wt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                                ("BACKGROUND",(0,1),(-1,1),CREAM),("LINEBELOW",(0,0),(-1,0),0.5,LINE)]))
        story.append(wt)
        topw = sorted(DIMS, key=lambda d: _w.get(d,0), reverse=True)[:3]
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f'<font color="#{_hex(GREY)}">ระบบให้น้ำหนักสูงสุดกับ '
                               f'{", ".join(DIM_NAMES[d] for d in topw)} ตามลักษณะความเสี่ยงของธุรกิจประเภทนี้</font>',
                               _S["Small"]))
        story.append(Spacer(1, 6 * mm))

    # hard-floor controls note
    story.append(Paragraph("เกณฑ์ขั้นต่ำที่บังคับ (Hard-floor controls)", _S["ColHead"]))
    story.append(Paragraph(
        f'<font color="#{_hex(INK_SOFT)}">บางความเสี่ยงพื้นฐานหากไม่มี จะทำให้มิตินั้น “ไม่ผ่านสีเขียว” ทันทีไม่ว่าคะแนนส่วนอื่นจะดีเพียงใด '
        f'เช่น ไม่แยกบัญชีธุรกิจ · ไม่มีการสำรองข้อมูล · ไม่มี MFA/ทบทวนสิทธิ์บัญชีสำคัญ · ไม่มีการนับเงินสด/สต็อก · ไม่มีซัพพลายเออร์สำรอง</font>',
        _S["Body"]))
    story.append(Spacer(1, 8 * mm))

    disc = ("ข้อจำกัดความรับผิด — รายงานนี้จัดทำจากข้อมูลที่ผู้ประเมินกรอกด้วยตนเอง "
            "ผลลัพธ์เป็นแนวทางเชิงวินิจฉัยเบื้องต้นเพื่อประกอบการตัดสินใจ "
            "มิใช่คำแนะนำทางการเงิน กฎหมาย หรือบัญชีอย่างเป็นทางการ")
    dt = Table([[Paragraph(f'<font size="8.5" color="#{_hex(GREY)}">{disc}</font>', _S["Small"])]], colWidths=[cw])
    dt.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.5, LINE),
                            ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    story.append(dt)
    story.append(PageBreak())


def _conclusion_page(story, data):
    cw = PAGE_W - LM - RM
    grade = data["overall_grade"]; gcol = GRADE_COLORS.get(grade, INK)
    story.append(Paragraph("CONCLUSION", _S["Kicker"]))
    story.append(Paragraph("ข้อสรุปและก้าวต่อไป", _S["H1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=4, spaceAfter=8))
    for para in _conclusion_text(data):
        story.append(Paragraph(para, _S["Body"]))
        story.append(Spacer(1, 4 * mm))
    story.append(Spacer(1, 2 * mm))

    # priority recap box: top risks + first quick wins
    qws = _priority_actions(data, 3)
    if qws:
        head = Paragraph("เรื่องที่แนะนำให้ต่อยอด" if not data.get("top_risks")
                         else "สิ่งที่ควรทำทันทีหลังอ่านรายงานนี้", _S["ColHead"])
        items = []
        for i, it in enumerate(qws, 1):
            items.append([Paragraph(f'<font color="#{_hex(GOLD)}">{i:02d}</font>', _S["RecNum"]),
                          Paragraph(f'<font name="{FB}" color="#{_hex(INK)}">{it["dim_name"]}</font> — {it["text"]}',
                                    _S["RecText"])])
        itbl = Table(items, colWidths=[8 * mm, cw - 8 * mm - 20])
        itbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (0, -1), 1), ("RIGHTPADDING", (0, 0), (0, -1), 1),
                                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        box = Table([[head], [itbl]], colWidths=[cw])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM), ("BOX", (0, 0), (-1, -1), 0.5, GOLD),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                                 ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                                 ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
        story.append(box)
    story.append(PageBreak())


def _references_page(story, data):
    cw = PAGE_W - LM - RM
    try:
        from narratives import get_benchmark_sources
        srcs = get_benchmark_sources()
    except Exception:
        srcs = data.get("benchmark_sources") or []
    story.append(Paragraph("REFERENCES & METHODOLOGY", _S["Kicker"]))
    story.append(Paragraph("แหล่งอ้างอิงและระเบียบวิธี", _S["H1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "ค่าเปรียบเทียบ (benchmark) ในรายงานนี้อ้างอิงจากงานวิจัยและรายงานอุตสาหกรรมด้านล่าง "
        "บางตัวเลขเป็นเกณฑ์สากลที่ใช้เป็นจุดอ้างอิง โปรดพิจารณาประกอบกับบริบทเฉพาะของธุรกิจคุณ",
        _S["Body"]))
    story.append(Spacer(1, 5 * mm))
    rows = []
    for i, (org, desc, url) in enumerate(srcs, 1):
        rows.append([
            Paragraph(f'<font name="{FB}" color="#{_hex(GOLD)}">[R{i}]</font>', _S["RecText"]),
            Paragraph(f'<font name="{FB}" color="#{_hex(INK)}">{org}</font><br/>'
                      f'<font color="#{_hex(BODY)}">{desc}</font>  '
                      f'<font color="#{_hex(GREY_LT)}">· {url}</font>', _S["RecText"]),
        ])
    if rows:
        t = Table(rows, colWidths=[9 * mm, cw - 9 * mm])
        rsty = [("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 1), ("RIGHTPADDING", (0, 0), (0, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]
        for i in range(len(rows)):
            rsty.append(("LINEBELOW", (0, i), (-1, i), 0.5, LINE))
        t.setStyle(TableStyle(rsty))
        story.append(t)
    story.append(PageBreak())


def generate_pdf(data):
    global _S
    _S = _styles()
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title="Business Health Assessment", author=BRAND_NAME)
    frame = Frame(LM, BM, PAGE_W - LM - RM, PAGE_H - TM - BM, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])
    story = []
    _cover(story, data)
    _about_page(story, data)
    _exec_snapshot(story, data)
    for d in DIMS:
        _dimension(story, data, d)
    _roadmap(story, data)
    _kpi_pages(story, data)
    _conclusion_page(story, data)
    _references_page(story, data)
    _cta(story)
    doc.build(story, canvasmaker=NumberedCanvas)
    buf.seek(0)
    return buf
