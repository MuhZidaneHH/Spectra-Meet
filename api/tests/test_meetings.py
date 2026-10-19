import json
import os
import subprocess
import sys

import pytest

from app.config import settings
from app.db import Meeting, get_engine
from app.runner import runner
from sqlmodel import Session

from conftest import upload, wait_status


def test_config_dan_health_dan_ping(client):
    cfg = client.get("/api/config").json()
    assert cfg["languages"][0]["value"] == "id-en" and "wav" in cfg["extensions"]
    health = client.get("/api/health").json()
    assert health["ready"] is True and health["mock_pipeline"] is True
    assert client.get("/api/ping").json()["ok"] is True


def test_unggah_ditolak_untuk_format_ukuran_dan_pilihan_salah(client):
    assert upload(client, "catatan.txt").status_code == 400
    assert upload(client, data=b"").status_code == 400
    assert upload(client, data=b"x" * (1024 * 1024 + 1)).status_code == 413
    assert upload(client, language="klingon").status_code == 422
    assert upload(client, speakers="99").status_code == 422
    # unggahan yang ditolak tidak meninggalkan berkas
    assert not any((settings.data_path / "audio").glob("*/*"))


def test_alur_penuh_sampai_hasil_dan_audio(client):
    r = upload(client, "Rapat Besar.wav", language="id", speakers="3", duration_sec="12.5")
    assert r.status_code == 201
    m = r.json()
    assert m["status"] == "uploaded" and m["filename"] == "Rapat Besar.wav" and m["duration_sec"] == 12.5

    assert client.get(f"/api/meetings/{m['id']}/result").status_code == 409  # belum selesai
    started = client.post(f"/api/meetings/{m['id']}/start").json()
    assert started["status"] == "processing" and started["started_at"].endswith("Z")
    assert client.post(f"/api/meetings/{m['id']}/start").status_code == 409  # sudah dimulai

    done = wait_status(client, m["id"], "done")
    assert done["progress"]["percent"] == 100 and done["progress"]["steps"] == ["done"] * 5

    result = client.get(f"/api/meetings/{m['id']}/result").json()
    assert result["summary"]["ringkasan"] and len(result["segments"]) == 9

    audio = client.get(f"/api/meetings/{m['id']}/audio", headers={"Range": "bytes=0-3"})
    assert audio.status_code == 206 and audio.content == b"RIFF"


def test_kemajuan_terlihat_selama_berjalan(client):
    m = upload(client).json()
    client.post(f"/api/meetings/{m['id']}/start")
    seen = set()
    while True:
        body = client.get(f"/api/meetings/{m['id']}").json()
        seen.add(tuple(body["progress"]["steps"]))
        if body["status"] != "processing":
            break
    assert len(seen) > 2  # beberapa keadaan antara, bukan langsung selesai


