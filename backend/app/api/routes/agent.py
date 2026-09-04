from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Project, User
from app.prompts import prompts
from app.providers.llm.base import get_llm_provider
from app.services import rag
from app.services.audit import log_action
from app.utils.errors import NotFoundError, PermissionError_, AppError

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentQuestion(BaseModel):
    project_id: str
    question: str = Field(min_length=3, max_length=2000)


@router.post("")
def ask(body: AgentQuestion, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.get(Project, body.project_id)
    if not p:
        raise NotFoundError("Project")
    if p.user_id != user.id:
        raise PermissionError_()

    # Generic questions ("what are the key facts?") share little vocabulary
    # with the documents, so blend the question with the blueprint summary
    # to steer retrieval toward the project's topic.
    from app.models.models import Blueprint
    bp = db.query(Blueprint).filter(Blueprint.project_id == body.project_id) \
        .order_by(Blueprint.created_at.desc()).first()
    summary = (bp.content.get("summary", "") if bp and isinstance(bp.content, dict) else "")[:300]
    query = f"{body.question} {summary}".strip()

    evidence = rag.retrieve(db, body.project_id, query, k=8)
    if not evidence:
        return {
            "answer": "This project has no processed source material yet. Add a source "
                      "(document, URL or text) first, then ask again.",
            "evidence": [],
        }

    system, user_prompt = prompts.render(
        "agent", 1,
        QUESTION=body.question,
        EVIDENCE="\n\n".join(
            f"[{e['source_title']} | page {e['page']} | para {e['paragraph']}]\n{e['text'][:600]}"
            for e in evidence if e["text"]
        ),
    )
    try:
        raw = get_llm_provider().generate_json(system, user_prompt)
    except Exception:
        raise AppError("The assistant could not process this question. Please retry.", 502)

    answer = str(raw.get("answer", "")).strip()
    if not answer:
        raise AppError("The assistant returned no answer. Please rephrase and retry.", 502)

    # Offline mode: match the operator's language. If the question is written
    # in Hindi/Telugu script, translate the (English) grounded answer back.
    if raw.pop("_offline_fallback", False):
        from app.services.translator import detect_script_language, localize_content
        script_lang = detect_script_language(body.question)
        if script_lang:
            try:
                localized = localize_content({"answer": answer}, script_lang)
                answer = str(localized.get("answer", answer))
            except Exception:
                pass

    # keep only evidence that actually exists in retrieval (no hallucinated refs)
    valid_titles = {e["source_title"] for e in evidence}
    cited = [c for c in raw.get("evidence", []) if isinstance(c, dict)
             and (not c.get("source_title") or c.get("source_title") in valid_titles)][:4]

    log_action(db, user.id, body.project_id, "agent.query", body.question[:120])
    return {"answer": answer, "evidence": cited}
