"""Pipeline TIRUAN untuk pengembangan web dan API tanpa model AI (USE_MOCK_PIPELINE=true).

Berjalan sebagai proses terpisah, sama seperti pipeline asli, dan menulis berkas yang sama di
folder kerja: progress.json (terus diperbarui) dan hasil.json (di akhir, berbentuk kontrak
docs/contoh-hasil.json).

    python dev/mock_pipeline.py run --audio A --workdir W [--from-step N] [--step-seconds S] [--fail-at-step N]

--fail-at-step N: gagal sekali di tahap N (ditandai berkas .mock_gagal), lalu percobaan berikutnya berhasil.
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "docs" / "contoh-hasil.json"
NAMES = ["Menyiapkan audio", "Mendeteksi suara", "Mengubah suara ke teks", "Mengenali pembicara", "Menyusun kesimpulan"]
TICKS = 4


def write_progress(workdir: Path, state: dict) -> None:
    state["updated_at"] = time.time()
    tmp = workdir / "progress.json.tmp"
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    for _ in range(10):
        try:
            os.replace(tmp, workdir / "progress.json")
            return
        except PermissionError:
            time.sleep(0.05)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--audio", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--language", default="id-en")
    ap.add_argument("--speakers", default="auto")
    ap.add_argument("--from-step", type=int, default=1)
    ap.add_argument("--step-seconds", type=float, default=2.0)
    ap.add_argument("--fail-at-step", type=int, default=0)
    a = ap.parse_args()

    workdir = Path(a.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    marker = workdir / ".mock_gagal"
    print(f"[mock] audio={a.audio} bahasa={a.language} pembicara={a.speakers} dari tahap {a.from_step}", flush=True)

    now = time.time()
    state = {
        "job_id": workdir.name,
        "status": "running",
        "step": a.from_step,
        "percent": 0.0,
        "steps": [
            {"id": i + 1, "name": n, "status": "done" if i + 1 < a.from_step else "pending",
             "started_at": now if i + 1 < a.from_step else None, "ended_at": now if i + 1 < a.from_step else None}
            for i, n in enumerate(NAMES)
        ],
        "resumed_from": a.from_step if a.from_step > 1 else None,
        "started_at": now,
        "error": None,
    }
    write_progress(workdir, state)

    for step in range(a.from_step, 6):
        st = state["steps"][step - 1]
        st.update(status="running", started_at=time.time(), ended_at=None)
        state.update(step=step, percent=0.0)
        write_progress(workdir, state)
        print(f"[tahap {step}] mulai", flush=True)

        failing = a.fail_at_step == step and not marker.exists()
        for tick in range(1, TICKS + 1):
            time.sleep(a.step_seconds / TICKS)
            if failing and tick == TICKS // 2:
                marker.write_text("sudah gagal sekali")
                st.update(status="failed", ended_at=time.time())
                state.update(status="failed", error={
                    "code": "OUT_OF_MEMORY",
                    "message": "Memori habis (simulasi). Tutup aplikasi lain, atau pakai WHISPER_MODEL yang lebih kecil di .env lalu coba lagi.",
                    "step": step,
                    "detail": f"[tahap {step}] ERROR: out of memory (disimulasikan oleh MOCK_FAIL_AT_STEP)",
                })
                write_progress(workdir, state)
                print(f"[tahap {step}] ERROR: out of memory (simulasi)", file=sys.stderr, flush=True)
                return 1
            state["percent"] = tick / TICKS * 100
            write_progress(workdir, state)
        st.update(status="done", ended_at=time.time())
        state["percent"] = 100.0
        write_progress(workdir, state)
        print(f"[tahap {step}] selesai", flush=True)

    shutil.copyfile(SAMPLE, workdir / "hasil.json")
    state["status"] = "done"
    write_progress(workdir, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
