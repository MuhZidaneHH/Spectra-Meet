"use client";

import { useEffect, useRef } from "react";
import { formatTime } from "@/lib/format";
import type { SpeakerStyle } from "@/lib/speakers";
import { T } from "@/lib/teks";
import type { Segment } from "@/lib/types";

/** Daftar kalimat per pembicara. Kalimat yang sedang diputar disorot dan diikuti gulirannya. */
export function TranscriptList({
  segments,
  activeIndex,
  styleOf,
  onSelect,
}: {
  segments: Segment[];
  activeIndex: number;
  styleOf: (id: string | null | undefined) => SpeakerStyle;
  onSelect: (segment: Segment) => void;
}) {
  const box = useRef<HTMLDivElement>(null);

  // Gulirkan HANYA kotak transkrip (bukan seluruh halaman) ke kalimat aktif.
  useEffect(() => {
    const container = box.current;
    const el = container?.querySelector<HTMLElement>(`[data-seg="${activeIndex}"]`);
    if (!container || !el || container.scrollHeight <= container.clientHeight + 4) return;
    container.scrollTo({ top: el.offsetTop - 40, behavior: "smooth" });
  }, [activeIndex]);

  if (segments.length === 0) return <p className="p-5 text-sm text-muted">{T.result.noSegments}</p>;

  return (
    <div ref={box} className="relative max-h-[620px] overflow-auto p-2 pb-3.5 max-lg:max-h-none">
      {segments.map((s, i) => {
        const who = styleOf(s.speaker);
        return (
          <button
            key={i}
            type="button"
            data-seg={i}
            onClick={() => onSelect(s)}
            className={`grid w-full grid-cols-[56px_1fr] gap-2.5 rounded-xl border p-3 text-left transition ${
              i === activeIndex
                ? "border-brand/40 bg-brand-soft"
                : "border-transparent hover:bg-surface-2"
            }`}
          >
            <span className="pt-0.5 text-xs font-bold tabular-nums text-muted">{formatTime(s.start)}</span>
            <span>
              <span className="mb-0.5 flex items-center gap-2 text-[0.86rem] font-extrabold" style={{ color: who.color }}>
                <i className="size-2.5 rounded-full" style={{ background: who.color }} />
                {who.name}
              </span>
              <span className="block text-[0.93rem]">{s.text}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
