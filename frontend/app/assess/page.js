"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { QUESTIONS_STEP1 } from "@/lib/constants";
import { submitAnswer, calculateScore } from "@/lib/api";
import QuestionCard from "@/components/QuestionCard";
import ProgressBar from "@/components/ProgressBar";

const MAX_RETRIES = 2;

async function submitWithRetry(id, qId, score) {
  let lastErr;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      await submitAnswer(id, qId, score);
      return;
    } catch (err) {
      lastErr = err;
      if (attempt < MAX_RETRIES) {
        await new Promise((r) => setTimeout(r, 600 * (attempt + 1)));
      }
    }
  }
  throw lastErr;
}

function AssessFlow() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");

  const [dimIndex, setDimIndex] = useState(0);
  const [qIndex, setQIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);

  const currentDim = QUESTIONS_STEP1[dimIndex];
  const currentQuestion = currentDim?.questions[qIndex];
  const totalQuestions = QUESTIONS_STEP1.reduce((sum, d) => sum + d.questions.length, 0);
  const globalIndex = QUESTIONS_STEP1
    .slice(0, dimIndex)
    .reduce((sum, d) => sum + d.questions.length, 0) + qIndex;

  function showToast(type, msg, ms = 3500) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), ms);
  }

  async function handleSelect(score) {
    const qId = currentQuestion.id;
    setAnswers((prev) => ({ ...prev, [qId]: score }));
    setSaving(true);

    try {
      await submitWithRetry(id, qId, score);
    } catch (err) {
      showToast("error", "บันทึกไม่สำเร็จ กรุณาตรวจสอบการเชื่อมต่อแล้วลองใหม่");
      setSaving(false);
      return;
    }

    setSaving(false);

    if (qIndex < currentDim.questions.length - 1) {
      setQIndex(qIndex + 1);
    } else if (dimIndex < QUESTIONS_STEP1.length - 1) {
      setDimIndex(dimIndex + 1);
      setQIndex(0);
    } else {
      setSaving(true);
      try {
        await calculateScore(id);
        router.push("/loading?id=" + id);
      } catch (err) {
        showToast("error", "เกิดข้อผิดพลาดในการคำนวณ: " + err.message, 5000);
        setSaving(false);
      }
    }
  }

  return (
    <main className="min-h-screen bg-surface flex flex-col">
      {/* top bar */}
      <header className="bg-card border-b border-gray-100 px-4 py-4 sticky top-0 z-10">
        <div className="max-w-lg mx-auto">
          <ProgressBar
            currentDim={currentDim?.id}
            questionIndex={globalIndex}
            totalQuestions={totalQuestions}
          />
        </div>
      </header>

      {/* question area */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        <div className="max-w-lg w-full space-y-6">

          {/* dim label */}
          <div className="flex items-center gap-2">
            <span className="text-xl">{currentDim?.icon}</span>
            <p className="text-xs font-semibold text-navy uppercase tracking-wider">
              {currentDim?.name}
            </p>
          </div>

          {/* question card */}
          <div className="bg-card rounded-card shadow-card p-5">
            <QuestionCard
              question={currentQuestion}
              selectedScore={answers[currentQuestion?.id]}
              onSelect={handleSelect}
            />
          </div>

          {saving && (
            <p className="text-center text-xs text-ink-faint animate-pulse">
              กำลังบันทึก...
            </p>
          )}

          {/* back button — ย้อนข้อที่แล้วได้ถ้าไม่ใช่ข้อแรก */}
          {(qIndex > 0 || dimIndex > 0) && !saving && (
            <button
              onClick={() => {
                if (qIndex > 0) {
                  setQIndex(qIndex - 1);
                } else {
                  const prevDim = QUESTIONS_STEP1[dimIndex - 1];
                  setDimIndex(dimIndex - 1);
                  setQIndex(prevDim.questions.length - 1);
                }
              }}
              className="w-full text-center text-sm text-ink-faint hover:text-ink-muted transition-colors py-1"
            >
              ← ย้อนกลับ
            </button>
          )}
        </div>
      </div>

      {/* toast */}
      {toast && (
        <div
          className={
            "fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-card shadow-card text-sm font-medium text-white max-w-xs text-center " +
            (toast.type === "error" ? "bg-risk-red" : "bg-navy")
          }
        >
          {toast.msg}
        </div>
      )}
    </main>
  );
}

export default function AssessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="text-ink-muted text-sm">กำลังโหลด...</div>
      </div>
    }>
      <AssessFlow />
    </Suspense>
  );
}
