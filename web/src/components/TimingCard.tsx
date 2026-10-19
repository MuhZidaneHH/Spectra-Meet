import { formatTime } from "@/lib/format";
import { T } from "@/lib/teks";
import type { PipelineInfo, TimingsSec } from "@/lib/types";
import { Icon } from "./Icon";

const KEYS: (keyof TimingsSec)[] = ["audio", "vad", "stt", "diarization", "summary"];

function seconds(value: number): string {
  return value < 10 ? `${value.toFixed(1)} dtk` : formatTime(value);
}

/** Rincian lama tiap tahap pipeline, dari progres yang ditulis pipeline. Disembunyikan bila datanya tidak ada. */
export function TimingCard({ pipeline }: { pipeline?: PipelineInfo | null }) {
  const timings = pipeline?.timings_sec;
  if (!timings || KEYS.every((k) => timings[k] === undefined)) return null;

  const total = KEYS.reduce((sum, k) => sum + (timings[k] ?? 0), 0);
  const longest = Math.max(...KEYS.map((k) => timings[k] ?? 0), 0.001);
  const reused = KEYS.some((k) => timings[k] !== undefined && timings[k]! < 0.05);
  const models = T.result.timingsModels(pipeline?.whisper_model ?? "", pipeline?.llm_model ?? "");

  return (
    <section className="mt-3.5 rounded-2xl border border-line bg-surface p-5 shadow-card">
      <h2 className="mb-3 flex items-center gap-2.5 text-[0.78rem] font-extrabold uppercase tracking-[0.07em] text-muted">
        <Icon name="clock" className="text-[1.1em] text-brand" />
        {T.result.timingsTitle}
      </h2>
      <ul className="grid gap-3">
        {KEYS.map((k, i) => {
          const value = timings[k];
          if (value === undefined) return null;
          return (
            <li key={k}>
              <div className="mb-1 flex items-baseline justify-between gap-3 text-[0.86rem]">
                <span className="font-semibold">{T.process.steps[i].title}</span>
                <span className="font-bold tabular-nums">{seconds(value)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                <i className="block h-full rounded-full bg-gradient-to-r from-brand to-cyan" style={{ width: `${Math.max((value / longest) * 100, 1.5)}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
      <div className="mt-3.5 flex justify-between gap-3 border-t border-line pt-3 text-[0.86rem] font-extrabold">
        <span>{T.result.timingsTotal}</span>
        <span className="tabular-nums">{seconds(total)}</span>
      </div>
      {models && <p className="mt-2 text-xs text-muted">{models}</p>}
      {reused && <p className="mt-2 text-xs text-muted">{T.result.timingsReused}</p>}
    </section>
  );
}
