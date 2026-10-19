"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { HEALTH_REFRESH_MS } from "@/lib/config";
import { T } from "@/lib/teks";
import type { Health } from "@/lib/types";
import { Chip, type ChipTone } from "./Chip";
import { Icon } from "./Icon";

function summarize(health: Health | null, failed: boolean): { tone: ChipTone; text: string } {
  if (failed) return { tone: "bad", text: T.engine.unreachable };
  if (!health) return { tone: "neutral", text: T.engine.loading };
  if (!health.ready) return { tone: "warn", text: T.engine.needsSetup };
  const detail = health.mock_pipeline ? T.engine.mock : `${health.device.toUpperCase()} · ${health.whisper_model}`;
  return { tone: "good", text: `${T.engine.ready} · ${detail}` };
}

/** Chip status mesin di header. Diklik membuka panel berisi hal yang belum beres dan cara memperbaikinya. */
export function EngineStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    api
      .health()
      .then((h) => {
        setHealth(h);
        setFailed(false);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    // Muat pertama lewat timer 0 ms (bukan setState langsung di badan effect), lalu berkala.
    const first = setTimeout(load, 0);
    const timer = setInterval(load, HEALTH_REFRESH_MS);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const { tone, text } = summarize(health, failed);

  return (
    <div ref={boxRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="engine-panel"
        title={T.engine.panelTitle}
        onClick={() => {
          if (!open) load();
          setOpen((v) => !v);
        }}
        className="rounded-full transition hover:brightness-95"
      >
        <Chip tone={tone}>
          <Icon name="cpu" />
          {text}
        </Chip>
      </button>

      {open && (
        <div
          id="engine-panel"
          className="absolute right-0 top-full z-50 mt-2 w-[min(380px,calc(100vw-32px))] rounded-2xl border border-line bg-surface p-4 shadow-card"
        >
          <h2 className="mb-3 text-sm font-extrabold">{T.engine.panelTitle}</h2>

          {failed && <p className="rounded-xl bg-bad-soft px-3 py-2.5 text-[0.84rem] text-bad">{T.engine.unreachableHint}</p>}

          {!failed && health && (
            <ul className="grid gap-2.5">
              {health.checks.map((c) => {
                const bad = !c.ok;
                return (
                  <li key={c.id} className="flex gap-2.5 text-[0.84rem]">
                    <span
                      className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full ${
                        c.ok ? "bg-good-soft text-good" : c.required ? "bg-bad-soft text-bad" : "bg-surface-2 text-muted"
                      }`}
                    >
                      <Icon name={c.ok ? "check" : "x"} className="size-3" />
                    </span>
                    <span className="min-w-0">
                      <span className="font-bold">{c.label}</span>
                      {bad && (
                        <span className="ml-1.5 text-xs text-muted">({c.required ? T.engine.required : T.engine.optional})</span>
                      )}
                      {bad && c.hint && <span className="mt-0.5 block text-muted">{c.hint}</span>}
                      {bad && c.env_var && (
                        <span className="mt-0.5 block text-muted">
                          {T.engine.editIn}{" "}
                          <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-xs text-ink">{c.env_var}</code>
                        </span>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}

          <p className="mt-3.5 border-t border-line pt-3 text-xs text-muted">{T.engine.restartNote}</p>
        </div>
      )}
    </div>
  );
}
