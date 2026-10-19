import { T } from "@/lib/teks";
import { Icon } from "./Icon";

/** Kesimpulan rekaman: hanya ringkasan. */
export function SummaryCard({ summary }: { summary: string }) {
  const paragraphs = summary
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <h2 className="mb-3 flex items-center gap-2.5 text-[0.78rem] font-extrabold uppercase tracking-[0.07em] text-muted">
        <Icon name="sparkle" className="text-[1.1em] text-brand" />
        {T.result.summaryTitle}
      </h2>
      {paragraphs.length === 0 ? (
        <p className="text-sm text-muted">{T.result.noSummary}</p>
      ) : (
        <div className="grid gap-3 text-[0.95rem] leading-relaxed">
          {paragraphs.map((p, i) => (
            <p key={i} className="whitespace-pre-line">
              {p}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
