"""Status mesin untuk chip di header web: apa yang sudah siap dan apa yang masih kurang."""

import shutil

from app.config import settings
from app.schemas import Health, HealthCheck


def _writable() -> bool:
    try:
        settings.data_path.mkdir(parents=True, exist_ok=True)
        probe = settings.data_path / ".tulis"
        probe.write_text("ok")
        probe.unlink()
        return True
    except OSError:
        return False


def check_health() -> Health:
    real = not settings.use_mock_pipeline
    checks = [
        HealthCheck(
            id="data_dir",
            label="Folder data bisa ditulis",
            ok=_writable(),
            required=True,
            hint=f"Folder {settings.data_path} tidak bisa dibuat atau ditulis.",
            env_var="DATA_DIR",
        )
    ]
    if real:
        py = settings.pipeline_python_path
        checks += [
            HealthCheck(
                id="pipeline_python",
                label="Lingkungan Python pipeline",
                ok=py.is_file(),
                required=True,
                hint=f"Tidak ditemukan di {py}. Siapkan venv pipeline (lihat README bagian Pipeline) atau isi PIPELINE_PYTHON.",
                env_var="PIPELINE_PYTHON",
            ),
            HealthCheck(
                id="ffmpeg",
                label="FFmpeg terpasang",
                ok=shutil.which("ffmpeg") is not None,
                required=True,
                hint="Pasang FFmpeg dan pastikan perintah ffmpeg bisa dijalankan dari terminal.",
            ),
            HealthCheck(
                id="hf_token",
                label="Token Hugging Face (pembeda pembicara)",
                ok=bool(settings.hf_token.strip()),
                required=True,
                hint="Buat token di huggingface.co/settings/tokens dan setujui lisensi model pyannote.",
                env_var="HF_TOKEN",
            ),
            HealthCheck(
                id="llm",
                label="Kunci dan model Gemini (ringkasan)",
                ok=bool(settings.llm_api_key.strip() and settings.llm_model.strip()),
                required=False,
                hint="Tanpa ini transkrip tetap dibuat, tetapi ringkasan dilewati.",
                env_var="LLM_API_KEY",
            ),
        ]
    for c in checks:
        if c.ok:
            c.hint = None  # saran hanya relevan bila pemeriksaan gagal
    return Health(
        ready=all(c.ok for c in checks if c.required),
        mock_pipeline=settings.use_mock_pipeline,
        device=settings.device,
        whisper_model=settings.whisper_model,
        checks=checks,
    )
