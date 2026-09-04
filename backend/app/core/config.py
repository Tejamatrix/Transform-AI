from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "TransformAI"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "sqlite:///./transformai.db"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 25

    LLM_PROVIDER: str = "offline"
    GLM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    # When the live provider fails (quota, timeout, rate limit), fall back to the
    # offline engine instead of failing the request. "strict" disables fallback.
    LLM_FALLBACK: str = "offline"

    EMBEDDING_PROVIDER: str = "hashed"
    EMBEDDING_DIM: int = 512

    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
