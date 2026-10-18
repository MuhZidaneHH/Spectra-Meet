"""Tahap 5: satu panggilan LLM (Gemini) untuk ringkasan, keputusan, tugas, dan pertanyaan terbuka.

Transkrip dari tahap 2-4 tetap dipakai walau tahap ini gagal. Karena itu `run_stage_5`
tidak melempar galat: ia mengembalikan status `ok`, `skipped`, atau `failed`.
"""

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

from . import errors
from .config import settings
from .errors import PipelineError
from .progress import ProgressWriter
from .schema import Segment, Summary, SummaryStatus

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "ringkasan.md"
MAX_ATTEMPTS = 2  # percobaan pertama + satu kali coba ulang dengan catatan perbaikan
# Jeda (detik) sebelum tiap percobaan ulang bila Gemini sedang sibuk. Terukur 18 Okt: model
# gemini-3.8-flash membalas "503 UNAVAILABLE, high demand" sesaat, lalu pulih.
RETRY_DELAYS = (3.0, 10.0)
TRANSIENT_MARKERS = ("503", "unavailable", "high demand", "500", "internal", "overloaded", "502", "504")

Generate = Callable[[str, str], str]  # (instruksi sistem, transkrip) -> teks jawaban


def load_prompt() -> str:
    """Isi prompts/ringkasan.md tanpa komentar HTML (catatan untuk penulis prompt)."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def format_transcript(segments: list[Segment]) -> str:
    lines = []
    for s in segments:
        m, sec = divmod(int(s.start), 60)
        lines.append(f"[{m:02d}:{sec:02d}] {s.speaker}: {s.text}")
    return "\n".join(lines)


def _format_instructions() -> str:
    """Bentuk JSON diturunkan dari model Summary, jadi nama field tidak bisa menyimpang dari kode."""
    contoh = {
        "summary": "teks",
        "decisions": ["teks"],
        "tasks": [{"description": "teks", "owner": None, "due": None}],
        "open_questions": ["teks"],
    }
    return (
        "Jawab HANYA dengan satu objek JSON valid, tanpa teks lain dan tanpa pagar kode, "
        "persis dengan bentuk ini:\n" + json.dumps(contoh, ensure_ascii=False, indent=2)
    )


def parse_summary(raw: str) -> Summary:
    """Baca jawaban LLM. Menerima JSON polos, atau JSON yang dibungkus pagar kode/teks lain."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return Summary.model_validate_json(text)


def _is_transient(exc: Exception) -> bool:
    low = f"{type(exc).__name__} {exc}".lower()
    return any(k in low for k in TRANSIENT_MARKERS)


def _generate_with_retry(generate: Generate, system: str, transcript: str) -> str:
    """Panggil LLM; galat sementara (Gemini sibuk) dicoba ulang dengan jeda, galat lain langsung naik."""
    for delay in (*RETRY_DELAYS, None):
        try:
            return generate(system, transcript)
        except Exception as exc:
            if delay is None or not _is_transient(exc):
                raise
            time.sleep(delay)
    raise AssertionError("tidak tercapai")


def summarize(segments: list[Segment], generate: Generate) -> Summary:
    """Panggil LLM, validasi, dan coba ulang sekali bila jawabannya rusak.

    Galat jaringan, kunci, atau kuota dari `generate` dibiarkan naik apa adanya.
    Melempar PipelineError(LLM_BAD_OUTPUT) bila jawaban tetap tidak valid.
    """
    system = f"{load_prompt()}\n\n{_format_instructions()}"
    transcript = format_transcript(segments)
    last_problem = ""
    for attempt in range(MAX_ATTEMPTS):
        instruction = system
        if attempt:
            instruction += f"\n\nJawaban sebelumnya ditolak ({last_problem}). Ulangi dan patuhi bentuk JSON di atas."
        raw = _generate_with_retry(generate, instruction, transcript)
        try:
            return parse_summary(raw)
        except ValueError as exc:  # pydantic.ValidationError adalah ValueError
            last_problem = str(exc).splitlines()[0][:200]
    raise PipelineError(
        errors.LLM_BAD_OUTPUT,
        "Ringkasan otomatis gagal: jawaban AI bukan JSON yang sesuai, juga setelah dicoba ulang.",
        step=5,
        detail=last_problem,
    )


def gemini_generate(system: str, transcript: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.llm_api_key)
    response = client.models.generate_content(
        model=settings.llm_model,
        contents=transcript,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text or ""


def classify_llm_error(exc: Exception) -> PipelineError:
    text = f"{type(exc).__name__}: {exc}"
    low = text.lower()
    if any(k in low for k in ("429", "resource_exhausted", "quota", "rate limit")):
        return PipelineError(errors.LLM_QUOTA, "Kuota Gemini habis atau terlalu cepat. Coba lagi beberapa saat lagi.", 5, text)
    if any(k in low for k in ("401", "403", "api key", "api_key", "permission_denied", "unauthenticated")):
        return PipelineError(errors.LLM_AUTH, "LLM_API_KEY ditolak. Periksa kunci API di .env.", 5, text)
    if any(k in low for k in ("404", "not_found", "is not found", "not supported for generatecontent")):
        return PipelineError(errors.LLM_MODEL_NOT_FOUND, "LLM_MODEL tidak ditemukan. Periksa nama model di .env.", 5, text)
    if _is_transient(exc):
        return PipelineError(
            errors.LLM_OVERLOADED,
            "Layanan Gemini sedang sibuk dan masih menolak setelah dicoba ulang. Coba lagi beberapa menit lagi.",
            5, text,
        )
    if any(k in low for k in ("connect", "timed out", "timeout", "unreachable", "name resolution", "dns")):
        return PipelineError(errors.LLM_UNREACHABLE, "Tidak bisa terhubung ke Gemini. Periksa koneksi internet.", 5, text)
    return PipelineError(errors.LLM_FAILED, "Ringkasan otomatis gagal karena galat tak terduga.", 5, text)


def run_stage_5(
    segments: list[Segment],
    progress: ProgressWriter,
    generate: Generate | None = None,
) -> tuple[SummaryStatus, Summary | None, str | None]:
    """Jalankan tahap 5. Mengembalikan (status, ringkasan, pesan galat). Tidak melempar galat."""
    progress.start_step(5)

    if not segments:
        progress.finish_step(5, skipped=True)
        return "skipped", None, "Tidak ada ucapan terdeteksi, jadi tidak ada yang diringkas."

    if generate is None:
        missing = [n for n, v in (("LLM_API_KEY", settings.llm_api_key), ("LLM_MODEL", settings.llm_model)) if not v.strip()]
        if settings.llm_provider != "google":
            err = PipelineError(errors.LLM_NOT_CONFIGURED, f"LLM_PROVIDER '{settings.llm_provider}' belum didukung (hanya google).", 5)
            progress.fail_step_softly(5, err)
            return "failed", None, err.message
        if missing:
            progress.finish_step(5, skipped=True)
            return "skipped", None, f"{' dan '.join(missing)} belum diisi di .env, jadi ringkasan dilewati."
        generate = gemini_generate

    try:
        summary = summarize(segments, generate)
    except Exception as exc:
        err = exc if isinstance(exc, PipelineError) else classify_llm_error(exc)
        progress.fail_step_softly(5, err)
        return "failed", None, err.message

    progress.finish_step(5)
    return "ok", summary, None
