import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export function Note({
  icon,
  tone = "neutral",
  children,
}: {
  icon: IconName;
  tone?: "neutral" | "warn" | "bad";
  children: ReactNode;
}) {
  const style = {
    neutral: "bg-surface-2 text-muted",
    warn: "bg-warn-soft text-warn",
    bad: "bg-bad-soft text-bad",
  }[tone];
  const iconStyle = tone === "neutral" ? "text-brand" : "";
  return (
    <div className={`flex gap-2.5 rounded-xl px-3.5 py-3 text-[0.84rem] leading-relaxed ${style}`}>
      <Icon name={icon} className={`mt-0.5 ${iconStyle}`} />
      <span>{children}</span>
    </div>
  );
}
