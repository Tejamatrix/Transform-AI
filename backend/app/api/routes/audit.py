from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import AuditLog, User
from app.schemas.schemas import AuditOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(project_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(AuditLog).filter(AuditLog.user_id == user.id)
    if project_id:
        q = q.filter(AuditLog.project_id == project_id)
    return q.order_by(AuditLog.created_at.desc()).limit(100).all()
