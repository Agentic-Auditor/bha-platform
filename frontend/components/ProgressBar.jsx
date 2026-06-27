"use client";

import { DIMENSIONS } from "@/lib/constants";

export default function ProgressBar({ currentDim, questionIndex, totalQuestions }) {
  const dimIndex = DIMENSIONS.findIndex((d) => d.id === currentDim);
  const overall = ((questionIndex + 1) / totalQuestions) * 100;

  return (
    <div className="space-y-2.5">
      {/* dim name + counter */}
      <div className="flex justify-between items-center text-xs">
        <span className="font-semibold text-navy">{DIMENSIONS[dimIndex]?.short || ""}</span>
        <span className="tabular-nums text-ink-muted">
          {questionIndex + 1} / {totalQuestions}
        </span>
      </div>

      {/* main progress bar */}
      <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: overall + "%",
            background: "linear-gradient(90deg, #0B1B4D, #C8963E)",
          }}
        />
      </div>

      {/* dimension segment dots */}
      <div className="flex gap-1">
        {DIMENSIONS.map((d, i) => (
          <div
            key={d.id}
            className={
              "flex-1 h-0.5 rounded-full transition-colors duration-300 " +
              (i < dimIndex
                ? "bg-navy"
                : i === dimIndex
                ? "bg-gold"
                : "bg-gray-200")
            }
          />
        ))}
      </div>
    </div>
  );
}
