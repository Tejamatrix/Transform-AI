"""RAG service: chunking, embedding persistence, semantic retrieval."""
from __future__ import annotations

import re

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Source, SourceChunk
from app.providers.embeddings import get_embedding_provider

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def chunk_text(text: str) -> list[dict]:
    """Paragraph-aware chunking that preserves page markers like [Page 3]."""
    chunks: list[dict] = []
    page = 0
    section = ""
    paragraphs = re.split(r"\n\s*\n", text)
    buf: list[str] = []
    buf_len = 0

    def flush():
        nonlocal buf, buf_len
        joined = " ".join(b.strip() for b in buf if b.strip())
        if joined:
            chunks.append({"text": joined, "page": page, "section": section,
                           "paragraph": len(chunks) + 1})
        buf, buf_len = [], 0

    for para in paragraphs:
        m = re.match(r"\s*\[Page (\d+)\]", para)
        if m:
            page = int(m.group(1))
        if not para.strip():
            continue
        # split very long paragraphs into sentence windows
        pieces = [para]
        if len(para) > CHUNK_SIZE:
            pieces = [para[i:i + CHUNK_SIZE] for i in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP)]
        for piece in pieces:
            if buf_len + len(piece) > CHUNK_SIZE and buf:
                flush()
            buf.append(piece)
            buf_len += len(piece)
    flush()
    return chunks


def embed_and_store_chunks(db: Session, source: Source) -> int:
    provider = get_embedding_provider()
    chunks = chunk_text(source.raw_text)
    if not chunks:
        return 0
    vectors = provider.embed([c["text"] for c in chunks])
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        db.add(SourceChunk(
            source_id=source.id,
            project_id=source.project_id,
            chunk_index=i,
            text=chunk["text"][:4000],
            page=chunk["page"],
            section=chunk["section"],
            paragraph=chunk["paragraph"],
            embedding=vec.astype(np.float32).tobytes(),
        ))
    db.commit()
    return len(chunks)


def _keywords(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z0-9']{3,}", text)}


def _hybrid_score(qvec: np.ndarray, q_kw: set[str], row_text: str, vec: np.ndarray) -> float:
    """Dense cosine + lexical overlap boost — hashed embeddings are lexical,
    so keyword agreement is a strong relevance signal here."""
    denom = (float(np.linalg.norm(qvec)) * float(np.linalg.norm(vec))) or 1e-9
    cosine = float(np.dot(qvec, vec) / denom)
    kw = _keywords(row_text)
    if q_kw and kw:
        overlap = len(q_kw & kw) / len(q_kw)
    else:
        overlap = 0.0
    return cosine + 0.35 * overlap


def retrieve(db: Session, project_id: str, query: str, k: int = 6) -> list[dict]:
    """Hybrid semantic retrieval across all sources in a project."""
    rows = db.query(SourceChunk).filter(SourceChunk.project_id == project_id).all()
    if not rows:
        return []
    provider = get_embedding_provider()
    qvec = provider.embed([query])[0]
    q_kw = _keywords(query)
    sources = {s.id: s for s in db.query(Source).filter(Source.project_id == project_id).all()}
    scored: list[tuple[float, SourceChunk]] = []
    for row in rows:
        if not row.embedding:
            continue
        vec = np.frombuffer(row.embedding, dtype=np.float32)
        scored.append((_hybrid_score(qvec, q_kw, row.text, vec), row))
    scored.sort(key=lambda x: -x[0])
    out = []
    seen: set[str] = set()
    for score, row in scored:
        if row.id in seen:
            continue
        seen.add(row.id)
        src = sources.get(row.source_id)
        out.append({
            "source_id": row.source_id,
            "source_title": (src.title if src else "") or (src.filename if src else ""),
            "source_type": src.source_type if src else "",
            "page": row.page,
            "section": row.section,
            "paragraph": row.paragraph,
            "chunk_index": row.chunk_index,
            "text": row.text,
            "score": round(score, 4),
        })
        if len(out) >= k:
            break
    return out


def retrieve_multi(db: Session, project_id: str, queries: list[str], k: int = 12) -> list[dict]:
    """Multi-query retrieval with reciprocal-rank fusion — several phrasings
    of the information need are asked at once; chunks that rank well across
    queries are the most relevant. Improves evidence coverage on vague queries."""
    rows = db.query(SourceChunk).filter(SourceChunk.project_id == project_id).all()
    if not rows:
        return []
    provider = get_embedding_provider()
    sources = {s.id: s for s in db.query(Source).filter(Source.project_id == project_id).all()}
    rrf: dict[str, float] = {}
    best: dict[str, tuple[float, SourceChunk]] = {}
    for q in [q for q in queries if q.strip()]:
        qvec = provider.embed([q])[0]
        q_kw = _keywords(q)
        scored: list[tuple[float, SourceChunk]] = []
        for row in rows:
            if not row.embedding:
                continue
            vec = np.frombuffer(row.embedding, dtype=np.float32)
            scored.append((_hybrid_score(qvec, q_kw, row.text, vec), row))
        scored.sort(key=lambda x: -x[0])
        for rank, (score, row) in enumerate(scored[:k]):
            rrf[row.id] = rrf.get(row.id, 0.0) + 1.0 / (60 + rank)
            if row.id not in best or score > best[row.id][0]:
                best[row.id] = (score, row)
    ranked = sorted(rrf.items(), key=lambda x: -x[1])
    out = []
    for chunk_id, fused in ranked:
        score, row = best[chunk_id]
        src = sources.get(row.source_id)
        out.append({
            "source_id": row.source_id,
            "source_title": (src.title if src else "") or (src.filename if src else ""),
            "source_type": src.source_type if src else "",
            "page": row.page,
            "section": row.section,
            "paragraph": row.paragraph,
            "chunk_index": row.chunk_index,
            "text": row.text,
            "score": round(fused, 4),
        })
        if len(out) >= k:
            break
    return out
