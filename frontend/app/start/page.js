"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BUSINESS_TYPES, CONTEXT_QUESTIONS } from "@/lib/constants";
import { createAssessment } from "@/lib/api";

export default function StartPage() {
  const router = useRouter();
  const [step, setStep] = useState(0); // 0 = business type, 1-4 = C1/C2/C3/C4
  const [businessType, setBusinessType] = useState(null);
  const [contextAnswers, setContextAnswers] = useState({});
  const [loading, setLoading] = useState(false);

  function handleSelectType(typeId) {
    setBusinessType(typeId);
    setStep(1);
  }

  async function handleContextAnswer(qId, value) {
    const updated = { ...contextAnswers, [qId]: value };
    setContextAnswers(updated);

    const questionIndex = step - 1;
    const isLast = questionIndex === CONTEXT_QUESTIONS.length - 1;

    if (!isLast) {
      setStep(step + 1);
      return;
    }

    setLoading(true);
    try {
      const data = await createAssessment(businessType, updated);
      // Persist assessment ID so user can resume if they close the browser
      try {
        localStorage.setItem("bha_assessment_id", data.assessment_id);
        localStorage.setItem("bha_assessment_ts", Date.now().toString());
      } catch (_) {}
      router.push("/assess?id=" + data.assessment_id);
    } catch (err) {
      alert("เกิดข้อผิดพลาด กรุณาลองใหม่");
      setLoading(false);
    }
  }

  // ── Step 0: Business type picker ──────────────────────────────────────────
  if (step === 0) {
    return (
      <main className="min-h-screen bg-surface flex flex-col items-center justify-center px-4 py-16">
        <div className="max-w-lg w-full space-y-6">
          {/* header */}
          <div className="text-center">
            <p className="text-xs font-semibold text-gold uppercase tracking-widest mb-2">
              ขั้นตอนที่ 1 / 2
            </p>
            <h1 className="text-2xl font-bold text-navy">
              ธุรกิจของคุณอยู่ในประเภทไหน?
            </h1>
            <p className="text-ink-muted text-sm mt-2">เลือกประเภทที่ใกล้เคียงที่สุด</p>
          </div>

          {/* type grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {BUSINESS_TYPES.map((bt) => (
              <button
                key={bt.id}
                onClick={() => handleSelectType(bt.id)}
                className="flex flex-col items-center p-6 rounded-card border-2 border-gray-100 bg-card shadow-card hover:border-gold hover:shadow-card-hover transition-all group"
              >
                <span className="text-4xl mb-2">{bt.icon}</span>
                <span className="font-semibold text-ink group-hover:text-navy transition-colors">{bt.label}</span>
                <span className="text-xs text-ink-muted mt-1 text-center">{bt.desc}</span>
              </button>
            ))}
          </div>
        </div>
      </main>
    );
  }

  // ── Steps 1-4: Context questions ──────────────────────────────────────────
  const cq = CONTEXT_QUESTIONS[step - 1];

  return (
    <main className="min-h-screen bg-surface flex flex-col items-center justify-center px-4 py-16">
      <div className="max-w-md w-full space-y-6">

        {/* progress dots */}
        <div className="flex justify-center gap-2">
          {CONTEXT_QUESTIONS.map((_, i) => (
            <div
              key={i}
              className={
                "w-2 h-2 rounded-full transition-colors " +
                (i < step - 1 ? "bg-navy" : i === step - 1 ? "bg-gold" : "bg-gray-200")
              }
            />
          ))}
        </div>

        {/* label + question */}
        <div className="text-center">
          <p className="text-xs font-semibold text-gold uppercase tracking-widest mb-2">
            ข้อมูลพื้นฐาน {step} / {CONTEXT_QUESTIONS.length}
          </p>
          <h2 className="text-xl font-bold text-navy leading-snug">{cq.text}</h2>
          <p className="text-ink-faint text-sm mt-1">ใช้เพื่อวิเคราะห์ให้ตรงกับธุรกิจคุณมากขึ้น</p>
        </div>

        {/* option buttons */}
        <div className="space-y-2.5">
          {cq.options.map((opt, i) => (
            <button
              key={i}
              onClick={() => !loading && handleContextAnswer(cq.id, opt)}
              disabled={loading}
              className="w-full text-left px-5 py-4 rounded-card border-2 border-gray-100 bg-card shadow-card hover:border-gold hover:shadow-card-hover disabled:opacity-50 font-medium text-ink transition-all"
            >
              {opt}
            </button>
          ))}
        </div>

        {loading && (
          <p className="text-center text-sm text-ink-muted animate-pulse">
            กำลังเตรียมแบบประเมิน...
          </p>
        )}

        {step > 1 && !loading && (
          <button
            onClick={() => setStep(step - 1)}
            className="w-full text-center text-sm text-ink-faint hover:text-ink-muted transition-colors"
          >
            ← ย้อนกลับ
          </button>
        )}
      </div>
    </main>
  );
}
