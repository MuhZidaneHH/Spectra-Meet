"""Satu-satunya tempat pipeline membaca konfigurasi.

Nilai berasal dari `.env` di akar repo (lihat `.env.example`). Modul lain cukup
`from .config import settings`.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: str = "data"

    llm_provider: str = "google"
    llm_api_key: str = ""
    llm_model: str = ""

    hf_token: str = ""
    whisper_model: str = "small"
    device: str = "cpu"
    compute_type: str = ""  # kosong = int8 di cpu, float16 di cuda
    align: bool = True  # False = lewati alignment kata (lebih cepat, tanpa unduh model align)

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def models_path(self) -> Path:
        return self.data_path / "models"

    @property
    def results_path(self) -> Path:
        return self.data_path / "hasil"

    @property
    def effective_compute_type(self) -> str:
        if self.compute_type.strip():
            return self.compute_type.strip()
        return "float16" if self.device == "cuda" else "int8"


settings = Settings()


def apply_hf_env() -> None:
    """Simpan cache model di data/models dan atur unduhan Hugging Face.

    Terukur di Windows (18 Okt): timeout bawaan 10 detik membuat unduhan macet
    di 0 byte pada jaringan lambat, dan klien xet ikut macet. Nilai yang sudah
    diisi pengguna di lingkungan tidak ditimpa.

    DISABLE_SAFETENSORS_CONVERSION: tanpa ini transformers menjalankan thread yang
    mengunduh konversi safetensors model alignment (sekitar 1,2 GB lagi) dan
    proses pipeline tidak mau keluar sampai unduhan itu selesai.
    """
    os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "true")
    os.environ.setdefault("HF_HOME", str(settings.models_path))
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
    os.environ.setdefault("PYTHONUTF8", "1")
