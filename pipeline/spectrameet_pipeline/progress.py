"""Menulis progres tahap 1-5 ke progress.json. API membacanya dengan polling.

Berkas ditulis lewat berkas sementara lalu diganti, supaya pembaca tidak pernah
melihat JSON setengah jadi. Di Windows penggantian bisa gagal sesaat bila API
sedang membuka berkas, jadi dicoba ulang.
"""

import os
import time
from pathlib import Path

from .errors import PipelineError
from .schema import ErrorInfo, Progress


class ProgressWriter:
    def __init__(self, job_dir: Path, job_id: str):
        self.path = job_dir / "progress.json"
        self.state = Progress(job_id=job_id, started_at=time.time())
        self._write()

    def start_step(self, step: int) -> None:
        now = time.time()
        s = self.state.steps[step - 1]
        s.status, s.started_at, s.ended_at = "running", now, None
        self.state.step, self.state.percent = step, 0.0
        self._write()

    def mark_resumed(self, first_recomputed_step: int) -> None:
        self.state.resumed_from = first_recomputed_step
        self._write()

    def reuse_step(self, step: int) -> None:
        """Tahap ini tidak dihitung ulang: hasil sebelumnya dipakai, langsung `done`."""
        self.start_step(step)
        self.finish_step(step)

    def update(self, percent: float) -> None:
        self.state.percent = max(0.0, min(100.0, float(percent)))
        self._write()

    def finish_step(self, step: int, skipped: bool = False) -> None:
        s = self.state.steps[step - 1]
        s.status = "skipped" if skipped else "done"
        s.ended_at = time.time()
        if s.started_at is None:
            s.started_at = s.ended_at
        self.state.percent = 100.0
        self._write()

    def done(self) -> None:
        self.state.status = "done"
        self._write()

    def fail(self, error: PipelineError) -> None:
        step = error.step or self.state.step
        self.state.status = "failed"
        self.state.steps[step - 1].status = "failed"
        self.state.steps[step - 1].ended_at = time.time()
        self.state.error = ErrorInfo(
            code=error.code, message=error.message, step=step, detail=error.detail
        )
        self._write()

    def fail_step_softly(self, step: int, error: PipelineError) -> None:
        """Tahap gagal tetapi pekerjaan lanjut (tahap 5: transkrip tetap berguna).

        Tahap ditandai `failed` dan `error` diisi, sedangkan status pekerjaan tetap
        berjalan dan akhirnya `done`.
        """
        s = self.state.steps[step - 1]
        s.status = "failed"
        s.ended_at = time.time()
        if s.started_at is None:
            s.started_at = s.ended_at
        self.state.error = ErrorInfo(
            code=error.code, message=error.message, step=step, detail=error.detail
        )
        self._write()

    def _write(self) -> None:
        self.state.updated_at = time.time()
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")
        for attempt in range(10):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.05)
