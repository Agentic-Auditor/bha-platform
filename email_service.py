import os
import logging

log = logging.getLogger("bha.email")

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@agentic-auditor.com")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://www.agentic-auditor.com")
BRAND_NAME = os.environ.get("BHA_BRAND_NAME", "AA · Agentic-Auditor")


def _send_email(to_email, subject, html_body):
    if not SENDGRID_API_KEY:
        log.info("[EMAIL] (no SendGrid key) would send to %s | Subject: %s", to_email, subject)
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        log.exception("[EMAIL ERROR] send failed: %s", e)
        return False


def send_lead_captured(email, assessment_id, business_name=""):
    name = business_name or "คุณผู้ประกอบการ"
    link = f"{FRONTEND_URL}/assess?id={assessment_id}"
    _send_email(
        email,
        "ยินดีต้อนรับสู่ Business Health Assessment",
        f"""
        <h2>สวัสดีครับ {name}</h2>
        <p>ขอบคุณที่ลงทะเบียนเพื่อตรวจสุขภาพธุรกิจกับ {BRAND_NAME}</p>
        <p>คลิกที่ลิงก์ด้านล่างเพื่อเริ่มทำแบบประเมิน:</p>
        <p><a href="{link}">เริ่มทำแบบประเมิน</a></p>
        """,
    )


def send_step1_complete(email, assessment_id, grade, business_name=""):
    name = business_name or "คุณผู้ประกอบการ"
    link = f"{FRONTEND_URL}/dashboard?id={assessment_id}"
    _send_email(
        email,
        f"ผลการประเมินสุขภาพธุรกิจ: {grade}",
        f"""
        <h2>{name} — ผลการประเมินพร้อมแล้ว!</h2>
        <p>เกรดสุขภาพธุรกิจของคุณ: <strong>{grade}</strong></p>
        <p>ดูผลวิเคราะห์ฟรีได้ที่:</p>
        <p><a href="{link}">ดู Dashboard</a></p>
        <p>ต้องการเจาะลึก? อัปเกรดเป็นรายงานเต็มรูปแบบเพียง ฿499</p>
        """,
    )


def send_payment_pending_admin(admin_email, payment_id, assessment_id, email):
    _send_email(
        admin_email,
        f"[BHA] สลิปรอตรวจ #{payment_id}",
        f"""
        <h2>มีสลิปใหม่รอตรวจสอบ</h2>
        <p>Payment #{payment_id}</p>
        <p>Assessment: {assessment_id}</p>
        <p>ผู้จ่าย: {email}</p>
        """,
    )


def send_payment_verified(email, assessment_id, business_name=""):
    name = business_name or "คุณผู้ประกอบการ"
    link = f"{FRONTEND_URL}/step2?id={assessment_id}"
    _send_email(
        email,
        "การชำระเงินสำเร็จ — เริ่มขั้นตอนที่ 2 ได้เลย!",
        f"""
        <h2>{name} — ขอบคุณสำหรับการชำระเงิน!</h2>
        <p>เราได้ตรวจสอบการชำระเงินของคุณเรียบร้อยแล้ว</p>
        <p>คลิกที่ลิงก์ด้านล่างเพื่อเริ่มทำแบบประเมินขั้นตอนที่ 2:</p>
        <p><a href="{link}">เริ่มขั้นตอนที่ 2</a></p>
        """,
    )


def send_payment_rejected(email, assessment_id, reason, business_name=""):
    name = business_name or "คุณผู้ประกอบการ"
    reasons_th = {
        "WRONG_AMOUNT": "ยอดเงินไม่ถูกต้อง",
        "UNREADABLE": "สลิปอ่านไม่ออก",
        "WRONG_ACCOUNT": "โอนผิดบัญชี",
        "DUPLICATE": "สลิปซ้ำกัน",
        "OTHER": "กรุณาติดต่อทีมงาน",
    }
    reason_text = reasons_th.get(reason, reason)
    link = f"{FRONTEND_URL}/payment?id={assessment_id}"
    _send_email(
        email,
        "การชำระเงินไม่สำเร็จ — กรุณาลองใหม่",
        f"""
        <h2>{name}</h2>
        <p>เราไม่สามารถยืนยันการชำระเงินของคุณได้</p>
        <p>เหตุผล: <strong>{reason_text}</strong></p>
        <p>กรุณาลองอัปโหลดสลิปใหม่:</p>
        <p><a href="{link}">อัปโหลดสลิปใหม่</a></p>
        """,
    )


def send_step2_complete(email, assessment_id, business_name=""):
    name = business_name or "คุณผู้ประกอบการ"
    link = f"{FRONTEND_URL}/report?id={assessment_id}"
    _send_email(
        email,
        "รายงานสุขภาพธุรกิจพร้อมแล้ว!",
        f"""
        <h2>{name} — รายงานฉบับเต็มพร้อมแล้ว!</h2>
        <p>ขอบคุณที่ทำแบบประเมินครบทุกขั้นตอน</p>
        <p>คลิกที่ลิงก์ด้านล่างเพื่อดูรายงาน:</p>
        <p><a href="{link}">ดูรายงานฉบับเต็ม</a></p>
        <hr>
        <p>ต้องการให้ผู้เชี่ยวชาญช่วยวิเคราะห์และวางแผนปรับปรุง?</p>
        <p><strong>{BRAND_NAME}</strong> — ติดต่อทีมที่ปรึกษาของเรา</p>
        """,
    )
