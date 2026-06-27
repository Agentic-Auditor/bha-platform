"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

const BTYPE_LABELS = {
  restaurant:    "ร้านอาหาร",
  retail:        "ค้าปลีก",
  ecommerce:     "ขายออนไลน์",
  brand:         "แบรนด์",
  service:       "บริการ",
  health_beauty: "สุขภาพ/ความงาม",
  oem:           "OEM/โรงงาน",
  startup:       "Startup",
  general:       "ทั่วไป",
};

const GRADE_COLORS = {
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
  WATCH:    "bg-amber-100 text-amber-700 border-amber-200",
  HEALTHY:  "bg-green-100 text-green-700 border-green-200",
  STRONG:   "bg-blue-100 text-blue-700 border-blue-200",
};

const BTYPE_COLORS = [
  "bg-navy/10 text-navy",
  "bg-blue-100 text-blue-700",
  "bg-teal-100 text-teal-700",
  "bg-amber-100 text-amber-700",
  "bg-purple-100 text-purple-700",
  "bg-pink-100 text-pink-700",
  "bg-orange-100 text-orange-700",
  "bg-green-100 text-green-700",
];

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl px-5 py-4">
      <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-3xl font-semibold text-gray-900">{value ?? "—"}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function BarRow({ label, value, max, colorClass, rank }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3 py-2">
      <span className="text-xs text-gray-400 w-4 text-right">{rank}</span>
      <span className="text-sm text-gray-700 w-32 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div
          className="h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: "rgb(15 30 68)" }}
        />
      </div>
      <span className="text-sm font-medium text-gray-700 w-8 text-right">{value}</span>
      <span className={`text-xs px-2 py-0.5 rounded-full border ${colorClass} w-24 text-center`}>
        {pct}%
      </span>
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function getToken() {
    return typeof window !== "undefined"
      ? sessionStorage.getItem("admin_token")
      : "";
  }

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_URL}/api/v1/admin/analytics`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (res.status === 401) {
          setError("Session หมดอายุ — กรุณา login ใหม่");
          setLoading(false);
          return;
        }
        const json = await res.json();
        setData(json);
      } catch {
        setError("ไม่สามารถโหลดข้อมูลได้");
      }
      setLoading(false);
    }
    load();
  }, []);

  const btypeMax = data?.business_type_dist?.[0]?.cnt ?? 1;
  const gradeMax = data?.grade_dist?.[0]?.cnt ?? 1;

  // Sparkline: last 14 days
  const daily = data?.daily_assessments_30d ?? [];
  const recent14 = daily.slice(-14);
  const maxDay = Math.max(...recent14.map((d) => d.cnt), 1);

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">Admin Panel</p>
            <h1 className="text-2xl font-semibold text-gray-900">Analytics</h1>
          </div>
          <div className="flex gap-3">
            <Link
              href="/admin/payments"
              className="text-sm text-gray-500 hover:text-gray-800 px-4 py-2 border border-gray-200 rounded-xl bg-white"
            >
              ← Payments
            </Link>
            <button
              onClick={() => window.location.reload()}
              className="text-sm text-gray-500 hover:text-gray-800 px-4 py-2 border border-gray-200 rounded-xl bg-white"
            >
              รีเฟรช
            </button>
          </div>
        </div>

        {loading && (
          <div className="text-center py-20 text-gray-400">กำลังโหลด...</div>
        )}
        {error && (
          <div className="bg-red-50 text-red-700 rounded-2xl px-5 py-4 text-sm">
            {error}{" "}
            <Link href="/admin" className="underline">
              Login ใหม่
            </Link>
          </div>
        )}

        {data && (
          <>
            {/* Summary cards — assessments */}
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-widest mb-3">แบบประเมิน</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard
                  label="ทั้งหมด"
                  value={data.summary?.total ?? 0}
                />
                <StatCard
                  label="ทำเสร็จสมบูรณ์"
                  value={data.summary?.completed ?? 0}
                  sub={
                    data.summary?.total
                      ? `${Math.round((data.summary.completed / data.summary.total) * 100)}% completion`
                      : ""
                  }
                />
                <StatCard
                  label="ชำระเงินแล้ว"
                  value={data.summary?.paid ?? 0}
                  sub={
                    data.summary?.completed
                      ? `${Math.round((data.summary.paid / data.summary.completed) * 100)}% conversion`
                      : ""
                  }
                />
                <StatCard
                  label="AI Narratives Cached"
                  value={data.narrative_cache?.total_cached ?? 0}
                  sub={`${data.narrative_cache?.total_hits ?? 0} cache hits`}
                />
              </div>
            </div>

            {/* Membership summary */}
            {data.membership && (
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-widest mb-3">Membership</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <StatCard label="ยื่นชำระทั้งหมด" value={data.membership.total ?? 0} />
                  <StatCard
                    label="อนุมัติแล้ว"
                    value={data.membership.approved ?? 0}
                    sub={
                      data.membership.total
                        ? `${Math.round(((data.membership.approved ?? 0) / data.membership.total) * 100)}% approval`
                        : ""
                    }
                  />
                  <StatCard label="รอตรวจสอบ" value={data.membership.pending ?? 0} />
                  <StatCard label="ปฏิเสธ" value={data.membership.rejected ?? 0} />
                </div>
              </div>
            )}

            {/* 2-col layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Business type distribution */}
              <div className="bg-white border border-gray-200 rounded-2xl px-6 py-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-4">
                  ประเภทธุรกิจ
                </h2>
                {data.business_type_dist.length === 0 ? (
                  <p className="text-sm text-gray-400">ยังไม่มีข้อมูล</p>
                ) : (
                  <div className="space-y-1">
                    {data.business_type_dist.map((row, i) => (
                      <BarRow
                        key={row.business_type}
                        rank={i + 1}
                        label={BTYPE_LABELS[row.business_type] ?? row.business_type}
                        value={row.cnt}
                        max={btypeMax}
                        colorClass={BTYPE_COLORS[i % BTYPE_COLORS.length]}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Grade distribution */}
              <div className="bg-white border border-gray-200 rounded-2xl px-6 py-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-4">
                  ผล Grade
                </h2>
                {data.grade_dist.length === 0 ? (
                  <p className="text-sm text-gray-400">ยังไม่มีข้อมูล</p>
                ) : (
                  <div className="space-y-3">
                    {data.grade_dist.map((row) => (
                      <BarRow
                        key={row.grade}
                        rank=""
                        label={row.grade}
                        value={row.cnt}
                        max={gradeMax}
                        colorClass={GRADE_COLORS[row.grade] ?? "bg-gray-100 text-gray-600 border-gray-200"}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Revenue bucket */}
              <div className="bg-white border border-gray-200 rounded-2xl px-6 py-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-4">
                  ยอดขายต่อเดือน (C2)
                </h2>
                {data.revenue_bucket_dist.length === 0 ? (
                  <p className="text-sm text-gray-400">ยังไม่มีข้อมูล</p>
                ) : (
                  <div className="space-y-2">
                    {data.revenue_bucket_dist.map((row, i) => (
                      <BarRow
                        key={row.revenue_bucket}
                        rank=""
                        label={row.revenue_bucket ?? "ไม่ระบุ"}
                        value={row.cnt}
                        max={data.revenue_bucket_dist[0]?.cnt ?? 1}
                        colorClass="bg-gray-100 text-gray-600 border-gray-200"
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Daily trend (last 14 days) */}
              <div className="bg-white border border-gray-200 rounded-2xl px-6 py-5">
                <h2 className="text-sm font-semibold text-gray-700 mb-4">
                  แบบประเมินรายวัน — 14 วันล่าสุด
                </h2>
                {recent14.length === 0 ? (
                  <p className="text-sm text-gray-400">ยังไม่มีข้อมูล</p>
                ) : (
                  <div className="flex items-end gap-1 h-24">
                    {recent14.map((d) => {
                      const h = Math.max(4, Math.round((d.cnt / maxDay) * 80));
                      return (
                        <div
                          key={d.day}
                          className="flex-1 flex flex-col items-center gap-1 group"
                        >
                          <div
                            className="w-full rounded-t"
                            style={{
                              height: `${h}px`,
                              backgroundColor: "rgb(15 30 68)",
                              opacity: 0.8,
                            }}
                            title={`${d.day}: ${d.cnt} assessments`}
                          />
                          <span
                            className="text-gray-300 group-hover:text-gray-500 transition-colors"
                            style={{ fontSize: "9px" }}
                          >
                            {d.day.slice(5)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
                {recent14.length > 0 && (
                  <p className="text-xs text-gray-400 mt-2">
                    รวม {recent14.reduce((s, d) => s + d.cnt, 0)} assessments
                    ใน 14 วัน
                  </p>
                )}
              </div>
            </div>

            {/* Narrative cache detail */}
            <div className="bg-white border border-gray-200 rounded-2xl px-6 py-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                AI Narrative Cache
              </h2>
              <div className="flex flex-wrap gap-6 text-sm">
                <div>
                  <span className="text-gray-400">Cached entries</span>{" "}
                  <span className="font-medium text-gray-800">
                    {data.narrative_cache?.total_cached ?? 0}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Total hits</span>{" "}
                  <span className="font-medium text-gray-800">
                    {data.narrative_cache?.total_hits ?? 0}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Business types cached</span>{" "}
                  <span className="font-medium text-gray-800">
                    {data.narrative_cache?.distinct_btypes ?? 0}
                  </span>
                </div>
                {data.narrative_cache?.total_cached > 0 &&
                  data.narrative_cache?.total_hits > 0 && (
                    <div>
                      <span className="text-gray-400">Avg hits/entry</span>{" "}
                      <span className="font-medium text-gray-800">
                        {(
                          data.narrative_cache.total_hits /
                          data.narrative_cache.total_cached
                        ).toFixed(1)}
                      </span>
                    </div>
                  )}
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
