"""Output generation service — every output consumes the same blueprint."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.models import Blueprint, Output, OutputVersion, Project
from app.prompts import prompts
from app.providers.llm.base import get_llm_provider, LLMError
from app.services import rag
from app.schemas.schemas import GenerationConfig
from app.utils.errors import AppError, NotFoundError, PermissionError_, GenerationError


def _own_blueprint(db: Session, blueprint_id: str, user_id: str) -> Blueprint:
    bp = db.get(Blueprint, blueprint_id)
    if not bp:
        raise NotFoundError("Blueprint")
    if bp.user_id != user_id:
        raise PermissionError_()
    return bp


def generate_output(db: Session, blueprint: Blueprint, output_type: str,
                    config: GenerationConfig) -> Output:
    project = db.get(Project, blueprint.project_id)

    # Richer evidence set: blueprint summary + key facts as distinct queries
    fact_queries = [f.get("text", "") for f in blueprint.content.get("key_facts", [])[:3] if f.get("text")]
    evidence = rag.retrieve_multi(
        db, blueprint.project_id,
        queries=[blueprint.content.get("summary", "")[:300]] + fact_queries,
        k=10,
    )
    if not evidence:
        evidence = [{"source_id": "", "source_title": "", "page": 0, "section": "",
                     "paragraph": 0, "chunk_index": 0, "text": ""}]

    system, user = prompts.render(
        prompts.OUTPUT_TYPE_TASKS[output_type], 1,
        BLUEPRINT=json.dumps(blueprint.content, ensure_ascii=False),
        CONFIG=json.dumps(config.model_dump(), ensure_ascii=False),
        EVIDENCE="\n\n".join(
            f"[{e['source_title']} | page {e['page']} | para {e['paragraph']}]\n{e['text'][:700]}"
            for e in evidence if e["text"]
        ),
    )

    try:
        raw = get_llm_provider().generate_json(system, user)
    except LLMError:
        raise
    except Exception:
        raise GenerationError()

    if not isinstance(raw, dict) or not raw:
        raise GenerationError("The generator returned an invalid response. Retry generation.")

    # Offline engine writes English (plus localized headings); localize fully.
    # Live LLM writes natively per the prompt LANGUAGE RULE and is left untouched.
    used_offline = raw.pop("_offline_fallback", False) or get_llm_provider().name == "offline"
    if config.language and config.language != "English" and used_offline:
        try:
            from app.services.translator import localize_content
            raw = localize_content(raw, config.language.lower())
        except Exception:
            pass  # untranslated fallback content still ships

    # platform limits survive translation
    if output_type == "x_thread":
        posts = raw.get("posts")
        if isinstance(posts, list):
            raw["posts"] = [str(p)[:280] for p in posts]
        sp = raw.get("single_post")
        if isinstance(sp, str):
            raw["single_post"] = sp[:280]

    output = Output(
        project_id=blueprint.project_id,
        blueprint_id=blueprint.id,
        user_id=blueprint.user_id,
        output_type=output_type,
        config=config.model_dump(),
        content=raw,
        status="generated",
        current_version=1,
    )
    db.add(output)
    db.flush()
    db.add(OutputVersion(output_id=output.id, version_number=1, action="generate", content=raw))
    db.commit()
    db.refresh(output)
    return output
