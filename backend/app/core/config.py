from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FinRisk Intelligence"
    app_env: str = "demo"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./finrisk.db"
    redis_url: str = "redis://localhost:6379/0"
    model_cache_dir: str = "/tmp/model-cache"
    backend_cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://frontend:3000"])

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins(self) -> List[str]:
        raw = os.getenv("BACKEND_CORS_ORIGINS", "")
        if raw:
            return [item.strip() for item in raw.split(",") if item.strip()]
        return self.backend_cors_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
