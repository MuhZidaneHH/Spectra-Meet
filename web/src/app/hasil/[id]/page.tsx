"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AudioPlayer } from "@/components/AudioPlayer";
import { Chip } from "@/components/Chip";
import { Icon } from "@/components/Icon";
import { Note } from "@/components/Note";
import { Stepper } from "@/components/Stepper";
import { TimingCard } from "@/components/TimingCard";
import { SummaryCard } from "@/components/SummaryCard";
import { useToast } from "@/components/Toast";
import { TranscriptList } from "@/components/TranscriptList";
import { api, ApiError } from "@/lib/api";
import { copyText } from "@/lib/clipboard";
import { formatTime } from "@/lib/format";
import { mapSpeakers, transcriptAsText } from "@/lib/speakers";
import { T } from "@/lib/teks";
import type { MeetingDetail, MeetingResult } from "@/lib/types";
import { useAudioPlayer } from "@/lib/useAudioPlayer";

const CARD = "rounded-2xl border border-line bg-surface shadow-card";
const BTN = "inline-flex items-center justify-center gap-2 rounded-xl px-[18px] py-[11px] text-[0.92rem] font-bold transition";
const BTN_PRIMARY = `${BTN} bg-brand text-brand-fg shadow-[0_6px_18px_color-mix(in_srgb,var(--brand)_35%,transparent)] hover:-translate-y-px hover:brightness-105`;
const BTN_GHOST = `${BTN} border border-line bg-surface hover:bg-surface-2`;

type State =
  | { kind: "loading" }
  | { kind: "notfound" }
  | { kind: "error"; detail?: string; badResult?: boolean }
  | { kind: "notdone"; meeting: MeetingDetail }
  | { kind: "ready"; meeting: MeetingDetail; result: MeetingResult };

/** Indeks kalimat yang sedang diputar: yang terakhir dimulai pada atau sebelum waktu sekarang. */
function activeSegment(starts: number[], time: number): number {
  let active = starts.length ? 0 : -1;
  for (let i = 0; i < starts.length; i++) if (starts[i] <= time) active = i;
  return active;
}

