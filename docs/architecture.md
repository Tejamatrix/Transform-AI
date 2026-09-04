# TransformAI — Architecture

## System flow

```
SOURCE MATERIAL (PDF/DOCX/TXT/URL/text)
      ↓  ingestion service (pluggable extractors)
RAW TEXT + METADATA (filename, page, paragraph preserved)
      ↓  chunking -> embedding -> vector storage (source_chunks)
CONTENT UNDERSTANDING (analyzer service + LLM)
      ↓
TRANSFORMATION BLUEPRINT  ←── editable (PATCH /api/blueprints/{id})
      ↓
OUTPUT PLANNING (operator selects formats + configuration)
      ↓
GENERATION (all generators consume the SAME blueprint + RAG evidence)
      ↓
FACT VALIDATION (claims vs retrieved evidence)
      ↓  + QUALITY SCORING
HUMAN REVIEW (edit / regenerate / shorten / expand / tone / versions)
      ↓
EXPORT (MD, TXT, DOCX, SRT)
```

## Key decisions

### 1. Blueprint as single source of truth
The analyzer runs once per project and produces `BlueprintContent` (validated by
Pydantic). Generators receive `BLUEPRINT + CONFIG + EVIDENCE` — never raw sources.
This guarantees AC5 (consistency): all outputs share the same facts and entities.

### 2. LLM abstraction
`LLMProvider` interface with two implementations:
- `OpenAIProvider` — any OpenAI-compatible endpoint (OpenAI, Azure, Groq, Ollama).
- `OfflineProvider` — deterministic heuristic engine that consumes the same prompts
  (it parses the `---MARKER---` context blocks). This makes the full product
  demonstrable without API keys and gives tests a deterministic provider.

Switching providers changes generation quality only — no application code changes.

### 3. RAG layer
- Chunking: paragraph-aware, ~900 chars, 120 overlap, preserves `[Page N]` markers.
- Embeddings: `HashedEmbeddingProvider` (deterministic feature hashing, dim 512)
  or OpenAI embeddings; persisted as bytes in `source_chunks.embedding`.
- Retrieval: cosine similarity over project-scoped chunks (numpy flat index —
  the FAISS-style MVP). Store abstraction allows Chroma/pgvector/FAISS drop-in.

### 4. FactTrace
Key facts and generated claims carry `SourceRef {source_id, source_title, page,
section, paragraph, chunk_index, quote}`. Validation attaches best-matching
evidence per claim with status VERIFIED / PARTIALLY_SUPPORTED / UNSUPPORTED.

### 5. Jobs
`workers/queue.py` — thread-pool executor with progress reporting to
`generation_jobs`. The `enqueue(job_id, fn)` interface is deliberately
Celery/RQ-compatible.

### 6. Structured responses
Every LLM call has a versioned prompt (registry in `app/prompts/prompts.py`) and a
Pydantic schema. Invalid responses trigger `AppError` → user-visible retry message,
never a stack trace.

## Data model

```
User 1─* Project 1─* Source 1─* SourceChunk
              │ 1─* Blueprint (content JSON, versioned)
              │ 1─* Output (blueprint_id FK) 1─* OutputVersion
              │                            1─* ValidationResult
              │ 1─* GenerationJob
              └─* AuditLog
```

## API surface

Auth: `POST /api/auth/register|login|logout`
Projects: `GET|POST /api/projects`, `GET|DELETE /api/projects/{id}`
Sources: `POST /api/sources/upload|url|text`, `GET /api/sources?project_id`, `GET /api/sources/{id}`
Analysis: `POST|GET /api/analysis/{project_id}`
Blueprint: `GET|PATCH /api/blueprints/{id}`
Generation: `POST /api/generate`, `GET /api/generate/job/{id}`,
            `GET /api/generate/project/{id}`, `GET /api/generate/output/{id}`,
            `GET .../versions`, `POST .../edit`, `POST .../regenerate`
Validation: `POST|GET /api/validate/{output_id}`
Export: `POST /api/export/{output_id}` (+ `/quality`)
Audit: `GET /api/audit`
Health: `GET /api/health` · Docs: `/api/docs`
