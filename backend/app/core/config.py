import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Database
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "self_healing_platform"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:root@127.0.0.1:5432/self_healing_platform"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    SECRET_KEY: str = "dev-secret-key-change-in-production-pipeline-32bytes-min"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    SAMPLES_DIR: Path = DATA_DIR / "samples"
    QUARANTINE_DIR: Path = DATA_DIR / "quarantine"
    DBT_PROJECT_DIR: Path = BASE_DIR / "dbt_project"

    # Alerting
    ALERT_WEBHOOK_URL: str = "http://localhost:8000/api/v1/health"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
