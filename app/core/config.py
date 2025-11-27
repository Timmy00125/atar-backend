from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Any


class Settings(BaseSettings):
    PROJECT_NAME: str = "ATAR Backend"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info: Any) -> Any:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Google Gemini
    GOOGLE_API_KEY: str

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
