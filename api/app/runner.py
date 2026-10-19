"""Menjalankan pipeline sebagai proses terpisah dan menyelesaikan catatan di database.

Satu pekerjaan pada satu waktu (laptop biasa tidak kuat dua sekaligus). Pipeline asli dan
tiruan sama-sama berjalan sebagai subproses yang menulis data/hasil/<id>/progress.json dan
hasil.json; log-nya masuk log.txt di folder yang sama.
"""

import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

from sqlmodel import Session, select

from app.config import REPO_ROOT, settings
from app.db import Meeting, get_engine, utcnow

# Kode galat pipeline (errors.py Dev 2) -> kode di kontrak (docs/kontrak-json.md bagian 2).
CODE_MAP = {
    "FFMPEG_MISSING": "FFMPEG_NOT_FOUND",
    "AUDIO_UNREADABLE": "AUDIO_UNREADABLE",
    "HF_TOKEN_MISSING": "HF_TOKEN_MISSING",
    "MODEL_UNAVAILABLE": "MODEL_DOWNLOAD_FAILED",
    "OUT_OF_MEMORY": "OUT_OF_MEMORY",
    "LLM_AUTH": "LLM_AUTH_FAILED",
    "LLM_UNREACHABLE": "LLM_TIMEOUT",
    "LLM_BAD_OUTPUT": "LLM_BAD_OUTPUT",
}


class StartError(Exception):
    """Pekerjaan tidak bisa dimulai (pipeline tidak ada atau tidak bisa dijalankan)."""


class Busy(StartError):
    """Masih ada pekerjaan lain yang berjalan."""


def job_dir(meeting_id: str) -> Path:
    return settings.results_dir / meeting_id


