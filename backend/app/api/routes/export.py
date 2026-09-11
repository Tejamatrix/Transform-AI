import urllib.parse

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Blueprint, Output, User
from app.schemas.schemas import ExportRequest
from app.services import exporter
from app.services.audit import log_action
from app.services import validator as val_svc
from app.utils.errors import NotFoundError, PermissionError_

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/{output_id}")
def export(output_id: str, body: ExportRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    o = db.get(Output, output_id)
    if not o or o.user_id != user.id:
        raise NotFoundError("Output")

    bp = db.get(Blueprint, o.blueprint_id)
    content = dict(o.content)
    quality = val_svc.score_quality(db, o, None)
    content["_quality"] = quality

    filename, data, media_type = exporter.export_output(o.output_type, content, body.format,
                                                        (bp.content.get("summary", "")[:40] if bp else o.output_type))
    log_action(db, user.id, o.project_id, "output.exported", f"{o.output_type} -> {body.format}")
    quoted = urllib.parse.quote(filename)
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )

@router.get("/{output_id}/quality")
def quality(output_id: str, refresh: bool = False, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    """Quality scores — computed once, then cached on the output row so page
    loads are instant. Pass ?refresh=true to force recomputation."""
    o = db.get(Output, output_id)
    if not o or o.user_id != user.id:
        raise NotFoundError("Output")
    if o.quality_json and not refresh:
        return o.quality_json
    from app.models.models import ValidationResult
    v = db.query(ValidationResult).filter(ValidationResult.output_id == o.id) \
        .order_by(ValidationResult.created_at.desc()).first()
    scores = val_svc.score_quality(db, o, v.summary if v else None)
    o.quality_json = scores
    db.commit()
    return scores
