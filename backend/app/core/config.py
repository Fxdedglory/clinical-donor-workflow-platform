import json
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Clinical Donor Screening & Quality Workflow Platform"
    app_version: str = "0.1.0"
    app_env: str = Field(default="dev", alias="APP_ENV")
    secret_key: str = Field(default="change-me-for-production-demo-only", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(default=20160, alias="REFRESH_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = "HS256"
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")
    session_timeout_minutes: int = Field(default=30, alias="SESSION_TIMEOUT_MINUTES")
    max_failed_login_attempts: int = Field(default=5, alias="MAX_FAILED_LOGIN_ATTEMPTS")
    account_lockout_minutes: int = Field(default=15, alias="ACCOUNT_LOCKOUT_MINUTES")
    password_min_length: int = Field(default=12, alias="PASSWORD_MIN_LENGTH")
    password_expiration_days: int = Field(default=180, alias="PASSWORD_EXPIRATION_DAYS")
    encryption_key: str | None = Field(default=None, alias="ENCRYPTION_KEY")
    mfa_dev_bypass_code: str = Field(default="000000", alias="MFA_DEV_BYPASS_CODE")
    document_signed_url_minutes: int = Field(default=10, alias="DOCUMENT_SIGNED_URL_MINUTES")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    email_provider: str = Field(default="console", alias="EMAIL_PROVIDER")
    email_from: str = Field(default="no-reply@teemails.com", alias="EMAIL_FROM")
    email_from_name: str = Field(default="Clinical Donor Workflow", alias="EMAIL_FROM_NAME")
    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")
    ses_region: str | None = Field(default=None, alias="SES_REGION")
    mailgun_api_key: str | None = Field(default=None, alias="MAILGUN_API_KEY")
    mailgun_domain: str | None = Field(default=None, alias="MAILGUN_DOMAIN")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    backup_encryption_key: str | None = Field(default=None, alias="BACKUP_ENCRYPTION_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://clinical_admin@localhost:5432/clinical_donor_workflow",
        alias="DATABASE_URL",
    )
    port: int = Field(default=8000, alias="PORT")
    startup_mode: str = Field(default="fastapi_react", alias="STARTUP_MODE")
    serve_frontend: bool = Field(default=True, alias="SERVE_FRONTEND")
    frontend_dist_dir: str = Field(default="frontend/dist", alias="FRONTEND_DIST_DIR")
    data_producer_metadata_root: str = Field(default="data/generated", alias="DATA_PRODUCER_METADATA_ROOT")
    data_producer_export_root: str = Field(default="data/exports", alias="DATA_PRODUCER_EXPORT_ROOT")
    data_producer_stop_file: str = Field(default="data/generated/STOP_CONTINUOUS", alias="DATA_PRODUCER_STOP_FILE")
    data_producer_min_interval_seconds: int = Field(default=1, alias="DATA_PRODUCER_MIN_INTERVAL_SECONDS")
    data_producer_max_cycles: int = Field(default=1000, alias="DATA_PRODUCER_MAX_CYCLES")
    data_producer_allow_infinite: bool = Field(default=False, alias="DATA_PRODUCER_ALLOW_INFINITE")
    enable_data_producer_api: bool = Field(default=True, alias="ENABLE_DATA_PRODUCER_API")
    scheduled_generation_enabled: bool = Field(default=False, alias="DATA_PRODUCER_SCHEDULED_GENERATION_ENABLED")
    scheduled_generation_interval_seconds: int = Field(default=3600, alias="DATA_PRODUCER_SCHEDULED_GENERATION_INTERVAL_SECONDS")
    scheduled_generation_run_on_startup: bool = Field(default=False, alias="DATA_PRODUCER_SCHEDULED_GENERATION_RUN_ON_STARTUP")
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://teemails.com",
        "https://www.teemails.com",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

