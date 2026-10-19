"""Satu-satunya tempat API membaca konfigurasi.

Semua nilai berasal dari file `.env` di akar repo (lihat `.env.example`).
Modul lain cukup `from app.config import settings`. Jangan membaca os.environ
atau menulis angka/jalur langsung di kode.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pilihan di form halaman Audio. Dikirim ke web lewat GET /api/config,
# jadi web tidak punya salinan sendiri. (value, label)
LANGUAGES = [
    ("id-en", "Indonesia + Inggris (campur)"),
    ("id", "Indonesia"),
    ("en", "Inggris"),
]
SPEAKER_OPTIONS = [
    ("auto", "Otomatis (disarankan)"),
    ("2", "2"),
    ("3", "3"),
    ("4", "4"),
    ("5+", "5+"),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Umum
    api_port: int = 8000
    data_dir: str = "data"

    # Unggahan
    max_upload_mb: int = 200
    allowed_extensions: str = "mp3,wav,m4a,webm,ogg,flac"
    poll_interval_ms: int = 1500

    # Pipeline
    use_mock_pipeline: bool = True
    pipeline_python: str = ""  # kosong = otomatis sesuai sistem operasi (lihat pipeline_python_path)
    mock_step_seconds: float = 2.0  # hanya pipeline tiruan
    mock_fail_at_step: int = 0  # hanya pipeline tiruan; 0 = tidak gagal

    # LLM dan suara ke teks (dibaca pipeline, diperiksa di sini untuk status)
    llm_api_key: str = ""
    llm_model: str = ""
    hf_token: str = ""
    whisper_model: str = "small"
    device: str = "cpu"

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def results_dir(self) -> Path:
        return self.data_path / "hasil"

    @property
    def extensions(self) -> list[str]:
        return [e.strip().lower().lstrip(".") for e in self.allowed_extensions.split(",") if e.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def pipeline_python_path(self) -> Path:
        """Python milik pipeline. Bila PIPELINE_PYTHON kosong: lokasi venv standar di sistem ini."""
        if not self.pipeline_python.strip():
            venv_python = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
            return REPO_ROOT / "pipeline" / ".venv" / venv_python
        path = Path(self.pipeline_python)
        return path if path.is_absolute() else REPO_ROOT / path


settings = Settings()
