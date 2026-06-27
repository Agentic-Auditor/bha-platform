# BHA Platform — Business Health Assessment
> **Agentic-Auditor** | ประเมินสุขภาพธุรกิจ 7 มิติ ด้วย AI

---

## ภาพรวม

BHA (Business Health Assessment) เป็นแพลตฟอร์มประเมินสุขภาพธุรกิจ SME ครอบคลุม **7 มิติ** ผ่านคำถาม **42 ข้อ** โดยระบบจะวิเคราะห์และสร้าง Narrative ด้วย AI (Claude) ปรับตามประเภทธุรกิจของผู้ใช้งาน

**แนวคิด**: ทำให้เจ้าของธุรกิจเห็น "จุดเสี่ยง" ก่อนที่ปัญหาจะลุกลาม โดยไม่ต้องจ้างที่ปรึกษา

---

## URLs & Deployment

| สิ่งแวดล้อม | URL |
|---|---|
| Production (หลัก) | `https://www.agentic-auditor.com/bha` |
| Vercel Direct | `https://frontend-phi-steel-50.vercel.app` |
| Backend API | Railway (PostgreSQL) |
| Admin Panel | `/admin` |

> **หมายเหตุ**: `agentic-auditor.com` เป็น Vercel project แยกจาก BHA มี rewrite rule ที่ route `/bha/*` มายัง BHA Vercel project

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS |
| Fonts | Noto Sans Thai + Inter (Google Fonts) |
| Backend | Flask + Gunicorn |
| Database | PostgreSQL (Railway, production) / SQLite (local dev) |
| AI Narrative | Anthropic Claude (claude-haiku-4-5) |
| Email | SendGrid |
| PDF Report | ReportLab |
| Hosting (Frontend) | Vercel (Hobby plan) |
| Hosting (Backend) | Railway |
| CI/CD | GitHub → Vercel auto-deploy (push to `main`) |

---

## Repository Structure

```
bha-platform/                  ← GitHub: Agentic-Auditor/bha-platform
├── app.py                     ← Flask API (main entry point)
├── scoring.py                 ← คำนวณคะแนน + weights
├── narratives.py              ← AI narrative generation (Claude)
├── pdf_report.py              ← สร้าง PDF report
├── email_service.py           ← SendGrid email
├── db.py                      ← Database connection
├── schema.sql                 ← Database schema
├── requirements.txt
├── Procfile                   ← gunicorn สำหรับ Railway
├── railway.json
└── frontend/                  ← Next.js (Vercel Root Directory = "frontend")
    ├── app/
    │   ├── layout.js          ← Root layout (fonts, metadata, OG tags)
    │   ├── page.js            ← Landing page
    │   ├── start/page.js      ← เลือกประเภทธุรกิจ + 4 context questions
    │   ├── assess/page.js     ← หน้าทำแบบประเมิน 42 ข้อ
    │   ├── report/page.js     ← ผลลัพธ์ (free preview)
    │   ├── register/page.js   ← [ปิดแล้ว] auto-redirect → /assess
    │   ├── payment/           ← อัปโหลดสลิป PromptPay
    │   ├── dashboard/         ← Member dashboard (trend, alerts)
    │   ├── member/            ← สมัครสมาชิก
    │   ├── membership/        ← ชำระ membership 890 ฿/ปี
    │   ├── login/             ← Email-based login
    │   ├── admin/             ← Admin panel (อนุมัติสลิป)
    │   ├── waiting/           ← หน้ารอผลตรวจสลิป
    │   ├── about/             ← [placeholder]
    │   └── services/          ← [placeholder]
    ├── components/
    │   ├── QuestionCard.jsx   ← Card คำถามหลัก
    │   ├── DimensionCard.jsx  ← แสดงผลแต่ละมิติ
    │   ├── GradeCard.jsx      ← แสดง grade รวม
    │   ├── TrafficLight.jsx   ← สีไฟ CRITICAL/WATCH/HEALTHY/STRONG
    │   ├── ProgressBar.jsx    ← Progress bar การทำแบบประเมิน
    │   ├── BlurredSection.jsx ← ส่วนที่ blur สำหรับ free users
    │   ├── NorthstarCTA.jsx   ← CTA upsell membership
    │   └── Navbar.jsx         ← [ไม่ได้ใช้งาน — ยังมีไฟล์อยู่]
    └── lib/
        ├── constants.js       ← BUSINESS_TYPES, DIMENSIONS, CONTEXT_QUESTIONS, คำถามทั้งหมด
        └── api.js             ← API client (fetch wrapper)
```

---

