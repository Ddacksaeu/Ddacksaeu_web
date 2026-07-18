from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded exclusively from environment variables."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = "sqlite+pysqlite:///./ddacksaeu.db"
    cors_origins: str = ""
    log_level: str = "INFO"
    app_version: str = "0.1.0"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    document_upload_dir: str = ".document_uploads"
    document_max_upload_bytes: int = 10 * 1024 * 1024
    document_min_extracted_characters: int = 100
    openai_timeout_seconds: float = 30.0

    @property
    def allowed_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if origins:
            return origins
        if self.app_env == "development":
            return ["http://localhost:5173"]
        return []

    @model_validator(mode="after")
    def reject_permissive_production_cors(self) -> Settings:
        if self.app_env != "development" and "*" in self.allowed_origins:
            raise ValueError("CORS_ORIGINS cannot contain '*' outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
