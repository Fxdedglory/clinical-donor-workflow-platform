from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(
    *,
    subject: str,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
    role: str | None = None,
    permissions: list[str] | None = None,
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expires_at,
    }
    if role:
        payload["role"] = role
    if permissions is not None:
        payload["permissions"] = permissions
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str, permissions: list[str]) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        role=role,
        permissions=permissions,
    )


def create_refresh_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes),
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