## User Flow (ปัจจุบัน)

```
Landing (/)
    ↓
Start (/start)
    ├── Step 0: เลือกประเภทธุรกิจ (8 ตัวเลือก)
    └── Step 1-4: Context questions (C1-C4)
           C1: อายุกิจการ
           C2: ยอดขายต่อเดือน
           C3: จำนวนพนักงาน
           C4: เป้าหมาย 12 เดือน
    ↓
Assess (/assess?id=...)
    └── 42 ข้อ (7 มิติ × 6 ข้อ)
    ↓
Results - Free Preview (/report?id=...)
    └── เห็น grade รวม + บางส่วน (ส่วนที่เหลือ blur)
    ↓
Payment (/payment?id=...)
    └── อัปโหลดสลิป PromptPay 499 ฿
    ↓
Waiting (/waiting?id=...)
    └── รอ admin อนุมัติ
    ↓
Full Results (/report?id=... [paid])
    └── ครบทุกมิติ + AI Narrative + PDF download
```

> **หมายเหตุ**: `/register` ถูกปิดแล้ว — ถ้าเข้า URL นี้โดยตรงจะ redirect ไป `/assess` อัตโนมัติ (ไม่มีหน้า email form อีกต่อไป)

---

## 7 มิติการประเมิน (Dimensions)

| ID | ชื่อมิติ | น้ำหนัก (default) |
|---|---|---|
| D1 | การเงินและสภาพคล่อง | 20% |
| D2 | ลูกค้าและการตลาด | 15% |
| D3 | ระบบงานและกระบวนการ | 15% |
| D4 | ทีมและทรัพยากรมนุษย์ | 10% |
| D5 | ซัพพลายเชนและต้นทุน | 10% |
| D6 | เทคโนโลยีและนวัตกรรม | 10% |
| D7 | ธรรมาภิบาลและความเสี่ยง | 20% |

> น้ำหนักปรับตามประเภทธุรกิจ เช่น ecommerce จะให้ D2 (25%) และ D6 (20%) มากกว่า

---

## 8 ประเภทธุรกิจ

| ID | ชื่อ |
|---|---|
| `restaurant` | ร้านอาหาร / คาเฟ่ |
| `retail` | ค้าปลีก / ร้านค้า |
| `ecommerce` | ขายออนไลน์ (Shopee, Lazada, TikTok Shop) |
| `brand` | เจ้าของแบรนด์ |
| `service` | ธุรกิจบริการ (ซ่อม, สอน, Freelance) |
| `health_beauty` | สุขภาพ / ความงาม (คลินิก, สปา, ฟิตเนส) |
| `oem` | โรงงาน / OEM |
| `startup` | Startup / Tech |

---

## ระบบคะแนน (Scoring)

```
แต่ละข้อ:  0–3 คะแนน (4-option multiple choice)
มิติละ:    6 ข้อ → max 18 คะแนนดิบ
คะแนน%:   (raw / 18) × 100

Weighted Score = Σ (dim_pct × dim_weight) ตาม business_type

Grade:
  CRITICAL  → ธุรกิจวิกฤต ต้องแก้ด่วน
  WATCH     → มีจุดเสี่ยง ควรจัดการ
  HEALTHY   → สุขภาพดี มีจุดพัฒนา
  STRONG    → แข็งแกร่ง พร้อมเติบโต
```

**Red Flag Questions**: แต่ละมิติมีคำถาม "ธงแดง" 1-2 ข้อ ถ้าตอบต่ำจะถูก flag พิเศษ

---

## API Endpoints (Backend)

```
GET  /api/health

POST /api/v1/assessments                          ← สร้าง session ใหม่
GET  /api/v1/assessments/:id                      ← ดึงข้อมูล assessment
POST /api/v1/assessments/:id/answers              ← บันทึกคำตอบ
POST /api/v1/assessments/:id/calculate            ← คำนวณคะแนน
GET  /api/v1/assessments/:id/results/free         ← ผลฟรี (บางส่วน)
GET  /api/v1/assessments/:id/results/full         ← ผลเต็ม (paid)
GET  /api/v1/assessments/:id/results/pdf          ← ดาวน์โหลด PDF

POST /api/v1/assessments/:id/payments             ← อัปโหลดสลิป 499 ฿
GET  /api/v1/assessments/:id/payments/:payId      ← ดูสถานะสลิป

POST /api/v1/users/login                          ← Email login (magic link)
POST /api/v1/users/logout
GET  /api/v1/users/me                             ← Profile + membership status
GET  /api/v1/users/trend                          ← ข้อมูล trend (member)
GET  /api/v1/users/alerts                         ← Alerts (member)

POST /api/v1/membership/payment                   ← ชำระ membership 890 ฿/ปี
GET  /api/v1/membership/payment/status

POST /api/v1/admin/login
GET  /api/v1/admin/payments                       ← รายการสลิปรอ approve
POST /api/v1/admin/payments/:id/approve
POST /api/v1/admin/payments/:id/reject
GET  /api/v1/admin/membership-payments
POST /api/v1/admin/membership-payments/:id/approve
POST /api/v1/admin/membership-payments/:id/reject
```

