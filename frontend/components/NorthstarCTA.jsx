export default function NorthstarCTA() {
  return (
    <div className="rounded-card bg-navy-gradient text-white p-6 shadow-card">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-8 h-8 rounded-full bg-gold/20 flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-gold text-sm">★</span>
        </div>
        <div>
          <h3 className="font-semibold text-base leading-snug">
            ต้องการที่ปรึกษาผู้เชี่ยวชาญ?
          </h3>
          <p className="text-white/70 text-sm mt-1 leading-relaxed">
            Agentic-Auditor — ตรวจสุขภาพธุรกิจเชิงลึก
            พร้อมแผนปฏิบัติจากผู้เชี่ยวชาญจริง
          </p>
        </div>
      </div>
      <a
        href="https://www.agentic-auditor.com"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block w-full text-center px-6 py-2.5 bg-gold text-white text-sm font-semibold rounded-pill shadow-gold hover:brightness-110 transition-all"
      >
        นัดพูดคุยกับที่ปรึกษา →
      </a>
    </div>
  );
}
