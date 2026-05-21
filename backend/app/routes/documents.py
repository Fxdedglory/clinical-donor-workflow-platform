from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.config import settings
from app.database import get_db
from app.models import DocumentAccess, SecureDocument, User
from app.services.document_security import (
    create_document_access_token,
    validate_document_access_token,
)
from app.services.security_audit import log_security_event, request_ip

router = APIRouter(prefix="/api/documents", tags=["Secure Documents"])


def _document_payload(document: SecureDocument) -> dict:
    return {
        "document_id": document.document_id,
        "record_type": document.record_type,
        "record_id": document.record_id,
        "document_name": document.document_name,
        "document_type": document.document_type,
        "access_classification": document.access_classification,
        "created_at": document.created_at,
    }


@router.get("/record/{record_type}/{record_id}")
def list_record_documents(
    record_type: str,
    record_id: str,
    request: Request,
    current_user: User = Depends(require_permission("documents.read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    documents = db.execute(
        select(SecureDocument)
        .where(
            SecureDocument.record_type == record_type,
            SecureDocument.record_id == record_id,
            SecureDocument.is_active.is_(True),
        )
        .order_by(SecureDocument.created_at.desc())
    ).scalars()
    log_security_event(
        db,
        event_type="DOCUMENT_LIST",
        user_id=current_user.user_id,
        request=request,
        details={"record_type": record_type, "record_id": record_id},
    )
    db.commit()
    return [_document_payload(document) for document in documents]


@router.post("/{document_id}/signed-url")
def create_signed_document_url(
    document_id: int,
    request: Request,
    current_user: User = Depends(require_permission("documents.read")),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    document = db.get(SecureDocument, document_id)
    if not document or not document.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    token = create_document_access_token(document.document_id, current_user.user_id)
    db.add(
        DocumentAccess(
            document_id=document.document_id,
            user_id=current_user.user_id,
            action_type="SIGNED_URL_CREATED",
            ip_address=request_ip(request),
            route=str(request.url.path),
            details={"document_name": document.document_name},
        )
    )
    log_security_event(
        db,
        event_type="DOCUMENT_SIGNED_URL",
        user_id=current_user.user_id,
        request=request,
        details={"document_id": document.document_id},
    )
    db.commit()
    return {
        "url": f"/api/documents/{document.document_id}/download?token={token}",
        "expires_in_minutes": settings.document_signed_url_minutes,
    }


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    token: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    document = db.get(SecureDocument, document_id)
    if not document or not document.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        user_id = validate_document_access_token(token, document_id)
    except ValueError as exc:
        db.add(
            DocumentAccess(
                document_id=document_id,
                user_id=None,
                action_type="DOWNLOAD_DENIED",
                ip_address=request_ip(request),
                route=str(request.url.path),
                success=False,
                details={"reason": "invalid_token"},
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid document token") from exc
    db.add(
        DocumentAccess(
            document_id=document.document_id,
            user_id=user_id,
            action_type="DOWNLOAD",
            ip_address=request_ip(request),
            route=str(request.url.path),
            details={"document_name": document.document_name},
        )
    )
    log_security_event(
        db,
        event_type="DOCUMENT_DOWNLOAD",
        user_id=user_id,
        request=request,
        details={"document_id": document.document_id, "document_type": document.document_type},
    )
    db.commit()
    return {
        "document_id": document.document_id,
        "document_name": document.document_name,
        "status": "secure_download_authorized",
        "message": "Document bytes are stored in protected encrypted storage in production deployments.",
    }

