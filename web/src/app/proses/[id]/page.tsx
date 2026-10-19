"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Chip } from "@/components/Chip";
import { Icon } from "@/components/Icon";
import { Note } from "@/components/Note";
import { StepList } from "@/components/StepList";
import { Stepper } from "@/components/Stepper";
import { api, ApiError } from "@/lib/api";
import { formatTime } from "@/lib/format";
import { T } from "@/lib/teks";
import type { MeetingDetail, PublicConfig } from "@/lib/types";

const CARD = "rounded-2xl border border-line bg-surface p-6 shadow-card";
const BTN = "inline-flex items-center justify-center gap-2 rounded-xl px-[18px] py-[11px] text-[0.92rem] font-bold transition";
const BTN_PRIMARY = `${BTN} bg-brand text-brand-fg shadow-[0_6px_18px_color-mix(in_srgb,var(--brand)_35%,transparent)] hover:-translate-y-px hover:brightness-105 disabled:pointer-events-none disabled:opacity-45`;
const BTN_GHOST = `${BTN} border border-line bg-surface hover:bg-surface-2 disabled:pointer-events-none disabled:opacity-45`;

/** Jam berdetak tiap detik selama `active`; 0 sebelum detak pertama. */
function useNow(active: boolean): number {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (!active) return;
    const first = setTimeout(() => setNow(Date.now()), 0);
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [active]);
  return now;
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-[720px] animate-[rise_0.25s_ease]">
      <Stepper current={2} />
      {children}
    </div>
  );
}

