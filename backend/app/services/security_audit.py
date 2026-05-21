from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import SecurityAudit, UserSessionRecord
from app.services.encryption import mask_sensitive_payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_id() -> str:
    return f"sess_{uuid4().hex}"


def request_ip(request: Request | None) -> str | None:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def request_device(request: Request | None) -> str | None:
    if not request:
        return None
    user_agent = request.headers.get("user-agent", "")
    return user_agent[:180] if user_agent else None


def log_security_event(
    db: Session,
    *,
    event_type: str,
    user_id: int | None = None,
    request: Request | None = None,
    route: str | None = None,
    success: bool = True,
    details: dict | None = None,
) -> SecurityAudit:
    entry = SecurityAudit(
        user_id=user_id,
        event_type=event_type,
        ip_address=request_ip(request),
        device=request_device(request),
        route=route or (str(request.url.path) if request else None),
        success=success,
        details=mask_sensitive_payload(details or {}),
    )
    db.add(entry)
    return entry


def revoke_session(db: Session, session: UserSessionRecord | None) -> None:
    if not session or not session.is_active:
        return
    session.is_active = False
    session.revoked_at = datetime.now(UTC)


def touch_session(session: UserSessionRecord) -> None:
    session.last_seen_at = datetime.now(UTC)
