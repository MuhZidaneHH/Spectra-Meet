"""Tes tahap 5 dengan LLM palsu (tanpa jaringan dan tanpa kunci)."""

import json

import pytest

from spectrameet_pipeline import errors, summarize
from spectrameet_pipeline.errors import PipelineError
from spectrameet_pipeline.progress import ProgressWriter
from spectrameet_pipeline.schema import Progress, Segment

SEGMEN = [
    Segment(start=0, end=5, speaker="SPEAKER_00", text="Kita putuskan rilis hari Jumat."),
    Segment(start=65, end=70, speaker="SPEAKER_01", text="Saya yang siapkan catatan rilisnya."),
]
BAGUS = {
    "summary": "Rapat memutuskan rilis hari Jumat.",
    "decisions": ["Rilis hari Jumat"],
    "tasks": [{"description": "Siapkan catatan rilis", "owner": None, "due": None}],
    "open_questions": [],
}


def penghasil(*jawaban):
    """LLM palsu: mengembalikan jawaban satu per satu dan mencatat panggilannya."""
    sisa = list(jawaban)
    panggilan = []

    def generate(system, transcript):
        panggilan.append((system, transcript))
        jawab = sisa.pop(0)
        if isinstance(jawab, Exception):
            raise jawab
        return jawab if isinstance(jawab, str) else json.dumps(jawab)

    generate.panggilan = panggilan
    return generate


@pytest.fixture
def progress(tmp_path):
    return ProgressWriter(tmp_path, "t5")


def baca(tmp_path) -> Progress:
    return Progress.model_validate_json((tmp_path / "progress.json").read_text(encoding="utf-8"))


def test_format_transkrip_memakai_menit_detik():
    assert summarize.format_transcript(SEGMEN).splitlines() == [
        "[00:00] SPEAKER_00: Kita putuskan rilis hari Jumat.",
        "[01:05] SPEAKER_01: Saya yang siapkan catatan rilisnya.",
    ]


def test_prompt_dibaca_tanpa_komentar_html():
    p = summarize.load_prompt()
    assert "<!--" not in p and "DRAF AWAL" not in p
    assert "summary" in p


def test_jawaban_benar(tmp_path, progress):
    gen = penghasil(BAGUS)
    status, ringkasan, galat = summarize.run_stage_5(SEGMEN, progress, gen)
    assert (status, galat) == ("ok", None)
    assert ringkasan.decisions == ["Rilis hari Jumat"]
    assert ringkasan.tasks[0].owner is None
    # transkrip dan bentuk JSON sampai ke LLM
    system, transcript = gen.panggilan[0]
    assert "[01:05] SPEAKER_01" in transcript and '"open_questions"' in system
    assert baca(tmp_path).steps[4].status == "done"


@pytest.mark.parametrize("bungkus", [
    "```json\n{}\n```",
    "Berikut hasilnya:\n{}\nSemoga membantu.",
])
def test_json_dibungkus_tetap_terbaca(bungkus, progress):
    status, ringkasan, _ = summarize.run_stage_5(SEGMEN, progress, penghasil(bungkus.replace("{}", json.dumps(BAGUS))))
    assert status == "ok" and ringkasan.summary.startswith("Rapat")


def test_jawaban_rusak_diulang_sekali_lalu_berhasil(progress):
    gen = penghasil("bukan json sama sekali", BAGUS)
    status, _, _ = summarize.run_stage_5(SEGMEN, progress, gen)
    assert status == "ok" and len(gen.panggilan) == 2
    assert "ditolak" in gen.panggilan[1][0]  # percobaan kedua membawa catatan perbaikan


def test_field_salah_dianggap_rusak(progress):
    gen = penghasil({"ringkasan": "salah nama field"}, {"summary": 123, "tasks": "x"})
    status, ringkasan, galat = summarize.run_stage_5(SEGMEN, progress, gen)
    assert status == "failed" and ringkasan is None and "bukan JSON yang sesuai" in galat


