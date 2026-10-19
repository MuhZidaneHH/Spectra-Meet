from sqlmodel import Session

from app.db import Meeting, get_engine, init_db


def test_init_db_aman_dipanggil_berulang(client):
    init_db()
    init_db()


def test_tabel_meetings_dibuat_dan_bisa_diisi(client):
    with Session(get_engine()) as db:
        db.add(Meeting(id="a", filename="a.wav", audio_path="audio/a/original.wav", size_bytes=1, language="id", speakers="auto"))
        db.commit()
        row = db.get(Meeting, "a")
        assert row.status == "uploaded" and row.created_at is not None
