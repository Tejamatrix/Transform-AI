import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON, Boolean, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32), default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    projects: Mapped[list["Project"]] = relationship(back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="projects")
    sources: Mapped[list["Source"]] = relationship(back_populates="project")
    blueprints: Mapped[list["Blueprint"]] = relationship(back_populates="project")
    outputs: Mapped[list["Output"]] = relationship(back_populates="project")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(512), default="")
    filename: Mapped[str] = mapped_column(String(512), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped["Project"] = relationship(back_populates="sources")
    chunks: Mapped[list["SourceChunk"]] = relationship(back_populates="source")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(255), default="")
    paragraph: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source: Mapped["Source"] = relationship(back_populates="chunks")


class Blueprint(Base):
    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    project: Mapped["Project"] = relationship(back_populates="blueprints")
    outputs: Mapped[list["Output"]] = relationship(back_populates="blueprint")


class Output(Base):
    __tablename__ = "outputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    blueprint_id: Mapped[str] = mapped_column(String(36), ForeignKey("blueprints.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    output_type: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="generated")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    blueprint: Mapped["Blueprint"] = relationship(back_populates="outputs")
    project: Mapped["Project"] = relationship(back_populates="outputs")
    versions: Mapped[list["OutputVersion"]] = relationship(back_populates="output")
    validations: Mapped[list["ValidationResult"]] = relationship(back_populates="output")


class OutputVersion(Base):
    __tablename__ = "output_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    output_id: Mapped[str] = mapped_column(String(36), ForeignKey("outputs.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(String(64), default="generate")
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    output: Mapped["Output"] = relationship(back_populates="versions")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    output_id: Mapped[str] = mapped_column(String(36), ForeignKey("outputs.id"), index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("output_versions.id"), index=True)
    claims: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    output: Mapped["Output"] = relationship(back_populates="validations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
