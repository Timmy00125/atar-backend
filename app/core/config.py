from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "ATAR Backend"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "atar_db"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/atar_db"

    # Google Gemini
    GOOGLE_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
