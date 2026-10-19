import { T } from "@/lib/teks";

const STEPS = [T.stepper.audio, T.stepper.process, T.stepper.result];

/** Penunjuk langkah 1-3 di atas halaman Audio, Proses, dan Hasil. */
export function Stepper({ current }: { current: 1 | 2 | 3 }) {
  return (
    <ol className="mb-6 flex flex-wrap items-center gap-2 text-[0.82rem] font-bold text-muted">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "on" : "wait";
        const badge = {
          done: "bg-good-soft text-good",
          on: "bg-brand text-brand-fg",
          wait: "bg-surface-2",
        }[state];
        return (
          <li key={label} className="flex items-center gap-2" aria-current={state === "on" ? "step" : undefined}>
            <span className={`inline-flex items-center gap-2 ${state === "on" ? "text-ink" : ""}`}>
              <span className={`grid size-6 place-items-center rounded-full text-xs ${badge}`}>{n}</span>
              {label}
            </span>
            {n < STEPS.length && <span className="h-0.5 w-7 rounded bg-line" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}
