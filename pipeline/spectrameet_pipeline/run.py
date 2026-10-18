"""Titik masuk tunggal: process(audio, opsi) menghasilkan JSON hasil."""

from pathlib import Path

from . import errors
from .audio import to_standard_wav
from .checkpoint import Checkpoints, audio_key, segmen_key, stt_key
from .config import settings
from .errors import PipelineError
from .progress import ProgressWriter
from .schema import Result, Segment
from .summarize import Generate, run_stage_5
from .transcribe import Options, require_hf_token, run_diarization, run_stt


def _model_name(step: int) -> str:
    if step == 4:
        return "pembeda pembicara (pyannote)"
    return f"suara ke teks (Whisper {settings.whisper_model})"


def classify(exc: Exception, step: int) -> PipelineError:
    """Ubah galat tak terduga menjadi PipelineError dengan kode dan pesan yang jelas."""
    if isinstance(exc, PipelineError):
        return exc
    text = f"{type(exc).__name__}: {exc}"
    low = text.lower()
    if isinstance(exc, MemoryError) or any(
        k in low for k in ("out of memory", "can't allocate memory", "not enough memory", "bad_alloc")
    ):
        return PipelineError(
            errors.OUT_OF_MEMORY,
            "Memori habis. Tutup aplikasi lain, atau pakai WHISPER_MODEL yang lebih kecil di .env lalu coba lagi.",
            step, text,
        )
    if any(k in low for k in ("401", "403", "gated", "access to model", "repository not found")):
        hint = (
            "Periksa HF_TOKEN dan pastikan lisensi model pyannote sudah disetujui di Hugging Face."
            if step == 4
            else "Periksa HF_TOKEN dan nama WHISPER_MODEL di .env."
        )
        return PipelineError(errors.MODEL_UNAVAILABLE, f"Model {_model_name(step)} tidak bisa diakses. {hint}", step, text)
    if any(k in low for k in (
        "localentrynotfound", "cannot find an appropriate cached snapshot", "outgoing traffic has been disabled",
        "connection", "timed out", "timeout", "offline",
    )):
        return PipelineError(
            errors.MODEL_UNAVAILABLE,
            f"Model {_model_name(step)} belum terunduh dan koneksi ke Hugging Face gagal. "
            "Sambungkan internet lalu coba lagi; unduhan dilanjutkan dari bagian yang sudah ada.",
            step, text,
        )
    return PipelineError(errors.UNKNOWN, "Pemrosesan gagal karena galat tak terduga.", step, text)


def process(
    audio_path: str | Path,
    options: Options | None = None,
    job_id: str = "lokal",
    job_dir: Path | None = None,
    generate: Generate | None = None,
    resume: bool = False,
) -> Result:
    """Jalankan tahap 1-5 untuk satu audio. Menulis progress.json dan hasil.json di `job_dir`.

    Tahap 1-4 yang gagal menghentikan pekerjaan: melempar PipelineError (progress.json
    sudah berisi galatnya). Tahap 5 (LLM) yang gagal atau dilewati tidak menghentikan
    apa pun: transkrip tetap disimpan dan `summary_status` menjelaskan keadaannya.

    Setiap tahap menyimpan hasilnya (lihat checkpoint.py). Dengan `resume=True`, tahap yang
    hasilnya masih berlaku (audio, bahasa, ukuran model, dan opsi sama) dilewati, sehingga
    "coba lagi" mulai dari tahap yang gagal. Tahap 5 selalu dijalankan. Tanpa `resume`,
    semua dihitung ulang dari awal.

    `generate` hanya untuk pengujian (mengganti panggilan Gemini).
    """
    options = options or Options()
    src = Path(audio_path)
    job_dir = Path(job_dir) if job_dir else settings.results_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    wav = job_dir / "audio.wav"
    lang = options.whisper_language

    cp = Checkpoints(job_dir)
    if not resume:
        cp.clear()
    audio_cp = stt_cp = segs_cp = None
    if resume and src.is_file():
        audio_cp = cp.load("audio", audio_key(src)) if wav.is_file() else None
        stt_cp = cp.load("stt", stt_key(src, lang)) if audio_cp else None
        segs_cp = cp.load("segmen", segmen_key(src, lang, options.speakers)) if stt_cp else None

    progress = ProgressWriter(job_dir, job_id)
    first = 1 if not audio_cp else 2 if not stt_cp else 4 if not segs_cp else 5
    if first > 1:
        progress.mark_resumed(first)

    try:
        if not segs_cp:
            require_hf_token()  # gagal cepat, sebelum transkripsi yang makan beberapa menit

        if audio_cp:
            progress.reuse_step(1)
            duration = audio_cp["duration"]
        else:
            progress.start_step(1)
            duration = to_standard_wav(src, wav)
            cp.save("audio", audio_key(src), {"duration": duration})
            progress.finish_step(1)

        if stt_cp:
            language, stt = stt_cp["language"], stt_cp["result"]
            progress.reuse_step(2)
            progress.reuse_step(3)
        else:
            language, stt = run_stt(str(wav), options, progress)
            cp.save("stt", stt_key(src, lang), {"language": language, "result": stt})

        if segs_cp:
            segments = [Segment(**s) for s in segs_cp["segments"]]
            progress.reuse_step(4)
        else:
            segments = run_diarization(str(wav), stt, options, progress)
            cp.save("segmen", segmen_key(src, lang, options.speakers),
                    {"segments": [s.model_dump() for s in segments]})

        status, summary, summary_error = run_stage_5(segments, progress, generate)

        result = Result(
            language=language,
            duration=duration,
            segments=segments,
            summary_status=status,
            summary_error=summary_error,
            **(summary.model_dump() if summary else {}),
        )
        (job_dir / "hasil.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        progress.done()
        return result
    except KeyboardInterrupt:
        progress.fail(PipelineError(errors.CANCELLED, "Pemrosesan dibatalkan.", progress.state.step))
        raise
    except Exception as exc:
        err = classify(exc, progress.state.step)
        progress.fail(err)
        raise err from exc
