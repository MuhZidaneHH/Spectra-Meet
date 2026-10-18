"""Tes ringan: tanpa model AI, hanya FFmpeg, progres, skema, dan klasifikasi galat."""

import json
import subprocess
import wave

import pytest

from spectrameet_pipeline import errors
from spectrameet_pipeline.audio import find_ffmpeg, to_standard_wav
from spectrameet_pipeline.errors import PipelineError
from spectrameet_pipeline.progress import ProgressWriter
from spectrameet_pipeline.run import classify
from spectrameet_pipeline.schema import Progress, Result, Segment
from spectrameet_pipeline.transcribe import Options


@pytest.fixture
def nada_mp3(tmp_path):
    """Nada 2 detik, stereo 44,1 kHz, supaya konversi ke 16 kHz mono terbukti."""
    out = tmp_path / "nada.mp3"
    subprocess.run(
        [find_ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-ac", "2", "-ar", "44100", str(out)],
        check=True,
    )
    return out


def test_konversi_ke_wav_standar(nada_mp3, tmp_path):
    dst = tmp_path / "keluar" / "audio.wav"
    durasi = to_standard_wav(nada_mp3, dst)
    assert 1.8 < durasi < 2.3
    with wave.open(str(dst)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)


def test_audio_tidak_ada(tmp_path):
    with pytest.raises(PipelineError) as e:
        to_standard_wav(tmp_path / "tidak-ada.mp3", tmp_path / "x.wav")
    assert e.value.code == errors.AUDIO_NOT_FOUND


def test_audio_rusak(tmp_path):
    rusak = tmp_path / "rusak.mp3"
    rusak.write_bytes(b"ini bukan audio" * 100)
    with pytest.raises(PipelineError) as e:
        to_standard_wav(rusak, tmp_path / "x.wav")
    assert e.value.code == errors.AUDIO_UNREADABLE


def test_progres_ditulis_dan_bisa_dibaca(tmp_path):
    p = ProgressWriter(tmp_path, "j1")
    p.start_step(1)
    p.update(50)
    p.finish_step(1)
    p.start_step(5)
    p.finish_step(5, skipped=True)
    p.done()
    data = Progress.model_validate_json((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert data.status == "done"
    assert [s.status for s in data.steps] == ["done", "pending", "pending", "pending", "skipped"]
    assert not list(tmp_path.glob("*.tmp"))


def test_progres_gagal_mencatat_galat(tmp_path):
    p = ProgressWriter(tmp_path, "j2")
    p.start_step(4)
    p.fail(PipelineError(errors.OUT_OF_MEMORY, "Memori habis.", step=4, detail="x"))
    data = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert data["status"] == "failed"
    assert data["steps"][3]["status"] == "failed"
    assert data["error"]["code"] == "OUT_OF_MEMORY"


def test_hasil_bolak_balik():
    r = Result(language="id", duration=3.0, segments=[Segment(start=0, end=1, speaker="SPEAKER_00", text="halo")])
    assert Result.model_validate_json(r.model_dump_json()) == r
    assert r.summary is None and r.tasks == []


@pytest.mark.parametrize("pilihan,harapan", [
    ("auto", {}), ("2", {"num_speakers": 2}), ("4", {"num_speakers": 4}), ("5+", {"min_speakers": 5}),
])
def test_opsi_pembicara(pilihan, harapan):
    assert Options(speakers=pilihan).speaker_args() == harapan


def test_bahasa_campur_memakai_id():
    assert Options(language="id-en").whisper_language == "id"
    assert Options(language="en").whisper_language == "en"


@pytest.mark.parametrize("galat,kode", [
    (MemoryError(), errors.OUT_OF_MEMORY),
    (RuntimeError("CUDA out of memory"), errors.OUT_OF_MEMORY),
    (RuntimeError("403 Client Error: gated repo"), errors.MODEL_UNAVAILABLE),
    (RuntimeError("Read timed out"), errors.MODEL_UNAVAILABLE),
    (ValueError("aneh"), errors.UNKNOWN),
])
def test_klasifikasi_galat(galat, kode):
    assert classify(galat, 3).code == kode


def test_contoh_hasil_sesuai_skema():
    """docs/contoh-hasil.json dipakai Dev 1 untuk membangun halaman Hasil; harus tetap valid."""
    from pathlib import Path

    contoh = Path(__file__).resolve().parents[2] / "docs" / "contoh-hasil.json"
    hasil = Result.model_validate_json(contoh.read_text(encoding="utf-8"))
    assert hasil.summary_status == "ok"
    urut = [s.start for s in hasil.segments]
    assert urut == sorted(urut)
