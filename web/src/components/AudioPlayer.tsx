"use client";

import { formatTime } from "@/lib/format";
import { T } from "@/lib/teks";
import type { AudioPlayerState } from "@/lib/useAudioPlayer";
import { Icon } from "./Icon";
import { Note } from "./Note";

/** Tampilan pemutar. Statusnya datang dari useAudioPlayer di halaman, agar transkrip bisa ikut mengendalikan. */
export function AudioPlayer({ player }: { player: AudioPlayerState }) {
  const { audioProps, current, duration, playing, rate, failed, seek, toggle, cycleRate } = player;
  const percent = duration > 0 ? Math.min(100, (current / duration) * 100) : 0;

  return (
    <div className="mb-[18px]">
      <audio {...audioProps} />
      <div className="grid grid-cols-[auto_1fr_auto] items-center gap-4 rounded-2xl border border-line bg-surface px-[18px] py-3.5 shadow-card">
        <button
          type="button"
          onClick={toggle}
          disabled={failed}
          aria-label={playing ? T.result.pause : T.result.play}
          className="grid size-[46px] place-items-center rounded-full bg-brand text-xl text-brand-fg shadow-[0_6px_16px_color-mix(in_srgb,var(--brand)_40%,transparent)] transition hover:brightness-105 disabled:opacity-45"
        >
          <Icon name={playing ? "pause" : "play"} />
        </button>

        <div>
          <div
            role="slider"
            tabIndex={0}
            aria-label={T.result.position}
            aria-valuemin={0}
            aria-valuemax={Math.round(duration)}
            aria-valuenow={Math.round(current)}
            aria-valuetext={formatTime(current)}
            onClick={(e) => {
              const box = e.currentTarget.getBoundingClientRect();
              seek(((e.clientX - box.left) / box.width) * duration);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight") {
                seek(current + 5);
                e.preventDefault();
              } else if (e.key === "ArrowLeft") {
                seek(current - 5);
                e.preventDefault();
              }
            }}
            className="relative h-2.5 cursor-pointer overflow-hidden rounded-full bg-surface-2"
          >
            <i className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-brand to-cyan" style={{ width: `${percent}%` }} />
          </div>
          <div className="mt-1.5 flex justify-between text-xs font-bold tabular-nums text-muted">
            <span>{formatTime(current)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={cycleRate}
          aria-label={T.result.rate}
          className="rounded-[10px] border border-line bg-surface px-3 py-[7px] text-[0.82rem] font-bold tabular-nums transition hover:bg-surface-2"
        >
          {rate.toFixed(1)}x
        </button>
      </div>
      {failed && (
        <div className="mt-2.5">
          <Note icon="alert" tone="warn">{T.result.audioFailed}</Note>
        </div>
      )}
    </div>
  );
}
