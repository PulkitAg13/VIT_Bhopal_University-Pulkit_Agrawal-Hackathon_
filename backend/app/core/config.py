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
    database_url: str = "postgresql+psycopg2://finrisk:finriskpass@localhost:5432/finrisk"
    redis_url: str = "redis://localhost:6379/0"
    model_cache_dir: str = "/tmp/model-cache"
    hf_home: str = Field(default="/tmp/hf-home", alias="HF_HOME")
    backend_cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://frontend:80",
        ]
    )
    # Model loading
    load_finbert: bool = True
    load_embeddings: bool = True
    # Stress testing
    stress_trigger_threshold: float = 7.0

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
