"""Model data pipeline. DRAF: menunggu disahkan di docs/kontrak-json.md (PM + Dev 1 + Dev 2).

Dua berkas keluaran per job, di data/hasil/<job_id>/:
  - progress.json  : `Progress`, ditulis terus selama pipeline berjalan
  - hasil.json     : `Result`, ditulis sekali di akhir
"""

from typing import Literal

from pydantic import BaseModel, Field

STEP_NAMES = [
    "Menyiapkan audio",
    "Mendeteksi suara",
    "Mengubah suara ke teks",
    "Mengenali pembicara",
    "Menyusun kesimpulan",
]

StepStatus = Literal["pending", "running", "done", "skipped", "failed"]
JobStatus = Literal["running", "done", "failed"]


class Segment(BaseModel):
    start: float  # detik dari awal audio
    end: float
    speaker: str  # "SPEAKER_00", "SPEAKER_01", ... atau "UNKNOWN"
    text: str


class Task(BaseModel):
    description: str
    owner: str | None = None
    due: str | None = None


class Summary(BaseModel):
    """Jawaban LLM (tahap 5). Nama field ini juga yang diminta dari LLM."""

    summary: str
    decisions: list[str] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


SummaryStatus = Literal["ok", "skipped", "failed"]


class Result(BaseModel):
    version: int = 1
    language: str  # kode bahasa terdeteksi atau dipilih, mis. "id"
    duration: float  # detik
    segments: list[Segment]
    # Tahap 5 (LLM). Transkrip tetap dihasilkan walau tahap ini dilewati atau gagal.
    #   ok      : summary dan lainnya terisi
    #   skipped : LLM belum dikonfigurasi atau tidak ada ucapan; summary = None
    #   failed  : LLM gagal; summary = None dan summary_error berisi alasannya
    summary_status: SummaryStatus = "skipped"
    summary_error: str | None = None
    summary: str | None = None
    decisions: list[str] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class StepState(BaseModel):
    id: int  # 1-5
    name: str
    status: StepStatus = "pending"
    started_at: float | None = None  # epoch detik
    ended_at: float | None = None


class ErrorInfo(BaseModel):
    code: str
    message: str
    step: int | None = None
    detail: str = ""


class Progress(BaseModel):
    job_id: str
    status: JobStatus = "running"
    step: int = 1  # tahap yang sedang atau terakhir berjalan
    percent: float = 0.0  # 0-100 untuk tahap itu, bila diketahui
    steps: list[StepState] = Field(
        default_factory=lambda: [StepState(id=i + 1, name=n) for i, n in enumerate(STEP_NAMES)]
    )
    # Diisi bila pekerjaan dilanjutkan dari hasil sebelumnya: tahap pertama yang dihitung ulang.
    # Tahap sebelumnya langsung `done` karena hasilnya dipakai ulang.
    resumed_from: int | None = None
    started_at: float | None = None
    updated_at: float | None = None
    error: ErrorInfo | None = None
