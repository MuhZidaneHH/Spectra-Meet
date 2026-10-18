"""Hasil antar tahap, disimpan di folder job agar kegagalan tidak mengulang tahap yang sudah selesai.

Tiga checkpoint, masing-masing membawa `key` (apa yang menghasilkannya). Checkpoint hanya
dipakai ulang bila key-nya sama dengan key sekarang, jadi mengganti audio, bahasa, ukuran
model, atau opsi alignment otomatis membuat tahap itu dihitung ulang.

  audio.json   tahap 1    durasi audio.wav
  stt.json     tahap 2-3  bahasa + hasil WhisperX (segmen dan kata)
  segmen.json  tahap 4    segmen berlabel pembicara (masukan tahap 5)

Berkas yang rusak atau tidak cocok dianggap tidak ada.
"""

import json
import os
from pathlib import Path
from typing import Any

from .config import settings

NAMES = ("audio", "stt", "segmen")  # urutan tahap; menghapus satu menghapus yang sesudahnya


def _plain(obj: Any):
    """Ubah tipe numpy/torch dari WhisperX menjadi tipe JSON biasa."""
    if hasattr(obj, "item"):
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    raise TypeError(f"Tidak bisa diserialkan ke JSON: {type(obj).__name__}")


def audio_key(src: Path) -> dict:
    st = src.stat()
    return {"path": str(src.resolve()), "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def stt_key(src: Path, whisper_language: str) -> dict:
    return {
        "audio": audio_key(src),
        "language": whisper_language,
        "model": settings.whisper_model,
        "align": settings.align,
    }


def segmen_key(src: Path, whisper_language: str, speakers: str) -> dict:
    return {"stt": stt_key(src, whisper_language), "speakers": speakers}


class Checkpoints:
    def __init__(self, job_dir: Path):
        self.dir = job_dir

    def _path(self, name: str) -> Path:
        return self.dir / f"{name}.json"

    def save(self, name: str, key: dict, payload: Any) -> None:
        # Menyimpan tahap N membuat checkpoint tahap sesudahnya tidak berlaku lagi.
        self.remove(*NAMES[NAMES.index(name) + 1 :])
        tmp = self._path(name).with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"key": key, "data": payload}, default=_plain, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path(name))

    def load(self, name: str, key: dict) -> Any | None:
        try:
            stored = json.loads(self._path(name).read_text(encoding="utf-8"))
            if stored["key"] == json.loads(json.dumps(key)):
                return stored["data"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def remove(self, *names: str) -> None:
        for name in names:
            self._path(name).unlink(missing_ok=True)

    def clear(self) -> None:
        self.remove(*NAMES)