def read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def log_tail(meeting_id: str, lines: int = 15) -> str:
    try:
        text = (job_dir(meeting_id) / "log.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.strip().splitlines()[-lines:])


def _kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


# Kode keluar Windows untuk crash native (access violation, stack buffer overrun). Di laptop dengan memori mepet
# penyebab paling umumnya memori habis di tengah memuat model.
_NATIVE_CRASH_CODES = {0xC0000005, 0xC0000409}
_OOM_MARKERS = ("memori habis", "memory allocation", "out of memory", "cannot allocate memory", "bad_alloc", "not enough memory")
OOM_MESSAGE = (
    "Memori komputer tidak cukup untuk memuat model. Tutup aplikasi lain (browser, editor), "
    "tambah ukuran pagefile Windows, atau pakai WHISPER_MODEL yang lebih kecil di .env, lalu coba lagi."
)


def looks_like_oom(meeting_id: str) -> bool:
    """Pipeline yang mati karena memori kadang tidak sempat menulis galatnya (galat native, mis. OpenBLAS)."""
    return any(k in log_tail(meeting_id, 40).lower() for k in _OOM_MARKERS)


class Runner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._procs: dict[str, subprocess.Popen] = {}
        self._cancelled: set[str] = set()
        self._threads: dict[str, threading.Thread] = {}

    # ----- status -------------------------------------------------------------------------------
    def active_id(self) -> str | None:
        with self._lock:
            for mid, proc in self._procs.items():
                if proc.poll() is None:
                    return mid
        return None

    def is_running(self, meeting_id: str) -> bool:
        with self._lock:
            proc = self._procs.get(meeting_id)
        return proc is not None and proc.poll() is None

    def wait(self, meeting_id: str, timeout: float = 30) -> None:
        """Menunggu penyelesaian (dipakai tes)."""
        t = self._threads.get(meeting_id)
        if t:
            t.join(timeout)

    # ----- perintah -----------------------------------------------------------------------------
    def _command(self, m: Meeting, first_step: int, resume: bool) -> tuple[list[str], Path]:
        audio = settings.data_path / m.audio_path
        if settings.use_mock_pipeline:
            cmd = [
                sys.executable, str(REPO_ROOT / "api" / "dev" / "mock_pipeline.py"), "run",
                "--audio", str(audio), "--workdir", str(job_dir(m.id)),
                "--language", m.language, "--speakers", m.speakers,
                "--from-step", str(first_step),
                "--step-seconds", str(settings.mock_step_seconds),
                "--fail-at-step", str(settings.mock_fail_at_step),
            ]
            return cmd, REPO_ROOT / "api"
        cmd = [
            str(settings.pipeline_python_path), "-m", "spectrameet_pipeline.cli", str(audio),
            "--job-id", m.id, "--language", m.language, "--speakers", m.speakers,
        ]
        if resume:
            cmd.append("--resume")
        return cmd, REPO_ROOT / "pipeline"

    def start(self, m: Meeting, *, resume: bool = False) -> None:
        """Memulai pekerjaan. `resume`: lanjut dari tahap yang gagal (hasil tahap sebelumnya dipakai ulang)."""
        with self._lock:
            if any(p.poll() is None for p in self._procs.values()):
                raise Busy("Masih ada rekaman lain yang sedang diproses. Tunggu sampai selesai atau batalkan dulu.")
            first_step = max(1, m.error_step or 1) if resume else 1
            wd = job_dir(m.id)
            wd.mkdir(parents=True, exist_ok=True)
            if not resume:
                (wd / "progress.json").unlink(missing_ok=True)
                (wd / "hasil.json").unlink(missing_ok=True)

            if not settings.use_mock_pipeline and not settings.pipeline_python_path.is_file():
                raise StartError(
                    f"Pipeline asli belum terpasang: {settings.pipeline_python_path} tidak ditemukan. "
                    "Siapkan venv pipeline (lihat README) atau set USE_MOCK_PIPELINE=true di .env."
                )

            cmd, cwd = self._command(m, first_step, resume)
            log = open(wd / "log.txt", "a", encoding="utf-8")
            log.write(f"[api] {utcnow().isoformat()}Z menjalankan: {' '.join(cmd)}\n")
            log.flush()
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            kwargs: dict = {}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True
            try:
                proc = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env, **kwargs)
            except OSError as exc:
                log.close()
                raise StartError(f"Pipeline tidak bisa dijalankan: {exc}") from exc

            self._procs[m.id] = proc
            self._cancelled.discard(m.id)
            thread = threading.Thread(target=self._watch, args=(m.id, proc, log), daemon=True)
            self._threads[m.id] = thread
            thread.start()

    def cancel(self, meeting_id: str) -> None:
        with self._lock:
            proc = self._procs.get(meeting_id)
            if proc is None or proc.poll() is not None:
                return
            self._cancelled.add(meeting_id)
        _kill_tree(proc)

    def shutdown(self) -> None:
        """Dipanggil saat API berhenti: jangan meninggalkan pipeline yatim."""
        with self._lock:
            procs = list(self._procs.values())
        for proc in procs:
            _kill_tree(proc)

    # ----- penyelesaian -------------------------------------------------------------------------
    def _watch(self, meeting_id: str, proc: subprocess.Popen, log) -> None:
        code = proc.wait()
        log.close()
        with self._lock:
            cancelled = meeting_id in self._cancelled
        if not cancelled and (code & 0xFFFFFFFF) in _NATIVE_CRASH_CODES:
            try:
                with open(job_dir(meeting_id) / "log.txt", "a", encoding="utf-8") as f:
                    f.write(f"[api] Pipeline mati mendadak (kode keluar {code & 0xFFFFFFFF:#x}): kemungkinan memori habis.\n")
            except OSError:
                pass
        self._finish(meeting_id, code, cancelled)

    def _finish(self, meeting_id: str, code: int, cancelled: bool) -> None:
        progress = read_json(job_dir(meeting_id) / "progress.json") or {}
        with Session(get_engine()) as db:
            m = db.get(Meeting, meeting_id)
            if m is None:
                return
            m.finished_at = utcnow()
            if cancelled:
                m.status, m.error_step, m.error_message = "cancelled", None, None
            elif code == 0 and (job_dir(meeting_id) / "hasil.json").is_file():
                m.status, m.error_step, m.error_message = "done", None, None
                m.current_step = 5
            else:
                err = progress.get("error") if isinstance(progress.get("error"), dict) else None
                step = (err or {}).get("step") or progress.get("step") or m.current_step or 1
                m.status = "failed"
                m.error_step = int(step)
                if err and err.get("message"):
                    m.error_message = str(err["message"])
                elif code != 0 and looks_like_oom(meeting_id):
                    m.error_message = OOM_MESSAGE
                elif code == 0:
                    m.error_message = "Pipeline selesai tetapi tidak menghasilkan berkas hasil.json."
                else:
                    m.error_message = f"Pipeline berhenti tak terduga (kode keluar {code}). Lihat log di bawah."
            db.add(m)
            db.commit()

    def fail_orphans(self) -> int:
        """Saat API menyala: pekerjaan yang tercatat `processing` tetapi prosesnya sudah tidak ada."""
        with Session(get_engine()) as db:
            rows = db.exec(select(Meeting).where(Meeting.status == "processing")).all()
            for m in rows:
                if self.is_running(m.id):
                    continue
                m.status, m.finished_at = "failed", utcnow()
                m.error_step = m.current_step or 1
                m.error_message = "Proses terhenti karena API dimatikan atau dijalankan ulang. Audio tetap tersimpan; coba lagi."
                db.add(m)
            db.commit()
            return len(rows)


runner = Runner()
