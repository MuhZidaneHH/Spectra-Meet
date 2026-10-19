"use client";

import { useEffect, useRef, useState } from "react";
import { MAX_RECORD_SECONDS } from "@/lib/config";
import { formatTime } from "@/lib/format";
import { T } from "@/lib/teks";
import { Icon } from "./Icon";

const PREFERRED_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

type Phase = "idle" | "recording" | "paused";

function extensionFor(mime: string): string {
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("mp4")) return "m4a";
  return "webm";
}

function stamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
}

// Dipanggil hanya dari event handler dan timer, tidak pernah saat render.
function nowMs(): number {
  return Date.now();
}

const SMALL_BTN =
  "inline-flex items-center gap-1.5 rounded-[10px] px-3 py-[7px] text-[0.82rem] font-bold transition";

/** Merekam dari mikrofon browser.
 * Idle: ketuk untuk mulai. Saat merekam: ketuk lingkaran untuk jeda/lanjut, "Berhenti" menyimpan
 * rekaman, "Ulangi" membuang dan merekam dari awal. Hasilnya diserahkan sebagai File biasa. */
export function Recorder({
  disabled,
  onRecorded,
  onError,
}: {
  disabled?: boolean;
  onRecorded: (file: File, seconds: number) => void;
  onError: (message: string) => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const accumulatedMs = useRef(0); // lama rekaman sebelum segmen yang sedang berjalan (jeda tidak dihitung)
  const segmentStart = useRef<number | null>(null);
  const afterStop = useRef<"save" | "redo">("save");
  const callbacks = useRef({ onRecorded, onError });

  useEffect(() => {
    callbacks.current = { onRecorded, onError };
  });

  const elapsedMs = () => accumulatedMs.current + (segmentStart.current !== null ? nowMs() - segmentStart.current : 0);

  const cleanup = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  };

  // Bila halaman ditinggalkan saat merekam: lepas mikrofon dan buang hasilnya.
  useEffect(
    () => () => {
      if (recorder.current) recorder.current.onstop = null;
      cleanup();
    },
    [],
  );

  const stopRecorder = (mode: "save" | "redo") => {
    if (recorder.current && recorder.current.state !== "inactive") {
      afterStop.current = mode;
      recorder.current.stop();
    }
  };

  const pause = () => {
    if (recorder.current?.state !== "recording" || segmentStart.current === null) return;
    recorder.current.pause();
    accumulatedMs.current += nowMs() - segmentStart.current;
    segmentStart.current = null;
    setSeconds(Math.floor(accumulatedMs.current / 1000));
    setPhase("paused");
  };

  const resume = () => {
    if (recorder.current?.state !== "paused") return;
    recorder.current.resume();
    segmentStart.current = nowMs();
    setPhase("recording");
  };

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      callbacks.current.onError(T.audio.errMicUnsupported);
      return;
    }
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      const name = e instanceof DOMException ? e.name : "";
      callbacks.current.onError(
        name === "NotAllowedError" ? T.audio.errMicDenied : name === "NotFoundError" ? T.audio.errMicMissing : T.audio.errMicGeneric,
      );
      return;
    }

    const mimeType = PREFERRED_TYPES.find((t) => MediaRecorder.isTypeSupported(t));
    const rec = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    rec.onstop = () => {
      const totalSeconds = elapsedMs() / 1000;
      const type = rec.mimeType || mimeType || "audio/webm";
      const mode = afterStop.current;
      afterStop.current = "save";
      cleanup();
      segmentStart.current = null;
      accumulatedMs.current = 0;
      setPhase("idle");
      setSeconds(0);
      if (mode === "redo") {
        void start(); // buang rekaman ini, mulai lagi dari nol
        return;
      }
      const file = new File(chunks, `rekaman-${stamp()}.${extensionFor(type)}`, { type });
      callbacks.current.onRecorded(file, totalSeconds);
    };

    stream.current = media;
    recorder.current = rec;
    accumulatedMs.current = 0;
    segmentStart.current = nowMs();
    rec.start(1000);
    setSeconds(0);
    setPhase("recording");
    timer.current = setInterval(() => {
      const s = Math.floor(elapsedMs() / 1000);
      setSeconds(s);
      if (s >= MAX_RECORD_SECONDS) stopRecorder("save");
    }, 500);
  };

  if (phase === "idle") {
    return (
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={T.audio.recordTitle}
        aria-disabled={disabled}
        onClick={() => !disabled && void start()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            void start();
          }
        }}
        className="grid cursor-pointer justify-items-center gap-1.5 rounded-2xl border-2 border-dashed border-line bg-surface-2 px-4 py-8 text-center transition hover:border-brand hover:bg-brand-soft aria-disabled:cursor-not-allowed aria-disabled:opacity-50"
      >
        <span className="grid size-[54px] place-items-center rounded-2xl bg-surface text-2xl text-bad shadow-card">
          <Icon name="mic" />
        </span>
        <b className="text-base">{T.audio.recordTitle}</b>
        <small className="text-muted">{T.audio.recordSub}</small>
      </div>
    );
  }

  const paused = phase === "paused";
  return (
    <div
      className={`grid justify-items-center gap-1.5 rounded-2xl border-2 border-dashed px-4 py-5 text-center ${
        paused ? "border-warn bg-warn-soft" : "border-bad bg-bad-soft"
      }`}
    >
      <button
        type="button"
        onClick={paused ? resume : pause}
        aria-label={paused ? T.audio.resume : T.audio.pause}
        className={`grid size-[54px] place-items-center rounded-2xl bg-surface text-2xl shadow-card transition hover:brightness-95 ${
          paused ? "text-warn" : "text-bad"
        }`}
      >
        <Icon name={paused ? "play" : "pause"} />
      </button>
      <b className="text-base">{paused ? T.audio.pausedTitle : T.audio.recordingTitle}</b>
      <span className="flex h-[30px] items-center gap-[3px]" aria-hidden="true">
        {[0, 0.1, 0.25, 0.05, 0.3, 0.15, 0.2].map((delay, i) => (
          <b
            key={i}
            className={`w-1 animate-[eq_0.9s_ease-in-out_infinite] rounded-[3px] ${paused ? "bg-warn [animation-play-state:paused]" : "bg-bad"}`}
            style={{ animationDelay: `${delay}s` }}
          />
        ))}
      </span>
      <small className={`font-bold tabular-nums ${paused ? "text-warn" : "text-bad"}`}>{formatTime(seconds)}</small>
      <small className="text-muted">{paused ? T.audio.hintResume : T.audio.hintPause}</small>
      <div className="mt-1.5 flex gap-2">
        <button
          type="button"
          onClick={() => stopRecorder("redo")}
          className={`${SMALL_BTN} border border-line bg-surface hover:bg-surface-2`}
        >
          <Icon name="refresh" />
          {T.audio.redo}
        </button>
        <button type="button" onClick={() => stopRecorder("save")} className={`${SMALL_BTN} bg-brand text-brand-fg hover:brightness-105`}>
          <Icon name="stop" />
          {T.audio.stopRecording}
        </button>
      </div>
    </div>
  );
}
