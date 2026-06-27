// Soft traffic-light dot — consultative, not alarming
const CONFIG = {
  RED:    { dot: "bg-risk-red",    ring: "ring-risk-red/30",    label: "วิกฤต" },
  YELLOW: { dot: "bg-risk-yellow", ring: "ring-risk-yellow/30", label: "ต้องระวัง" },
  GREEN:  { dot: "bg-risk-green",  ring: "ring-risk-green/30",  label: "สุขภาพดี" },
};

const SIZE = {
  sm: "w-2.5 h-2.5",
  md: "w-3.5 h-3.5",
  lg: "w-4 h-4",
};

export default function TrafficLight({ color, size = "md" }) {
  const c = CONFIG[color] || CONFIG.RED;
  return (
    <span
      className={`inline-block flex-shrink-0 ${SIZE[size]} rounded-full ${c.dot} ring-2 ${c.ring}`}
      title={c.label}
      aria-label={c.label}
    />
  );
}
