"use client";

// step2 was removed in v2.0 — the assessment is now a single 42-question flow.
// Users who arrive here (e.g. old bookmarks) are redirected to /report.

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function Step2Redirect() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");

  useEffect(() => {
    router.replace(id ? `/report?id=${id}` : "/");
  }, [router, id]);

  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-gray-400">กำลังนำไปยังรายงาน...</div>
    </main>
  );
}

export default function Step2Page() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          กำลังโหลด...
        </div>
      }
    >
      <Step2Redirect />
    </Suspense>
  );
}
