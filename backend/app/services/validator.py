"""Trust layer: fact validation + quality scoring."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.models import Output, ValidationResult
from app.prompts import prompts
from app.providers.llm.base import get_llm_provider
from app.services import rag
from app.utils.errors import AppError, NotFoundError, PermissionError_


def _output_text(content: dict) -> str:
    """Flatten structured output content into plain text for claim extraction."""
    parts: list[str] = []

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            parts.append(obj)

    walk(content)
    return "\n".join(parts)


def validate_output(db: Session, output: Output) -> ValidationResult:
    evidence = rag.retrieve(db, output.project_id, _output_text(output.content)[:600], k=14)
    system, user = prompts.render(
        "validator", 1,
        OUTPUT=json.dumps(output.content, ensure_ascii=False)[:20000],
        EVIDENCE="\n\n".join(
            f"[{e['source_title']} | page {e['page']} | para {e['paragraph']}]\n{e['text'][:500]}"
            for e in evidence if e["text"]
        ),
    )
    try:
        raw = get_llm_provider().generate_json(system, user)
    except Exception:
        raise AppError("Validation failed. Please retry.", 502)

    if not isinstance(raw, dict):
        raise AppError("Validator returned an invalid structure. Please retry.", 502)

    # Normalize live-LLM claim shapes: str entries, status casing, numeric confidence.
    norm_claims = []
    for c in raw.get("claims") or []:
        if isinstance(c, str) and c.strip():
            norm_claims.append({"claim": c.strip()[:600], "status": "UNSUPPORTED",
                                "confidence": 0.0, "evidence": []})
        elif isinstance(c, dict) and str(c.get("claim", "")).strip():
            status = str(c.get("status", "UNSUPPORTED")).upper().replace(" ", "_")
            if status not in ("VERIFIED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"):
                status = "VERIFIED" if "VERIF" in status else "UNSUPPORTED"
            try:
                conf = max(0.0, min(1.0, float(c.get("confidence", 0) or 0)))
            except (TypeError, ValueError):
                conf = 0.0
            ev = [e for e in (c.get("evidence") or []) if isinstance(e, dict)]
            norm_claims.append({"claim": str(c["claim"])[:600], "status": status,
                                "confidence": round(conf, 2), "evidence": ev[:4]})
    raw["claims"] = norm_claims[:60]

    summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
    if not summary.get("total") and norm_claims:
        v = sum(1 for c in norm_claims if c["status"] == "VERIFIED")
        p = sum(1 for c in norm_claims if c["status"] == "PARTIALLY_SUPPORTED")
        summary = {"verified": v, "partially_supported": p,
                   "unsupported": len(norm_claims) - v - p, "total": len(norm_claims)}
    raw["summary"] = summary

    if not norm_claims:
        raise AppError("Validator returned an invalid structure. Please retry.", 502)

    result = ValidationResult(
        output_id=output.id,
        version_id="",  # set by route against current version
        claims=raw.get("claims", []),
        summary=raw.get("summary", {}),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def score_quality(db: Session, output: Output, validation_summary: dict | None) -> dict:
    from app.models.models import Blueprint
    bp = db.get(Blueprint, output.blueprint_id)
    system, user = prompts.render(
        "quality", 1,
        OUTPUT=json.dumps(output.content, ensure_ascii=False)[:15000],
        BLUEPRINT=json.dumps((bp.content if bp else {}), ensure_ascii=False)[:8000],
        VALIDATION=json.dumps(validation_summary or {}, ensure_ascii=False),
    )
    try:
        scores = get_llm_provider().generate_json(system, user)
        if not isinstance(scores, dict) or "overall" not in scores:
            raise ValueError
        return scores
    except Exception:
        # deterministic fallback so scoring never blocks the workflow
        from app.providers.llm.offline_engine import run_quality
        return run_quality(output.content, (bp.content if bp else {}), validation_summary)
