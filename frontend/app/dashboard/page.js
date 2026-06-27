"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getFreeResults } from "@/lib/api";
import { DIMENSIONS } from "@/lib/constants";
import GradeCard from "@/components/GradeCard";
import DimensionCard from "@/components/DimensionCard";
import BlurredSection from "@/components/BlurredSection";
import NorthstarCTA from "@/components/NorthstarCTA";

function DashboardContent() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");

  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    getFreeResults(id)
      .then(setResults)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <main className="min-h-screen bg-surface flex items-center justify-center px-4">
        <div className="text-center text-risk-red text-sm">{error}</div>
      </main>
    );
  }

  if (!results) {
    return (
      <main className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-ink-muted text-sm animate-pulse">กำลังโหลดผลลัพธ์...</div>
      </main>
    );
  }

  const redCount = Object.values(results.dim_light).filter((l) => l === "RED").length;

  return (
    <main className="min-h-screen bg-surface">
      {/* ── Page header ─────────────────────────────────── */}
      <header className="bg-navy-gradient text-white px-4 pt-10 pb-8">
        <div className="max-w-lg mx-auto text-center">
          <p className="text-xs font-semibold text-gold uppercase tracking-widest mb-2">
            ★ Northstar Business Health Assessment
          </p>
          <h1 className="text-2xl font-bold">ผลการประเมิน</h1>
          <p className="text-white/50 text-xs mt-1">
            {results.business_name || "ธุรกิจของคุณ"}
          </p>
        </div>
      </header>

      {/* ── Content ─────────────────────────────────────── */}
      <div className="max-w-lg mx-auto px-4 -mt-4 pb-12 space-y-5">

        {/* Overall grade card */}
        <GradeCard grade={results.overall_grade} score={results.overall_score} />

        {/* Red flag summary */}
        {redCount > 0 && (
          <div className="flex items-center gap-3 bg-risk-bg-red border border-risk-red/20 rounded-card px-4 py-3 shadow-card">
            <span className="text-risk-red text-lg">⚠️</span>
            <p className="text-sm text-risk-red font-medium">
              พบ {redCount} มิติที่ต้องการความสนใจเร่งด่วน
            </p>
          </div>
        )}

        {/* 7 dimension cards */}
        <div>
          <h2 className="text-sm font-semibold text-navy uppercase tracking-wider mb-3">
            สุขภาพ 7 มิติ
          </h2>
          <div className="space-y-2.5">
            {DIMENSIONS.map((dim) => (
              <DimensionCard
                key={dim.id}
                dimension={dim}
                light={results.dim_light[dim.id]}
                pct={results.dim_pct[dim.id]}
                summary={results.summaries[dim.id]}
                isTopRisk={results.top_risks.includes(dim.id)}
              />
            ))}
          </div>
        </div>

        {/* Blurred unlock section */}
        <BlurredSection onUnlock={() => router.push("/payment?id=" + id)} />

        {/* Northstar CTA */}
        <NorthstarCTA />
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-ink-muted text-sm">กำลังโหลด...</div>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
