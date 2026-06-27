"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { uploadSlip } from "@/lib/api";

const PROMPTPAY_NUMBER =
  process.env.NEXT_PUBLIC_PROMPTPAY_NUMBER || "XXX-XXX-7890";
const PROMPTPAY_NAME =
  process.env.NEXT_PUBLIC_PROMPTPAY_NAME || "Northstar Corporation";
// QR image: place file at frontend/public/promptpay-qr.png
const QR_IMAGE = "/promptpay-qr.png";
const PRICE = "499";

function PaymentContent() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  function handleFile(e) {
    const f = e.target.files[0];
    if (!f) return;
    // Basic size guard — 5 MB max
    if (f.size > 5 * 1024 * 1024) {
      setError("ไฟล์ใหญ่เกินไป (สูงสุด 5 MB)");
      return;
    }
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const data = await uploadSlip(id, file);
      router.push(`/waiting?id=${id}&pid=${data.payment_id}`);
    } catch (err) {
      setError("อัปโหลดไม่สำเร็จ: " + err.message);
      setUploading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-8">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            ปลดล็อครายงานฉบับเต็ม
          </h1>
          <p className="text-gray-500 mt-1">
            ชำระเงิน ฿{PRICE} ผ่าน PromptPay แล้วอัปโหลดสลิป
          </p>
        </div>

        {/* PromptPay box */}
        <div className="bg-white border-2 border-gray-200 rounded-2xl overflow-hidden">
          {/* QR Code — file lives at frontend/public/promptpay-qr.png */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 flex flex-col items-center justify-center py-8 gap-2">
            <img
              src={QR_IMAGE}
              alt="PromptPay QR Code"
              className="w-52 h-52 object-contain rounded-xl bg-white p-2 shadow-sm"
              onError={(e) => {
                // Fallback if image not found
                e.currentTarget.style.display = "none";
                e.currentTarget.nextSibling.style.display = "flex";
              }}
            />
            {/* Fallback placeholder (hidden when QR loads) */}
            <div
              style={{ display: "none" }}
              className="w-52 h-52 bg-white rounded-xl border-2 border-dashed border-gray-300 items-center justify-center flex-col gap-2"
            >
              <span className="text-4xl">📱</span>
              <p className="text-xs text-gray-400 text-center px-4">
                วาง promptpay-qr.png<br />ใน frontend/public/
              </p>
            </div>
          </div>

          <div className="px-6 py-4 space-y-1 border-t border-gray-100 bg-gray-50">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">ชื่อบัญชี</span>
              <span className="font-medium text-gray-900">{PROMPTPAY_NAME}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">เบอร์ PromptPay</span>
              <span className="font-medium text-gray-900 tracking-wide">
                {PROMPTPAY_NUMBER}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">ยอดชำระ</span>
              <span className="font-bold text-blue-600 text-base">
                ฿{PRICE}
              </span>
            </div>
          </div>
        </div>

        {/* Slip upload */}
        <div className="space-y-3">
          <label className="block w-full py-4 px-4 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-blue-400 transition-colors text-center">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/heic"
              onChange={handleFile}
              className="hidden"
            />
            <span className="text-sm text-gray-500">
              {file ? (
                <span className="text-blue-600 font-medium">{file.name}</span>
              ) : (
                <>
                  <span className="text-2xl block mb-1">📎</span>
                  คลิกเพื่อเลือกรูปสลิป (JPG / PNG / HEIC)
                </>
              )}
            </span>
          </label>

          {preview && (
            <img
              src={preview}
              alt="Slip preview"
              className="w-full max-h-52 object-contain rounded-xl border"
            />
          )}

          {error && (
            <p className="text-sm text-red-600 text-center">{error}</p>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {uploading ? "กำลังอัปโหลด..." : "อัปโหลดสลิป"}
          </button>

          <p className="text-center text-xs text-gray-400">
            ทีมงานจะตรวจสอบสลิปภายใน 30 นาที
            <br />
            คุณจะได้รับแจ้งทางอีเมลเมื่อตรวจสอบเสร็จ
          </p>

          <p className="text-center text-xs text-gray-400">
            การชำระเงินถือว่ายอมรับ{" "}
            <Link href="/terms" className="underline hover:text-gray-600">เงื่อนไขการใช้บริการ</Link>
            {" "}และ{" "}
            <Link href="/privacy" className="underline hover:text-gray-600">นโยบายความเป็นส่วนตัว</Link>
          </p>
        </div>
      </div>
    </main>
  );
}

export default function PaymentPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          กำลังโหลด...
        </div>
      }
    >
      <PaymentContent />
    </Suspense>
  );
}
