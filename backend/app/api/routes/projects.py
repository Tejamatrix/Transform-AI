from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Project, Source, Output, User
from app.schemas.schemas import ProjectCreate, ProjectOut, MessageOut
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_out(db: Session, p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        description=p.description,
        created_at=p.created_at.isoformat(),
        source_count=db.query(Source).filter(Source.project_id == p.id).count(),
        output_count=db.query(Output).filter(Output.project_id == p.id).count(),
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.updated_at.desc()).all()
    return [_to_out(db, p) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(user_id=user.id, name=body.name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    log_action(db, user.id, project.id, "project.created", project.name)
    return _to_out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user.id:
        raise PermissionError_()
    return _to_out(db, p)


@router.delete("/{project_id}", response_model=MessageOut)
def delete_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user.id:
        raise PermissionError_()
    # cascade delete dependents
    from app.models.models import Blueprint, SourceChunk, OutputVersion, ValidationResult, GenerationJob, AuditLog
    project_ids = [p.id]
    source_ids = [s.id for s in db.query(Source).filter(Source.project_id == p.id).all()]
    bp_ids = [b.id for b in db.query(Blueprint).filter(Blueprint.project_id == p.id).all()]
    output_ids = [o.id for o in db.query(Output).filter(Output.project_id == p.id).all()]
    if source_ids:
        db.query(SourceChunk).filter(SourceChunk.source_id.in_(source_ids)).delete(synchronize_session=False)
    if output_ids:
        db.query(ValidationResult).filter(ValidationResult.output_id.in_(output_ids)).delete(synchronize_session=False)
        db.query(OutputVersion).filter(OutputVersion.output_id.in_(output_ids)).delete(synchronize_session=False)
    db.query(Output).filter(Output.project_id.in_(project_ids)).delete(synchronize_session=False)
    db.query(Blueprint).filter(Blueprint.project_id.in_(project_ids)).delete(synchronize_session=False)
    db.query(Source).filter(Source.project_id.in_(project_ids)).delete(synchronize_session=False)
    db.query(GenerationJob).filter(GenerationJob.project_id.in_(project_ids)).delete(synchronize_session=False)
    db.delete(p)
    db.commit()
    log_action(db, user.id, None, "project.deleted", p.name)
    return MessageOut(message="Project deleted.", id=project_id)
