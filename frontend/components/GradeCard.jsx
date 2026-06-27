import { GRADE_CONFIG } from "@/lib/constants";

export default function GradeCard({ grade, score }) {
  const config = GRADE_CONFIG[grade] || GRADE_CONFIG.WATCH;
  return (
    <div className={"rounded-card border-2 " + config.border + " " + config.bg + " p-6 text-center shadow-card"}>
      {/* Grade badge */}
      <div className={"inline-flex items-center gap-2 px-3 py-1 rounded-pill text-xs font-semibold uppercase tracking-widest mb-3 " + config.badgeBg + " " + config.color}>
        <span>{config.icon}</span>
        <span>{config.label}</span>
      </div>

      {/* Score */}
      <div className={"text-5xl font-bold tabular-nums " + config.color}>
        {Math.round(score)}
        <span className="text-2xl font-medium opacity-60">%</span>
      </div>

      {/* Thai label */}
      <div className="text-ink-muted text-sm mt-2 leading-relaxed">{config.labelTh}</div>

      {/* Gold accent line */}
      <div className="gold-line mt-4 mx-auto w-24" />
    </div>
  );
}
