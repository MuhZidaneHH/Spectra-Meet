"""Database SQLite lokal (data/spectrameet.db). Satu tabel: meetings.

Skema sama dengan database yang sudah ada di komputer pengguna, jadi rekaman lama tetap terbaca.
Detail galat (kode, log) tidak disimpan di sini: dibaca dari data/hasil/<id>/ saat dibutuhkan.
"""

from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, create_engine

from app.config import settings

# Status meeting: uploaded -> processing -> done | failed | cancelled

def utcnow() -> datetime:
    """Waktu UTC dengan zona (SQLModel mewajibkannya). Dikirim ke web dengan akhiran Z."""
    return datetime.now(timezone.utc)


class Meeting(SQLModel, table=True):
    __tablename__ = "meetings"

    id: str = Field(primary_key=True)
    filename: str
    audio_path: str  # relatif terhadap DATA_DIR, mis. audio/<id>/original.m4a
    size_bytes: int
    duration_sec: float | None = None
    language: str
    speakers: str
    status: str = "uploaded"
    current_step: int = 0
    error_step: int | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


_engines: dict[str, Engine] = {}


def get_engine() -> Engine:
    """Satu engine per berkas database (berubah hanya saat tes memindahkan DATA_DIR)."""
    path = settings.data_path / "spectrameet.db"
    key = str(path)
    if key not in _engines:
        path.parent.mkdir(parents=True, exist_ok=True)
        _engines[key] = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    return _engines[key]


def init_db() -> None:
    """Membuat tabel bila belum ada. Aman dipanggil berulang."""
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
