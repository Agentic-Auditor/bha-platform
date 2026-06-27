import TrafficLight from "./TrafficLight";

const LIGHT_BG = {
  RED:    "border-risk-bg-red   bg-risk-bg-red/60",
  YELLOW: "border-risk-bg-yellow bg-risk-bg-yellow/60",
  GREEN:  "border-risk-bg-green  bg-risk-bg-green/30",
};

export default function DimensionCard({ dimension, light, pct, summary, isTopRisk }) {
  const bgClass = isTopRisk
    ? LIGHT_BG[light] || LIGHT_BG.RED
    : "border-gray-100 bg-card";

  return (
    <div className={"rounded-card border p-4 shadow-card transition-shadow hover:shadow-card-hover " + bgClass}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2.5">
          <TrafficLight color={light} size="lg" />
          <span className="font-semibold text-ink text-sm">{dimension.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {isTopRisk && (
            <span className="text-[10px] font-bold uppercase tracking-wider text-risk-red bg-risk-bg-red px-2 py-0.5 rounded-pill">
              ความเสี่ยงสูง
            </span>
          )}
          <span className="text-sm font-semibold tabular-nums text-ink-muted">{Math.round(pct)}%</span>
        </div>
      </div>

      {/* mini progress track */}
      <div className="w-full h-1 bg-gray-100 rounded-full mt-2 mb-2.5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: pct + "%",
            background: light === "GREEN" ? "#16A34A" : light === "YELLOW" ? "#F59E0B" : "#DC2626",
          }}
        />
      </div>

      {summary && (
        <p className="text-xs text-ink-muted leading-relaxed">{summary}</p>
      )}
    </div>
  );
}
