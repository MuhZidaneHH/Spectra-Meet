"""Tahap 2-4 dengan WhisperX: deteksi suara (VAD), suara ke teks, siapa yang bicara.

Dipecah dua agar hasilnya bisa disimpan di antaranya (lihat checkpoint.py):
  run_stt          tahap 2-3  ->  bahasa + hasil WhisperX
  run_diarization  tahap 4    ->  segmen berlabel pembicara

WhisperX menjalankan VAD di dalam `transcribe`, jadi tahap 2 dianggap selesai saat
laporan progres pertama dari tahap suara-ke-teks datang (VAD sudah memotong audio).
"""

from dataclasses import dataclass

from . import errors
from .config import apply_hf_env, settings
from .errors import PipelineError
from .progress import ProgressWriter
from .schema import Segment

# Pilihan form web -> kode bahasa Whisper. "id-en" (campur) memakai "id"; Whisper
# hanya menerima satu bahasa per rekaman, kata Inggris tetap ikut tertranskripsi.
LANGUAGE_MAP = {"id-en": "id", "id": "id", "en": "en"}


@dataclass
class Options:
    language: str = "id-en"  # id-en | id | en
    speakers: str = "auto"  # auto | 2 | 3 | 4 | 5+

    @property
    def whisper_language(self) -> str:
        return LANGUAGE_MAP.get(self.language, "id")

    def speaker_args(self) -> dict:
        if self.speakers == "auto":
            return {}
        if self.speakers.endswith("+"):
            return {"min_speakers": int(self.speakers[:-1])}
        return {"num_speakers": int(self.speakers)}


def require_hf_token() -> None:
    if not settings.hf_token.strip():
        raise PipelineError(
            errors.HF_TOKEN_MISSING,
            "HF_TOKEN belum diisi di .env. Token Hugging Face diperlukan untuk model pembeda pembicara.",
            step=4,
        )


def run_stt(wav_path: str, options: Options, progress: ProgressWriter) -> tuple[str, dict]:
    """Tahap 2-3. Mengembalikan (bahasa, hasil WhisperX dengan segmen dan kata)."""
    apply_hf_env()
    progress.start_step(2)
    import whisperx  # berat; diimpor di sini agar `--help` dan tes ringan tetap cepat

    device = settings.device
    language = options.whisper_language
    audio = whisperx.load_audio(wav_path)

    model = whisperx.load_model(
        settings.whisper_model,
        device,
        compute_type=settings.effective_compute_type,
        language=language,
    )

    state = {"in_stt": False}

    def on_stt(percent: float) -> None:
        if not state["in_stt"]:
            state["in_stt"] = True
            progress.finish_step(2)
            progress.start_step(3)
        # 0-100 untuk transkripsi saja; alignment dihitung sisa 10% bila aktif
        progress.update(percent * (0.9 if settings.align else 1.0))

    result = model.transcribe(
        audio,
        batch_size=16 if device == "cuda" else 8,
        language=language,
        progress_callback=on_stt,
    )
    if not state["in_stt"]:  # tidak ada ucapan terdeteksi, callback tidak pernah dipanggil
        progress.finish_step(2)
        progress.start_step(3)
    detected = result.get("language", language)
    del model

    if settings.align and result["segments"]:
        align_model, metadata = whisperx.load_align_model(language_code=detected, device=device)
        result = whisperx.align(
            result["segments"], align_model, metadata, audio, device,
            progress_callback=lambda p: progress.update(90 + p * 0.1),
        )
        del align_model
    progress.finish_step(3)
    return detected, result


def run_diarization(wav_path: str, stt_result: dict, options: Options, progress: ProgressWriter) -> list[Segment]:
    """Tahap 4. Memberi label pembicara pada hasil tahap 3."""
    apply_hf_env()
    require_hf_token()
    progress.start_step(4)
    import whisperx
    from whisperx.diarize import DiarizationPipeline

    audio = whisperx.load_audio(wav_path)
    diarizer = DiarizationPipeline(token=settings.hf_token, device=settings.device)
    diarization = diarizer(audio, progress_callback=progress.update, **options.speaker_args())
    result = whisperx.assign_word_speakers(diarization, stt_result)
    progress.finish_step(4)

    return [
        Segment(
            start=float(s["start"]),
            end=float(s["end"]),
            speaker=s.get("speaker", "UNKNOWN"),
            text=s["text"].strip(),
        )
        for s in result["segments"]
        if s.get("text", "").strip()
    ]
