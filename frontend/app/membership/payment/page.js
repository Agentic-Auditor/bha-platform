"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { getMe, getMembershipPaymentStatus, uploadMembershipSlip } from "@/lib/api";

const PROMPTPAY_NUMBER = "0812345678"; // TODO: เปลี่ยนเป็นเบอร์จริงของธุรกิจ
const AMOUNT_THB = 890;

// Simple PromptPay QR placeholder (in production use a real QR lib)
function QRCodeBox({ amount, phone }) {
  return (
    <div className="flex flex-col items-center gap-3">
      {/* QR Placeholder — replace with actual QR code image or library */}
      <div className="w-48 h-48 bg-white border-2 border-[#1B2B4B] rounded-2xl flex items-center justify-center relative overflow-hidden">
        {/* Simulated QR pattern */}
        <div className="grid grid-cols-7 gap-0.5 opacity-80 scale-90">
          {Array.from({ length: 49 }).map((_, i) => {
            const isCorner = [0,1,6,7,13,14,35,36,42,43,48].includes(i);
            const isFill   = Math.random() > 0.55 || isCorner;
            return (
              <div key={i}
                   className={`w-4 h-4 rounded-sm ${isFill ? "bg-[#1B2B4B]" : "bg-transparent"}`} />
            );
          })}
        </div>
        {/* PromptPay logo overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-10 h-10 bg-white rounded-full border border-[#E5E7EB] flex items-center justify-center shadow">
            <span className="text-xs font-bold text-[#1B2B4B]">PP</span>
          </div>
        </div>
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-[#374151]">PromptPay</p>
        <p className="text-xs text-[#6B7280]">{phone}</p>
        <p className="text-xl font-bold text-[#1B2B4B] mt-1">฿{amount.toLocaleString()}</p>
      </div>
    </div>
  );
}

const STATUS_MAP = {
  pending:  { label: "รอการตรวจสอบ",  color: "bg-yellow-100 text-yellow-700" },
  verified: { label: "อนุมัติแล้ว",   color: "bg-green-100 text-green-700"  },
  rejected: { label: "ปฏิเสธ",        color: "bg-red-100 text-red-700"      },
};

export default function MembershipPaymentPage() {
  const router = useRouter();
  const fileRef = useRef(null);

  const [user,        setUser]        = useState(null);
  const [payStatus,   setPayStatus]   = useState(null);
  const [file,        setFile]        = useState(null);
  const [preview,     setPreview]     = useState(null);
  const [uploading,   setUploading]   = useState(false);
  const [uploaded,    setUploaded]    = useState(false);
  const [error,       setError]       = useState("");
  const [loading,     setLoading]     = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [me, ps] = await Promise.all([getMe(), getMembershipPaymentStatus()]);
        setUser(me);
        setPayStatus(ps.payment);

        // Already a member — redirect to dashboard
        if (me.is_active_member) {
          router.push("/member");
        }
      } catch (err) {
        if (err.message?.includes("Unauthorized")) {
          router.push("/login");
        } else {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function handleFileChange(e) {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError("");
  }

  function handleDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError("");
  }

  async function handleUpload() {
    if (!file) { setError("กรุณาเลือกไฟล์สลิป"); return; }
    setUploading(true);
    setError("");
    try {
      await uploadMembershipSlip(file);
      setUploaded(true);
      // Refresh payment status
      const ps = await getMembershipPaymentStatus();
      setPayStatus(ps.payment);
    } catch (err) {
      setError(err.message || "อัปโหลดไม่สำเร็จ กรุณาลองใหม่");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FB] flex items-center justify-center">
        <p className="text-[#6B7280] text-sm">กำลังโหลด...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FB]">
      {/* Header */}
      <header className="bg-white border-b border-[#E5E7EB]">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <a href="/member" className="text-[#6B7280] hover:text-[#1B2B4B] transition">
            ← กลับ
          </a>
          <h1 className="text-base font-semibold text-[#111827]">สมัครสมาชิก</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">

        {/* Existing pending payment */}
        {payStatus && payStatus.status !== "rejected" && !uploaded && (
          <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6">
            <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium mb-3
                            ${STATUS_MAP[payStatus.status]?.color}`}>
              {STATUS_MAP[payStatus.status]?.label}
            </div>
            <p className="text-sm text-[#374151]">
              {payStatus.status === "pending"
                ? "เราได้รับสลิปของคุณแล้ว และกำลังตรวจสอบ โดยปกติใช้เวลาไม่เกิน 24 ชั่วโมง"
                : "การชำระเงินได้รับการยืนยันแล้ว กรุณารีเฟรชหน้า"}
            </p>
            {payStatus.status === "verified" && (
              <a href="/member"
                 className="inline-block mt-3 bg-[#1B2B4B] text-white text-sm font-semibold
                            px-5 py-2.5 rounded-xl hover:bg-[#243760] transition">
                ไปยัง Dashboard
              </a>
            )}
          </div>
        )}

        {/* Payment instructions */}
        {(!payStatus || payStatus.status === "rejected" || uploaded) && !uploaded && (
          <>
            {/* Benefits */}
            <div className="bg-gradient-to-br from-[#1B2B4B] to-[#2D4270] rounded-2xl p-6 text-white">
              <h2 className="text-lg font-bold mb-1">BHA สมาชิก 1 ปี</h2>
              <p className="text-3xl font-bold mb-4">฿890 <span className="text-base font-normal text-white/60">/ปี</span></p>
              <div className="space-y-2">
                {[
                  "📊 Trend Dashboard — ดูแนวโน้มทั้ง 7 มิติ",
                  "🔔 Alert System — แจ้งเตือนมิติที่แย่ลง",
                  "📄 รายงาน PDF เต็มรูปแบบไม่จำกัด",
                  "💬 รายงาน AI วิเคราะห์เชิงลึกทุกครั้ง",
                ].map(b => (
                  <div key={b} className="flex items-start gap-2 text-sm text-white/80">
                    <span>{b.split(" ")[0]}</span>
                    <span>{b.split(" ").slice(1).join(" ")}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* QR Code */}
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6">
              <h3 className="font-semibold text-[#111827] mb-4">ชำระผ่าน PromptPay</h3>
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <QRCodeBox amount={AMOUNT_THB} phone={PROMPTPAY_NUMBER} />
                <div className="space-y-3 text-sm text-[#374151] flex-1">
                  <div className="flex justify-between">
                    <span className="text-[#6B7280]">จำนวนเงิน</span>
                    <span className="font-semibold text-[#1B2B4B]">฿{AMOUNT_THB.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7280]">เบอร์ PromptPay</span>
                    <span className="font-semibold">{PROMPTPAY_NUMBER}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7280]">ระยะเวลา</span>
                    <span className="font-semibold">1 ปี</span>
                  </div>
                  <hr className="border-[#F3F4F6]" />
                  <ol className="list-decimal list-inside space-y-1 text-[#6B7280] text-xs">
                    <li>เปิดแอปธนาคารของคุณ</li>
                    <li>สแกน QR หรือโอนผ่านเบอร์ PromptPay</li>
                    <li>โอนจำนวน ฿{AMOUNT_THB}</li>
                    <li>บันทึกสลิป และอัปโหลดด้านล่าง</li>
                  </ol>
                </div>
              </div>
            </div>

            {/* Slip upload */}
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6">
              <h3 className="font-semibold text-[#111827] mb-4">อัปโหลดสลิปการโอนเงิน</h3>

              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={e => e.preventDefault()}
                onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-[#D1D5DB] rounded-xl p-6
                           flex flex-col items-center justify-center gap-2
                           cursor-pointer hover:border-[#1B2B4B] hover:bg-[#F8F9FF]
                           transition text-center"
              >
                {preview ? (
                  <img src={preview} alt="slip preview"
                       className="max-h-48 rounded-lg object-contain" />
                ) : (
                  <>
                    <div className="text-3xl">📎</div>
                    <p className="text-sm font-medium text-[#374151]">คลิกหรือลากไฟล์สลิปมาวางที่นี่</p>
                    <p className="text-xs text-[#9CA3AF]">PNG, JPG, WEBP — ขนาดไม่เกิน 5MB</p>
                  </>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>

              {file && (
                <p className="text-xs text-[#6B7280] mt-2">ไฟล์: {file.name}</p>
              )}

              {error && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mt-3">
                  {error}
                </p>
              )}

              {payStatus?.status === "rejected" && (
                <div className="mt-3 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                  <p className="text-sm text-red-700 font-medium">สลิปก่อนหน้าถูกปฏิเสธ</p>
                  {payStatus.reject_reason && (
                    <p className="text-xs text-red-600 mt-0.5">เหตุผล: {payStatus.reject_reason}</p>
                  )}
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={uploading || !file}
                className="w-full mt-4 bg-[#1B2B4B] hover:bg-[#243760] text-white font-semibold
                           py-3 rounded-xl transition disabled:opacity-60 text-sm"
              >
                {uploading ? "กำลังอัปโหลด..." : "ส่งสลิป"}
              </button>
            </div>
          </>
        )}

        {/* Success state */}
        {uploaded && (
          <div className="bg-white rounded-2xl border border-green-200 p-8 text-center">
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-lg font-bold text-[#111827] mb-2">ส่งสลิปสำเร็จ!</h2>
            <p className="text-sm text-[#6B7280] mb-5 max-w-sm mx-auto">
              เราจะตรวจสอบและเปิดใช้งานบัญชีสมาชิกของคุณภายใน 24 ชั่วโมง
              คุณจะได้รับการแจ้งเตือนทางอีเมล
            </p>
            <a href="/member"
               className="inline-block bg-[#1B2B4B] text-white text-sm font-semibold
                          px-6 py-3 rounded-xl hover:bg-[#243760] transition">
              กลับไปยัง Dashboard
            </a>
          </div>
        )}
      </main>
    </div>
  );
}
