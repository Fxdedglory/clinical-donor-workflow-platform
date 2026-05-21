from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def password_needs_rehash(hashed_password: str | None) -> bool:
    if not hashed_password:
        return True
    return pwd_context.needs_update(hashed_password)


def validate_password_policy(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
) -> list[str]:
    issues: list[str] = []
    if len(password) < settings.password_min_length:
        issues.append(f"Password must be at least {settings.password_min_length} characters.")
    if not any(char.islower() for char in password):
        issues.append("Password must include a lowercase letter.")
    if not any(char.isupper() for char in password):
        issues.append("Password must include an uppercase letter.")
    if not any(char.isdigit() for char in password):
        issues.append("Password must include a number.")
    if not any(not char.isalnum() for char in password):
        issues.append("Password must include a symbol.")
    lowered = password.lower()
    if username and username.lower() in lowered:
        issues.append("Password cannot contain the username.")
    if email:
        local_part = email.split("@", 1)[0].lower()
        if local_part and local_part in lowered:
            issues.append("Password cannot contain the email name.")
    return issues


def create_token(
    *,
    subject: str,
    token_type: Literal["access", "refresh", "mfa", "password_reset", "document"],
    expires_delta: timedelta,
    role: str | None = None,
    permissions: list[str] | None = None,
    session_id: str | None = None,
    extra_claims: dict | None = None,
) -> str:
    expires_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    if session_id:
        payload["sid"] = session_id
    if role:
        payload["role"] = role
    if permissions is not None:
        payload["permissions"] = permissions
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str, role: str, permissions: list[str], session_id: str | None = None
) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        role=role,
        permissions=permissions,
        session_id=session_id,
    )


def create_refresh_token(subject: str, session_id: str | None = None) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes),
        session_id=session_id,
    )


def create_mfa_challenge_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type="mfa",
        expires_delta=timedelta(minutes=10),
    )


def create_password_reset_token(subject: str, reset_id: int) -> str:
    return create_token(
        subject=subject,
        token_type="password_reset",
        expires_delta=timedelta(minutes=30),
        extra_claims={"reset_id": reset_id},
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
