from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./tripmind.db"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT: int = 90
    HTTP_TIMEOUT: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
