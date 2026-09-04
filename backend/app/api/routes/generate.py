import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Blueprint, GenerationJob, Output, OutputVersion, Project, User
from app.schemas.schemas import GenerateRequest, JobOut, OutputOut, EditActionRequest
from app.services import generator as gen_svc
from app.services import validator as val_svc
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_, AppError
from app.workers.queue import enqueue

router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("", response_model=JobOut, status_code=202)
def generate(body: GenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Project, body.project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user.id:
        raise PermissionError_()
    bp = db.get(Blueprint, body.blueprint_id)
    if not bp or bp.project_id != body.project_id or bp.user_id != user.id:
        raise NotFoundError("Blueprint")

    job = GenerationJob(
        user_id=user.id, project_id=body.project_id,
        job_type="generate", status="queued",
        detail=f"{len(body.outputs)} output(s): {', '.join(body.outputs)}",
    )
    db.add(job)
    db.commit()

    requested = body.outputs
    config = body.configuration
    blueprint_id = body.blueprint_id
    project_id = body.project_id
    user_id = user.id

    def work(report) -> dict:
        made: list[str] = []
        for i, output_type in enumerate(requested):
            report(int(10 + 80 * i / len(requested)), f"Generating {output_type}...")
            db2 = SessionLocalSafe()
            try:
                bp2 = db2.get(Blueprint, blueprint_id)
                output = gen_svc.generate_output(db2, bp2, output_type, config)
                made.append(output.id)
            finally:
                db2.close()
        return {"output_ids": made}

    enqueue(job.id, work)
    log_action(db, user.id, project_id, "generate.started", ", ".join(requested))
    return job


def SessionLocalSafe():
    from app.core.database import SessionLocal
    return SessionLocal()


@router.get("/job/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise NotFoundError("Job")
    return job


@router.get("/project/{project_id}", response_model=list[OutputOut])
def list_outputs(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user.id:
        raise PermissionError_()
    return db.query(Output).filter(Output.project_id == project_id) \
        .order_by(Output.created_at.desc()).all()


@router.get("/output/{output_id}", response_model=OutputOut)
def get_output(output_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = db.get(Output, output_id)
    if not o or o.user_id != user.id:
        raise NotFoundError("Output")
    return o


@router.get("/output/{output_id}/versions")
def list_versions(output_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = db.get(Output, output_id)
    if not o or o.user_id != user.id:
        raise NotFoundError("Output")
    versions = db.query(OutputVersion).filter(OutputVersion.output_id == output_id) \
        .order_by(OutputVersion.version_number.desc()).all()
    return [{"id": v.id, "version_number": v.version_number, "action": v.action,
             "created_at": v.created_at.isoformat(), "content": v.content} for v in versions]


@router.post("/output/{output_id}/edit", response_model=OutputOut)
def edit_output(output_id: str, body: EditActionRequest, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    o = db.get(Output, output_id)
    if not o or o.user_id != user.id:
        raise NotFoundError("Output")
    bp = db.get(Blueprint, o.blueprint_id)

    if body.action == "edit":
        if body.content is None:
            raise AppError("Edited content is required.")
        new_content = body.content
        action = "manual_edit"
    else:
        action = body.action
        from app.providers.llm.offline_engine import run_edit
        new_content = run_edit(action, o.content, body.section, body.tone, body.audience,
                               body.instruction, (bp.content if bp else {}), o.config)

    o.content = new_content
    o.current_version += 1
    db.add(OutputVersion(output_id=o.id, version_number=o.current_version, action=action, content=new_content))
    db.commit()
    db.refresh(o)
    log_action(db, user.id, o.project_id, "output.edited", f"{o.output_type} v{o.current_version} ({action})")
    return o


@router.post("/output/{output_id}/regenerate", response_model=OutputOut)
def regenerate_output(output_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = db.get(Output, output_id)
    if not o or o.user_id != user.id:
        raise NotFoundError("Output")
    bp = db.get(Blueprint, o.blueprint_id)
    if not bp:
        raise NotFoundError("Blueprint")
    config = o.config
    try:
        from app.schemas.schemas import GenerationConfig
        cfg = GenerationConfig(**config)
    except Exception:
        cfg = GenerationConfig()
    fresh = gen_svc.generate_output(db, bp, o.output_type, cfg)
    o.content = fresh.content
    o.current_version += 1
    db.add(OutputVersion(output_id=o.id, version_number=o.current_version, action="regenerate", content=o.content))
    db.query(OutputVersion).filter(OutputVersion.output_id == fresh.id).delete(synchronize_session=False)
    db.delete(fresh)
    db.commit()
    db.refresh(o)
    log_action(db, user.id, o.project_id, "output.regenerated", o.output_type)
    return o
