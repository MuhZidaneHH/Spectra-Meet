"""Tahap 1: ubah audio apa pun ke WAV standar (16 kHz, mono) dengan FFmpeg."""

import shutil
import subprocess
from pathlib import Path

from . import errors
from .errors import PipelineError


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise PipelineError(
            errors.FFMPEG_MISSING,
            "FFmpeg tidak ditemukan. Pasang FFmpeg dan pastikan perintah `ffmpeg` bisa dijalankan.",
            step=1,
        )
    return path


def probe_duration(path: Path) -> float:
    """Durasi dalam detik dari WAV hasil konversi."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise PipelineError(errors.FFMPEG_MISSING, "ffprobe tidak ditemukan (ikut paket FFmpeg).", step=1)
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        raise PipelineError(errors.AUDIO_UNREADABLE, "Durasi audio tidak terbaca.", step=1, detail=out.stderr[-500:])


def to_standard_wav(src: Path, dst: Path) -> float:
    """Tulis `dst` sebagai WAV 16 kHz mono 16-bit. Mengembalikan durasi (detik)."""
    if not src.is_file():
        raise PipelineError(errors.AUDIO_NOT_FOUND, f"File audio tidak ditemukan: {src}", step=1)
    ffmpeg = find_ffmpeg()
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0 or not dst.is_file() or dst.stat().st_size < 1000:
        raise PipelineError(
            errors.AUDIO_UNREADABLE,
            "File audio rusak atau formatnya tidak dikenali.",
            step=1,
            detail=proc.stderr[-1000:],
        )
    return probe_duration(dst)
