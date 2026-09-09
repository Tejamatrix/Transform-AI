from typing import Any, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Projects ----------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    source_count: int = 0
    output_count: int = 0

    class Config:
        from_attributes = True


# ---------- Sources ----------

class TextSourceCreate(BaseModel):
    project_id: str
    title: str = "Pasted text"
    text: str = Field(min_length=1)
    url: Optional[str] = None


class SourceOut(BaseModel):
    id: str
    project_id: str
    source_type: str
    title: str
    filename: str
    status: str
    error: str
    char_count: int = 0
    chunk_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class SourceDetail(SourceOut):
    raw_text: str = ""
    meta_json: dict = {}


# ---------- Analysis / Blueprint ----------

class SourceRef(BaseModel):
    source_id: str
    source_title: str
    page: int = 0
    section: str = ""
    paragraph: int = 0
    chunk_index: int = 0
    quote: str = ""


class Entity(BaseModel):
    name: str
    type: str
    description: str = ""


class KeyFact(BaseModel):
    text: str
    source_refs: list[SourceRef] = []


class BlueprintContent(BaseModel):
    domain: str = ""
    intent: str = ""
    summary: str = ""
    audience: str = ""
    communication_objective: str = ""
    entities: list[Entity] = []
    key_facts: list[KeyFact] = []
    statistics: list[str] = []
    timeline: list[dict] = []
    risks: list[str] = []
    recommendations: list[str] = []
    important_quotes: list[str] = []
    source_references: list[SourceRef] = []
    conflicts: list[dict] = []
    recommended_outputs: list[str] = []
    confidence: float = 0.0


class BlueprintOut(BaseModel):
    id: str
    project_id: str
    version: int
    status: str
    content: dict  # validated against BlueprintContent on the write path
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BlueprintPatch(BaseModel):
    content: dict


# ---------- Generation ----------

OUTPUT_TYPES = Literal[
    "executive_summary", "advisory", "linkedin", "x_thread",
    "presentation", "infographic", "video_package",
]

AUDIENCES = Literal[
    "general_public", "government_officials", "executives", "technical_teams",
    "security_professionals", "students", "customers", "internal_employees", "custom",
]
TONES = Literal[
    "professional", "formal", "neutral", "urgent", "educational",
    "persuasive", "technical", "conversational",
]
DETAIL_LEVELS = Literal["brief", "moderate", "detailed", "highly_detailed"]
OBJECTIVES = Literal["inform", "alert", "educate", "persuade", "promote", "brief", "mobilise"]
LANGUAGES = Literal["English", "Hindi", "Telugu"]


class GenerationConfig(BaseModel):
    audience: AUDIENCES = "general_public"
    tone: TONES = "professional"
    language: LANGUAGES = "English"
    detail: DETAIL_LEVELS = "moderate"
    objective: OBJECTIVES = "inform"
    style: Literal["standard", "storytelling", "data_driven", "action_oriented"] = "standard"
    custom_audience: str = ""
    variants: int = Field(default=1, ge=1, le=3)
    slide_count: int = Field(default=6, ge=3, le=12)


class GenerateRequest(BaseModel):
    project_id: str
    blueprint_id: str
    outputs: list[OUTPUT_TYPES] = Field(min_length=1)
    configuration: GenerationConfig = GenerationConfig()


class OutputOut(BaseModel):
    id: str
    project_id: str
    blueprint_id: str
    output_type: str
    config: dict
    content: dict
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    detail: str
    result_json: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EditActionRequest(BaseModel):
    action: Literal["edit", "regenerate", "shorten", "expand", "change_tone", "change_audience", "rewrite_section"]
    content: Optional[dict] = None
    section: Optional[str] = None
    tone: Optional[str] = None
    audience: Optional[str] = None
    instruction: str = ""


# ---------- Validation ----------

class ValidationClaimOut(BaseModel):
    claim: str
    status: Literal["VERIFIED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"]
    confidence: float = 0.0
    evidence: list[SourceRef] = []


class ValidationOut(BaseModel):
    id: str
    output_id: str
    version_id: str
    claims: list[ValidationClaimOut]
    summary: dict
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Export ----------

class ExportRequest(BaseModel):
    format: Literal["txt", "md", "docx", "srt", "pdf", "pptx", "html", "json", "csv"]


# ---------- Generic ----------

class MessageOut(BaseModel):
    message: str
    id: Optional[str] = None


class AuditOut(BaseModel):
    id: str
    user_id: Optional[str]
    project_id: Optional[str]
    action: str
    detail: str
    created_at: datetime

    class Config:
        from_attributes = True
