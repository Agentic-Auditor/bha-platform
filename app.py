import json
import logging
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from db import get_db, init_db
from scoring import calculate_score, DIM_QUESTIONS, ALL_DIMENSIONS
from narratives import get_narrative, get_roadmap, get_kpi_table, get_benchmark
from report_model import assemble_report_model
import email_service

# ── Logging ────────────────────────────────────────────────────────
# Configure once for standalone/dev runs. Under gunicorn the root logger
# already has handlers, so we don't clobber them. Level via LOG_LEVEL (INFO).
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("bha")

app = Flask(__name__)

# ── Startup guards: fail loud if secrets are missing in production ──
_FLASK_ENV = os.environ.get("FLASK_ENV", "production")
_SECRET_KEY = os.environ.get("SECRET_KEY")
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
if _FLASK_ENV != "development":
    if not _SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable must be set in production")
    if not _ADMIN_TOKEN:
        raise RuntimeError("ADMIN_TOKEN environment variable must be set in production")

app.secret_key = _SECRET_KEY or "dev-secret-change-me"
ADMIN_TOKEN = _ADMIN_TOKEN or "dev-admin-token"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL", "")
FRONTEND_URLS = [u.strip() for u in FRONTEND_URL.split(",")]
if _FLASK_ENV == "development":
    FRONTEND_URLS += ["http://localhost:3000", "http://localhost:3001"]
CORS(app, supports_credentials=True, origins=FRONTEND_URLS)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
)

SLIP_STORAGE_PATH = os.environ.get("SLIP_STORAGE_PATH", os.path.join(os.path.dirname(__file__), "slips"))
os.makedirs(SLIP_STORAGE_PATH, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

VALID_BUSINESS_TYPES = {"restaurant", "brand", "oem", "startup"}
VALID_REJECT_REASONS = {"WRONG_AMOUNT", "UNREADABLE", "WRONG_ACCOUNT", "DUPLICATE", "OTHER"}

# All 42 scored question IDs (6 per dimension × 7 dimensions)
VALID_ASSESSMENT_QUESTIONS = {q for qs in DIM_QUESTIONS.values() for q in qs}

# Onboarding context question IDs (not scored, stored as context_json)
VALID_CONTEXT_QUESTIONS = {"C1", "C2", "C3", "C4"}  # C4 = goal_bucket (12-month goal)

TOTAL_QUESTIONS = 42  # 6 questions × 7 dimensions


def _get_session_token():
    return request.cookies.get("session_token")


def _validate_session(assessment_id):
    token = _get_session_token()
    if not token:
        return None
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM assessments WHERE id = %s AND session_token = %s",
            (assessment_id, token),
        ).fetchone()
    finally:
        db.close()
    if not row:
        return None
    return dict(row)


def _build_context(assessment):
    """Extract narrative context dict from an assessment row."""
    raw = json.loads(assessment.get("context_json") or "{}")
    return {
        "business_type":   assessment.get("business_type", "general"),
        "age_bucket":      raw.get("C1", ""),   # อายุกิจการ
        "revenue_bucket":  raw.get("C2", ""),   # ยอดขายต่อเดือน
        "employee_bucket": raw.get("C3", ""),   # จำนวนพนักงาน
        "goal_bucket":     raw.get("C4", ""),   # เป้าหมาย 12 เดือน
        "business_name":   assessment.get("business_name", ""),
    }


def _update_status(assessment_id, status):
    db = get_db()
    try:
        db.execute(
            "UPDATE assessments SET status = %s, updated_at = %s WHERE id = %s",
            (status, datetime.utcnow().isoformat(), assessment_id),
        )
        db.commit()
    finally:
        db.close()


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────

@app.route("/api/health")
def health():
    import db as _db
    db_type = "postgresql" if _db.DATABASE_URL else "sqlite"
    return jsonify({"status": "ok", "db": db_type})


# ──────────────────────────────────────────────
# Assessment endpoints
# ──────────────────────────────────────────────

@app.route("/api/v1/assessments", methods=["POST"])
@limiter.limit("10 per hour")
def create_assessment():
    data = request.get_json() or {}
    business_type = data.get("business_type", "")
    if business_type not in VALID_BUSINESS_TYPES:
        return jsonify({"error": "Invalid business_type"}), 400

    # Optional onboarding context (C1/C2/C3) stored but not scored
    context = {}
    for key in VALID_CONTEXT_QUESTIONS:
        if key in data:
            context[key] = data[key]

    assessment_id = str(uuid.uuid4())
    session_token = str(uuid.uuid4())

    db = get_db()
    try:
        db.execute(
            """INSERT INTO assessments (id, session_token, business_type, context_json, status)
               VALUES (%s, %s, %s, %s, 'STARTED')""",
            (assessment_id, session_token, business_type, json.dumps(context) if context else None),
        )
        db.commit()
    finally:
        db.close()

    resp = make_response(jsonify({"assessment_id": assessment_id}))
    resp.set_cookie(
        "session_token",
        session_token,
        httponly=True,
        secure=_FLASK_ENV != "development",
        samesite="None" if _FLASK_ENV != "development" else "Lax",
        max_age=7 * 24 * 3600,
        path="/",
    )
    return resp


