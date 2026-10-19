"""Bentuk respons API. Dari sinilah OpenAPI dibuat, dan web memakai tipe yang sama (web/src/lib/types.ts)."""

from datetime import datetime, timezone

from pydantic import BaseModel, field_serializer

from app.db import Meeting


def _iso_utc(value: datetime | None) -> str | None:
    """Waktu di database adalah UTC tanpa zona; kirim dengan akhiran Z supaya browser tidak salah baca."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class Option(BaseModel):
    value: str
    label: str


class PublicConfig(BaseModel):
    extensions: list[str]
    max_upload_mb: int
    poll_interval_ms: int
    languages: list[Option]
    speaker_options: list[Option]


class HealthCheck(BaseModel):
    id: str
    label: str
    ok: bool
    required: bool
    hint: str | None = None
    env_var: str | None = None


class Health(BaseModel):
    ready: bool
    mock_pipeline: bool
    device: str
    whisper_model: str
    checks: list[HealthCheck]


class ProgressError(BaseModel):
    code: str
    hint: str | None = None
    log_tail: str | None = None


class Progress(BaseModel):
    percent: int  # 0-100 untuk seluruh pekerjaan
    steps: list[str]  # lima status: waiting | running | done | failed
    error: ProgressError | None = None


class MeetingOut(BaseModel):
    id: str
    filename: str
    status: str
    language: str
    speakers: str
    size_bytes: int
    duration_sec: float | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_serializer("created_at", "started_at", "finished_at")
    def _ser(self, value: datetime | None) -> str | None:
        return _iso_utc(value)

    @classmethod
    def of(cls, m: Meeting) -> "MeetingOut":
        return cls(**{k: getattr(m, k) for k in cls.model_fields})


class MeetingDetail(MeetingOut):
    current_step: int
    error_step: int | None = None
    error_message: str | None = None
    progress: Progress
