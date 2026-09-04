# TransformAI

AI-powered multimodal content transformation platform. Upload heterogeneous source
material (PDF, DOCX, TXT, URL, pasted text), let the system build a single
**Transformation Blueprint**, and generate audience-specific deliverables — Executive
Summary, Advisory, LinkedIn, X Thread, Presentation, Infographic spec, Video Package —
with **FactTrace** source traceability, fact validation and quality scoring.

## Quick start

### Backend (port 8000)

```bash
cd backend
py -3.13 -m venv venv                # first run only
.\venv\Scripts\pip install -r requirements.txt email-validator
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/api/docs

### Frontend (port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — register an operator account and start a transformation.

> **No API keys required.** The platform ships with a deterministic offline AI engine
> (`LLM_PROVIDER=offline`) that runs the full pipeline — analysis, all 7 generators,
> validation, quality — locally. To upgrade quality, set `LLM_PROVIDER=openai`,
> `OPENAI_API_KEY=...` (optionally `OPENAI_BASE_URL` for Azure/Groq/Ollama-compatible
> endpoints) in `backend/.env` and restart. No code changes needed.

## Demo script (2-minute SIH flow)

1. Open the platform → sign in
2. **New Transformation** → name it → paste the incident report (or upload the PDF)
3. **Analyze sources** → review the Blueprint: domain, intent, entities, facts, timeline
4. Continue → recommended outputs are pre-selected (Advisory, Exec Summary, Presentation, Infographic)
5. Pick audience/tone/objective → **Generate** → progress bar
6. Review outputs → open Advisory → **FactTrace** tab → click a claim → see source + page + evidence
7. Quality scores shown at the top (accuracy, fidelity, …)
8. Edit: Shorten / Change tone / Regenerate → version history updates
9. Export MD / DOCX (SRT for video package)

## Architecture

```
transform-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/      REST endpoints (auth, projects, sources, analysis,
│   │   │                    blueprints, generate, validate, export, audit)
│   │   ├── models/          SQLAlchemy: users, projects, sources, source_chunks,
│   │   │                    blueprints, outputs, output_versions, validation_results,
│   │   │                    audit_logs, generation_jobs
│   │   ├── schemas/         Pydantic contracts incl. BlueprintContent schema
│   │   ├── services/        ingestion, rag, analyzer, generator, validator, exporter
│   │   ├── providers/
│   │   │   ├── llm/         LLM abstraction: OpenAI-compatible + offline engine
│   │   │   └── embeddings.py  Embedding + vector store abstractions
│   │   ├── prompts/         Versioned prompt registry (analyzer, generators,
│   │   │                    validator, quality, editor)
│   │   ├── workers/         Thread-pool job queue (Celery-swappable)
│   │   ├── core/            config, security (PBKDF2 + JWT), database
│   │   └── utils/           errors — safe messages, no stack traces leak
│   └── tests/test_e2e.py    44-check end-to-end workflow test
└── frontend/
    └── src/
        ├── app/             Landing, auth, dashboard, wizard, review, settings
        ├── components/      Design system: Button, Card, Input, Badge, Toast,
        │                    OutputRenderer
        └── lib/             api client, types
```

### Design principles (enforced)

- **Blueprint is mandatory** — every generator consumes the same blueprint; no
  per-output re-interpretation of sources.
- **Structured AI responses** — Pydantic-validated; repair/retry on failure.
- **Provider abstraction** — LLM, embeddings and vector store are swappable via env.
- **Prompts live in the registry**, never in API handlers.
- **User isolation** — every query is ownership-checked; users never see each other's data.

### Swapping implementations

| Concern      | Env var               | Options                          |
| ------------ | --------------------- | -------------------------------- |
| LLM          | `LLM_PROVIDER`        | `offline` (default), `openai`    |
| Model        | `LLM_MODEL`           | any chat model                   |
| Embeddings   | `EMBEDDING_PROVIDER`  | `hashed` (default), `openai`     |
| Database     | `DATABASE_URL`        | SQLite (default), PostgreSQL     |

## Security

PBKDF2-SHA256 password hashing · JWT bearer auth · file type/size validation ·
path-safe uploads · user-level data isolation · audit logging · no secrets in
frontend · generic error messages (no stack traces).
