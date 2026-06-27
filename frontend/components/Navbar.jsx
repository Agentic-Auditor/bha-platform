"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "BHA", sublabel: "Business Health Assessment", href: "/" },
  { label: "บริการอื่น", sublabel: "Services", href: "/services" },
  { label: "เกี่ยวกับเรา", sublabel: "About", href: "/about" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  // ซ่อน navbar ในหน้า admin
  if (pathname?.startsWith("/admin")) return null;

  const isActive = (href) => {
    if (href === "/") return pathname === "/" || pathname?.startsWith("/start") || pathname?.startsWith("/assess") || pathname?.startsWith("/dashboard") || pathname?.startsWith("/payment") || pathname?.startsWith("/waiting") || pathname?.startsWith("/loading") || pathname?.startsWith("/report");
    return pathname?.startsWith(href);
  };

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 1000,
      background: "rgba(10, 22, 40, 0.97)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid rgba(212, 175, 55, 0.15)",
    }}>
      <div style={{
        maxWidth: "1200px", margin: "0 auto",
        padding: "0 24px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: "60px",
      }}>

        {/* Logo */}
        <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "32px", height: "32px",
            background: "linear-gradient(135deg, #D4AF37, #F0D060)",
            borderRadius: "6px",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "13px", fontWeight: "800", color: "#0A1628",
            fontFamily: "serif",
          }}>AA</div>
          <div>
            <div style={{ fontSize: "14px", fontWeight: "700", color: "#fff", lineHeight: 1.1 }}>
              Agentic-Auditor
            </div>
            <div style={{ fontSize: "10px", color: "rgba(212,175,55,0.7)", letterSpacing: "0.1em" }}>
              BUSINESS INTELLIGENCE
            </div>
          </div>
        </Link>

        {/* Desktop Tabs */}
        <div style={{ display: "flex", gap: "4px" }} className="nav-desktop">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} style={{ textDecoration: "none" }}>
              <div style={{
                padding: "8px 20px",
                borderRadius: "6px",
                background: isActive(item.href) ? "rgba(212,175,55,0.12)" : "transparent",
                border: isActive(item.href) ? "1px solid rgba(212,175,55,0.3)" : "1px solid transparent",
                cursor: "pointer",
                transition: "all 0.2s",
              }}>
                <div style={{
                  fontSize: "14px", fontWeight: "600",
                  color: isActive(item.href) ? "#D4AF37" : "rgba(255,255,255,0.75)",
                }}>
                  {item.label}
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Mobile Hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="nav-mobile"
          style={{
            background: "none", border: "none", cursor: "pointer",
            color: "#fff", fontSize: "22px", padding: "4px",
          }}
        >
          {menuOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="nav-mobile" style={{
          background: "#0A1628",
          borderTop: "1px solid rgba(255,255,255,0.08)",
          padding: "12px 24px 20px",
        }}>
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} style={{ textDecoration: "none" }}
              onClick={() => setMenuOpen(false)}>
              <div style={{
                padding: "14px 0",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                color: isActive(item.href) ? "#D4AF37" : "rgba(255,255,255,0.8)",
                fontSize: "16px", fontWeight: "600",
              }}>
                {item.label}
                <span style={{ fontSize: "12px", color: "rgba(255,255,255,0.35)", marginLeft: "8px", fontWeight: "400" }}>
                  {item.sublabel}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <style>{`
        .nav-desktop { display: flex; }
        .nav-mobile { display: none; }
        @media (max-width: 640px) {
          .nav-desktop { display: none !important; }
          .nav-mobile { display: block !important; }
        }
      `}</style>
    </nav>
  );
}
