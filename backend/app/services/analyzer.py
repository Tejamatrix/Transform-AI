"""Content Understanding Engine — source text -> Transformation Blueprint."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import Blueprint, Project, Source
from app.prompts import prompts
from app.providers.llm.base import get_llm_provider, LLMError
from app.services import rag
from app.schemas.schemas import BlueprintContent
from app.utils.errors import AppError, NotFoundError, PermissionError_


def _own_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project")
    if project.user_id != user_id:
        raise PermissionError_()
    return project


def _source_ref_payload(source: Source, chunk: dict | None) -> dict:
    if chunk is None:
        return {"source_id": source.id, "source_title": source.title or source.filename,
                "page": 0, "section": "", "paragraph": 0, "chunk_index": 0, "quote": source.raw_text[:300]}
    return {
        "source_id": source.id,
        "source_title": source.title or source.filename,
        "page": chunk.get("page", 0),
        "section": chunk.get("section", ""),
        "paragraph": chunk.get("paragraph", 0),
        "chunk_index": chunk.get("chunk_index", 0),
        "quote": (chunk.get("text", "") or "")[:300],
    }


def _coerce_int(v, default: int = 0) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return default


def _normalize_source_ref(r) -> dict:
    if isinstance(r, str) and r.strip():
        return {"source_id": "", "source_title": r.strip()[:200], "page": 0, "section": "",
                "paragraph": 0, "chunk_index": 0, "quote": ""}
    if isinstance(r, dict):
        return {
            "source_id": str(r.get("source_id", "") or "")[:64],
            "source_title": str(r.get("source_title", "") or "")[:200],
            "page": _coerce_int(r.get("page")),
            "section": str(r.get("section", "") or "")[:120],
            "paragraph": _coerce_int(r.get("paragraph")),
            "chunk_index": _coerce_int(r.get("chunk_index")),
            "quote": str(r.get("quote", "") or "")[:300],
        }
    return {"source_id": "", "source_title": "", "page": 0, "section": "",
            "paragraph": 0, "chunk_index": 0, "quote": ""}


def _normalize_raw(raw: dict) -> dict:
    """Repair common LLM deviations so a live provider's near-miss JSON still
    validates instead of failing the analysis (strings-as-objects, bad
    numerics, scalar lists, etc.)."""
    if not isinstance(raw, dict):
        return {}

    # entities: str -> {name, type}
    ents = []
    for e in raw.get("entities") or []:
        if isinstance(e, str) and e.strip():
            ents.append({"name": e.strip()[:120], "type": "Entity", "description": ""})
        elif isinstance(e, dict) and str(e.get("name", "") or "").strip():
            ents.append({"name": str(e["name"])[:120], "type": str(e.get("type") or "Entity")[:40],
                         "description": str(e.get("description") or "")[:300]})
    raw["entities"] = ents[:40]

    # key_facts: str -> {text, source_refs}; deep-normalize nested refs
    facts = []
    for f in raw.get("key_facts") or []:
        if isinstance(f, str) and f.strip():
            facts.append({"text": f.strip()[:600], "source_refs": []})
        elif isinstance(f, dict) and str(f.get("text", "") or "").strip():
            refs = f.get("source_refs") if isinstance(f.get("source_refs"), list) else []
            facts.append({"text": str(f["text"])[:600],
                          "source_refs": [_normalize_source_ref(r) for r in refs][:4]})
    raw["key_facts"] = facts[:40]

    # scalar string lists
    for key in ("statistics", "risks", "recommendations", "important_quotes", "recommended_outputs"):
        val = raw.get(key)
        if isinstance(val, str):
            val = [val]
        if not isinstance(val, list):
            val = []
        raw[key] = [str(x)[:500] for x in val if x][:24]

    # timeline entries
    tl = []
    for t in raw.get("timeline") or []:
        if isinstance(t, str) and t.strip():
            tl.append({"date": "", "label": "", "event": t.strip()[:300]})
        elif isinstance(t, dict) and (t.get("event") or t.get("date")):
            tl.append({"date": str(t.get("date", ""))[:32], "label": str(t.get("label", ""))[:120],
                       "event": str(t.get("event", ""))[:300]})
    raw["timeline"] = tl[:24]

    # conflicts must be dicts
    raw["conflicts"] = [c for c in (raw.get("conflicts") or []) if isinstance(c, dict)][:10]

    # source_references must be dicts with a quote
    refs = []
    for r in raw.get("source_references") or []:
        if isinstance(r, dict):
            refs.append({"source_id": str(r.get("source_id", "")), "source_title": str(r.get("source_title", ""))[:200],
                         "page": int(r.get("page", 0) or 0), "section": str(r.get("section", ""))[:120],
                         "paragraph": int(r.get("paragraph", 0) or 0), "chunk_index": int(r.get("chunk_index", 0) or 0),
                         "quote": str(r.get("quote", ""))[:300]})
    raw["source_references"] = refs[:12]

    # scalars
    raw["summary"] = str(raw.get("summary", "") or "")[:4000]
    raw["domain"] = str(raw.get("domain", "general") or "general")[:40]
    raw["intent"] = str(raw.get("intent", "inform") or "inform")[:40]
    raw["audience"] = str(raw.get("audience", "") or "")[:120]
    raw["communication_objective"] = str(raw.get("communication_objective", "") or "")[:60]
    try:
        raw["confidence"] = max(0.0, min(1.0, float(raw.get("confidence", 0.7) or 0.7)))
    except (TypeError, ValueError):
        raw["confidence"] = 0.7
    return raw


def analyze_project(db: Session, project_id: str, user_id: str) -> Blueprint:
    project = _own_project(db, project_id, user_id)
    sources = db.query(Source).filter(Source.project_id == project_id, Source.status == "ready").all()
    if not sources:
        raise AppError("Add at least one processed source before analysis.")

    # Multi-query hybrid retrieval: several phrasings of the information need
    # are fused (RRF) so evidence coverage stays high even on thin sources.
    evidence = rag.retrieve_multi(
        db, project_id,
        queries=[
            " ".join(s.raw_text[:300] for s in sources[:2]),
            f"{sources[0].title or ''} key facts events dates numbers",
            "risks impact recommendations actions timeline",
        ],
        k=14,
    )

    ref_map = {e["source_id"]: e for e in evidence}
    # Code sources use a dedicated analyzer prompt (explains what the code does)
    has_code = any(s.source_type == "code" for s in sources)
    all_code = all(s.source_type == "code" for s in sources)
    prompt_name = "code_analyzer" if all_code else "analyzer"
    code_block = ""
    if has_code:
        code_block = "\n\n".join(
            f"### CODE: {s.title or s.filename} (language={s.meta_json.get('code_language', 'unknown')})\n"
            f"```\n{s.raw_text[:10000]}\n```"
            for s in sources if s.source_type == "code"
        )
    source_block = "\n\n".join(
        f"### SOURCE: {s.title or s.filename} (id={s.id}, type={s.source_type})\n{s.raw_text[:12000]}"
        for s in sources if s.source_type != "code"
    ) + code_block
    evidence_block = "\n\n".join(
        f"[{e['source_title']} | page {e['page']} | para {e['paragraph']}]\n{e['text'][:600]}"
        for e in evidence
    )

    system, user = prompts.render(
        prompt_name, 1,
        SOURCE=source_block,
        EVIDENCE=evidence_block,
    )

    try:
        raw = get_llm_provider().generate_json(system, user)
    except LLMError:
        raise
    except Exception:
        raise AppError("Analysis failed. Please retry.", 502)

    # Enforce schema with self-healing: normalize -> validate -> retry with
    # repair instructions -> deterministic offline fallback. The first attempt
    # must always yield a blueprint.
    content = None
    try:
        normalized = _normalize_raw(raw if isinstance(raw, dict) else {})
        content = BlueprintContent(**{k: v for k, v in normalized.items() if k in BlueprintContent.model_fields})
    except Exception:
        content = None

    if content is None:
        try:
            repair_user = (
                user
                + "\n\nIMPORTANT: The previous response failed schema validation. Return ONLY the JSON again, "
                "strictly matching the required keys and types: every list entry must be an object with the "
                "exact keys specified (no strings instead of objects). Use \"\" for unknown text fields and 0 "
                "for unknown numbers. Omit null values."
            )
            raw2 = get_llm_provider().generate_json(system, repair_user)
            normalized2 = _normalize_raw(raw2 if isinstance(raw2, dict) else {})
            content = BlueprintContent(**{k: v for k, v in normalized2.items() if k in BlueprintContent.model_fields})
        except Exception:
            content = None

    if content is None:
        # last resort: deterministic offline analysis — first attempt always yields a blueprint
        from app.providers.llm.offline_engine import run_analyzer
        combined_text = "\n\n".join(f"{s.title or s.filename}\n{s.raw_text[:8000]}" for s in sources)
        fallback = run_analyzer(combined_text, sources[0].title or sources[0].filename or "Source")
        content = BlueprintContent(**{k: v for k, v in fallback.items() if k in BlueprintContent.model_fields})

    # ---- deterministic self-heal on the live result ----
    combined_src = "\n".join(s.raw_text[:6000] for s in sources)

    # intent stabilization: strong alert signals override a soft "report" verdict
    import re as _re
    if content.intent == "report" and _re.search(
        r"unauthorized|breach|ransomware|attack|phishing|outage|exploit|compromis", combined_src, _re.I
    ):
        content = content.model_copy(update={"intent": "alert"})

    # thin-extraction backfill from the deterministic engine (per source)
    from app.providers.llm.offline_engine import run_analyzer as _off
    if not (content.recommendations and content.risks and content.statistics and content.important_quotes):
        for s in sources:
            mini = _off(s.raw_text[:8000], s.title or s.filename or "Source")
            updates = {}
            if not content.recommendations and mini["recommendations"]:
                updates["recommendations"] = mini["recommendations"][:6]
            if not content.risks and mini["risks"]:
                updates["risks"] = mini["risks"][:6]
            if not content.statistics and mini["statistics"]:
                updates["statistics"] = mini["statistics"][:8]
            if not content.important_quotes and mini["important_quotes"]:
                updates["important_quotes"] = mini["important_quotes"][:4]
            if not content.timeline and mini["timeline"]:
                updates["timeline"] = mini["timeline"][:8]
            if updates:
                content = content.model_copy(update=updates)
        if not content.recommended_outputs:
            content = content.model_copy(update={"recommended_outputs": [
                "executive_summary", "advisory", "presentation", "infographic"]})

    # Attach deterministic refs: each key fact gets its best-matching evidence
    fact_texts = [f.get("text", "") for f in (raw.get("key_facts") or [])]
    if fact_texts and evidence:
        from app.providers.embeddings import get_embedding_provider
        import numpy as np
        provider = get_embedding_provider()
        fvecs = provider.embed(fact_texts[:24])
        evecs = provider.embed([e["text"] for e in evidence])
        new_facts = []
        for i, f in enumerate(fact_texts):
            refs = []
            if i < len(fvecs):
                sims = [(float(np.dot(fvecs[i], ev) / ((np.linalg.norm(fvecs[i]) * np.linalg.norm(ev)) or 1e-9)), j)
                        for j, ev in enumerate(evecs)]
                sims.sort(reverse=True)
                for score, j in sims[:2]:
                    if score > 0.15:
                        e = evidence[j]
                        refs.append(_source_ref_payload(db.get(Source, e["source_id"]), e))
            new_facts.append({"text": f, "source_refs": refs})
        content.key_facts = new_facts  # type: ignore[assignment]
        content = BlueprintContent(**content.model_dump())  # re-validate after mutation

    content.source_references = [
        {"source_id": e["source_id"], "source_title": e["source_title"], "page": e["page"],
         "section": e["section"], "paragraph": e["paragraph"], "chunk_index": e["chunk_index"],
         "quote": e["text"][:300]} for e in evidence[:10]
    ]

    # Conflict detection across multiple sources (dates appearing with different facts)
    if len(sources) > 1:
        from app.providers.llm.offline_engine import detect_conflicts
        per_source = []
        for s in sources:
            from app.providers.llm.offline_engine import run_analyzer
            mini = run_analyzer(s.raw_text[:8000], s.title or s.filename)
            per_source.append({"source_title": s.title or s.filename, "timeline": mini["timeline"]})
        content.conflicts = detect_conflicts(per_source)  # type: ignore[assignment]

    blueprint = Blueprint(project_id=project_id, user_id=user_id, content=content.model_dump(), status="ready")
    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return blueprint