function ResultView({
  meeting,
  result,
  languageLabel,
}: {
  meeting: MeetingDetail;
  result: MeetingResult;
  languageLabel: string;
}) {
  const segments = result.segments;
  const { list: speakerList, styleOf } = useMemo(() => mapSpeakers(segments, result.speakers), [segments, result.speakers]);
  const fallbackDuration = meeting.duration_sec ?? segments.at(-1)?.end ?? 0;
  const player = useAudioPlayer(api.audioUrl(meeting.id), fallbackDuration);
  const { show, toast } = useToast();
  const [tab, setTab] = useState<"sum" | "tr">("sum");

  const activeIndex = activeSegment(
    segments.map((s) => s.start),
    player.current,
  );

  async function copy(text: string, done: string) {
    show((await copyText(text)) ? done : T.result.copyFailed);
  }

  const tookSec =
    meeting.started_at && meeting.finished_at ? (Date.parse(meeting.finished_at) - Date.parse(meeting.started_at)) / 1000 : null;

  return (
    <>
      <Stepper current={3} />

      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-[1.6rem] font-extrabold">{meeting.filename}</h1>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {player.duration > 0 && (
              <Chip>
                <Icon name="clock" />
                {formatTime(player.duration)}
              </Chip>
            )}
            {speakerList.length > 0 && (
              <Chip>
                <Icon name="users" />
                {T.result.speakersChip(speakerList.length)}
              </Chip>
            )}
            <Chip>
              <Icon name="globe" />
              {languageLabel}
            </Chip>
            {tookSec !== null && (
              <Chip tone="good">
                <span className="size-2 rounded-full bg-current" />
                {T.result.tookChip(formatTime(tookSec))}
              </Chip>
            )}
          </div>
        </div>
        <div className="flex gap-2.5">
          <button
            type="button"
            className={BTN_GHOST}
            onClick={() =>
              copy(`${meeting.filename}\n\n${T.result.summaryTitle.toUpperCase()}\n${result.summary.ringkasan}`, T.result.copiedSummary)
            }
          >
            <Icon name="copy" />
            {T.result.copySummary}
          </button>
          <Link href="/" className={BTN_PRIMARY}>
            <Icon name="upload" />
            {T.result.otherAudio}
          </Link>
        </div>
      </div>

      <AudioPlayer player={player} />

      <div className="mb-3.5 flex gap-1.5 rounded-xl bg-surface-2 p-1 lg:hidden" role="tablist">
        {(
          [
            ["sum", T.result.tabSummary],
            ["tr", T.result.tabTranscript],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`flex-1 rounded-[9px] p-2 text-[0.84rem] font-bold ${
              tab === key ? "bg-surface text-ink shadow-sm" : "text-muted"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <section className={tab === "sum" ? "" : "max-lg:hidden"}>
          <SummaryCard summary={result.summary.ringkasan} />
          <TimingCard pipeline={result.pipeline} />
        </section>

        <section className={`${CARD} overflow-hidden ${tab === "tr" ? "" : "max-lg:hidden"}`}>
          <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-line px-[18px] py-3.5">
            <b>{T.result.transcriptTitle}</b>
            <div className="flex flex-wrap items-center gap-3">
              <ul className="flex flex-wrap gap-3 text-[0.78rem] font-bold">
                {speakerList.map((s) => (
                  <li key={s.name} className="inline-flex items-center gap-1.5">
                    <i className="size-2.5 rounded-full" style={{ background: s.color }} />
                    {s.name}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="inline-flex items-center gap-1.5 rounded-[10px] border border-line bg-surface px-3 py-[7px] text-[0.82rem] font-bold transition hover:bg-surface-2"
                onClick={() => copy(transcriptAsText(segments, styleOf), T.result.copiedTranscript)}
              >
                <Icon name="copy" />
                {T.result.copyTranscript}
              </button>
            </div>
          </div>
          <TranscriptList
            segments={segments}
            activeIndex={activeIndex}
            styleOf={styleOf}
            onSelect={(s) => {
              player.seek(s.start);
              player.play();
            }}
          />
        </section>
      </div>

      {toast}
    </>
  );
}

export default function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [languages, setLanguages] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    api
      .config()
      .then((c) => setLanguages(c.languages))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let alive = true;
    api
      .getMeeting(id)
      .then(async (meeting) => {
        if (!alive) return;
        if (meeting.status !== "done") {
          setState({ kind: "notdone", meeting });
          return;
        }
        const result = await api.getResult(id);
        if (alive) setState({ kind: "ready", meeting, result });
      })
      .catch((e: unknown) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 404) setState({ kind: "notfound" });
        else setState({ kind: "error", detail: e instanceof ApiError ? e.message : undefined, badResult: e instanceof ApiError && e.status >= 500 }); // detail dari API membantu Dev 2 dan PM melacak hasil yang menyimpang dari kontrak
      });
    return () => {
      alive = false;
    };
  }, [id]);

  if (state.kind === "ready") {
    const { meeting } = state;
    const languageLabel = languages.find((l) => l.value === meeting.language)?.label ?? meeting.language;
    return <ResultView meeting={meeting} result={state.result} languageLabel={languageLabel} />;
  }

  if (state.kind === "loading") return <p className="text-sm text-muted">{T.result.loading}</p>;

  return (
    <div className="mx-auto max-w-[720px]">
      <div className={`${CARD} p-6`}>
        {state.kind === "notfound" && (
          <>
            <h2 className="mb-1.5 text-[1.4rem] font-extrabold">{T.result.notFoundTitle}</h2>
            <p className="text-muted">{T.process.notFoundText}</p>
          </>
        )}
        {state.kind === "notdone" && (
          <>
            <h2 className="mb-1.5 text-[1.4rem] font-extrabold">{T.result.notDoneTitle}</h2>
            <p className="text-muted">{T.result.notDoneText}</p>
          </>
        )}
        {state.kind === "error" && (
          <>
            <Note icon="alert" tone="bad">{state.badResult ? T.result.badResult : T.result.loadFailed}</Note>
            {state.detail && (
              <p className="mt-3 break-words rounded-xl bg-surface-2 px-3.5 py-3 font-mono text-[0.78rem] leading-relaxed text-muted">{state.detail}</p>
            )}
          </>
        )}
        <div className="mt-5 flex gap-2.5">
          {state.kind === "notdone" && (
            <Link href={`/proses/${id}`} className={BTN_PRIMARY}>
              {T.result.seeProcess}
            </Link>
          )}
          <Link href="/" className={state.kind === "notdone" ? BTN_GHOST : BTN_PRIMARY}>
            {T.process.back}
          </Link>
        </div>
      </div>
    </div>
  );
}