export default function ProcessPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [problem, setProblem] = useState<"notfound" | "network" | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const status = meeting?.status;
  const pollMs = config?.poll_interval_ms ?? 1500;
  const now = useNow(status === "processing");

  useEffect(() => {
    api
      .config()
      .then(setConfig)
      .catch(() => {});
  }, []);

  // Menanyakan status selama masih diproses (atau sebelum status pertama diketahui).
  useEffect(() => {
    if (status && status !== "processing") return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const m = await api.getMeeting(id);
        if (!alive) return;
        setMeeting(m);
        setProblem(null);
        if (m.status !== "processing") return;
      } catch (e) {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 404) {
          setProblem("notfound");
          return;
        }
        setProblem("network"); // API sesaat tidak terjangkau: coba terus
      }
      timer = setTimeout(tick, pollMs);
    };
    timer = setTimeout(tick, 0);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [id, status, pollMs]);

  async function act(action: () => Promise<MeetingDetail>, after?: () => void) {
    setBusy(true);
    setActionError(null);
    try {
      setMeeting(await action());
      after?.();
    } catch (e) {
      setActionError(e instanceof ApiError ? e.message : T.audio.errNetwork);
    } finally {
      setBusy(false);
    }
  }

  if (problem === "notfound") {
    return (
      <Shell>
        <div className={CARD}>
          <h2 className="mb-1.5 text-[1.4rem] font-extrabold">{T.process.notFoundTitle}</h2>
          <p className="text-muted">{T.process.notFoundText}</p>
          <div className="mt-5">
            <Link href="/" className={BTN_PRIMARY}>
              {T.process.back}
            </Link>
          </div>
        </div>
      </Shell>
    );
  }

  if (!meeting) {
    return (
      <Shell>
        <p className="text-sm text-muted">{problem === "network" ? T.process.networkError : T.process.loading}</p>
      </Shell>
    );
  }

  const m = meeting;
  const languageLabel = config?.languages.find((l) => l.value === m.language)?.label ?? m.language;
  const meta = T.process.meta([
    ...(m.duration_sec ? [formatTime(m.duration_sec)] : []),
    languageLabel,
    T.process.speakersLabel(m.speakers),
  ]);

  const started = m.started_at ? Date.parse(m.started_at) : null;
  const ended = m.finished_at ? Date.parse(m.finished_at) : null;
  const elapsedSec = started === null ? 0 : ended !== null && m.status !== "processing" ? (ended - started) / 1000 : Math.max(0, (now - started) / 1000);

  const errorBox = actionError && (
    <div className="mt-4" role="alert">
      <Note icon="alert" tone="bad">{actionError}</Note>
    </div>
  );

  if (m.status === "uploaded") {
    return (
      <Shell>
        <div className={CARD}>
          <h2 className="mb-1.5 text-[1.4rem] font-extrabold">{T.process.notStartedTitle}</h2>
          <p className="text-muted">
            {m.filename} · {T.process.notStartedText}
          </p>
          {errorBox}
          <div className="mt-5 flex gap-2.5">
            <button type="button" disabled={busy} className={BTN_PRIMARY} onClick={() => act(() => api.startMeeting(id))}>
              <Icon name="sparkle" />
              {T.process.start}
            </button>
            <Link href="/" className={BTN_GHOST}>
              {T.process.back}
            </Link>
          </div>
        </div>
      </Shell>
    );
  }

  if (m.status === "failed" || m.status === "cancelled") {
    const failed = m.status === "failed";
    const step = m.error_step ?? 1;
    const detail = m.progress.error;
    // Saran dari kode galat yang disepakati di kontrak; bila kodenya tidak dikenal, pakai saran dari pipeline.
    const advice = T.process.errorHint(detail?.code) ?? detail?.hint;
    return (
      <Shell>
        <div className={CARD}>
          <span className="mb-3.5 grid size-[54px] place-items-center rounded-2xl bg-bad-soft text-[1.6rem] text-bad">
            <Icon name="alert" />
          </span>
          <h2 className="mb-1.5 text-[1.4rem] font-extrabold">
            {failed ? T.process.failTitle(step, T.process.steps[step - 1]?.title ?? "") : T.process.cancelledTitle}
          </h2>
          <p className="text-muted">{failed ? T.process.failText : T.process.cancelledText}</p>
          {failed && (
            <div className="mt-3.5 overflow-auto rounded-xl bg-surface-2 px-3.5 py-3 font-mono text-[0.78rem] leading-relaxed text-muted">
              <div>
                [tahap {step}
                {detail?.code ? ` · ${detail.code}` : ""}] {m.error_message}
              </div>
              {advice && (
                <div>
                  {T.process.hint} {advice}
                </div>
              )}
              {detail?.log_tail && (
                <pre className="mt-2 whitespace-pre-wrap break-words border-t border-line pt-2">{detail.log_tail}</pre>
              )}
            </div>
          )}
          {errorBox}
          <div className="mt-5 flex gap-2.5">
            <button type="button" disabled={busy} className={BTN_PRIMARY} onClick={() => act(() => api.retryMeeting(id))}>
              <Icon name="sparkle" />
              {failed ? T.process.retry : T.process.restart}
            </button>
            <Link href="/" className={BTN_GHOST}>
              {T.process.back}
            </Link>
          </div>
        </div>
      </Shell>
    );
  }

  const done = m.status === "done";
  const percent = done ? 100 : m.progress.percent;
  return (
    <Shell>
      <div className={CARD}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-[1.4rem] font-extrabold">{m.filename}</h2>
            <p className="text-[0.88rem] text-muted">{meta}</p>
          </div>
          <Chip tone={done ? "good" : "brand"}>
            <span className="size-2 rounded-full bg-current" />
            {done ? T.process.chipDone : T.process.chipRunning}
          </Chip>
        </div>

        <div className="my-3 mb-2 h-3 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <i className="block h-full rounded-full bg-gradient-to-r from-brand to-cyan transition-[width] duration-500" style={{ width: `${Math.max(percent, done ? 100 : 4)}%` }} />
        </div>
        <div className="flex flex-wrap justify-between gap-1.5 text-[0.86rem] font-bold">
          <span>{percent}%</span>
          <span className="text-muted">
            {done ? T.process.tookLabel : T.process.elapsed} <b className="tabular-nums text-ink">{formatTime(elapsedSec)}</b>
            {!done && <> · {T.process.elapsedNote}</>}
          </span>
        </div>

        <StepList steps={done ? Array(5).fill("done") : m.progress.steps} />

        {!done && <Note icon="alert" tone="warn">{T.process.keepOpen}</Note>}
        {problem === "network" && !done && (
          <div className="mt-2.5">
            <Note icon="alert" tone="bad">{T.process.networkError}</Note>
          </div>
        )}
        {errorBox}

        <div className="mt-[22px] flex justify-end gap-2.5">
          {!done && (
            <button type="button" disabled={busy} className={BTN_GHOST} onClick={() => act(() => api.cancelMeeting(id), () => router.push("/"))}>
              {T.process.cancel}
            </button>
          )}
          {done ? (
            <Link href={`/hasil/${id}`} className={BTN_PRIMARY}>
              <Icon name="sparkle" />
              {T.process.viewResult}
            </Link>
          ) : (
            <button type="button" disabled className={BTN_PRIMARY}>
              <Icon name="sparkle" />
              {T.process.viewResult}
            </button>
          )}
        </div>
      </div>
    </Shell>
  );
}
