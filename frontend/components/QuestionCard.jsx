"use client";

// Score 0 = lightest red-tinted, 1 = yellow-tinted, 2 = green-light, 3 = green
// Tints are intentionally soft so the user doesn't feel judged while answering
const OPTION_STYLE = [
  // score 0
  "border-risk-red/30   bg-risk-bg-red/40   hover:border-risk-red/60   hover:bg-risk-bg-red/70",
  // score 1
  "border-risk-yellow/30 bg-risk-bg-yellow/30 hover:border-risk-yellow/60 hover:bg-risk-bg-yellow/60",
  // score 2
  "border-risk-green/20  bg-risk-bg-green/20  hover:border-risk-green/50  hover:bg-risk-bg-green/40",
  // score 3
  "border-risk-green/40  bg-risk-bg-green/40  hover:border-risk-green/70  hover:bg-risk-bg-green/60",
];

const SELECTED_STYLE = [
  "border-risk-red    bg-risk-bg-red    ring-2 ring-risk-red/20",
  "border-risk-yellow bg-risk-bg-yellow ring-2 ring-risk-yellow/20",
  "border-risk-green  bg-risk-bg-green  ring-2 ring-risk-green/20",
  "border-risk-green  bg-risk-bg-green  ring-2 ring-risk-green/30",
];

export default function QuestionCard({ question, selectedScore, onSelect }) {
  return (
    <div className="space-y-3">
      <h3 className="text-base font-semibold text-ink leading-relaxed">{question.text}</h3>
      <div className="space-y-2">
        {question.options.map((option, idx) => {
          const isSelected = selectedScore === idx;
          return (
            <button
              key={idx}
              onClick={() => onSelect(idx)}
              className={
                "w-full text-left px-4 py-3.5 rounded-card border-2 transition-all " +
                (isSelected ? SELECTED_STYLE[idx] : OPTION_STYLE[idx])
              }
            >
              <span className="text-sm leading-relaxed text-ink">{option}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