def test_hanya_satu_job_dalam_satu_waktu_dan_batalkan(client, monkeypatch):
    monkeypatch.setattr(settings, "mock_step_seconds", 5)
    a = upload(client).json()
    b = upload(client).json()
    assert client.post(f"/api/meetings/{a['id']}/start").status_code == 200
    assert client.post(f"/api/meetings/{b['id']}/start").status_code == 409

    cancelled = client.post(f"/api/meetings/{a['id']}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert runner.active_id() is None
    assert client.post(f"/api/meetings/{b['id']}/start").status_code == 200  # slot kosong lagi
    client.post(f"/api/meetings/{b['id']}/cancel")


def test_batal_dan_coba_lagi_yang_tidak_semestinya_ditolak(client):
    m = upload(client).json()
    assert client.post(f"/api/meetings/{m['id']}/cancel").status_code == 409
    assert client.post(f"/api/meetings/{m['id']}/retry").status_code == 409
    assert client.get("/api/meetings/tidak-ada").status_code == 404


def test_gagal_lalu_coba_lagi_dari_tahap_yang_gagal(client, monkeypatch):
    monkeypatch.setattr(settings, "mock_fail_at_step", 3)
    m = upload(client).json()
    client.post(f"/api/meetings/{m['id']}/start")
    failed = wait_status(client, m["id"], "failed")
    assert failed["error_step"] == 3
    assert failed["progress"]["steps"] == ["done", "done", "failed", "waiting", "waiting"]
    assert failed["progress"]["error"]["code"] == "OUT_OF_MEMORY"
    assert "memori" in failed["error_message"].lower()

    retried = client.post(f"/api/meetings/{m['id']}/retry").json()
    assert retried["status"] == "processing"
    done = wait_status(client, m["id"], "done")
    assert done["error_step"] is None

    log = (settings.results_dir / m["id"] / "log.txt").read_text(encoding="utf-8")
    assert "--from-step 3" in log  # tahap 1-2 tidak diulang


def test_hasil_belum_ada_dan_rekaman_tidak_ada(client):
    assert client.get("/api/meetings/xx/result").status_code == 404
    assert client.get("/api/meetings/xx/audio").status_code == 404


def test_hasil_tidak_sesuai_kontrak_dilaporkan_dengan_nama_field(client):
    m = upload(client).json()
    client.post(f"/api/meetings/{m['id']}/start")
    wait_status(client, m["id"], "done")
    path = settings.results_dir / m["id"] / "hasil.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["segments"][1]["start"]
    path.write_text(json.dumps(data), encoding="utf-8")
    r = client.get(f"/api/meetings/{m['id']}/result")
    assert r.status_code == 500 and "segments.1.start" in r.json()["detail"]


def test_hasil_bentuk_datar_pipeline_asli_tampil_sebagai_kontrak(client):
    m = upload(client).json()
    client.post(f"/api/meetings/{m['id']}/start")
    wait_status(client, m["id"], "done")
    flat = {"version": 1, "language": "id", "duration": 9.0, "summary_status": "ok", "summary": "Isi.",
            "segments": [{"start": 0, "end": 3, "speaker": "SPEAKER_00", "text": "Halo"}],
            "decisions": [], "tasks": [{"description": "T", "owner": None, "due": None}], "open_questions": []}
    (settings.results_dir / m["id"] / "hasil.json").write_text(json.dumps(flat), encoding="utf-8")
    r = client.get(f"/api/meetings/{m['id']}/result").json()
    assert r["summary"]["ringkasan"] == "Isi." and r["speakers"][0]["label"] == "Pembicara 1"


def test_pipeline_asli_yang_hilang_menjadi_gagal_dengan_pesan_jelas(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_pipeline", False)
    monkeypatch.setattr(settings, "pipeline_python", str(settings.data_path / "tidak" / "ada" / "python.exe"))
    m = upload(client).json()
    body = client.post(f"/api/meetings/{m['id']}/start").json()
    assert body["status"] == "failed" and "belum terpasang" in body["error_message"]
    health = client.get("/api/health").json()
    assert health["ready"] is False
    assert {c["id"] for c in health["checks"] if not c["ok"] and c["required"]} >= {"pipeline_python"}


def test_job_yatim_ditandai_gagal_saat_api_menyala(client):
    m = upload(client).json()
    with Session(get_engine()) as db:
        row = db.get(Meeting, m["id"])
        row.status, row.current_step = "processing", 3
        db.add(row)
        db.commit()
    assert runner.fail_orphans() == 1
    body = client.get(f"/api/meetings/{m['id']}").json()
    assert body["status"] == "failed" and body["error_step"] == 3


def test_pipeline_mati_karena_memori_dikenali_walau_tanpa_galat_tertulis(client, monkeypatch):
    from app.runner import OOM_MESSAGE

    m = upload(client).json()
    wd = settings.results_dir / m["id"]
    wd.mkdir(parents=True)
    (wd / "log.txt").write_text("OpenBLAS error: Memory allocation still failed after 10 retries, giving up.\n", encoding="utf-8")
    with Session(get_engine()) as db:
        row = db.get(Meeting, m["id"])
        row.status = "processing"
        db.add(row)
        db.commit()
    runner._finish(m["id"], 1, False)
    body = client.get(f"/api/meetings/{m['id']}").json()
    assert body["status"] == "failed" and body["error_message"] == OOM_MESSAGE
    assert body["progress"]["error"]["code"] == "OUT_OF_MEMORY"


@pytest.mark.skipif(os.name != "nt", reason="kode crash native khusus Windows")
def test_crash_native_windows_dianggap_masalah_memori(client):
    m = upload(client).json()
    (settings.results_dir / m["id"]).mkdir(parents=True)
    with Session(get_engine()) as db:
        row = db.get(Meeting, m["id"])
        row.status = "processing"
        db.add(row)
        db.commit()
    proc = subprocess.Popen([sys.executable, "-c", "import ctypes; ctypes.windll.kernel32.ExitProcess(0xC0000005)"])
    with open(settings.results_dir / m["id"] / "log.txt", "w", encoding="utf-8") as log:
        runner._watch(m["id"], proc, log)
    body = client.get(f"/api/meetings/{m['id']}").json()
    assert body["status"] == "failed" and "Memori" in body["error_message"]
    assert body["progress"]["error"]["code"] == "OUT_OF_MEMORY"