@app.route("/api/v1/assessments/<assessment_id>", methods=["GET"])
def get_assessment(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401
    assessment.pop("session_token", None)
    return jsonify(assessment)


@app.route("/api/v1/assessments/<assessment_id>/lead", methods=["PATCH"])
def capture_lead(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    db = get_db()
    try:
        # Only downgrade to LEAD_CAPTURED if assessment hasn't progressed further
        TERMINAL_STATUSES = ("CALCULATED", "STEP1_COMPLETE", "PAYMENT_PENDING", "PAYMENT_VERIFIED")
        current_status = assessment.get("status", "")
        new_status = current_status if current_status in TERMINAL_STATUSES else "LEAD_CAPTURED"
        db.execute(
            """UPDATE assessments
               SET business_name = %s, email = %s, status = %s, updated_at = %s
               WHERE id = %s""",
            (name, email, new_status, datetime.utcnow().isoformat(), assessment_id),
        )
        db.commit()
    finally:
        db.close()

    return jsonify({"status": "LEAD_CAPTURED"})


# ──────────────────────────────────────────────
# Answer endpoints
# ──────────────────────────────────────────────

@app.route("/api/v1/assessments/<assessment_id>/answers", methods=["POST"])
def submit_answer(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    question_id = data.get("question_id", "")
    score = data.get("score")

    if score not in (0, 1, 2, 3):
        return jsonify({"error": "Score must be 0-3"}), 400

    if question_id not in VALID_ASSESSMENT_QUESTIONS:
        return jsonify({"error": "Invalid question_id"}), 400

    db = get_db()
    try:
        db.execute(
            """INSERT INTO answers (assessment_id, question_id, score, answered_at)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT(assessment_id, question_id)
               DO UPDATE SET score = excluded.score, answered_at = excluded.answered_at""",
            (assessment_id, question_id, score, datetime.utcnow().isoformat()),
        )
        db.commit()
    finally:
        db.close()

    if assessment["status"] in ("STARTED", "LEAD_CAPTURED"):
        _update_status(assessment_id, "IN_PROGRESS")

    return jsonify({"saved": True})


# ──────────────────────────────────────────────
# Calculate endpoint
# ──────────────────────────────────────────────

@app.route("/api/v1/assessments/<assessment_id>/calculate", methods=["POST"])
def calculate(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        rows = db.execute(
            "SELECT question_id, score FROM answers WHERE assessment_id = %s",
            (assessment_id,),
        ).fetchall()

        if len(rows) < TOTAL_QUESTIONS:
            return jsonify({
                "error": f"Only {len(rows)} of {TOTAL_QUESTIONS} answers submitted"
            }), 400

        answers = {row["question_id"]: row["score"] for row in rows}
        result = calculate_score(answers, assessment["business_type"])

        # Load context_json for narrative personalisation
        context = json.loads(assessment.get("context_json") or "{}")

        now = datetime.utcnow().isoformat()
        db.execute(
            """INSERT INTO results (
                 assessment_id,
                 d1_raw, d2_raw, d3_raw, d4_raw, d5_raw, d6_raw, d7_raw,
                 d1_pct, d2_pct, d3_pct, d4_pct, d5_pct, d6_pct, d7_pct,
                 d1_light, d2_light, d3_light, d4_light, d5_light, d6_light, d7_light,
                 overall_score, overall_grade, red_flags, red_flag_count, calculated_at
               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT(assessment_id) DO UPDATE SET
                 d1_raw=excluded.d1_raw, d2_raw=excluded.d2_raw, d3_raw=excluded.d3_raw,
                 d4_raw=excluded.d4_raw, d5_raw=excluded.d5_raw, d6_raw=excluded.d6_raw,
                 d7_raw=excluded.d7_raw,
                 d1_pct=excluded.d1_pct, d2_pct=excluded.d2_pct, d3_pct=excluded.d3_pct,
                 d4_pct=excluded.d4_pct, d5_pct=excluded.d5_pct, d6_pct=excluded.d6_pct,
                 d7_pct=excluded.d7_pct,
                 d1_light=excluded.d1_light, d2_light=excluded.d2_light, d3_light=excluded.d3_light,
                 d4_light=excluded.d4_light, d5_light=excluded.d5_light, d6_light=excluded.d6_light,
                 d7_light=excluded.d7_light,
                 overall_score=excluded.overall_score, overall_grade=excluded.overall_grade,
                 red_flags=excluded.red_flags, red_flag_count=excluded.red_flag_count,
                 calculated_at=excluded.calculated_at""",
            (
                assessment_id,
                result["dim_raw"]["D1"], result["dim_raw"]["D2"], result["dim_raw"]["D3"],
                result["dim_raw"]["D4"], result["dim_raw"]["D5"], result["dim_raw"]["D6"],
                result["dim_raw"]["D7"],
                result["dim_pct"]["D1"], result["dim_pct"]["D2"], result["dim_pct"]["D3"],
                result["dim_pct"]["D4"], result["dim_pct"]["D5"], result["dim_pct"]["D6"],
                result["dim_pct"]["D7"],
                result["dim_light"]["D1"], result["dim_light"]["D2"], result["dim_light"]["D3"],
                result["dim_light"]["D4"], result["dim_light"]["D5"], result["dim_light"]["D6"],
                result["dim_light"]["D7"],
                result["overall"], result["grade"],
                json.dumps(result["red_flags"]), result["red_count"],
                now,
            ),
        )

        db.execute(
            "UPDATE assessments SET status = 'CALCULATED', step1_completed_at = %s, updated_at = %s WHERE id = %s",
            (now, now, assessment_id),
        )
        db.commit()
    finally:
        db.close()

    return jsonify({
        "overall": result["overall"],
        "grade": result["grade"],
        "dim_light": result["dim_light"],
        "red_flags": result["red_flags"],
    })


# ──────────────────────────────────────────────
# Results endpoints
# ──────────────────────────────────────────────

@app.route("/api/v1/assessments/<assessment_id>/results/free", methods=["GET"])
def get_free_results(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    model = build_report_model(assessment_id, assessment)
    if not model:
        return jsonify({"error": "Results not found. Run /calculate first."}), 404

    return jsonify({
        "overall_score": model["overall_score"],
        "overall_grade": model["overall_grade"],
        "dim_light": model["dim_light"],
        "dim_pct": model["dim_pct"],
        "top_risks": model["top_risks"],
        "summaries": model["summaries"],
    })


@app.route("/api/v1/assessments/<assessment_id>/results/full", methods=["GET"])
def get_full_results(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        payment = db.execute(
            "SELECT status FROM payments WHERE assessment_id = %s AND status = 'verified'",
            (assessment_id,),
        ).fetchone()

        if not payment:
            return jsonify({"error": "Payment not verified"}), 403

        row = db.execute(
            "SELECT * FROM results WHERE assessment_id = %s",
            (assessment_id,),
        ).fetchone()
    finally:
        db.close()

    if not row:
        return jsonify({"error": "Results not found"}), 404

    model = build_report_model(assessment_id, assessment)
    if not model:
        return jsonify({"error": "Results not found"}), 404

    return jsonify({
        "overall_score": model["overall_score"],
        "overall_grade": model["overall_grade"],
        "red_flags": model["red_flags"],
        "red_flag_count": model["red_flag_count"],
        "dim_light": model["dim_light"],
        "dim_pct": model["dim_pct"],
        "dim_raw": model["dim_raw"],
        "top_risks": model["top_risks"],
        "narratives": model["narratives"],
    })


def build_report_model(assessment_id, assessment=None):
    """Single source of truth for an assessment's report data.

    Every consumer — summary results, full results, PDF, email — MUST build its
    view from this one function, so that scores, traffic lights, narratives,
    roadmap, KPI and benchmark are always assembled from the SAME data in a
    single pass and can never drift apart. This is what replaced the four
    copy-pasted assembly blocks that used to cause "report contradicts itself".

    Returns a model dict, or None if no results row exists yet (caller -> 404).

    NOTE: lights/pcts/raws are read from the frozen `results` columns (current
    behavior, preserved). Recomputing them live from answers via
    calculate_score is the planned phase-2 change; when it lands it belongs
    HERE only, and every consumer inherits it for free.
    """
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM results WHERE assessment_id = %s",
            (assessment_id,),
        ).fetchone()
        if not row:
            return None

        if assessment is None:
            assessment = db.execute(
                "SELECT * FROM assessments WHERE id = %s", (assessment_id,)
            ).fetchone()
            if not assessment:
                return None

        answers_rows = db.execute(
            "SELECT question_id, score FROM answers WHERE assessment_id = %s",
            (assessment_id,),
        ).fetchall()
    finally:
        db.close()

    result = dict(row)
    if not isinstance(assessment, dict):
        assessment = dict(assessment)
    answers = {r["question_id"]: r["score"] for r in answers_rows}
    context = _build_context(assessment)

    # Assembly (incl. the phase-2 live recompute) lives in the DB-free,
    # unit-tested report_model.assemble_report_model. Here we only supply the
    # already-fetched rows plus open cache handles, so the logic stays testable.
    narr_db = get_db()
    bmark_db = get_db()
    try:
        return assemble_report_model(
            result, assessment, answers, context,
            assessment_id=assessment_id, narr_db=narr_db, bmark_db=bmark_db,
        )
    finally:
        narr_db.close()
        bmark_db.close()


def _build_pdf_bytes(assessment_id, assessment=None):
    """Generate PDF for an assessment and return raw bytes (or None on error)."""
    from pdf_report import generate_pdf

    model = build_report_model(assessment_id, assessment)
    if not model:
        return None

    pdf_data = {
        "overall_score": model["overall_score"],
        "overall_grade": model["overall_grade"],
        "red_flags":     model["red_flags"],
        "dim_light":     model["dim_light"],
        "dim_pct":       model["dim_pct"],
        "dim_raw":       model["dim_raw"],
        "top_risks":     model["top_risks"],
        "narratives":    model["narratives"],
        "business_name": model["business_name"],
        "business_type": model["business_type"],
        "email":         model["email"],
        "roadmap":       model["roadmap"],
        "kpi_table":     model["kpi_table"],
        "benchmark":     model["benchmark"],
    }

    # Generation-time invariant guard. Always logs any issue; raises only when
    # BHA_STRICT_VALIDATION=1 (use in staging/CI to fail loud). In production it
    # is fail-soft so a stray non-critical issue never blocks a paid delivery.
    try:
        from report_validate import assert_report_ok
        assert_report_ok(
            pdf_data,
            strict=os.environ.get("BHA_STRICT_VALIDATION") == "1",
            log=log.warning,
        )
    except ImportError:
        pass

    buf = generate_pdf(pdf_data)
    return buf.read()


@app.route("/api/v1/assessments/<assessment_id>/results/pdf", methods=["GET"])
def get_pdf_report(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        payment = db.execute(
            "SELECT status FROM payments WHERE assessment_id = %s AND status = 'verified'",
            (assessment_id,),
        ).fetchone()

        if not payment:
            return jsonify({"error": "Payment not verified"}), 403

        row = db.execute(
            "SELECT * FROM results WHERE assessment_id = %s",
            (assessment_id,),
        ).fetchone()
    finally:
        db.close()

    if not row:
        return jsonify({"error": "Results not found"}), 404

    # All report assembly lives in build_report_model (called via _build_pdf_bytes).
    pdf_bytes = _build_pdf_bytes(assessment_id, assessment)
    if not pdf_bytes:
        return jsonify({"error": "Could not generate PDF"}), 500

    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'attachment; filename="BHA_Report_{assessment_id[:8]}.pdf"'
    return resp


# ──────────────────────────────────────────────
# Payment endpoints
# ──────────────────────────────────────────────

def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/v1/assessments/<assessment_id>/payments", methods=["POST"])
@limiter.limit("5 per hour")
def upload_slip(assessment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    # Accept assessment in any post-calculate status
    if assessment["status"] not in ("CALCULATED", "STEP1_COMPLETE", "LEAD_CAPTURED", "PAYMENT_PENDING"):
        return jsonify({"error": "Assessment must be calculated before payment"}), 400

    if "slip" not in request.files:
        return jsonify({"error": "No slip file uploaded"}), 400

    slip = request.files["slip"]
    if not slip.filename or not _allowed_file(slip.filename):
        return jsonify({"error": "Invalid file type. Use PNG, JPG, or WEBP"}), 400

    # Accept name + email from form fields (combined lead+payment form)
    customer_name  = request.form.get("name", "").strip()
    customer_email = request.form.get("email", "").strip() or assessment.get("email", "")

    ext = slip.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    slip_path = os.path.join(SLIP_STORAGE_PATH, filename)
    slip.save(slip_path)

    # Read slip bytes for email attachment
    with open(slip_path, "rb") as _f:
        slip_bytes = _f.read()

    now = datetime.utcnow().isoformat()
    db = get_db()
    try:
        # Upsert lead info if email provided
        if customer_email:
            db.execute(
                """UPDATE assessments SET business_name = %s, email = %s, updated_at = %s
                   WHERE id = %s""",
                (customer_name or assessment.get("business_name", ""), customer_email, now, assessment_id),
            )

        row = db.execute(
            """INSERT INTO payments (assessment_id, amount, slip_url, slip_uploaded_at, status, created_at)
               VALUES (%s, 499.00, %s, %s, 'pending', %s) RETURNING id""",
            (assessment_id, f"/slips/{filename}", now, now),
        ).fetchone()
        payment_id = row["id"] if row else None
        db.execute(
            "UPDATE assessments SET status = 'PAYMENT_PENDING', updated_at = %s WHERE id = %s",
            (now, assessment_id),
        )
        db.commit()
    finally:
        db.close()

    # Notify admin with slip image attached (fire-and-forget)
    try:
        email_service.send_payment_pending_admin(
            payment_id=payment_id,
            assessment_id=assessment_id,
            customer_email=customer_email,
            slip_url=f"/slips/{filename}",
            slip_image_bytes=slip_bytes,
            slip_ext=ext,
        )
    except Exception as _e:
        log.exception("[EMAIL] admin notify failed: %s", _e)

    return jsonify({"payment_id": payment_id, "status": "pending"})


@app.route("/api/v1/assessments/<assessment_id>/payments/<int:payment_id>", methods=["GET"])
def get_payment_status(assessment_id, payment_id):
    assessment = _validate_session(assessment_id)
    if not assessment:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    try:
        row = db.execute(
            "SELECT id, assessment_id, amount, status, reject_reason, created_at FROM payments WHERE id = %s AND assessment_id = %s",
            (payment_id, assessment_id),
        ).fetchone()
    finally:
        db.close()

    if not row:
        return jsonify({"error": "Payment not found"}), 404

    return jsonify(dict(row))


# ──────────────────────────────────────────────
# Admin auth decorator (defined early — used by slip route and admin routes)
# ──────────────────────────────────────────────

def _require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != ADMIN_TOKEN:
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


@app.route("/slips/<filename>")
@_require_admin
def serve_slip(filename):
    """Slip images are admin-only — payment evidence should not be publicly accessible."""
    return send_from_directory(SLIP_STORAGE_PATH, filename)


# ──────────────────────────────────────────────
# Admin endpoints
# ──────────────────────────────────────────────

@app.route("/api/v1/admin/payments", methods=["GET"])
@_require_admin
def admin_list_payments():
    status_filter = request.args.get("status", "pending")
    db = get_db()
    try:
        rows = db.execute(
            """SELECT p.id, p.assessment_id, p.amount, p.slip_url, p.status,
                      p.reject_reason, p.notes, p.created_at, p.verified_at,
                      a.business_name, a.email
               FROM payments p
               JOIN assessments a ON p.assessment_id = a.id
               WHERE p.status = %s
               ORDER BY p.created_at DESC""",
            (status_filter,),
        ).fetchall()
    finally:
        db.close()

    return jsonify({"payments": [dict(r) for r in rows]})


@app.route("/api/v1/admin/payments/<int:payment_id>/approve", methods=["POST"])
@_require_admin
def admin_approve_payment(payment_id):
    db = get_db()
    try:
        payment = db.execute("SELECT * FROM payments WHERE id = %s", (payment_id,)).fetchone()
        if not payment:
            return jsonify({"error": "Payment not found"}), 404

        if payment["status"] != "pending":
            return jsonify({"error": "Payment already processed"}), 400

        now = datetime.utcnow().isoformat()
        db.execute(
            "UPDATE payments SET status = 'verified', verified_at = %s, verified_by = 'admin' WHERE id = %s",
            (now, payment_id),
        )
        db.execute(
            "UPDATE assessments SET status = 'PAYMENT_VERIFIED', updated_at = %s WHERE id = %s",
            (now, payment["assessment_id"]),
        )
        db.commit()

        # Fetch assessment for email + PDF
        assessment_row = db.execute(
            "SELECT * FROM assessments WHERE id = %s", (payment["assessment_id"],)
        ).fetchone()
    finally:
        db.close()

    # Generate PDF (best-effort — don't let failures block email)
    pdf_bytes = None
    try:
        pdf_bytes = _build_pdf_bytes(payment["assessment_id"], assessment_row)
        log.info("[PDF] Generated %s bytes for %s", len(pdf_bytes) if pdf_bytes else 0, payment['assessment_id'])
    except Exception as _pdf_e:
        log.exception("[PDF ERROR] _build_pdf_bytes failed for %s: %s", payment['assessment_id'], _pdf_e)

    # Send customer email regardless of PDF result
    try:
        email_service.send_payment_verified(
            email=assessment_row["email"] if assessment_row else "",
            assessment_id=payment["assessment_id"],
            business_name=assessment_row["business_name"] if assessment_row else "",
            pdf_bytes=pdf_bytes,
        )
        log.info("[EMAIL] send_payment_verified queued for %s", assessment_row['email'] if assessment_row else 'unknown')
    except Exception as _e:
        log.exception("[EMAIL ERROR] send_payment_verified failed: %s", _e)

    return jsonify({"status": "verified"})


@app.route("/api/v1/admin/payments/<int:payment_id>/reject", methods=["POST"])
@_require_admin
def admin_reject_payment(payment_id):
    data = request.get_json() or {}
    reason_code = data.get("reason_code", "")
    notes = data.get("notes", "")

    if reason_code not in VALID_REJECT_REASONS:
        return jsonify({"error": "Invalid reason_code"}), 400

    db = get_db()
    try:
        payment = db.execute("SELECT * FROM payments WHERE id = %s", (payment_id,)).fetchone()
        if not payment:
            return jsonify({"error": "Payment not found"}), 404

        if payment["status"] != "pending":
            return jsonify({"error": "Payment already processed"}), 400

        now = datetime.utcnow().isoformat()
        db.execute(
            "UPDATE payments SET status = 'rejected', reject_reason = %s, notes = %s, verified_at = %s, verified_by = 'admin' WHERE id = %s",
            (reason_code, notes, now, payment_id),
        )
        db.execute(
            "UPDATE assessments SET status = 'CALCULATED', updated_at = %s WHERE id = %s",
            (now, payment["assessment_id"]),
        )
        db.commit()

        # Fetch assessment for rejection email
        assessment_row = db.execute(
            "SELECT * FROM assessments WHERE id = %s", (payment["assessment_id"],)
        ).fetchone()
    finally:
        db.close()

    # Notify customer of rejection (fire-and-forget)
    try:
        email_service.send_payment_rejected(
            email=assessment_row["email"] if assessment_row else "",
            assessment_id=payment["assessment_id"],
            reason=reason_code,
            business_name=assessment_row["business_name"] if assessment_row else "",
        )
    except Exception as _e:
        log.exception("[EMAIL] send_payment_rejected failed: %s", _e)

    return jsonify({"status": "rejected"})


# ──────────────────────────────────────────────
# Admin login
# ──────────────────────────────────────────────

@app.route("/api/v1/admin/login", methods=["POST"])
@limiter.limit("10 per minute")
def admin_login():
    data = request.get_json() or {}
    token = data.get("token", "")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Invalid token"}), 401
    return jsonify({"ok": True})


@app.route("/admin")
def admin_panel():
    """Serve the admin panel HTML."""
    import os as _os
    html_path = _os.path.join(_os.path.dirname(__file__), "admin.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


# ══════════════════════════════════════════════════════════════════════════════
# Membership System (v3)
# ══════════════════════════════════════════════════════════════════════════════

MEMBERSHIP_PRICE = 890.00  # THB/year

# ── Helper ────────────────────────────────────────────────────────────────────

def _get_user_token():
    return request.cookies.get("user_token")


def _get_current_user():
    """Return user dict if user_token cookie is valid, else None."""
    token = _get_user_token()
    if not token:
        return None
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM users WHERE user_token = %s", (token,)
        ).fetchone()
    finally:
        db.close()
    return dict(row) if row else None


def _require_user(f):
    """Decorator: 401 if no valid user_token cookie."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized — please login"}), 401
        return f(user, *args, **kwargs)
    return decorated


def _require_member(f):
    """Decorator: 403 if user is not an active member."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized — please login"}), 401
        expires = user.get("membership_expires_at")
        is_member = (
            user["membership_status"] == "member"
            and expires
            and expires > datetime.utcnow().isoformat()
        )
        if not is_member:
            return jsonify({"error": "Member-only feature", "upgrade_url": "/membership/payment"}), 403
        return f(user, *args, **kwargs)
    return decorated


def _set_user_token_cookie(resp, token):
    resp.set_cookie(
        "user_token",
        token,
        httponly=True,
        secure=_FLASK_ENV != "development",
        samesite="None" if _FLASK_ENV != "development" else "Lax",
        max_age=365 * 24 * 3600,
        path="/",
    )
    return resp


# ── User auth ─────────────────────────────────────────────────────────────────

@app.route("/api/v1/users/login", methods=["POST"])
def user_login():
    """Email-based login/register (passwordless).
    Creates a new user if email not seen before; returns existing user otherwise.
    Issues a user_token cookie valid for 1 year.
    """
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name") or "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400

    db = get_db()
    try:
        row = db.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
        now = datetime.utcnow().isoformat()

        if row:
            user = dict(row)
            # Update name if provided and different
            if name and name != user.get("name"):
                db.execute(
                    "UPDATE users SET name = %s, updated_at = %s WHERE id = %s",
                    (name, now, user["id"]),
                )
                db.commit()
                user["name"] = name
        else:
            user_id    = str(uuid.uuid4())
            user_token = str(uuid.uuid4())
            db.execute(
                """INSERT INTO users (id, email, name, user_token, membership_status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'free', %s, %s)""",
                (user_id, email, name or None, user_token, now, now),
            )
            db.commit()
            user = {
                "id": user_id, "email": email, "name": name or None,
                "user_token": user_token, "membership_status": "free",
                "membership_expires_at": None,
            }
    finally:
        db.close()

    resp = make_response(jsonify({
        "id":                    user["id"],
        "email":                 user["email"],
        "name":                  user.get("name"),
        "membership_status":     user["membership_status"],
        "membership_expires_at": user.get("membership_expires_at"),
        "is_new":                not bool(row) if 'row' in dir() else False,
    }))
    _set_user_token_cookie(resp, user["user_token"])
    return resp


@app.route("/api/v1/users/logout", methods=["POST"])
def user_logout():
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie("user_token", path="/")
    return resp


@app.route("/api/v1/users/me", methods=["GET"])
@_require_user
def user_me(user):
    """Return current user profile + membership status."""
    expires = user.get("membership_expires_at")
    is_active = (
        user["membership_status"] == "member"
        and expires
        and expires > datetime.utcnow().isoformat()
    )
    return jsonify({
        "id":                    user["id"],
        "email":                 user["email"],
        "name":                  user.get("name"),
        "membership_status":     user["membership_status"],
        "membership_expires_at": expires,
        "is_active_member":      is_active,
    })


# ── Trend & Alerts (member-only) ──────────────────────────────────────────────

@app.route("/api/v1/users/trend", methods=["GET"])
@_require_member
def user_trend(user):
    """Return all completed assessments for this user (by email), newest first.
    Used to render the trend dashboard chart.
    """
    db = get_db()
    try:
        rows = db.execute(
            """SELECT a.id, a.business_type, a.business_name, a.created_at,
                      r.d1_pct, r.d2_pct, r.d3_pct, r.d4_pct,
                      r.d5_pct, r.d6_pct, r.d7_pct,
                      r.overall_score, r.overall_grade,
                      r.d1_light, r.d2_light, r.d3_light, r.d4_light,
                      r.d5_light, r.d6_light, r.d7_light,
                      r.red_flag_count
               FROM assessments a
               JOIN results r ON r.assessment_id = a.id
               WHERE a.email = %s
               ORDER BY a.created_at DESC
               LIMIT 20""",
            (user["email"],),
        ).fetchall()
    finally:
        db.close()

    return jsonify({"assessments": [dict(r) for r in rows]})


@app.route("/api/v1/users/alerts", methods=["GET"])
@_require_member
def user_alerts(user):
    """Compare last 2 assessments. Return dimensions that worsened.
    A dimension 'worsened' if pct dropped by ≥10pp or light moved toward RED.
    """
    db = get_db()
    try:
        rows = db.execute(
            """SELECT r.d1_pct, r.d2_pct, r.d3_pct, r.d4_pct,
                      r.d5_pct, r.d6_pct, r.d7_pct,
                      r.d1_light, r.d2_light, r.d3_light, r.d4_light,
                      r.d5_light, r.d6_light, r.d7_light,
                      a.created_at
               FROM assessments a
               JOIN results r ON r.assessment_id = a.id
               WHERE a.email = %s
               ORDER BY a.created_at DESC
               LIMIT 2""",
            (user["email"],),
        ).fetchall()
    finally:
        db.close()

    if len(rows) < 2:
        return jsonify({"alerts": [], "has_comparison": False})

    LIGHT_RANK = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    DIM_NAMES_TH = {
        "D1": "กลยุทธ์และวิสัยทัศน์",
        "D2": "ลูกค้าและการตลาด",
        "D3": "การดำเนินงาน",
        "D4": "การเงิน",
        "D5": "ทีมและบุคลากร",
        "D6": "นวัตกรรมและการปรับตัว",
        "D7": "ธรรมาภิบาลและการควบคุม",
    }

    current = dict(rows[0])
    previous = dict(rows[1])
    alerts = []

    for i in range(1, 8):
        key = f"D{i}"
        pct_col   = f"d{i}_pct"
        light_col = f"d{i}_light"

        cur_pct   = current.get(pct_col) or 0
        prev_pct  = previous.get(pct_col) or 0
        cur_light = current.get(light_col) or "GREEN"
        prev_light = previous.get(light_col) or "GREEN"

        pct_drop  = prev_pct - cur_pct
        light_worse = LIGHT_RANK.get(cur_light, 0) > LIGHT_RANK.get(prev_light, 0)

        if pct_drop >= 10 or light_worse:
            alerts.append({
                "dimension":   key,
                "name":        DIM_NAMES_TH[key],
                "prev_pct":    round(prev_pct, 1),
                "cur_pct":     round(cur_pct, 1),
                "drop":        round(pct_drop, 1),
                "prev_light":  prev_light,
                "cur_light":   cur_light,
                "severity":    "high" if cur_light == "RED" else "medium",
            })

    return jsonify({
        "alerts":         alerts,
        "has_comparison": True,
        "compared_at":    current.get("created_at"),
        "baseline_at":    previous.get("created_at"),
    })


# ── Membership payment (PromptPay QR) ─────────────────────────────────────────

@app.route("/api/v1/membership/payment", methods=["POST"])
@_require_user
def submit_membership_payment(user):
    """Upload PromptPay slip for 890 THB/year membership.
    Only one pending payment allowed at a time.
    """
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM membership_payments WHERE user_id = %s AND status = 'pending'",
            (user["id"],),
        ).fetchone()
        if existing:
            return jsonify({"error": "You already have a pending payment. Please wait for admin review."}), 409

        if "slip" not in request.files:
            return jsonify({"error": "No slip file uploaded"}), 400

        slip = request.files["slip"]
        if not slip.filename or not _allowed_file(slip.filename):
            return jsonify({"error": "Invalid file type. Use PNG, JPG, or WEBP"}), 400

        ext = slip.filename.rsplit(".", 1)[1].lower()
        filename = f"mem_{uuid.uuid4().hex}.{ext}"
        slip.save(os.path.join(SLIP_STORAGE_PATH, filename))

        now = datetime.utcnow().isoformat()
        row = db.execute(
            """INSERT INTO membership_payments
               (user_id, amount, slip_url, slip_uploaded_at, status, created_at)
               VALUES (%s, %s, %s, %s, 'pending', %s) RETURNING id""",
            (user["id"], MEMBERSHIP_PRICE, f"/slips/{filename}", now, now),
        ).fetchone()
        payment_id = row["id"] if row else None
        db.commit()
    finally:
        db.close()

    return jsonify({"payment_id": payment_id, "status": "pending", "amount": MEMBERSHIP_PRICE})


@app.route("/api/v1/membership/payment/status", methods=["GET"])
@_require_user
def membership_payment_status(user):
    """Get the latest membership payment status for the logged-in user."""
    db = get_db()
    try:
        row = db.execute(
            """SELECT id, amount, status, reject_reason, slip_uploaded_at, created_at
               FROM membership_payments
               WHERE user_id = %s
               ORDER BY created_at DESC LIMIT 1""",
            (user["id"],),
        ).fetchone()
    finally:
        db.close()

    if not row:
        return jsonify({"payment": None})
    return jsonify({"payment": dict(row)})


# ── Admin: Membership payments ────────────────────────────────────────────────

@app.route("/api/v1/admin/membership-payments", methods=["GET"])
@_require_admin
def admin_list_membership_payments():
    status_filter = request.args.get("status", "pending")
    db = get_db()
    try:
        rows = db.execute(
            """SELECT mp.id, mp.user_id, mp.amount, mp.slip_url, mp.status,
                      mp.reject_reason, mp.notes, mp.created_at, mp.verified_at,
                      u.email, u.name
               FROM membership_payments mp
               JOIN users u ON mp.user_id = u.id
               WHERE mp.status = %s
               ORDER BY mp.created_at DESC""",
            (status_filter,),
        ).fetchall()
    finally:
        db.close()
    return jsonify({"payments": [dict(r) for r in rows]})


@app.route("/api/v1/admin/membership-payments/<int:payment_id>/approve", methods=["POST"])
@_require_admin
def admin_approve_membership(payment_id):
    db = get_db()
    try:
        payment = db.execute(
            "SELECT * FROM membership_payments WHERE id = %s", (payment_id,)
        ).fetchone()
        if not payment:
            return jsonify({"error": "Payment not found"}), 404
        if payment["status"] != "pending":
            return jsonify({"error": "Payment already processed"}), 400

        now = datetime.utcnow().isoformat()
        # Membership expires 365 days from approval
        from datetime import timedelta
        expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()

        db.execute(
            "UPDATE membership_payments SET status='verified', verified_at=%s, verified_by='admin' WHERE id=%s",
            (now, payment_id),
        )
        db.execute(
            """UPDATE users
               SET membership_status='member', membership_expires_at=%s, updated_at=%s
               WHERE id=%s""",
            (expires_at, now, payment["user_id"]),
        )
        db.commit()
    finally:
        db.close()
    return jsonify({"status": "verified", "membership_expires_at": expires_at})


@app.route("/api/v1/admin/membership-payments/<int:payment_id>/reject", methods=["POST"])
@_require_admin
def admin_reject_membership(payment_id):
    data = request.get_json() or {}
    reason_code = data.get("reason_code", "OTHER")
    notes = data.get("notes", "")

    if reason_code not in VALID_REJECT_REASONS:
        return jsonify({"error": "Invalid reason_code"}), 400

    db = get_db()
    try:
        payment = db.execute(
            "SELECT * FROM membership_payments WHERE id = %s", (payment_id,)
        ).fetchone()
        if not payment:
            return jsonify({"error": "Payment not found"}), 404
        if payment["status"] != "pending":
            return jsonify({"error": "Payment already processed"}), 400

        now = datetime.utcnow().isoformat()
        db.execute(
            """UPDATE membership_payments
               SET status='rejected', reject_reason=%s, notes=%s, verified_at=%s, verified_by='admin'
               WHERE id=%s""",
            (reason_code, notes, now, payment_id),
        )
        db.commit()
    finally:
        db.close()
    return jsonify({"status": "rejected"})


# ── TEST ONLY — remove after PDF testing ───────────────────────────────────
_TEST_TOKEN = "bha-pdf-test-2025"

@app.route("/api/v1/test/force-paid/<assessment_id>", methods=["POST"])
def test_force_paid(assessment_id):
    """DEV TEST ONLY: create verified payment to allow PDF download."""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {_TEST_TOKEN}":
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    try:
        db.execute(
            """INSERT INTO payments
               (assessment_id, slip_url, status, verified_at)
               VALUES (%s, 'test-slip.png', 'verified', NOW())
               ON CONFLICT (assessment_id) DO NOTHING""",
            (assessment_id,)
        )
        db.commit()
    finally:
        db.close()
    return jsonify({"status": "ok", "assessment_id": assessment_id})
# ── END TEST ONLY ───────────────────────────────────────────────────────────

# ── end of app.py ──────────────────────────────────────────────────────────

# Initialize DB schema on every startup (gunicorn + dev server)
init_db()


# ── Temp debug: test email pipeline ──────────────────────────────────────────
@app.route("/api/v1/admin/debug-email/<assessment_id>", methods=["POST"])
@_require_admin
def debug_email(assessment_id):
    """Test PDF generation and email delivery for a given assessment."""
    results = {}
    # Step 1: PDF
    try:
        pdf_bytes = _build_pdf_bytes(assessment_id)
        results["pdf"] = {"ok": True, "bytes": len(pdf_bytes) if pdf_bytes else 0}
    except Exception as e:
        results["pdf"] = {"ok": False, "error": str(e)}
        pdf_bytes = None

    # Step 2: Email
    db = get_db()
    try:
        row = db.execute("SELECT * FROM assessments WHERE id = %s", (assessment_id,)).fetchone()
    finally:
        db.close()

    if not row:
        return jsonify({"error": "Assessment not found", "pdf": results.get("pdf")}), 404

    to_email = row["email"] or ""
    results["to_email"] = to_email
    try:
        ok = email_service._send_email(
            to_email,
            "[BHA Debug] Email pipeline test",
            f"<p>PDF size: {len(pdf_bytes) if pdf_bytes else 0} bytes</p><p>Assessment: {assessment_id}</p>",
            attachment_bytes=pdf_bytes,
            attachment_filename="debug_report.pdf",
        )
        results["email"] = {"ok": ok}
    except Exception as e:
        results["email"] = {"ok": False, "error": str(e)}

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
