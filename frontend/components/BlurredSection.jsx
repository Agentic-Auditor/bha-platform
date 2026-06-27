"use client";

export default function BlurredSection({ children, onUnlock }) {
  return (
    <div className="relative rounded-card overflow-hidden shadow-card">
      {/* blurred preview */}
      <div className="filter blur-sm pointer-events-none select-none p-5 bg-surface">
        {children || (
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded w-full" />
            <div className="h-4 bg-gray-200 rounded w-4/5" />
            <div className="h-4 bg-gray-200 rounded w-3/5" />
            <div className="h-3 bg-gray-100 rounded w-2/3 mt-4" />
            <div className="h-3 bg-gray-100 rounded w-1/2" />
            <div className="h-3 bg-gray-100 rounded w-3/4" />
          </div>
        )}
      </div>

      {/* lock overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/70 backdrop-blur-sm px-6">
        {/* lock icon ring */}
        <div className="w-12 h-12 rounded-full bg-navy/5 border border-navy/10 flex items-center justify-center mb-3">
          <span className="text-xl">🔒</span>
        </div>
        <p className="text-sm font-semibold text-navy mb-1">รายงานฉบับเต็ม</p>
        <p className="text-xs text-ink-muted text-center leading-relaxed mb-3">
          Root Cause · แผนปฏิบัติรายมิติ · KPI Benchmark
          <br />AI วิเคราะห์เฉพาะประเภทธุรกิจของคุณ
        </p>
        {onUnlock && (
          <button
            onClick={onUnlock}
            className="px-7 py-2.5 bg-gold text-white text-sm font-semibold rounded-pill shadow-gold hover:brightness-110 transition-all"
          >
            ปลดล็อคเลย — ฿499
          </button>
        )}
        <p className="text-xs text-ink-faint mt-2">ชำระครั้งเดียว · ได้รับ PDF ทางอีเมล</p>
      </div>
    </div>
  );
}
