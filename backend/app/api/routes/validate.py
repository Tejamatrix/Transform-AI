from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Output, OutputVersion, User
from app.schemas.schemas import ValidationOut
from app.services import validator as val_svc
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_

router = APIRouter(prefix="/api/validate", tags=["validate"])


def _own(output_id: str, db: Session, user_id: str) -> Output:
    o = db.get(Output, output_id)
    if not o or o.user_id != user_id:
        raise NotFoundError("Output")
    return o


@router.post("/{output_id}", response_model=ValidationOut, status_code=201)
def validate(output_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = _own(output_id, db, user.id)
    current = db.query(OutputVersion).filter(OutputVersion.output_id == o.id) \
        .order_by(OutputVersion.version_number.desc()).first()
    result = val_svc.validate_output(db, o)
    result.version_id = current.id if current else ""
    db.commit()
    log_action(db, user.id, o.project_id, "validation.run", f"{o.output_type}")
    return result


@router.get("/{output_id}")
def latest_validation(output_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = _own(output_id, db, user.id)
    from app.models.models import ValidationResult
    v = db.query(ValidationResult).filter(ValidationResult.output_id == o.id) \
        .order_by(ValidationResult.created_at.desc()).first()
    if not v:
        return {"validated": False}
    from app.services.grounding import build_grounding_map
    return {
        "validated": True,
        "id": v.id,
        "claims": v.claims,
        "summary": v.summary,
        "created_at": v.created_at.isoformat(),
        "grounding": build_grounding_map(db, o, v),
    }
