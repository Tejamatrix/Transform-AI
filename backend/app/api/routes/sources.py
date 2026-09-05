import os
import re
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Project, Source, User
from app.schemas.schemas import TextSourceCreate, SourceOut, SourceDetail
from app.services.ingestion import get_extractor, get_extractor_for_upload, validate_upload
from app.services import rag
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_, IngestionError, AppError

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _own_project(db: Session, project_id: str, user_id: str) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user_id:
        raise PermissionError_()
    return p


def _out(s: Source, chunk_count: int = 0) -> SourceOut:
    return SourceOut(
        id=s.id, project_id=s.project_id, source_type=s.source_type, title=s.title,
        filename=s.filename, status=s.status, error=s.error,
        char_count=len(s.raw_text or ""), chunk_count=chunk_count,
        created_at=s.created_at.isoformat(),
    )


def _process(db: Session, source: Source, data: bytes | str, source_type: str, user: User,
             filename: str = ""):
    """Extract -> chunk -> embed -> ready (synchronous for MVP; queue-compatible)."""
    try:
        if source_type == "code" and filename:
            extractor = get_extractor_for_upload(filename)
        else:
            extractor = get_extractor(source_type)
        text, meta = extractor.extract(data)
        source.raw_text = text
        source.title = source.title or meta.get("title") or source.filename or source_type.title()
        source.meta_json = meta
        source.status = "ready"
        chunk_count = rag.embed_and_store_chunks(db, source)
        log_action(db, user.id, source.project_id, "source.processed", f"{source_type}: {source.title} ({chunk_count} chunks)")
    except IngestionError as e:
        source.status = "failed"
        source.error = e.message
        db.commit()
    except Exception:
        source.status = "failed"
        source.error = "Processing failed unexpectedly. Please try again."
        db.commit()


@router.post("/upload", response_model=SourceOut, status_code=201)
async def upload_source(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _own_project(db, project_id, user.id)
    data = await file.read()
    ext = validate_upload(file.filename or "", len(data), file.content_type or "")
    safe_name = f"{uuid.uuid4().hex}_{re.sub(r'[^A-Za-z0-9._-]', '_', file.filename)}"
    path = os.path.join(settings.UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(data)

    source = Source(
        project_id=project.id, user_id=user.id, source_type=ext,
        title=re.sub(r"\.[a-zA-Z0-9]+$", "", file.filename or "Upload"),
        filename=file.filename or "upload", status="processing",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    log_action(db, user.id, project.id, "source.uploaded", file.filename or "")
    _process(db, source, data, ext, user, filename=file.filename or "")
    db.refresh(source)
    from app.models.models import SourceChunk
    cc = db.query(SourceChunk).filter(SourceChunk.source_id == source.id).count()
    if source.status == "failed":
        return JSONResponse(status_code=422, content={
            "detail": source.error, "source_id": source.id, "status": "failed"})
    return _out(source, cc)


@router.post("/url", response_model=SourceOut, status_code=201)
def add_url_source(body: TextSourceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not body.url:
        raise IngestionError("A URL is required.")
    project = _own_project(db, body.project_id, user.id)
    source = Source(project_id=project.id, user_id=user.id, source_type="url",
                    title=body.url, status="processing")
    db.add(source)
    db.commit()
    db.refresh(source)
    log_action(db, user.id, project.id, "source.url_added", body.url)
    _process(db, source, body.url, "url", user)
    db.refresh(source)
    from app.models.models import SourceChunk
    cc = db.query(SourceChunk).filter(SourceChunk.source_id == source.id).count()
    if source.status == "failed":
        return JSONResponse(status_code=422, content={"detail": source.error, "source_id": source.id, "status": "failed"})
    return _out(source, cc)


@router.post("/text", response_model=SourceOut, status_code=201)
def add_text_source(body: TextSourceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _own_project(db, body.project_id, user.id)
    source = Source(project_id=project.id, user_id=user.id, source_type="text",
                    title=body.title or "Pasted text", status="processing")
    db.add(source)
    db.commit()
    db.refresh(source)
    log_action(db, user.id, project.id, "source.text_added", body.title or "")
    _process(db, source, body.text, "text", user)
    db.refresh(source)
    from app.models.models import SourceChunk
    cc = db.query(SourceChunk).filter(SourceChunk.source_id == source.id).count()
    if source.status == "failed":
        return JSONResponse(status_code=422, content={"detail": source.error, "source_id": source.id, "status": "failed"})
    return _out(source, cc)


@router.get("", response_model=list[SourceOut])
def list_sources(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _own_project(db, project_id, user.id)
    sources = db.query(Source).filter(Source.project_id == project_id).order_by(Source.created_at.desc()).all()
    from app.models.models import SourceChunk
    out = []
    for s in sources:
        cc = db.query(SourceChunk).filter(SourceChunk.source_id == s.id).count()
        out.append(_out(s, cc))
    return out


@router.get("/{source_id}", response_model=SourceDetail)
def get_source(source_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.get(Source, source_id)
    if not s:
        raise NotFoundError("Source")
    if s.user_id != user.id:
        raise PermissionError_()
    from app.models.models import SourceChunk
    cc = db.query(SourceChunk).filter(SourceChunk.source_id == s.id).count()
    d = _out(s, cc)
    return SourceDetail(**d.model_dump(), raw_text=s.raw_text, meta_json=s.meta_json)


@router.get("/{source_id}/transcript")
def get_transcript(source_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Transcript of a video/audio source as a downloadable TXT (Whisper layer)."""
    import urllib.parse

    s = db.get(Source, source_id)
    if not s:
        raise NotFoundError("Source")
    if s.user_id != user.id:
        raise PermissionError_()

    text = s.raw_text or ""
    start = text.find("Spoken audio transcript")
    if start == -1:
        raise AppError("This source has no transcript (audio was absent or transcription unavailable).")
    transcript = text[start + len("Spoken audio transcript (Whisper):"):].strip()
    # cut before the next section if present (frame OCR block)
    for marker in ("Text extracted from sampled video frames",):
        idx = transcript.find(marker)
        if idx != -1:
            transcript = transcript[:idx].strip()
    if not transcript:
        raise AppError("This source has no transcript content.")

    filename = (s.title or s.filename or "transcript").strip() or "transcript"
    safe = urllib.parse.quote(f"transcript_{filename}.txt")
    log_action(db, user.id, s.project_id, "source.transcript_exported", s.title or s.filename)
    return JSONResponse(
        content={"filename": safe, "transcript": transcript},
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe}"},
    )
