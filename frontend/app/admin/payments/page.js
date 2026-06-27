"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

const REJECT_REASONS = [
  { code: "WRONG_AMOUNT", label: "ยอดเงินไม่ถูกต้อง" },
  { code: "UNREADABLE", label: "สลิปอ่านไม่ออก" },
  { code: "WRONG_ACCOUNT", label: "โอนผิดบัญชี" },
  { code: "DUPLICATE", label: "สลิปซ้ำกัน" },
  { code: "OTHER", label: "อื่นๆ" },
];

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [filter, setFilter] = useState("pending");
  const [loading, setLoading] = useState(true);

  function getToken() {
    return typeof window !== "undefined"
      ? sessionStorage.getItem("admin_token")
      : "";
  }

  async function fetchPayments() {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/payments?status=${filter}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      const data = await res.json();
      setPayments(Array.isArray(data) ? data : data.payments || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchPayments();
  }, [filter]);

  async function handleApprove(paymentId) {
    await fetch(`${API_URL}/api/v1/admin/payments/${paymentId}/approve`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
      },
    });
    fetchPayments();
  }

  async function handleReject(paymentId, reasonCode, notes = "") {
    await fetch(`${API_URL}/api/v1/admin/payments/${paymentId}/reject`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reason_code: reasonCode, notes }),
    });
    fetchPayments();
  }

  return (
    <main className="min-h-screen px-4 py-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Slip Review Queue</h1>
        <Link
          href="/admin/analytics"
          className="text-sm text-gray-500 hover:text-gray-800 px-4 py-2 border border-gray-200 rounded-xl bg-white"
        >
          Analytics →
        </Link>
      </div>

      <div className="flex gap-2 mb-6">
        {["pending", "verified", "rejected"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === s
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-gray-400">กำลังโหลด...</p>
      ) : payments.length === 0 ? (
        <p className="text-gray-400">ไม่มีรายการ</p>
      ) : (
        <div className="space-y-4">
          {payments.map((p) => (
            <PaymentCard
              key={p.id}
              payment={p}
              onApprove={() => handleApprove(p.id)}
              onReject={(code, notes) => handleReject(p.id, code, notes)}
              showActions={filter === "pending"}
            />
          ))}
        </div>
      )}
    </main>
  );
}

function PaymentCard({ payment, onApprove, onReject, showActions }) {
  const [rejectCode, setRejectCode] = useState("WRONG_AMOUNT");
  const [notes, setNotes] = useState("");

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="font-medium text-gray-900">
            #{payment.id} — {payment.email || "N/A"}
          </div>
          <div className="text-sm text-gray-500">
            {payment.business_name || "ไม่ระบุชื่อ"} | ฿{payment.amount}
          </div>
          <div className="text-xs text-gray-400">{payment.created_at}</div>
        </div>
        <span
          className={`text-xs px-2 py-1 rounded-full ${
            payment.status === "verified"
              ? "bg-green-100 text-green-700"
              : payment.status === "rejected"
              ? "bg-red-100 text-red-700"
              : "bg-amber-100 text-amber-700"
          }`}
        >
          {payment.status}
        </span>
      </div>

      {payment.slip_url && (
        <img
          src={`${API_URL}${payment.slip_url}`}
          alt="Slip"
          className="w-full max-h-64 object-contain rounded-lg border mb-3"
        />
      )}

      {showActions && (
        <div className="space-y-3 border-t pt-3">
          <button
            onClick={onApprove}
            className="w-full py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700"
          >
            Approve
          </button>
          <div className="flex gap-2">
            <select
              value={rejectCode}
              onChange={(e) => setRejectCode(e.target.value)}
              className="flex-1 px-3 py-2 border rounded-lg text-sm"
            >
              {REJECT_REASONS.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => onReject(rejectCode, notes)}
              className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {payment.reject_reason && (
        <div className="text-sm text-red-600 mt-2">
          เหตุผล: {payment.reject_reason}
        </div>
      )}
    </div>
  );
}
