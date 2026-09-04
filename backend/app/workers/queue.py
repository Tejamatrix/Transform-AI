"""Background job queue abstraction.

MVP: thread-pool executor writing progress to generation_jobs. The interface
(enqueue/get) is deliberately queue-implementation-agnostic so Celery/RQ can
replace it without touching routes or services.
"""
from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from app.core.database import SessionLocal
from app.models.models import GenerationJob

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="transformai-job")


def _run_job(job_id: str, fn: Callable[[object], dict]):
    """Execute job in a worker thread with its own DB session."""
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        job.status = "running"
        job.progress = max(job.progress, 5)
        db.commit()

        def report(pct: int, detail: str = ""):
            j = db.get(GenerationJob, job_id)
            if j:
                j.progress = min(99, max(j.progress, pct))
                if detail:
                    j.detail = detail
                db.commit()

        result = fn(report)
        job = db.get(GenerationJob, job_id)
        if job:
            job.status = "completed"
            job.progress = 100
            job.result_json = result or {}
            job.detail = ""
            db.commit()
    except Exception as e:
        db.rollback()
        job = db.get(GenerationJob, job_id)
        if job:
            job.status = "failed"
            job.detail = str(e) or "Job failed"
            db.commit()
        traceback.print_exc()
    finally:
        db.close()


def enqueue(job_id: str, fn: Callable[[object], dict]) -> str:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job:
            job.status = "queued"
            db.commit()
    finally:
        db.close()
    _executor.submit(_run_job, job_id, fn)
    return job_id
