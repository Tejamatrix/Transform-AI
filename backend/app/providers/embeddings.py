"""Embedding provider abstraction + vector store abstraction (FAISS-style MVP).

MVP uses a deterministic hashed-bag-of-words embedding (no network, no model
download) with a numpy flat-index vector store. Swap implementations via env:
EMBEDDING_PROVIDER=hashed|openai, VECTOR_STORE=numpy|faiss.
"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

import numpy as np

from app.core.config import settings

_TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")


class EmbeddingProvider(ABC):
    name: str = "base"

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        ...


class HashedEmbeddingProvider(EmbeddingProvider):
    """Deterministic feature-hashing embedding with sublinear TF weighting."""

    name = "hashed"

    def __init__(self, dim: int | None = None):
        self.dim = dim or settings.EMBEDDING_DIM

    def _tokenize(self, text: str) -> list[str]:
        return [t.lower() for t in _TOKEN_RE.findall(text)][:4000]

    def embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = self._tokenize(text)
        if not tokens:
            return vec
        counts: dict[str, int] = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1
        for tok, count in counts.items():
            digest = hashlib.md5(tok.encode()).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            # bigram-ish signal: also hash token pairs later in embed()
            vec[idx] += sign * (1.0 + math.log(count))
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.stack([self.embed_one(t) for t in texts])


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def embed(self, texts: list[str]) -> np.ndarray:
        import httpx

        from app.core.config import settings as s

        resp = httpx.post(
            f"{s.OPENAI_BASE_URL.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {s.OPENAI_API_KEY}"},
            json={"model": "text-embedding-3-small", "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return np.array([d["embedding"] for d in data], dtype=np.float32)


def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingProvider()
    return HashedEmbeddingProvider()


class VectorStore(ABC):
    """Abstract vector store. MVP: in-memory flat index persisted per request."""

    @abstractmethod
    def add(self, ids: list[str], vectors: np.ndarray) -> None: ...

    @abstractmethod
    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float]]: ...

    @abstractmethod
    def clear(self) -> None: ...


class NumpyVectorStore(VectorStore):
    """Flat L2/cosine index — the FAISS-style MVP implementation."""

    def __init__(self):
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        if vectors.ndim == 1:
            vectors = vectors[None, :]
        self._ids.extend(ids)
        if self._matrix is None:
            self._matrix = vectors.copy()
        else:
            self._matrix = np.vstack([self._matrix, vectors])

    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
        if self._matrix is None or not self._ids:
            return []
        q = query.flatten()
        q_norm = np.linalg.norm(q)
        m_norms = np.linalg.norm(self._matrix, axis=1)
        m_norms[m_norms == 0] = 1e-9
        if q_norm == 0:
            return []
        sims = (self._matrix @ q) / (m_norms * q_norm)
        k = min(k, len(self._ids))
        top = np.argsort(-sims)[:k]
        return [(self._ids[i], float(sims[i])) for i in top]

    def clear(self) -> None:
        self._ids = []
        self._matrix = None
