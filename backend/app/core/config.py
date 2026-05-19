from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Clinical Donor Screening & Quality Workflow Platform"
    app_version: str = "0.1.0"
    database_url: str = Field(
        default="postgresql+psycopg://clinical_admin:clinical_demo_password@localhost:5432/clinical_donor_workflow",
        alias="DATABASE_URL",
    )
    cors_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

