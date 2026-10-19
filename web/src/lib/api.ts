// Satu-satunya tempat web memanggil API. Semua jalur lewat /api (diteruskan Next ke FastAPI).
import type { Health, Meeting, MeetingDetail, MeetingResult, PublicConfig } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* respons bukan JSON */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string) => request<T>(path, { method: "POST" });

/** Unggahan dibatalkan pengguna (bukan galat). */
export class UploadAborted extends Error {}

export type UploadProgress = { loaded: number; total: number };

/** Mengunggah audio dengan laporan progres. fetch() tidak bisa melaporkan progres
 * unggahan, jadi bagian ini memakai XMLHttpRequest. Mengembalikan janji dan fungsi pembatal. */
function uploadMeeting(
  file: File,
  opts: { language: string; speakers: string; durationSec: number | null },
  onProgress: (p: UploadProgress) => void,
): { promise: Promise<Meeting>; abort: () => void } {
  const form = new FormData();
  form.append("file", file);
  form.append("language", opts.language);
  form.append("speakers", opts.speakers);
  if (opts.durationSec !== null) form.append("duration_sec", String(opts.durationSec));

  const xhr = new XMLHttpRequest();
  const promise = new Promise<Meeting>((resolve, reject) => {
    xhr.open("POST", "/api/meetings");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress({ loaded: e.loaded, total: e.total });
    };
    xhr.onload = () => {
      let body: { detail?: unknown } | null = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* respons bukan JSON */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as unknown as Meeting);
      else reject(new ApiError(typeof body?.detail === "string" ? body.detail : xhr.statusText, xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("Jaringan terputus.", 0));
    xhr.onabort = () => reject(new UploadAborted());
    xhr.send(form);
  });
  return { promise, abort: () => xhr.abort() };
}

export const api = {
  config: () => request<PublicConfig>("/config"),
  health: () => request<Health>("/health"),

  uploadMeeting,
  startMeeting: (id: string) => post<MeetingDetail>(`/meetings/${id}/start`),
  retryMeeting: (id: string) => post<MeetingDetail>(`/meetings/${id}/retry`),
  cancelMeeting: (id: string) => post<MeetingDetail>(`/meetings/${id}/cancel`),
  getMeeting: (id: string) => request<MeetingDetail>(`/meetings/${id}`),
  getResult: (id: string) => request<MeetingResult>(`/meetings/${id}/result`),
  /** Alamat audio untuk elemen <audio>; mendukung lompat posisi (Range). */
  audioUrl: (id: string) => `/api/meetings/${id}/audio`,
};
