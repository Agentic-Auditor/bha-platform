"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function LoadingAnimation() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");

  useEffect(() => {
    const timer = setTimeout(() => {
      router.push(`/dashboard?id=${id}`);
    }, 2500);
    return () => clearTimeout(timer);
  }, [router, id]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="text-center space-y-6">
        <div className="relative w-20 h-20 mx-auto">
          <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
          <div className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            กำลังวิเคราะห์ผลลัพธ์
          </h2>
          <p className="text-gray-500 mt-2">
            ระบบกำลังประมวลผลคำตอบของคุณ...
          </p>
        </div>
      </div>
    </main>
  );
}

export default function LoadingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">กำลังโหลด...</div>}>
      <LoadingAnimation />
    </Suspense>
  );
}
