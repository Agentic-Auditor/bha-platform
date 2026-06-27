"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

// Landing page — Premium / Trust / Expert mood
// Navy gradient hero + gold CTA, business type strip, benefit cards
const BUSINESS_TYPES = [
  { icon: "🍜", label: "ร้านอาหาร" },
  { icon: "🏪", label: "ค้าปลีก" },
  { icon: "📦", label: "ขายออนไลน์" },
  { icon: "🏷️", label: "เจ้าของแบรนด์" },
  { icon: "🛎️", label: "ธุรกิจบริการ" },
  { icon: "💆", label: "สุขภาพ/ความงาม" },
  { icon: "🏭", label: "โรงงาน/OEM" },
  { icon: "🚀", label: "Startup" },
];

const MAX_AGE_MS = 3 * 24 * 60 * 60 * 1000; // 3 days

export default function LandingPage() {
  const [resumeId, setResumeId] = useState(null);

  useEffect(() => {
    try {
      const id = localStorage.getItem("bha_assessment_id");
      const ts = parseInt(localStorage.getItem("bha_assessment_ts") || "0", 10);
      if (id && Date.now() - ts < MAX_AGE_MS) setResumeId(id);
    } catch (_) {}
  }, []);

  function clearResume() {
    try { localStorage.removeItem("bha_assessment_id"); localStorage.removeItem("bha_assessment_ts"); } catch (_) {}
    setResumeId(null);
  }

  return (
    <main className="min-h-screen flex flex-col">

      {/* ── Resume banner ──────────────────────────────────── */}
      {resumeId && (
        <div className="bg-gold/10 border-b border-gold/30 px-4 py-3 flex items-center justify-between gap-3">
          <p className="text-sm text-ink font-medium">
            คุณมีแบบประเมินที่ยังไม่เสร็จ
          </p>
          <div className="flex gap-2 shrink-0">
            <Link
              href={`/assess?id=${resumeId}`}
              className="text-xs px-3 py-1.5 bg-navy text-white rounded-pill font-semibold hover:opacity-90"
            >
              ทำต่อ →
            </Link>
            <button
              onClick={clearResume}
              className="text-xs px-3 py-1.5 border border-gray-300 text-ink-muted rounded-pill hover:bg-gray-100"
            >
              เริ่มใหม่
            </button>
          </div>
        </div>
      )}

      {/* ── Hero (navy gradient) ──────────────────────────────── */}
      <section className="bg-navy-gradient text-white flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">

        {/* Northstar badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-pill bg-white/10 border border-white/20 text-gold text-xs font-semibold uppercase tracking-widest mb-8">
          <span>★</span>
          <span>Northstar Corporation</span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold leading-tight mb-4 max-w-sm">
          รู้จุดอ่อนธุรกิจ<br />
          <span className="text-gold">ก่อนที่ปัญหาจะลุกลาม</span>
        </h1>

        <p className="text-white/70 text-base leading-relaxed mb-3 max-w-xs">
          ประเมินสุขภาพธุรกิจ 7 มิติ ปรับตามประเภทธุรกิจของคุณ
        </p>

        {/* trust micro-copy */}
        <p className="text-white/40 text-xs mb-8">
          ออกแบบจากมุมมองการเงิน ระบบงาน และการควบคุมภายใน
        </p>

        {/* time badge + CTA */}
        <div className="flex flex-col items-center gap-3">
          <span className="text-xs text-white/50 border border-white/20 rounded-pill px-3 py-1">
            ⏱ ใช้เวลา 10–12 นาที
          </span>
          <Link
            href="/start"
            className="px-8 py-3.5 bg-gold text-white font-semibold rounded-pill text-base shadow-gold hover:brightness-110 transition-all"
          >
            เริ่มประเมินฟรี →
          </Link>
        </div>

        {/* gold accent line */}
        <div className="gold-line w-32 mt-12 mx-auto opacity-40" />
      </section>

      {/* ── Business type strip ───────────────────────────────── */}
      <section className="bg-navy border-t border-white/10 px-6 py-5">
        <p className="text-center text-white/40 text-xs uppercase tracking-widest mb-4">
          รองรับ 8 ประเภทธุรกิจ
        </p>
        <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
          {BUSINESS_TYPES.map((b) => (
            <span
              key={b.label}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-white/8 border border-white/15 text-white/70 text-xs"
            >
              <span>{b.icon}</span>
              <span>{b.label}</span>
            </span>
          ))}
        </div>
      </section>

      {/* ── Benefit cards (light surface) ────────────────────── */}
      <section className="bg-surface px-6 py-10">
        <div className="max-w-lg mx-auto space-y-3">
          {[
            { icon: "📊", text: "42 คำถาม ครอบคลุม 7 มิติธุรกิจ" },
            { icon: "🚦", text: "ผลลัพธ์แบบสัญญาณไฟจราจรทันที" },
            { icon: "🎯", text: "เกรดรวมพร้อมจุดเสี่ยงสำคัญ" },
            { icon: "📄", text: "รายงาน AI ปรับตามประเภทธุรกิจ พร้อมแผนปฏิบัติ" },
          ].map((b, i) => (
            <div key={i} className="flex items-center gap-3 bg-card rounded-card px-4 py-3.5 shadow-card">
              <span className="text-xl">{b.icon}</span>
              <span className="text-sm text-ink font-medium">{b.text}</span>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-ink-faint mt-8">
          โดย Northstar Corporation
        </p>
      </section>

    </main>
  );
}
