"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import { Note } from "@/components/Note";
import { Recorder } from "@/components/Recorder";
import { SourcePreview, type SourceOrigin } from "@/components/SourcePreview";
import { Stepper } from "@/components/Stepper";
import { UploadBox } from "@/components/UploadBox";
import { UploadProgress, type SubmitState } from "@/components/UploadProgress";
import { api, ApiError, UploadAborted } from "@/lib/api";
import { extensionOf, readDuration } from "@/lib/audio";
import { T } from "@/lib/teks";
import type { Option, PublicConfig } from "@/lib/types";

// meetingId terisi setelah file terunggah, agar "Proses" yang gagal di tengah jalan
// (mis. mesin sibuk) tidak mengunggah ulang file yang sama.
type Source = {
  file: File;
  origin: SourceOrigin;
  previewUrl: string; // alamat blob untuk pemutar pratinjau
  durationSec: number | null;
  meetingId?: string;
};

const SELECT_CLASS =
  "w-full rounded-xl border border-line bg-surface px-3.5 py-3 outline-none focus:border-brand focus:ring-[3px] focus:ring-brand/25";

function Field({
  id,
  label,
  options,
  value,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  options: Option[];
  value: string;
  disabled?: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={id} className="text-[0.82rem] font-bold">
        {label}
      </label>
      <select
        id={id}
        className={`${SELECT_CLASS} disabled:opacity-60`}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function AudioPage() {
  const router = useRouter();
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [configFailed, setConfigFailed] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const [language, setLanguage] = useState<string | null>(null);
  const [speakers, setSpeakers] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<SubmitState | null>(null); // null = tidak sedang mengirim
  const abortUpload = useRef<(() => void) | null>(null);

  useEffect(() => {
    api
      .config()
      .then(setConfig)
      .catch(() => setConfigFailed(true));
  }, []);

  const extensionList = config?.extensions.map((e) => e.toUpperCase()).join(", ") ?? "";

  // Alamat blob pratinjau dilepas saat file diganti/dihapus dan saat halaman ditinggalkan.
  const previewUrl = useRef<string | null>(null);
  useEffect(
    () => () => {
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    },
    [],
  );

  function removeSource() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setSource(null);
    setError(null);
  }

  function renameSource(name: string) {
    // File tidak bisa diubah namanya; buat File baru yang berbagi isi yang sama (tanpa menyalin data).
    // meetingId direset karena nama di API harus ikut berubah.
    setSource((s) =>
      s ? { ...s, file: new File([s.file], name, { type: s.file.type, lastModified: s.file.lastModified }), meetingId: undefined } : s,
    );
  }

  async function acceptFile(file: File, origin: SourceOrigin, knownDuration?: number) {
    if (!config) return;
    if (!config.extensions.includes(extensionOf(file.name))) {
      setError(T.audio.errBadType(extensionList));
      return;
    }
    if (file.size > config.max_upload_mb * 1024 * 1024) {
      setError(T.audio.errTooBig(config.max_upload_mb));
      return;
    }
    setError(null);
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    const url = URL.createObjectURL(file);
    previewUrl.current = url;
    setSource({ file, origin, previewUrl: url, durationSec: knownDuration ?? null });
    if (knownDuration === undefined) {
      const durationSec = await readDuration(file);
      setSource((cur) => (cur?.previewUrl === url ? { ...cur, durationSec } : cur)); // dicocokkan lewat url, karena file bisa diganti nama
    }
  }

  const languageValue = language ?? config?.languages[0]?.value ?? "";
  const speakersValue = speakers ?? config?.speaker_options[0]?.value ?? "";
  const submitting = progress !== null;
  const ready = config !== null && source !== null && !submitting;

  async function start() {
    if (!source) return;
    setError(null);
    setProgress({ phase: "upload", loaded: 0, total: source.file.size });
    try {
      let meetingId = source.meetingId;
      if (!meetingId) {
        const upload = api.uploadMeeting(
          source.file,
          { language: languageValue, speakers: speakersValue, durationSec: source.durationSec },
          ({ loaded, total }) => setProgress(loaded >= total ? { phase: "saving" } : { phase: "upload", loaded, total }),
        );
        abortUpload.current = upload.abort;
        const created = await upload.promise;
        abortUpload.current = null;
        meetingId = created.id;
        setSource({ ...source, meetingId });
      }
      setProgress({ phase: "start" });
      await api.startMeeting(meetingId);
      router.push(`/proses/${meetingId}`);
    } catch (e) {
      abortUpload.current = null;
      setProgress(null);
      if (e instanceof UploadAborted) return; // dibatalkan pengguna, bukan galat
      setError(e instanceof ApiError && e.status !== 0 ? e.message : T.audio.errNetwork);
    }
  }

  return (
    <div className="mx-auto max-w-[720px] animate-[rise_0.25s_ease]">
      <Stepper current={1} />

      <div className="mb-5">
        <h1 className="mb-1.5 text-[1.9rem] font-extrabold">{T.audio.title}</h1>
        <p className="text-muted">{T.audio.subtitle}</p>
      </div>

      <div className="rounded-2xl border border-line bg-surface p-6 shadow-card">
        {configFailed && <Note icon="alert" tone="bad">{T.audio.configFailed}</Note>}
        {!config && !configFailed && <p className="text-sm text-muted">{T.audio.configLoading}</p>}

        {config && (
          <>
            {source ? (
              <SourcePreview
                file={source.file}
                origin={source.origin}
                previewUrl={source.previewUrl}
                durationSec={source.durationSec}
                busy={submitting}
                onRename={renameSource}
                onRemove={removeSource}
              />
            ) : (
              <div className="grid gap-3.5 sm:grid-cols-2">
                <UploadBox extensions={config.extensions} onFile={(f) => acceptFile(f, "upload")} />
                <Recorder onRecorded={(f, secs) => acceptFile(f, "record", secs)} onError={setError} />
              </div>
            )}

            {error && (
              <div className="mt-3.5" role="alert">
                <Note icon="alert" tone="bad">{error}</Note>
              </div>
            )}

            <div className="mt-[18px] grid gap-3.5 sm:grid-cols-2">
              <Field
                id="lang"
                label={T.audio.language}
                options={config.languages}
                value={languageValue}
                disabled={submitting}
                onChange={(v) => {
                  setLanguage(v);
                  setSource((s) => (s ? { ...s, meetingId: undefined } : s)); // pilihan berubah: unggah ulang dengan pilihan baru
                }}
              />
              <Field
                id="spk"
                label={T.audio.speakers}
                options={config.speaker_options}
                value={speakersValue}
                disabled={submitting}
                onChange={(v) => {
                  setSpeakers(v);
                  setSource((s) => (s ? { ...s, meetingId: undefined } : s));
                }}
              />
            </div>

            <div className="mt-[18px] grid gap-2.5">
              <Note icon="clock">{T.audio.noteTime}</Note>
              <Note icon="lock">{T.audio.notePrivacy}</Note>
            </div>

            {progress && <UploadProgress state={progress} onCancel={() => abortUpload.current?.()} />}

            <div className="mt-[22px] flex justify-end">
              <button
                type="button"
                disabled={!ready}
                onClick={start}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-[18px] py-[11px] text-[0.92rem] font-bold text-brand-fg shadow-[0_6px_18px_color-mix(in_srgb,var(--brand)_35%,transparent)] transition hover:-translate-y-px hover:brightness-105 disabled:pointer-events-none disabled:opacity-45"
              >
                <Icon name="sparkle" />
                {submitting ? T.audio.sending : T.audio.start}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
