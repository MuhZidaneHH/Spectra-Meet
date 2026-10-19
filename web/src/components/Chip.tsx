import type { ReactNode } from "react";

const TONES = {
  neutral: "bg-surface-2 text-muted",
  good: "bg-good-soft text-good",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  brand: "bg-brand-soft text-brand",
} as const;

export type ChipTone = keyof typeof TONES;

export function Chip({ tone = "neutral", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${TONES[tone]}`}>
      {children}
    </span>
  );
}
