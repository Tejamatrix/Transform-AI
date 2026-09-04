from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.utils.errors import AppError, app_error_handler, validation_error_handler, unhandled_handler
from app.api.routes import (
    auth, projects, sources, analysis, blueprints, generate, validate, export, audit, agent,
)

app = FastAPI(title=settings.APP_NAME, version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# register models
from app.models import models  # noqa: F401,E402

Base.metadata.create_all(bind=engine)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_handler)

from fastapi.exceptions import RequestValidationError  # noqa: E402

app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(sources.router)
app.include_router(analysis.router)
app.include_router(blueprints.router)
app.include_router(generate.router)
app.include_router(validate.router)
app.include_router(export.router)
app.include_router(audit.router)
app.include_router(agent.router)


@app.get("/api/health")
def health():
    from app.providers.llm.base import get_llm_provider
    from app.core.config import settings as s
    return {
        "status": "ok",
        "app": s.APP_NAME,
        "llm_provider": get_llm_provider().name,
        "llm_model": s.LLM_MODEL if s.LLM_PROVIDER == "openai" else "offline-engine",
        "llm_fallback": s.LLM_FALLBACK,
    }
