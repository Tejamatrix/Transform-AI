from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Blueprint, Project, User
from app.schemas.schemas import BlueprintOut
from app.services import analyzer as analyzer_svc
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/{project_id}", response_model=BlueprintOut, status_code=201)
def run_analysis(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    blueprint = analyzer_svc.analyze_project(db, project_id, user.id)
    log_action(db, user.id, project_id, "analysis.completed", f"blueprint {blueprint.id}")
    return blueprint


@router.get("/{project_id}", response_model=list[BlueprintOut])
def list_analyses(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Project, project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user.id:
        raise PermissionError_()
    return db.query(Blueprint).filter(Blueprint.project_id == project_id) \
        .order_by(Blueprint.created_at.desc()).all()
