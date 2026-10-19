import { formatBytes } from "@/lib/format";
import { T } from "@/lib/teks";

/** Tahap pengiriman: mengunggah (dengan angka), menyimpan di server, lalu memulai proses. */
export type SubmitState = { phase: "upload"; loaded: number; total: number } | { phase: "saving" } | { phase: "start" };

export function UploadProgress({ state, onCancel }: { state: SubmitState; onCancel: () => void }) {
  const uploading = state.phase === "upload";
  const percent = uploading && state.total > 0 ? Math.min(100, Math.floor((state.loaded / state.total) * 100)) : 100;
  const label = uploading
    ? T.audio.uploadProgress(percent, formatBytes(state.loaded), formatBytes(state.total))
    : state.phase === "saving"
      ? T.audio.uploadSaving
      : T.audio.uploadStarting;

  return (
    <div role="status" className="mt-[18px] rounded-xl bg-brand-soft px-3.5 py-3">
      <div className="flex items-center justify-between gap-3 text-[0.86rem] font-bold text-brand">
        <span>{label}</span>
        {uploading && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg px-2.5 py-1 text-[0.82rem] font-bold text-muted transition hover:bg-surface hover:text-ink"
          >
            {T.audio.cancelUpload}
          </button>
        )}
      </div>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={uploading ? percent : undefined}
        className="mt-2 h-2 overflow-hidden rounded-full bg-surface"
      >
        <i
          className={`block h-full rounded-full bg-gradient-to-r from-brand to-cyan transition-[width] duration-200 ${
            uploading ? "" : "animate-pulse"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
