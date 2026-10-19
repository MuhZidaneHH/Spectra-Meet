"""Semua endpoint /api. Web hanya bicara ke sini (lewat penerusan Next.js)."""

import mimetypes
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from app import contract
from app.config import LANGUAGES, SPEAKER_OPTIONS, settings
from app.db import Meeting, get_session, utcnow
from app.health import check_health
from app.runner import CODE_MAP, Busy, StartError, job_dir, log_tail, looks_like_oom, read_json, runner
from app.schemas import _iso_utc, Health, MeetingDetail, MeetingOut, Option, Progress, ProgressError, PublicConfig

router = APIRouter(prefix="/api")

STEP_STATUS = {"pending": "waiting", "waiting": "waiting", "running": "running", "done": "done", "skipped": "done", "failed": "failed"}


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "mock_pipeline": settings.use_mock_pipeline}


@router.get("/config", response_model=PublicConfig)
def public_config() -> PublicConfig:
    return PublicConfig(
        extensions=settings.extensions,
        max_upload_mb=settings.max_upload_mb,
        poll_interval_ms=settings.poll_interval_ms,
        languages=[Option(value=v, label=l) for v, l in LANGUAGES],
        speaker_options=[Option(value=v, label=l) for v, l in SPEAKER_OPTIONS],
    )


@router.get("/health", response_model=Health)
def health() -> Health:
    return check_health()


# ----- helper ---------------------------------------------------------------------------------------
def _get(db: Session, meeting_id: str) -> Meeting:
    m = db.get(Meeting, meeting_id)
    if m is None:
        raise HTTPException(404, "Rekaman tidak ditemukan.")
    return m


def _build_progress(m: Meeting) -> Progress:
    raw = read_json(job_dir(m.id) / "progress.json") or {}
    steps = ["waiting"] * 5
    raw_steps = raw.get("steps")
    if isinstance(raw_steps, list):
        for i, st in enumerate(raw_steps[:5]):
            name = st.get("status") if isinstance(st, dict) else st
            steps[i] = STEP_STATUS.get(str(name), "waiting")

    if m.status == "done":
        steps = ["done"] * 5
    elif m.status == "uploaded":
        steps = ["waiting"] * 5
    elif m.status == "processing" and "running" not in steps and "done" not in steps:
        steps[0] = "running"  # baru dimulai, progress.json belum ditulis
    elif m.status == "failed" and m.error_step and "failed" not in steps:
        steps[m.error_step - 1] = "failed"

    if m.status == "done":
        percent = 100
    elif m.status == "processing":
        within = float(raw.get("percent") or 0) if isinstance(raw.get("percent"), (int, float)) else 0.0
        percent = round((steps.count("done") * 100 + (within if "running" in steps else 0)) / 5)
    else:
        percent = round(steps.count("done") * 100 / 5)

    error = None
    if m.status == "failed":
        err = raw.get("error") if isinstance(raw.get("error"), dict) else {}
        raw_code = str(err.get("code") or "UNKNOWN")
        tail = err.get("detail") or log_tail(m.id)
        code = CODE_MAP.get(raw_code, "UNKNOWN")
        if not err and looks_like_oom(m.id):
            code = "OUT_OF_MEMORY"
        error = ProgressError(code=code, log_tail=str(tail) or None)
    return Progress(percent=min(percent, 100), steps=steps, error=error)


def _detail(m: Meeting) -> MeetingDetail:
    base = MeetingOut.of(m).model_dump()
    return MeetingDetail(
        **base,
        current_step=m.current_step,
        error_step=m.error_step,
        error_message=m.error_message,
        progress=_build_progress(m),
    )


def _current_step(m: Meeting) -> int:
    raw = read_json(job_dir(m.id) / "progress.json") or {}
    step = raw.get("step")
    return int(step) if isinstance(step, int) and 1 <= step <= 5 else m.current_step


def _launch(db: Session, m: Meeting, *, resume: bool) -> None:
    try:
        runner.start(m, resume=resume)
    except Busy as exc:
        raise HTTPException(409, str(exc)) from exc
    except StartError as exc:
        m.status, m.error_step, m.error_message, m.finished_at = "failed", 1, str(exc), utcnow()
        db.add(m)
        db.commit()
        db.refresh(m)
        return
    m.status, m.started_at, m.finished_at = "processing", utcnow(), None
    m.error_message = None
    if not resume:
        m.error_step = None
    m.current_step = max(1, m.error_step or 1) if resume else 1
    db.add(m)
    db.commit()
    db.refresh(m)


