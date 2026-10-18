"""Galat pipeline dengan kode tetap, supaya web dapat menampilkan pesan yang jelas."""


class PipelineError(Exception):
    """Galat yang dipahami pipeline. `code` tetap, `message` untuk pengguna."""

    def __init__(self, code: str, message: str, step: int | None = None, detail: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.step = step
        self.detail = detail


# Kode galat (daftar ini dipakai juga oleh docs/kontrak-json.md)
AUDIO_NOT_FOUND = "AUDIO_NOT_FOUND"
FFMPEG_MISSING = "FFMPEG_MISSING"
AUDIO_UNREADABLE = "AUDIO_UNREADABLE"
HF_TOKEN_MISSING = "HF_TOKEN_MISSING"
MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
OUT_OF_MEMORY = "OUT_OF_MEMORY"
CANCELLED = "CANCELLED"  # dihentikan pengguna (Ctrl+C atau sinyal berhenti)
LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"  # kunci atau model LLM belum diisi
LLM_AUTH = "LLM_AUTH"  # kunci ditolak
LLM_MODEL_NOT_FOUND = "LLM_MODEL_NOT_FOUND"
LLM_QUOTA = "LLM_QUOTA"  # kuota habis atau terlalu cepat
LLM_OVERLOADED = "LLM_OVERLOADED"  # Gemini sibuk (503); sudah dicoba ulang otomatis
LLM_UNREACHABLE = "LLM_UNREACHABLE"
LLM_BAD_OUTPUT = "LLM_BAD_OUTPUT"  # jawaban bukan JSON yang sesuai, juga setelah dicoba ulang
LLM_FAILED = "LLM_FAILED"
UNKNOWN = "UNKNOWN"
