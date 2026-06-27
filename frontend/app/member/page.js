"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getMe, getTrend, getAlerts, userLogout } from "@/lib/api";

const DIM_LABELS = {
  d1_pct: "กลยุทธ์",
  d2_pct: "ลูกค้า",
  d3_pct: "การดำเนินงาน",
  d4_pct: "การเงิน",
  d5_pct: "ทีม",
  d6_pct: "นวัตกรรม",
  d7_pct: "ธรรมาภิบาล",
};

const LIGHT_COLOR = {
  GREEN:  { bg: "#DCFCE7", text: "#15803D", dot: "#22C55E" },
  YELLOW: { bg: "#FEF9C3", text: "#854D0E", dot: "#EAB308" },
  RED:    { bg: "#FEE2E2", text: "#991B1B", dot: "#EF4444" },
};

function TrafficDot({ light }) {
  const c = LIGHT_COLOR[light] || LIGHT_COLOR.GREEN;
  return (
    <span className="inline-block w-2.5 h-2.5 rounded-full mr-1"
          style={{ background: c.dot }} />
  );
}

function MiniBar({ pct, light }) {
  const c = LIGHT_COLOR[light] || LIGHT_COLOR.GREEN;
  return (
    <div className="w-full h-1.5 bg-[#F3F4F6] rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all"
           style={{ width: `${pct}%`, background: c.dot }} />
    </div>
  );
}

// Simple inline trend sparkline (SVG)
function Sparkline({ data, color = "#1B2B4B" }) {
  if (!data || data.length < 2) return null;
  const w = 120, h = 36;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round" />
      {data.map((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = h - ((v - min) / range) * (h - 4) - 2;
        return <circle key={i} cx={x} cy={y} r="3" fill={color} />;
      })}
    </svg>
  );
}

