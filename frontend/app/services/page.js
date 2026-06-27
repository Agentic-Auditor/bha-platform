export const metadata = { title: "บริการอื่น | Agentic-Auditor" };

export default function ServicesPage() {
  return (
    <div style={{
      minHeight: "100vh", background: "#0A1628",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "var(--font-noto-thai), sans-serif",
    }}>
      <div style={{ textAlign: "center", padding: "40px" }}>
        <div style={{
          width: "56px", height: "56px", margin: "0 auto 24px",
          background: "linear-gradient(135deg, #D4AF37, #F0D060)",
          borderRadius: "12px",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "22px", fontWeight: "800", color: "#0A1628",
        }}>AA</div>
        <h1 style={{ fontSize: "32px", fontWeight: "700", color: "#fff", marginBottom: "12px" }}>
          บริการอื่นๆ
        </h1>
        <p style={{ fontSize: "18px", color: "rgba(255,255,255,0.5)", marginBottom: "32px" }}>
          กำลังพัฒนาบริการเพิ่มเติม — เร็วๆ นี้
        </p>
        <a href="/" style={{
          display: "inline-block",
          background: "rgba(212,175,55,0.12)",
          border: "1px solid rgba(212,175,55,0.3)",
          color: "#D4AF37", padding: "12px 32px",
          borderRadius: "6px", textDecoration: "none",
          fontSize: "15px", fontWeight: "600",
        }}>
          ← กลับหน้าหลัก
        </a>
      </div>
    </div>
  );
}
