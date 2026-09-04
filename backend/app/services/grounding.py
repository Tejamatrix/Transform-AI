"""FactTrace overlay service.

Maps validation claims onto the generated content so the UI can render
inline, color-coded grounding (verified / partial / unsupported) directly in
the output text. Matching is deterministic: claims were extracted from the
flattened output text, so normalized sentence matching recovers their
positions reliably.
"""
from __future__ import annotations

import json
import re

from app.models.models import Output, ValidationResult
from sqlalchemy.orm import Session

_WORD_RE = re.compile(r"[^\w\u0900-\u097F\u0C00-\u0C7F]+")


def _norm(s: str) -> str:
    return _WORD_RE.sub(" ", s.lower()).strip()


def build_grounding_map(db: Session, output: Output, result: ValidationResult | None) -> dict | None:
    """Return {claim_index: {status, evidence, segments}} mapping for the UI.

    segments: list of [start_text, status_or_null] pairs the frontend can use,
    but the frontend re-splits sentences itself, so we return per-claim status
    plus a normalized claim index the frontend matches against.
    """
    if not result:
        return None
    claims = result.claims or []
    lookup: dict[str, int] = {}
    for i, c in enumerate(claims):
        key = _norm(str(c.get("claim", "")))
        if key and key not in lookup:
            lookup[key] = i
    return {
        "validated": True,
        "claims": [
            {
                "index": i,
                "claim": c.get("claim", ""),
                "status": c.get("status", "UNSUPPORTED"),
                "confidence": c.get("confidence", 0),
                "evidence": c.get("evidence", []),
            }
            for i, c in enumerate(claims)
        ],
        "summary": result.summary or {},
    }