export default function MemberPage() {
  const router = useRouter();
  const [user, setUser]     = useState(null);
  const [trend, setTrend]   = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    async function load() {
      try {
        const me = await getMe();
        setUser(me);
        if (me.is_active_member) {
          const [t, a] = await Promise.all([getTrend(), getAlerts()]);
          setTrend(t);
          setAlerts(a);
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

  async function handleLogout() {
    await userLogout().catch(() => {});
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FB] flex items-center justify-center">
        <p className="text-[#6B7280] text-sm">กำลังโหลด...</p>
      </div>
    );
  }

  if (!user) return null;

  const assessments = trend?.assessments || [];
  const isMember    = user.is_active_member;

  // Build per-dimension trend arrays from newest→oldest (reverse for chart)
  const dimKeys = Object.keys(DIM_LABELS);
  const dimTrends = {};
  dimKeys.forEach(k => {
    dimTrends[k] = [...assessments].reverse().map(a => +(a[k] || 0).toFixed(1));
  });

  const latestAssessment = assessments[0] || null;

  return (
    <div className="min-h-screen bg-[#F8F9FB]">
      {/* Header */}
      <header className="bg-white border-b border-[#E5E7EB] sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#1B2B4B] flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                  stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-[#111827]">
                {user.name || user.email}
              </p>
              <p className="text-xs text-[#6B7280]">
                {isMember
                  ? `สมาชิก · หมดอายุ ${new Date(user.membership_expires_at).toLocaleDateString("th-TH")}`
                  : "ผู้ใช้งานทั่วไป"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a href="/" className="text-xs text-[#6B7280] hover:text-[#1B2B4B] transition px-3 py-1.5">
              ทำแบบประเมินใหม่
            </a>
            <button onClick={handleLogout}
                    className="text-xs text-[#6B7280] hover:text-[#1B2B4B] border border-[#E5E7EB]
                               rounded-lg px-3 py-1.5 transition">
              ออกจากระบบ
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Upgrade CTA if not member */}
        {!isMember && (
          <div className="bg-gradient-to-r from-[#1B2B4B] to-[#2D4270] rounded-2xl p-6 mb-8 text-white">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold mb-1">ยกระดับเป็นสมาชิก</h2>
                <p className="text-sm text-white/70 mb-4 max-w-md">
                  เพื่อดู Trend Dashboard, Alert System, และรายงาน PDF เต็มรูปแบบ
                  เพียง <strong className="text-white">890 บาท/ปี</strong>
                </p>
                <a href="/membership/payment"
                   className="inline-block bg-white text-[#1B2B4B] font-semibold text-sm
                              px-5 py-2.5 rounded-xl hover:bg-white/90 transition">
                  สมัครสมาชิก 890 ฿/ปี
                </a>
              </div>
              <div className="text-4xl">🚀</div>
            </div>
          </div>
        )}

        {/* Alerts */}
        {isMember && alerts?.alerts?.length > 0 && (
          <div className="mb-6">
            <h2 className="text-base font-semibold text-[#111827] mb-3 flex items-center gap-2">
              <span className="text-red-500">⚠️</span> แจ้งเตือนมิติที่แย่ลง
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {alerts.alerts.map(alert => (
                <div key={alert.dimension}
                     className="bg-white border border-[#FCA5A5] rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm text-[#111827]">{alert.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                      ${alert.severity === "high"
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700"}`}>
                      {alert.severity === "high" ? "สำคัญมาก" : "ควรระวัง"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-[#6B7280]">
                    <div className="flex items-center gap-1">
                      <TrafficDot light={alert.prev_light} />
                      {alert.prev_pct}%
                    </div>
                    <span>→</span>
                    <div className="flex items-center gap-1">
                      <TrafficDot light={alert.cur_light} />
                      {alert.cur_pct}%
                    </div>
                    <span className="text-red-600 font-medium">▼ {alert.drop}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Latest snapshot */}
        {latestAssessment && (
          <div className="mb-6">
            <h2 className="text-base font-semibold text-[#111827] mb-3">
              ผลการประเมินล่าสุด
            </h2>
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm text-[#6B7280]">
                    {new Date(latestAssessment.created_at).toLocaleDateString("th-TH", {
                      year: "numeric", month: "long", day: "numeric"
                    })}
                  </p>
                  <p className="font-semibold text-[#111827]">
                    คะแนนรวม {latestAssessment.overall_score?.toFixed(0)}%
                  </p>
                </div>
                <span className="text-2xl font-bold text-[#1B2B4B]">
                  {latestAssessment.overall_grade}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {dimKeys.map(k => {
                  const lightKey = k.replace("_pct", "_light");
                  const light = latestAssessment[lightKey] || "GREEN";
                  const pct   = +(latestAssessment[k] || 0).toFixed(0);
                  const c     = LIGHT_COLOR[light];
                  return (
                    <div key={k} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[#6B7280]">{DIM_LABELS[k]}</span>
                        <span className="text-xs font-medium" style={{ color: c.text }}>
                          {pct}%
                        </span>
                      </div>
                      <MiniBar pct={pct} light={light} />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Trend chart (member only) */}
        {isMember && assessments.length >= 2 && (
          <div className="mb-6">
            <h2 className="text-base font-semibold text-[#111827] mb-3">
              แนวโน้มทั้ง 7 มิติ ({assessments.length} ครั้ง)
            </h2>
            <div className="bg-white rounded-2xl border border-[#E5E7EB] p-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                {dimKeys.map((k, idx) => {
                  const data = dimTrends[k];
                  const latest = data[data.length - 1];
                  const prev   = data[data.length - 2];
                  const delta  = latest - prev;
                  const lightKey = k.replace("_pct", "_light");
                  const light = latestAssessment?.[lightKey] || "GREEN";
                  const c = LIGHT_COLOR[light];
                  const lineColor = c.dot;
                  return (
                    <div key={k} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-[#374151]">
                          {DIM_LABELS[k]}
                        </span>
                        <span className={`text-xs font-semibold ${delta >= 0 ? "text-green-600" : "text-red-500"}`}>
                          {delta >= 0 ? "+" : ""}{delta.toFixed(0)}%
                        </span>
                      </div>
                      <Sparkline data={data} color={lineColor} />
                      <p className="text-xs text-[#6B7280]">
                        ล่าสุด <strong style={{ color: c.text }}>{latest}%</strong>
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* X-axis labels */}
              {assessments.length > 0 && (
                <div className="mt-4 pt-4 border-t border-[#F3F4F6]">
                  <p className="text-xs text-[#9CA3AF]">
                    ประเมินครั้งแรก:{" "}
                    {new Date(assessments[assessments.length - 1]?.created_at)
                      .toLocaleDateString("th-TH")}
                    {" "}→ ล่าสุด:{" "}
                    {new Date(assessments[0]?.created_at).toLocaleDateString("th-TH")}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* History list */}
        {assessments.length > 0 && (
          <div>
            <h2 className="text-base font-semibold text-[#111827] mb-3">
              ประวัติการประเมิน
            </h2>
            <div className="bg-white rounded-2xl border border-[#E5E7EB] overflow-hidden">
              {assessments.map((a, i) => {
                const lightKey = "d1_light"; // just for color indicator
                return (
                  <div key={a.id}
                       className={`flex items-center justify-between px-5 py-4
                                   ${i < assessments.length - 1 ? "border-b border-[#F3F4F6]" : ""}`}>
                    <div>
                      <p className="text-sm font-medium text-[#111827]">
                        ครั้งที่ {assessments.length - i}
                      </p>
                      <p className="text-xs text-[#6B7280]">
                        {new Date(a.created_at).toLocaleDateString("th-TH", {
                          year: "numeric", month: "short", day: "numeric"
                        })}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-[#1B2B4B]">
                        {a.overall_score?.toFixed(0)}%
                      </span>
                      <span className="text-sm font-bold text-[#374151]">{a.overall_grade}</span>
                      {a.red_flag_count > 0 && (
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                          {a.red_flag_count} RED
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty state */}
        {assessments.length === 0 && (
          <div className="text-center py-16">
            <p className="text-4xl mb-4">📊</p>
            <p className="text-[#374151] font-medium mb-2">ยังไม่มีข้อมูลการประเมิน</p>
            <p className="text-sm text-[#6B7280] mb-5">ทำแบบประเมินธุรกิจครั้งแรกของคุณ</p>
            <a href="/"
               className="inline-block bg-[#1B2B4B] text-white text-sm font-semibold
                          px-6 py-3 rounded-xl hover:bg-[#243760] transition">
              เริ่มประเมินธุรกิจ
            </a>
          </div>
        )}

        {error && (
          <p className="text-sm text-red-600 mt-4">{error}</p>
        )}
      </main>
    </div>
  );
}
