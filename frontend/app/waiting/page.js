"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getPaymentStatus } from "@/lib/api";

function WaitingContent() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");
  const pid = params.get("pid");

  const [status, setStatus] = useState("pending");
  const [rejectReason, setRejectReason] = useState(null);

  useEffect(() => {
    if (!pid) return;
    const interval = setInterval(async () => {
      try {
        const data = await getPaymentStatus(id, pid);
        if (data.status === "verified") {
          clearInterval(interval);
          setStatus("verified");
          router.push(`/report?id=${id}`);
        } else if (data.status === "rejected") {
          clearInterval(interval);
          setStatus("rejected");
          setRejectReason(data.reject_reason);
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [pid, id, router]);

  if (status === "rejected") {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div className="max-w-md w-full text-center space-y-4">
          <div className="text-5xl">❌</div>
          <h1 className="text-2xl font-bold text-gray-900">
            สลิปไม่ผ่านการตรวจสอบ
          </h1>
          <p className="text-gray-600">{rejectReason}</p>
          <button
            onClick={() => router.push(`/payment?id=${id}`)}
            className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700"
          >
            อัปโหลดสลิปใหม่
          </button>
        </div>
      </main>
    );
  }

  function copyLink() {
    try { navigator.clipboard.writeText(window.location.href); } catch (_) {}
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 bg-surface">
      <div className="max-w-md w-full text-center space-y-5">
        {/* spinner */}
        <div className="relative w-16 h-16 mx-auto">
          <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
          <div className="absolute inset-0 rounded-full border-4 border-navy border-t-transparent animate-spin" />
        </div>

        <div>
          <h1 className="text-xl font-semibold text-ink mb-1">กำลังตรวจสอบสลิป</h1>
          <p className="text-sm text-ink-muted">
            ทีมงานจะตรวจสอบภายใน 30 นาที<br />
            คุณจะได้รับ <strong>อีเมลพร้อมรายงาน PDF</strong> ทันทีที่อนุมัติ
          </p>
        </div>

        {/* Action strip */}
        <div className="bg-card rounded-card border border-gray-100 shadow-card px-5 py-4 space-y-3 text-left">
          <p className="text-xs font-semibold text-navy uppercase tracking-wider">ปิด tab ได้เลย ✓</p>
          <p className="text-sm text-ink-muted leading-relaxed">
            ไม่ต้องรอหน้านี้ — รายงานจะส่งไปที่อีเมลที่ลงทะเบียนไว้โดยอัตโนมัติ
          </p>
          <button
            onClick={copyLink}
            className="w-full text-xs text-ink-muted border border-gray-200 rounded-pill py-2 hover:bg-gray-50 transition-colors"
          >
            📋 คัดลอก link หน้านี้ (สำรองไว้ตรวจสถานะ)
          </button>
        </div>

        <p className="text-xs text-ink-faint">
          หน้านี้อัปเดตอัตโนมัติทุก 10 วินาที
        </p>
      </div>
    </main>
  );
}

export default function WaitingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">กำลังโหลด...</div>}>
      <WaitingContent />
    </Suspense>
  );
}
