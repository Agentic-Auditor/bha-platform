"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { userLogin } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [name, setName]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!email.trim()) { setError("กรุณาใส่อีเมล"); return; }
    setLoading(true);
    try {
      await userLogin(email.trim().toLowerCase(), name.trim());
      router.push("/member");
    } catch (err) {
      setError(err.message || "เกิดข้อผิดพลาด กรุณาลองใหม่");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F8F9FB] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#1B2B4B] mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-[#1B2B4B]">เข้าสู่ระบบสมาชิก</h1>
          <p className="text-sm text-[#6B7280] mt-1">ใช้อีเมลเพื่อเข้าถึงข้อมูลและ Dashboard ของคุณ</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-[#E5E7EB] p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">
                ชื่อ (ไม่บังคับ)
              </label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="ชื่อของคุณ"
                className="w-full border border-[#D1D5DB] rounded-xl px-4 py-3 text-sm
                           text-[#111827] placeholder-[#9CA3AF]
                           focus:outline-none focus:ring-2 focus:ring-[#1B2B4B]/20 focus:border-[#1B2B4B]
                           transition"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">
                อีเมล <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full border border-[#D1D5DB] rounded-xl px-4 py-3 text-sm
                           text-[#111827] placeholder-[#9CA3AF]
                           focus:outline-none focus:ring-2 focus:ring-[#1B2B4B]/20 focus:border-[#1B2B4B]
                           transition"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#1B2B4B] hover:bg-[#243760] text-white font-semibold
                         py-3 rounded-xl transition disabled:opacity-60 text-sm"
            >
              {loading ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบ / สมัครสมาชิก"}
            </button>
          </form>

          <p className="text-xs text-[#9CA3AF] text-center mt-5 leading-relaxed">
            ระบบจะสร้างบัญชีให้อัตโนมัติหากอีเมลนี้ยังไม่เคยลงทะเบียน
            <br />ไม่จำเป็นต้องตั้งรหัสผ่าน
          </p>
        </div>

        {/* Benefits */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          {[
            { icon: "📊", text: "Trend Dashboard" },
            { icon: "🔔", text: "Alert System" },
            { icon: "📄", text: "รายงาน PDF เต็มรูปแบบ" },
          ].map(item => (
            <div key={item.text}
                 className="bg-white rounded-xl border border-[#E5E7EB] p-3 text-center">
              <div className="text-xl mb-1">{item.icon}</div>
              <p className="text-xs text-[#6B7280] leading-tight">{item.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
