from __future__ import annotations

from datetime import timedelta

from app.auth.security import create_token, decode_token
from app.core.config import settings


def create_document_access_token(document_id: int, user_id: int) -> str:
    return create_token(
        subject=str(user_id),
        token_type="document",
        expires_delta=timedelta(minutes=settings.document_signed_url_minutes),
        extra_claims={"document_id": document_id},
    )


def validate_document_access_token(token: str, document_id: int) -> int:
    payload = decode_token(token)
    if payload.get("type") != "document" or payload.get("document_id") != document_id:
        raise ValueError("Invalid document token")
    return int(payload["sub"])
