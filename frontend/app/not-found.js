import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-surface flex flex-col items-center justify-center px-6 text-center">
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-pill bg-navy/8 border border-navy/15 text-navy text-xs font-semibold uppercase tracking-widest mb-8">
        <span>★</span>
        <span>Northstar Corporation</span>
      </div>

      <p className="text-6xl font-bold text-navy/20 mb-4">404</p>
      <h1 className="text-xl font-semibold text-ink mb-2">ไม่พบหน้านี้</h1>
      <p className="text-ink-muted text-sm mb-8 max-w-xs">
        URL ที่คุณเข้ามาอาจถูกลบหรือพิมพ์ผิด
      </p>

      <Link
        href="/"
        className="px-6 py-3 bg-navy text-white font-semibold rounded-pill text-sm hover:opacity-90 transition-opacity"
      >
        กลับหน้าแรก
      </Link>
    </main>
  );
}
