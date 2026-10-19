"""Kontrak hasil (docs/kontrak-json.md, versi 1.x) dan penyesuaian keluaran pipeline ke kontrak.

Aturan pemeriksaan: yang wajib hanya yang dibutuhkan tampilan (`segments` dan `summary.ringkasan`).
Kunci tambahan dari pipeline diterima dan diteruskan apa adanya. Galat menyebut jalur field
(mis. `segments.2.start`) supaya pembuat pipeline tahu persis apa yang salah.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import settings

SUPPORTED_MAJOR = "1"
SCHEMA_VERSION = "1.0"


class ContractError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


class _Loose(BaseModel):
    model_config = ConfigDict(extra="allow")


class Segment(_Loose):
    start: float
    end: float
    speaker: str | None = None
    text: str


class SpeakerInfo(_Loose):
    id: str
    label: str


class Item(_Loose):
    text: str
    timestamp_sec: float | None = None


class Task(_Loose):
    text: str
    owner_speaker: str | None = None
    due_text: str | None = None
    timestamp_sec: float | None = None


class Summary(_Loose):
    ringkasan: str
    keputusan: list[Item] = []
    tugas: list[Task] = []
    pertanyaan_terbuka: list[Item] = []


class Warning_(_Loose):
    code: str
    message: str
    at_sec: float | None = None


class Result(_Loose):
    schema_version: str = SCHEMA_VERSION
    is_sample: bool | None = None
    meeting: dict[str, Any] | None = None
    pipeline: dict[str, Any] | None = None
    speakers: list[SpeakerInfo] = []
    segments: list[Segment]
    summary: Summary
    warnings: list[Warning_] = []


def validate_result(data: Any) -> dict:
    """Memeriksa hasil terhadap kontrak. Mengembalikan dict siap kirim, atau melempar ContractError."""
    if not isinstance(data, dict):
        raise ContractError(["hasil.json harus berupa objek JSON"])
    version = str(data.get("schema_version", SCHEMA_VERSION))
    if version.split(".")[0] != SUPPORTED_MAJOR:
        raise ContractError([f"schema_version: versi {version} tidak didukung; web memahami {SUPPORTED_MAJOR}.x"])
    try:
        return Result.model_validate(data).model_dump(mode="json")
    except ValidationError as exc:
        problems = [".".join(str(p) for p in e["loc"]) + f": {e['msg']}" for e in exc.errors()]
        raise ContractError(problems) from exc


# ----- Penyesuaian keluaran pipeline (Dev 2) ke kontrak ------------------------------------------
# pipeline/spectrameet_pipeline/schema.py kini menulis bentuk datar berbahasa Inggris
# (summary: str, decisions, tasks, open_questions). Kontrak memakai bentuk bersarang. Selama
# keduanya belum disamakan (butuh persetujuan PM + Dev 1 + Dev 2), API menjembatani di sini.

_SPEAKER_LABEL = "Pembicara {n}"
_STEP_KEYS = ["audio", "vad", "stt", "diarization", "summary"]


def _timings(progress: dict | None) -> dict[str, float]:
    out: dict[str, float] = {}
    steps = (progress or {}).get("steps")
    if isinstance(steps, list):
        for key, st in zip(_STEP_KEYS, steps):
            if isinstance(st, dict) and st.get("started_at") and st.get("ended_at"):
                out[key] = round(float(st["ended_at"]) - float(st["started_at"]), 1)
    return out


def to_contract(raw: Any, *, meeting_id: str, filename: str, created_at: str, progress: dict | None = None) -> Any:
    """Bentuk hasil pipeline menjadi bentuk kontrak. Hasil yang sudah berbentuk kontrak (ada
    `schema_version`) diteruskan tanpa diubah, supaya penyamaan nanti tidak butuh perubahan di sini."""
    if not isinstance(raw, dict) or "schema_version" in raw:
        return raw

    segments = []
    ids: list[str] = []
    for s in raw.get("segments") or []:
        if not isinstance(s, dict):
            segments.append(s)
            continue
        sp = s.get("speaker")
        sp = None if sp in (None, "", "UNKNOWN") else sp
        if sp and sp not in ids:
            ids.append(sp)
        segments.append({**s, "speaker": sp})
    ids.sort()
    speakers = [{"id": i, "label": _SPEAKER_LABEL.format(n=n + 1)} for n, i in enumerate(ids)]

    tasks = []
    for t in raw.get("tasks") or []:
        if not isinstance(t, dict):
            tasks.append(t)
            continue
        owner = t.get("owner")
        item: dict[str, Any] = {
            "owner_speaker": owner if owner in ids else None,
            "text": t.get("description", ""),
            "due_text": t.get("due"),
            "timestamp_sec": None,
        }
        if owner and owner not in ids:
            item["owner_name"] = owner  # nama yang disebut di transkrip, bukan ID pembicara
        tasks.append(item)

    summary = raw.get("summary")
    return {
        "schema_version": SCHEMA_VERSION,
        "meeting": {
            "id": meeting_id,
            "title": filename,
            "audio_file": filename,
            "duration_sec": raw.get("duration"),
            "language": raw.get("language"),
            "created_at": created_at,
        },
        "pipeline": {
            "whisper_model": settings.whisper_model,
            "diarization_model": "pyannote/speaker-diarization-community-1",
            "llm_model": settings.llm_model,
            "timings_sec": _timings(progress),
        },
        "speakers": speakers,
        "segments": segments,
        "summary": {
            "ringkasan": summary if isinstance(summary, str) else "",
            "keputusan": [{"text": d, "timestamp_sec": None} for d in raw.get("decisions") or []],
            "tugas": tasks,
            "pertanyaan_terbuka": [{"text": q, "timestamp_sec": None} for q in raw.get("open_questions") or []],
        },
        "warnings": [],
        "summary_status": raw.get("summary_status"),
        "summary_error": raw.get("summary_error"),
    }
