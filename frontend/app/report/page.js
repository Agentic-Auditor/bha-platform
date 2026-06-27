"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getFullResults, downloadPdf } from "@/lib/api";
import { DIMENSIONS } from "@/lib/constants";
import GradeCard from "@/components/GradeCard";
import TrafficLight from "@/components/TrafficLight";
import NorthstarCTA from "@/components/NorthstarCTA";

function ReportContent() {
  const params = useSearchParams();
  const id = params.get("id");

  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;
    getFullResults(id)
      .then(setResults)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center text-red-600">{error}</div>
      </main>
    );
  }

  if (!results) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-gray-400">กำลังโหลดรายงาน...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-8 max-w-2xl mx-auto space-y-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">
          รายงานสุขภาพธุรกิจฉบับเต็ม
        </h1>
        <p className="text-gray-500 text-sm mt-1">Full Business Health Report</p>
      </div>

      <GradeCard grade={results.overall_grade} score={results.overall_score} />

      <button
        onClick={() => downloadPdf(id)}
        className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
        ดาวน์โหลดรายงาน PDF
      </button>

      {results.red_flag_count > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h3 className="text-red-700 font-semibold mb-1">
            พบ Red Flag {results.red_flag_count} มิติ
          </h3>
          <p className="text-red-600 text-sm">
            มิติ: {results.red_flags.join(", ")}
          </p>
        </div>
      )}

      {DIMENSIONS.map((dim) => {
        const narrative = results.narratives[dim.id];
        const light = results.dim_light[dim.id];
        const pct = results.dim_pct[dim.id];

        return (
          <div key={dim.id} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <TrafficLight color={light} size="lg" />
                <h2 className="text-lg font-semibold">{dim.name}</h2>
              </div>
              <span className="text-sm text-gray-500">{Math.round(pct)}%</span>
            </div>

            {narrative?.summary && (
              <p className="text-gray-700 font-medium">{narrative.summary}</p>
            )}

            {/* current_state (v2) — fallback to detail for backward compat */}
            {(narrative?.current_state || narrative?.detail) && (
              <div>
                <h4 className="text-sm font-semibold text-gray-500 mb-1">
                  สถานการณ์ปัจจุบัน
                </h4>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {narrative.current_state || narrative.detail}
                </p>
              </div>
            )}

            {narrative?.root_cause && (
              <div>
                <h4 className="text-sm font-semibold text-gray-500 mb-1">
                  สาเหตุที่แท้จริง
                </h4>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {narrative.root_cause}
                </p>
              </div>
            )}

            {narrative?.whats_working && (
              <div>
                <h4 className="text-sm font-semibold text-gray-500 mb-1">
                  สิ่งที่ทำดีแล้ว
                </h4>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {narrative.whats_working}
                </p>
              </div>
            )}

            {narrative?.actions?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-500 mb-2">
                  แผนปฏิบัติ
                </h4>
                <ul className="space-y-2">
                  {narrative.actions.map((action, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-gray-600"
                    >
                      <span className="text-blue-500 mt-0.5 flex-shrink-0">
                        {i + 1}.
                      </span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {narrative?.industry_context && (
              <div className="bg-gray-50 rounded-lg p-3">
                <h4 className="text-sm font-semibold text-gray-500 mb-1">
                  บริบทอุตสาหกรรม
                </h4>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {narrative.industry_context}
                </p>
              </div>
            )}

            {narrative?.cta_flag && (
              <div className="text-sm text-blue-600 bg-blue-50 rounded-lg p-3">
                แนะนำ: ปรึกษา Northstar SMEs Health Check สำหรับมิตินี้
              </div>
            )}
          </div>
        );
      })}

      <NorthstarCTA />
    </main>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">กำลังโหลด...</div>}>
      <ReportContent />
    </Suspense>
  );
}
