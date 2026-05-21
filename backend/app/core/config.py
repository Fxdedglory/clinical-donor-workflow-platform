from functools import lru_cache

from pydantic import Field
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
    app_base_url: str = Field(default="http://localhost:8501", alias="APP_BASE_URL")
    email_provider: str = Field(default="console", alias="EMAIL_PROVIDER")
    email_from: str = Field(default="no-reply@teemails.com", alias="EMAIL_FROM")
    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")
    ses_region: str | None = Field(default=None, alias="SES_REGION")
    mailgun_api_key: str | None = Field(default=None, alias="MAILGUN_API_KEY")
    mailgun_domain: str | None = Field(default=None, alias="MAILGUN_DOMAIN")
    backup_encryption_key: str | None = Field(default=None, alias="BACKUP_ENCRYPTION_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://clinical_admin:clinical_demo_password@localhost:5432/clinical_donor_workflow",
        alias="DATABASE_URL",
    )
    cors_origins: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "https://teemails.com",
        "https://www.teemails.com",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

