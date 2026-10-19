import time

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import init_db
from app.main import app
from app.runner import runner


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """API dengan folder data sementara dan pipeline tiruan yang cepat."""
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "use_mock_pipeline", True)
    monkeypatch.setattr(settings, "mock_step_seconds", 0.4)
    monkeypatch.setattr(settings, "mock_fail_at_step", 0)
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    init_db()
    with TestClient(app) as c:
        yield c
    runner.shutdown()


def upload(client, name="rapat.wav", data=b"RIFF....fake-audio", **form):
    return client.post("/api/meetings", files={"file": (name, data, "audio/wav")}, data=form)


def wait_status(client, meeting_id, *wanted, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/meetings/{meeting_id}").json()
        if body["status"] in wanted:
            return body
        time.sleep(0.1)
    raise AssertionError(f"status tidak pernah menjadi {wanted}: {body['status']}")