# ----- meetings -------------------------------------------------------------------------------------
@router.post("/meetings", response_model=MeetingOut, status_code=201)
async def upload_meeting(
    file: UploadFile = File(...),
    language: str = Form(LANGUAGES[0][0]),
    speakers: str = Form(SPEAKER_OPTIONS[0][0]),
    duration_sec: float | None = Form(None),
    db: Session = Depends(get_session),
) -> MeetingOut:
    if language not in {v for v, _ in LANGUAGES}:
        raise HTTPException(422, "Pilihan bahasa tidak dikenal.")
    if speakers not in {v for v, _ in SPEAKER_OPTIONS}:
        raise HTTPException(422, "Pilihan jumlah pembicara tidak dikenal.")

    filename = Path((file.filename or "").replace("\\", "/")).name or "rekaman"
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in settings.extensions:
        raise HTTPException(400, f"Format .{ext or '?'} tidak didukung. Gunakan: {', '.join(settings.extensions).upper()}.")

    meeting_id = uuid.uuid4().hex
    rel = Path("audio") / meeting_id / f"original.{ext}"
    dest = settings.data_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(413, f"File terlalu besar. Batas {settings.max_upload_mb} MB (ubah MAX_UPLOAD_MB di .env).")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "File kosong.")
    except BaseException:
        shutil.rmtree(dest.parent, ignore_errors=True)
        raise

    m = Meeting(
        id=meeting_id,
        filename=filename,
        audio_path=rel.as_posix(),
        size_bytes=size,
        duration_sec=duration_sec if duration_sec and duration_sec > 0 else None,
        language=language,
        speakers=speakers,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return MeetingOut.of(m)


@router.get("/meetings/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: str, db: Session = Depends(get_session)) -> MeetingDetail:
    m = _get(db, meeting_id)
    if m.status == "processing":
        step = _current_step(m)
        if step != m.current_step:
            m.current_step = step
            db.add(m)
            db.commit()
            db.refresh(m)
    return _detail(m)


@router.post("/meetings/{meeting_id}/start", response_model=MeetingDetail)
def start_meeting(meeting_id: str, db: Session = Depends(get_session)) -> MeetingDetail:
    m = _get(db, meeting_id)
    if m.status != "uploaded":
        raise HTTPException(409, "Rekaman ini sudah pernah dimulai.")
    _launch(db, m, resume=False)
    return _detail(m)


@router.post("/meetings/{meeting_id}/retry", response_model=MeetingDetail)
def retry_meeting(meeting_id: str, db: Session = Depends(get_session)) -> MeetingDetail:
    m = _get(db, meeting_id)
    if m.status not in ("failed", "cancelled"):
        raise HTTPException(409, "Hanya rekaman yang gagal atau dibatalkan yang bisa dicoba lagi.")
    _launch(db, m, resume=m.status == "failed")
    return _detail(m)


@router.post("/meetings/{meeting_id}/cancel", response_model=MeetingDetail)
def cancel_meeting(meeting_id: str, db: Session = Depends(get_session)) -> MeetingDetail:
    m = _get(db, meeting_id)
    if m.status != "processing":
        raise HTTPException(409, "Rekaman ini tidak sedang diproses.")
    runner.cancel(meeting_id)
    runner.wait(meeting_id, timeout=10)
    db.refresh(m)
    if m.status == "processing":  # pipeline sudah tidak ada tetapi pencatatan belum selesai
        m.status, m.finished_at = "cancelled", utcnow()
        db.add(m)
        db.commit()
        db.refresh(m)
    return _detail(m)


@router.get("/meetings/{meeting_id}/result")
def get_result(meeting_id: str, db: Session = Depends(get_session)) -> dict:
    m = _get(db, meeting_id)
    if m.status != "done":
        raise HTTPException(409, "Hasil belum siap: rekaman ini belum selesai diproses.")
    wd = job_dir(m.id)
    raw = read_json(wd / "hasil.json")
    if raw is None:
        raise HTTPException(500, "Berkas hasil.json tidak ada atau bukan JSON yang valid.")
    shaped = contract.to_contract(
        raw,
        meeting_id=m.id,
        filename=m.filename,
        created_at=_iso_utc(m.created_at),
        progress=read_json(wd / "progress.json"),
    )
    try:
        return contract.validate_result(shaped)
    except contract.ContractError as exc:
        raise HTTPException(500, "Hasil tidak sesuai kontrak: " + "; ".join(exc.problems)) from exc


@router.get("/meetings/{meeting_id}/audio")
def get_audio(meeting_id: str, db: Session = Depends(get_session)) -> FileResponse:
    m = _get(db, meeting_id)
    path = settings.data_path / m.audio_path
    if not path.is_file():
        raise HTTPException(404, "Berkas audio tidak ditemukan.")
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media)  # FileResponse melayani Range, jadi pemutar bisa melompat
