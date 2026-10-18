"""Tes mulai ulang dari tahap yang gagal dan penanganan galat, dengan tahap AI palsu."""

import json
import subprocess

import pytest

from spectrameet_pipeline import errors, run
from spectrameet_pipeline.audio import find_ffmpeg
from spectrameet_pipeline.config import settings
from spectrameet_pipeline.errors import PipelineError
from spectrameet_pipeline.schema import Progress, Segment
from spectrameet_pipeline.transcribe import Options

BAGUS = {"summary": "ringkas", "decisions": [], "tasks": [], "open_questions": []}


@pytest.fixture
def audio(tmp_path):
    out = tmp_path / "rekaman.mp3"
    subprocess.run([find_ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-ac", "1", str(out)], check=True)
    return out


class Palsu:
    """Pengganti run_stt dan run_diarization yang mencatat berapa kali dipanggil."""

    def __init__(self, monkeypatch):
        self.stt_calls = 0
        self.diar_calls = 0
        self.diar_error = None
        monkeypatch.setattr(settings, "hf_token", "hf_palsu")
        monkeypatch.setattr(run, "run_stt", self.stt)
        monkeypatch.setattr(run, "run_diarization", self.diar)

    def stt(self, wav, options, progress):
        self.stt_calls += 1
        progress.start_step(2); progress.finish_step(2)
        progress.start_step(3); progress.finish_step(3)
        return "id", {"segments": [{"start": 0.0, "end": 1.0, "text": "halo"}], "word_segments": []}

    def diar(self, wav, stt_result, options, progress):
        self.diar_calls += 1
        progress.start_step(4)
        if self.diar_error:
            raise self.diar_error
        progress.finish_step(4)
        return [Segment(start=0, end=1, speaker="SPEAKER_00", text=stt_result["segments"][0]["text"])]


@pytest.fixture
def palsu(monkeypatch):
    return Palsu(monkeypatch)


def bagus(system, transcript):
    return json.dumps(BAGUS)


def baca(job_dir) -> Progress:
    return Progress.model_validate_json((job_dir / "progress.json").read_text(encoding="utf-8"))


def jalankan(audio, job_dir, resume=False, generate=bagus, options=None):
    return run.process(audio, options, job_id="j", job_dir=job_dir, generate=generate, resume=resume)


def test_tanpa_resume_semua_dihitung_dan_checkpoint_ditulis(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    assert (palsu.stt_calls, palsu.diar_calls) == (1, 1)
    assert all((tmp_path / f"{n}.json").is_file() for n in ("audio", "stt", "segmen", "hasil"))
    assert baca(tmp_path).resumed_from is None


def test_resume_setelah_sukses_hanya_menjalankan_tahap5(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    hasil = jalankan(audio, tmp_path, resume=True)
    assert (palsu.stt_calls, palsu.diar_calls) == (1, 1)  # tidak bertambah
    p = baca(tmp_path)
    assert p.resumed_from == 5 and p.status == "done"
    assert [s.status for s in p.steps] == ["done"] * 5
    assert hasil.segments[0].text == "halo" and hasil.summary == "ringkas"


def test_diarization_gagal_lalu_resume_tidak_mengulang_transkripsi(audio, tmp_path, palsu):
    palsu.diar_error = MemoryError()
    with pytest.raises(PipelineError) as e:
        jalankan(audio, tmp_path)
    assert e.value.code == errors.OUT_OF_MEMORY and e.value.step == 4
    p = baca(tmp_path)
    assert p.status == "failed" and p.steps[3].status == "failed" and p.error.step == 4
    assert (tmp_path / "stt.json").is_file() and not (tmp_path / "segmen.json").exists()
    assert not (tmp_path / "hasil.json").exists()

    palsu.diar_error = None
    hasil = jalankan(audio, tmp_path, resume=True)
    assert (palsu.stt_calls, palsu.diar_calls) == (1, 2)
    p = baca(tmp_path)
    assert p.resumed_from == 4 and p.status == "done" and p.error is None
    assert hasil.segments[0].speaker == "SPEAKER_00"


def test_ringkasan_gagal_lalu_resume_hanya_mengulang_ringkasan(audio, tmp_path, palsu):
    hasil = jalankan(audio, tmp_path, generate=lambda s, t: "rusak")
    assert hasil.summary_status == "failed"
    assert baca(tmp_path).steps[4].status == "failed"

    hasil = jalankan(audio, tmp_path, resume=True)
    assert (palsu.stt_calls, palsu.diar_calls) == (1, 1)
    assert hasil.summary_status == "ok" and baca(tmp_path).error is None


def test_ganti_opsi_pembicara_hanya_mengulang_tahap4(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    jalankan(audio, tmp_path, resume=True, options=Options(speakers="2"))
    assert (palsu.stt_calls, palsu.diar_calls) == (1, 2)
    assert baca(tmp_path).resumed_from == 4


def test_ganti_model_whisper_mengulang_dari_tahap2(audio, tmp_path, palsu, monkeypatch):
    jalankan(audio, tmp_path)
    monkeypatch.setattr(settings, "whisper_model", "medium")
    jalankan(audio, tmp_path, resume=True)
    assert (palsu.stt_calls, palsu.diar_calls) == (2, 2)
    assert baca(tmp_path).resumed_from == 2


def test_ganti_isi_audio_mengulang_semua(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    audio.write_bytes(audio.read_bytes()[:-500])  # ukuran berubah = rekaman berbeda
    jalankan(audio, tmp_path, resume=True)
    assert (palsu.stt_calls, palsu.diar_calls) == (2, 2)
    assert baca(tmp_path).resumed_from is None


def test_checkpoint_rusak_dihitung_ulang(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    (tmp_path / "stt.json").write_text("{setengah json", encoding="utf-8")
    jalankan(audio, tmp_path, resume=True)
    assert (palsu.stt_calls, palsu.diar_calls) == (2, 2)  # segmen ikut dihitung ulang
    assert baca(tmp_path).resumed_from == 2


def test_tanpa_flag_resume_mulai_dari_nol(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    jalankan(audio, tmp_path)
    assert (palsu.stt_calls, palsu.diar_calls) == (2, 2)


def test_token_kosong_gagal_cepat_sebelum_transkripsi(audio, tmp_path, palsu, monkeypatch):
    monkeypatch.setattr(settings, "hf_token", "")
    with pytest.raises(PipelineError) as e:
        jalankan(audio, tmp_path)
    assert e.value.code == errors.HF_TOKEN_MISSING and e.value.step == 4
    assert palsu.stt_calls == 0
    assert baca(tmp_path).steps[3].status == "failed"


def test_resume_dengan_segmen_tersimpan_tidak_butuh_token(audio, tmp_path, palsu, monkeypatch):
    jalankan(audio, tmp_path)
    monkeypatch.setattr(settings, "hf_token", "")
    assert jalankan(audio, tmp_path, resume=True).summary_status == "ok"


def test_audio_rusak_menghentikan_di_tahap1(tmp_path, palsu):
    rusak = tmp_path / "rusak.mp3"
    rusak.write_bytes(b"bukan audio" * 200)
    with pytest.raises(PipelineError) as e:
        jalankan(rusak, tmp_path / "job")
    assert e.value.code == errors.AUDIO_UNREADABLE and e.value.step == 1
    assert palsu.stt_calls == 0 and baca(tmp_path / "job").steps[0].status == "failed"


def test_audio_hilang_saat_resume(audio, tmp_path, palsu):
    jalankan(audio, tmp_path)
    audio.unlink()
    with pytest.raises(PipelineError) as e:
        jalankan(audio, tmp_path, resume=True)
    assert e.value.code == errors.AUDIO_NOT_FOUND


def test_dibatalkan_dicatat_sebagai_cancelled(audio, tmp_path, palsu):
    palsu.diar_error = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        jalankan(audio, tmp_path)
    p = baca(tmp_path)
    assert p.status == "failed" and p.error.code == errors.CANCELLED and p.error.step == 4


@pytest.mark.parametrize("galat,step,kode,kata", [
    (RuntimeError("[enforce fail] DefaultCPUAllocator: not enough memory"), 3, errors.OUT_OF_MEMORY, "WHISPER_MODEL"),
    (RuntimeError("LocalEntryNotFoundError: Cannot find an appropriate cached snapshot folder"), 2,
     errors.MODEL_UNAVAILABLE, "Whisper"),
    (RuntimeError("LocalEntryNotFoundError: Cannot find an appropriate cached snapshot folder"), 4,
     errors.MODEL_UNAVAILABLE, "pyannote"),
    (RuntimeError("GatedRepoError: 403 Client Error"), 4, errors.MODEL_UNAVAILABLE, "lisensi"),
    (RuntimeError("401 Unauthorized"), 2, errors.MODEL_UNAVAILABLE, "WHISPER_MODEL"),
])
def test_pesan_galat_menyebut_model_dan_langkah_perbaikan(galat, step, kode, kata):
    e = run.classify(galat, step)
    assert e.code == kode and kata in e.message and e.step == step
