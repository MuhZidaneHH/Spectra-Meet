import { T } from "@/lib/teks";
import type { StepState } from "@/lib/types";

const CIRCLE: Record<StepState, string> = {
  waiting: "bg-surface-2 text-muted",
  running: "bg-brand text-brand-fg shadow-[0_0_0_6px_color-mix(in_srgb,var(--brand)_20%,transparent)]",
  done: "bg-good-soft text-good",
  failed: "bg-bad-soft text-bad",
};

const CHIP: Record<StepState, string> = {
  waiting: "",
  running: "bg-brand-soft text-brand",
  done: "bg-good-soft text-good",
  failed: "bg-bad-soft text-bad",
};

const CHIP_TEXT: Record<StepState, string> = {
  waiting: "",
  running: T.process.stepRunning,
  done: T.process.stepDone,
  failed: T.process.stepFailed,
};

function asState(value: string): StepState {
  return value === "running" || value === "done" || value === "failed" ? value : "waiting";
}

/** Lima langkah pipeline dengan status masing-masing. `steps` datang dari progres API. */
export function StepList({ steps }: { steps: string[] }) {
  return (
    <ol className="my-4 grid">
      {T.process.steps.map((step, i) => {
        const state = asState(steps[i] ?? "waiting");
        const last = i === T.process.steps.length - 1;
        return (
          <li
            key={step.title}
            className={`relative grid grid-cols-[34px_1fr_auto] items-center gap-3.5 py-3 ${
              last ? "" : "after:absolute after:-bottom-3 after:left-4 after:top-[46px] after:w-0.5 after:content-['']"
            } ${state === "done" ? "after:bg-good" : "after:bg-line"}`}
          >
            <span className={`z-10 grid size-[34px] place-items-center rounded-full text-[0.85rem] font-extrabold ${CIRCLE[state]}`}>
              {i + 1}
            </span>
            <span className={state === "waiting" ? "text-muted" : ""}>
              <b className="block">{step.title}</b>
              <small className="text-muted">{step.sub}</small>
            </span>
            {CHIP_TEXT[state] && (
              <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${CHIP[state]}`}>{CHIP_TEXT[state]}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