---

## Database Schema

| Table | คำอธิบาย |
|---|---|
| `assessments` | ข้อมูล session (business_type, context_json, status) |
| `answers` | คำตอบแต่ละข้อ (score 0-3) |
| `results` | คะแนนแต่ละมิติ + grade รวม |
| `payments` | สลิป PromptPay 499 ฿ + status (pending/approved/rejected) |
| `narrative_cache` | AI narratives cache (hash-based, ลดค่า API) |
| `users` | Email-based identity + membership status |
| `membership_payments` | สลิป membership 890 ฿/ปี |

---

## Monetization

| แผน | ราคา | สิทธิ์ |
|---|---|---|
| ฟรี | 0 ฿ | ผลบางส่วน (blur ส่วนที่เหลือ) |
| One-time Report | 499 ฿ | ผลเต็ม + AI Narrative + PDF |
| Membership | 890 ฿/ปี | Dashboard, Trend Tracking, Alerts, ประเมินได้หลายครั้ง |

ชำระผ่าน PromptPay QR → อัปโหลดสลิป → Admin อนุมัติ manual

---

## Environment Variables

### Backend (Railway)
```
SECRET_KEY          ← Flask secret
ADMIN_TOKEN         ← Admin API auth
FRONTEND_URL        ← Comma-separated allowed origins
ANTHROPIC_API_KEY   ← Claude AI
SENDGRID_API_KEY    ← Email
ADMIN_NOTIFY_EMAIL  ← รับแจ้งเตือนสลิปใหม่
REDIS_URL           ← Rate limiting (optional)
SLIP_STORAGE_PATH   ← เก็บไฟล์สลิป
```

### Frontend (Vercel)
```
NEXT_PUBLIC_API_URL         ← URL ของ Backend
NEXT_PUBLIC_SITE_URL        ← https://www.agentic-auditor.com
```

---

## Local Development

### Backend
```bash
cd BHA_Platform
pip install -r requirements.txt
FLASK_ENV=development python app.py
```

### Frontend
```bash
cd BHA_Platform/frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## GitHub & Deploy

- **Repo**: `github.com/Agentic-Auditor/bha-platform`
- **Branch**: `main`
- **Vercel Root Directory**: `frontend`
- **Auto-deploy**: push to `main` → Vercel builds อัตโนมัติ
- **Vercel Plan**: Hobby (ปุ่ม Redeploy ใน dashboard ล็อก → ใช้ empty commit แทน)

```bash
# Force redeploy (workaround Hobby plan)
git commit --allow-empty -m "chore: trigger redeploy"
git push origin main
```

---

## สถานะปัจจุบัน (มิถุนายน 2025)

| Feature | สถานะ |
|---|---|
| แบบประเมิน 42 ข้อ | ✅ ใช้งานได้ |
| AI Narrative | ✅ ใช้งานได้ (cached) |
| PDF Report | ✅ ใช้งานได้ |
| ชำระเงิน 499 ฿ | ✅ ใช้งานได้ |
| Membership 890 ฿/ปี | ✅ ใช้งานได้ |
| Member Dashboard | ✅ ใช้งานได้ |
| Email capture (/register) | ❌ ปิดแล้ว → redirect อัตโนมัติ |
| Navbar | ❌ ไม่ได้ใช้งาน (ไฟล์ยังอยู่) |
| About / Services pages | ⚠️ Placeholder เท่านั้น |

---

## จุดที่ต้องพัฒนาต่อ (Backlog)

- [ ] เพิ่ม PDPA consent screen ก่อนเริ่มประเมิน (มีอยู่ใน GitHub แต่ถูก revert ใน workspace)
- [ ] เชื่อม Navbar กับหน้า `agentic-auditor.com` (ไม่ใช่ BHA)
- [ ] พัฒนาหน้า About และ Services
- [ ] ระบบ email magic link login ให้ user กลับมาดูผลได้
- [ ] Dashboard trend แสดงกราฟ progress หลายครั้ง
- [ ] SEO / sitemap สำหรับ `/bha`