def test_tetap_rusak_menjadi_gagal_lunak(tmp_path, progress):
    status, ringkasan, galat = summarize.run_stage_5(SEGMEN, progress, penghasil("rusak", "rusak lagi"))
    assert status == "failed" and ringkasan is None
    data = baca(tmp_path)
    assert data.steps[4].status == "failed"
    assert data.status == "running"  # pekerjaan tidak dianggap gagal
    assert data.error.code == errors.LLM_BAD_OUTPUT and data.error.step == 5


@pytest.mark.parametrize("galat,kode", [
    (RuntimeError("429 RESOURCE_EXHAUSTED: quota"), errors.LLM_QUOTA),
    (RuntimeError("403 PERMISSION_DENIED: API key not valid"), errors.LLM_AUTH),
    (RuntimeError("404 NOT_FOUND: models/xyz is not found"), errors.LLM_MODEL_NOT_FOUND),
    (RuntimeError("Connection timed out"), errors.LLM_UNREACHABLE),
    (ValueError("aneh"), errors.LLM_FAILED),
])
def test_galat_llm_dikenali(galat, kode, tmp_path, progress):
    status, _, pesan = summarize.run_stage_5(SEGMEN, progress, penghasil(galat))
    assert status == "failed" and pesan
    assert baca(tmp_path).error.code == kode


def test_tanpa_ucapan_dilewati_tanpa_memanggil_llm(progress):
    gen = penghasil()
    status, ringkasan, galat = summarize.run_stage_5([], progress, gen)
    assert status == "skipped" and ringkasan is None and gen.panggilan == []


def test_tanpa_kunci_dilewati(monkeypatch, tmp_path, progress):
    monkeypatch.setattr(summarize.settings, "llm_api_key", "")
    status, _, pesan = summarize.run_stage_5(SEGMEN, progress)
    assert status == "skipped" and "LLM_API_KEY" in pesan
    assert baca(tmp_path).steps[4].status == "skipped"


def test_kunci_ada_tapi_model_kosong_disebut(monkeypatch, progress):
    monkeypatch.setattr(summarize.settings, "llm_api_key", "kunci-palsu")
    monkeypatch.setattr(summarize.settings, "llm_model", "")
    status, _, pesan = summarize.run_stage_5(SEGMEN, progress)
    assert status == "skipped" and "LLM_MODEL" in pesan and "LLM_API_KEY" not in pesan


SIBUK = RuntimeError("ServerError: 503 UNAVAILABLE. This model is currently experiencing high demand.")


def test_gemini_sibuk_dicoba_ulang_lalu_berhasil(monkeypatch, progress):
    monkeypatch.setattr(summarize, "RETRY_DELAYS", (0, 0))
    gen = penghasil(SIBUK, SIBUK, BAGUS)
    status, ringkasan, _ = summarize.run_stage_5(SEGMEN, progress, gen)
    assert status == "ok" and len(gen.panggilan) == 3


def test_gemini_tetap_sibuk_menjadi_llm_overloaded(monkeypatch, tmp_path, progress):
    monkeypatch.setattr(summarize, "RETRY_DELAYS", (0, 0))
    gen = penghasil(SIBUK, SIBUK, SIBUK)
    status, _, pesan = summarize.run_stage_5(SEGMEN, progress, gen)
    assert status == "failed" and "sibuk" in pesan and len(gen.panggilan) == 3
    assert baca(tmp_path).error.code == errors.LLM_OVERLOADED


def test_galat_kunci_tidak_dicoba_ulang(monkeypatch, progress):
    monkeypatch.setattr(summarize, "RETRY_DELAYS", (0, 0))
    gen = penghasil(RuntimeError("403 PERMISSION_DENIED: API key not valid"), BAGUS)
    status, _, _ = summarize.run_stage_5(SEGMEN, progress, gen)
    assert status == "failed" and len(gen.panggilan) == 1
