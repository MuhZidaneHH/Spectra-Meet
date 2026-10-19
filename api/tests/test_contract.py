import copy
import json

import pytest

from app.config import REPO_ROOT
from app.contract import ContractError, to_contract, validate_result

SAMPLE = json.loads((REPO_ROOT / "docs" / "contoh-hasil.json").read_text(encoding="utf-8"))


def test_contoh_pm_lolos_dan_terbaca_lengkap():
    out = validate_result(SAMPLE)
    assert len(out["segments"]) == 9
    assert out["summary"]["tugas"][2]["owner_speaker"] is None
    assert out["speakers"][0] == {"id": "SPEAKER_00", "label": "Pembicara 1"}
    assert out["warnings"][0]["code"] == "OVERLAP_SPEECH"


def test_hanya_segments_dan_ringkasan_yang_wajib_bagi_tampilan():
    out = validate_result({"segments": [], "summary": {"ringkasan": "x"}})
    assert out["speakers"] == [] and out["warnings"] == []


def test_kunci_tambahan_dari_pipeline_diterima():
    data = copy.deepcopy(SAMPLE)
    data["catatan_baru"] = 1
    data["segments"][0]["confidence"] = 0.9
    out = validate_result(data)
    assert out["catatan_baru"] == 1 and out["segments"][0]["confidence"] == 0.9


def test_versi_mayor_lain_ditolak_dengan_pesan_jelas():
    with pytest.raises(ContractError, match="2.0"):
        validate_result({**SAMPLE, "schema_version": "2.0"})


@pytest.mark.parametrize(
    "mutate, path",
    [
        (lambda d: d.pop("segments"), "segments"),
        (lambda d: d["segments"][2].pop("start"), "segments.2.start"),
        (lambda d: d["segments"][0].pop("text"), "segments.0.text"),
        (lambda d: d.pop("summary"), "summary"),
        (lambda d: d["summary"].pop("ringkasan"), "summary.ringkasan"),
        (lambda d: d["summary"]["tugas"][0].pop("text"), "summary.tugas.0.text"),
    ],
)
def test_galat_menyebut_field_yang_bermasalah(mutate, path):
    data = copy.deepcopy(SAMPLE)
    mutate(data)
    with pytest.raises(ContractError) as exc:
        validate_result(data)
    assert any(p.startswith(path) for p in exc.value.problems), exc.value.problems


def test_berkas_rusak_dan_bentuk_salah():
    with pytest.raises(ContractError):
        validate_result([1, 2])


def test_bentuk_datar_pipeline_dijembatani_ke_kontrak():
    flat = {
        "version": 1, "language": "id", "duration": 60.0,
        "segments": [
            {"start": 0, "end": 5, "speaker": "SPEAKER_01", "text": "a"},
            {"start": 5, "end": 9, "speaker": "SPEAKER_00", "text": "b"},
            {"start": 9, "end": 12, "speaker": "UNKNOWN", "text": "c"},
        ],
        "summary_status": "ok", "summary": "Ringkas.", "decisions": ["Putus A"],
        "tasks": [
            {"description": "Kerjakan X", "owner": "SPEAKER_01", "due": "Besok"},
            {"description": "Kerjakan Y", "owner": "Budi", "due": None},
        ],
        "open_questions": ["Kapan?"],
    }
    out = validate_result(to_contract(flat, meeting_id="m1", filename="r.wav", created_at="2026-10-19T00:00:00Z"))
    assert [s["id"] for s in out["speakers"]] == ["SPEAKER_00", "SPEAKER_01"]
    assert out["segments"][2]["speaker"] is None  # UNKNOWN -> null
    assert out["summary"]["ringkasan"] == "Ringkas."
    assert out["summary"]["tugas"][0]["owner_speaker"] == "SPEAKER_01"
    assert out["summary"]["tugas"][1]["owner_speaker"] is None and out["summary"]["tugas"][1]["owner_name"] == "Budi"
    assert out["summary"]["keputusan"][0]["text"] == "Putus A"


def test_hasil_yang_sudah_berbentuk_kontrak_diteruskan_apa_adanya():
    assert to_contract(SAMPLE, meeting_id="x", filename="x", created_at="x") is SAMPLE
