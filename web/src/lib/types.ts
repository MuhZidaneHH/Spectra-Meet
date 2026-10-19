// Bentuk data dari API. Cerminan api/app/schemas.py (respons) dan api/app/contract.py (hasil, docs/kontrak-json.md).
// Ubah keduanya bersama bila API berubah.

export type Option = { value: string; label: string };

export type PublicConfig = {
  extensions: string[];
  max_upload_mb: number;
  poll_interval_ms: number;
  languages: Option[];
  speaker_options: Option[];
};

export type HealthCheck = {
  id: string;
  label: string;
  ok: boolean;
  required: boolean;
  hint?: string | null;
  env_var?: string | null;
};

export type Health = {
  ready: boolean;
  mock_pipeline: boolean;
  device: string;
  whisper_model: string;
  checks: HealthCheck[];
};

export type MeetingStatus = "uploaded" | "processing" | "done" | "failed" | "cancelled";

/** Status satu dari lima langkah pipeline. */
export type StepState = "waiting" | "running" | "done" | "failed";

export type ProgressError = { code: string; hint?: string | null; log_tail?: string | null };

export type Progress = {
  percent: number;
  steps: string[];
  error?: ProgressError | null;
};

export type Meeting = {
  id: string;
  filename: string;
  status: MeetingStatus;
  language: string;
  speakers: string;
  size_bytes: number;
  duration_sec: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type MeetingDetail = Meeting & {
  current_step: number;
  error_step: number | null;
  error_message: string | null;
  progress: Progress;
};

// ----- Hasil (kontrak JSON 1.x) -----
export type Segment = { start: number; end: number; speaker: string | null; text: string };
export type SpeakerInfo = { id: string; label: string };
export type SummaryItem = { text: string; timestamp_sec?: number | null };
export type SummaryTask = {
  text: string;
  owner_speaker?: string | null;
  owner_name?: string | null;
  due_text?: string | null;
  timestamp_sec?: number | null;
};
export type Summary = {
  ringkasan: string;
  keputusan: SummaryItem[];
  tugas: SummaryTask[];
  pertanyaan_terbuka: SummaryItem[];
};
export type ResultWarning = { code: string; message: string; at_sec?: number | null };

/** Lama tiap tahap dalam detik (kunci: audio, vad, stt, diarization, summary). */
export type TimingsSec = Partial<Record<"audio" | "vad" | "stt" | "diarization" | "summary", number>>;

export type PipelineInfo = {
  whisper_model?: string;
  diarization_model?: string;
  llm_model?: string;
  timings_sec?: TimingsSec;
};

export type MeetingResult = {
  schema_version: string;
  pipeline?: PipelineInfo | null;
  speakers: SpeakerInfo[];
  segments: Segment[];
  summary: Summary;
  warnings: ResultWarning[];
};
