from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Blueprint, Project, User
from app.schemas.schemas import BlueprintOut, BlueprintPatch, MessageOut
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_

router = APIRouter(prefix="/api/blueprints", tags=["blueprints"])


def _own(db: Session, blueprint_id: str, user_id: str) -> Blueprint:
    bp = db.get(Blueprint, blueprint_id)
    if not bp:
        raise NotFoundError("Blueprint")
    if bp.user_id != user_id:
        raise PermissionError_()
    return bp


@router.get("/{blueprint_id}", response_model=BlueprintOut)
def get_blueprint(blueprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _own(db, blueprint_id, user.id)


@router.patch("/{blueprint_id}", response_model=BlueprintOut)
def patch_blueprint(blueprint_id: str, body: BlueprintPatch, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    bp = _own(db, blueprint_id, user.id)
    # Validate against schema; preserve unknown keys the operator added.
    from app.schemas.schemas import BlueprintContent
    merged = {**bp.content, **body.content}
    validated = BlueprintContent(**{k: v for k, v in merged.items() if k in BlueprintContent.model_fields})
    bp.content = validated.model_dump()
    bp.version += 1
    db.commit()
    db.refresh(bp)
    log_action(db, user.id, bp.project_id, "blueprint.edited", f"v{bp.version}")
    return bp
