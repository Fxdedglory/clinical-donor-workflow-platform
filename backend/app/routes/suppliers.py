from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_permission, require_permission
from app.auth.security import (
    create_invitation_token,
    decode_token,
    get_password_hash,
    validate_password_policy,
    verify_password,
)
from app.core.config import settings
from app.database import get_db
from app.models import (
    AuthIdentity,
    BackgroundJob,
    DocumentAccess,
    DocumentVersion,
    ExternalInvitation,
    MFAConfiguration,
    Notification,
    Organization,
    RealtimeEvent,
    Role,
    SecureDocument,
    SidebarState,
    SignatureEvent,
    SupplierRelationship,
    User,
    UserPreference,
    WorkflowTask,
)
from app.services.audit import log_audit
from app.services.email import EmailMessage, EmailType, send_email
from app.services.encryption import encrypt_text
from app.services.security_audit import hash_token, log_security_event, request_ip
from app.services.tenant_access import (
    apply_org_scope,
    ensure_org_access,
    is_external_user,
    require_organization,
)

router = APIRouter(prefix="/api/suppliers", tags=["Supplier Portal"])


class SupplierOrganizationCreate(BaseModel):
    organization_name: str
    organization_type: str = "Supplier"
    contact_email: str
    risk_tier: str = "Medium"
    approval_status: str = "Pending Approval"


class SupplierInvitationCreate(BaseModel):
    organization_id: int
    email: str
    role_name: str = "Supplier External User"


class SupplierInvitationAccept(BaseModel):
    token: str
    username: str
    full_name: str
    password: str


class SupplierApprovalUpdate(BaseModel):
    approval_status: str = "Approved"
    relationship_status: str = "Approved"


class SupplierDocumentUpload(BaseModel):
    record_type: str
    record_id: str
    document_name: str
    document_type: str
    storage_reference: str = "supplier-portal-upload-placeholder"
    checksum_sha256: str | None = None


class SupplierDocumentReview(BaseModel):
    approval_status: str
    review_note: str = ""


class SupplierTaskAction(BaseModel):
    status: str = "Completed"
    response_note: str = ""


class SignatureRequest(BaseModel):
    record_type: str
    record_id: str
    signature_type: str = "Supplier Approval"
    reason: str
    meaning: str = "I certify this supplier response is complete and attributable to my authenticated identity."
    password: str
    prior_state: str | None = None
    new_state: str | None = None


def _org_payload(org: Organization) -> dict:
    return {
        "organization_id": org.organization_id,
        "organization_name": org.organization_name,
        "organization_type": org.organization_type,
        "approval_status": org.approval_status,
        "contact_email": org.contact_email,
        "mfa_required": org.mfa_required,
        "is_active": org.is_active,
        "created_at": org.created_at,
    }


def _invitation_payload(invitation: ExternalInvitation) -> dict:
    return {
        "invitation_id": invitation.invitation_id,
        "organization_id": invitation.organization_id,
        "email": invitation.email,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "created_user_id": invitation.created_user_id,
        "created_at": invitation.created_at,
    }


def _task_payload(task: WorkflowTask) -> dict:
    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "workflow_state": task.workflow_state,
        "queue_name": task.queue_name,
        "due_date": task.due_date,
        "related_record_type": task.related_record_type,
        "related_record_id": task.related_record_id,
        "organization_id": task.organization_id,
    }


def _latest_document_version(db: Session, document_id: int) -> DocumentVersion | None:
    return db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(desc(DocumentVersion.version_number))
        .limit(1)
    ).scalar_one_or_none()


def _document_payload(document: SecureDocument, db: Session) -> dict:
    org = db.get(Organization, document.organization_id) if document.organization_id else None
    uploader = db.get(User, document.uploaded_by) if document.uploaded_by else None
    version = _latest_document_version(db, document.document_id)
    metadata = version.extra_metadata if version and isinstance(version.extra_metadata, dict) else {}
    return {
        "document_id": document.document_id,
        "organization_id": document.organization_id,
        "organization_name": org.organization_name if org else "",
        "record_type": document.record_type,
        "record_id": document.record_id,
        "document_name": document.document_name,
        "document_type": document.document_type,
        "access_classification": document.access_classification,
        "approval_status": version.approval_status if version else document.access_classification,
        "document_status": version.document_status if version else "",
        "version_number": version.version_number if version else None,
        "uploaded_by": uploader.username if uploader else "",
        "approved_by": version.approved_by if version else None,
        "approved_at": version.approved_at if version else None,
        "review_note": metadata.get("review_note", ""),
        "created_at": document.created_at,
    }


def _find_invitation(db: Session, token: str) -> ExternalInvitation:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid invitation") from exc
    if payload.get("type") != "invitation":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid invitation")
    invitation = db.get(ExternalInvitation, payload.get("invitation_id"))
    if not invitation or invitation.token_hash != hash_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid invitation")
    if invitation.expires_at <= datetime.now(UTC) or invitation.status not in {"Pending Acceptance", "Sent"}:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation is no longer active")
    return invitation


@router.get("/organizations")
def list_supplier_organizations(
    current_user: User = Depends(require_permission("suppliers.read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(Organization).where(Organization.organization_type.in_(["Supplier", "supplier", "Partner", "partner"]))
    query = apply_org_scope(query, Organization, current_user)
    return [_org_payload(org) for org in db.execute(query.order_by(Organization.organization_name)).scalars().all()]


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
def create_supplier_organization(
    payload: SupplierOrganizationCreate,
    current_user: User = Depends(require_permission("suppliers.manage")),
    db: Session = Depends(get_db),
) -> dict:
    existing = db.execute(
        select(Organization).where(Organization.organization_name == payload.organization_name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization already exists")
    org = Organization(
        organization_name=payload.organization_name,
        organization_type=payload.organization_type,
        approval_status=payload.approval_status,
        contact_email=str(payload.contact_email),
        mfa_required=True,
    )
    db.add(org)
    db.flush()
    internal_org_id = current_user.organization_id or 1
    db.add(
        SupplierRelationship(
            internal_organization_id=internal_org_id,
            external_organization_id=org.organization_id,
            status=payload.approval_status,
            risk_tier=payload.risk_tier,
            onboarding_status="Organization Created",
            approved_by=current_user.user_id if payload.approval_status == "Approved" else None,
            approved_at=datetime.now(UTC) if payload.approval_status == "Approved" else None,
        )
    )
    log_security_event(
        db,
        event_type="SUPPLIER_ORGANIZATION_CREATED",
        user_id=current_user.user_id,
        details={"organization_id": org.organization_id, "organization_name": org.organization_name},
    )
    db.commit()
    db.refresh(org)
    return _org_payload(org)


@router.post("/invitations", status_code=status.HTTP_201_CREATED)
def create_supplier_invitation(
    payload: SupplierInvitationCreate,
    request: Request,
    current_user: User = Depends(require_permission("suppliers.manage")),
    db: Session = Depends(get_db),
) -> dict:
    org = db.get(Organization, payload.organization_id)
    if not org or not org.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    role = db.execute(select(Role).where(Role.role_name == payload.role_name)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier role not found")
    invitation = ExternalInvitation(
        organization_id=org.organization_id,
        email=str(payload.email),
        invited_by=current_user.user_id,
        role_id=role.role_id,
        token_hash=f"pending_{uuid4().hex}",
        status="Pending Acceptance",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        extra_metadata={"organization_name": org.organization_name},
    )
    db.add(invitation)
    db.flush()
    token = create_invitation_token(str(payload.email), invitation.invitation_id)
    invitation.token_hash = hash_token(token)
    invitation_url = f"{settings.app_base_url.rstrip('/')}/?supplier_invite={token}"
    send_email(
        db,
        EmailMessage(
            to_email=str(payload.email),
            subject="Supplier portal invitation",
            body=(
                f"You have been invited to collaborate with Clinical Donor Workflow Platform for "
                f"{org.organization_name}. Use this single-use onboarding link within 7 days: {invitation_url}"
            ),
            email_type=EmailType.SUPPLIER_INVITE,
            metadata={"invitation_id": invitation.invitation_id, "organization_id": org.organization_id},
        ),
        user_id=current_user.user_id,
        request=request,
    )
    db.add(
        BackgroundJob(
            job_type="Supplier Invitation Delivery",
            status="Queued",
            payload={"invitation_id": invitation.invitation_id, "email": invitation.email},
            organization_id=org.organization_id,
        )
    )
    log_security_event(
        db,
        event_type="SUPPLIER_INVITATION_CREATED",
        user_id=current_user.user_id,
        request=request,
        details={"invitation_id": invitation.invitation_id, "organization_id": org.organization_id},
    )
    db.commit()
    response = _invitation_payload(invitation)
    if settings.app_env != "prod":
        response["demo_invitation_url"] = invitation_url
    return response


@router.get("/invitations")
def list_supplier_invitations(
    current_user: User = Depends(require_permission("suppliers.manage")),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(ExternalInvitation).order_by(desc(ExternalInvitation.created_at)).limit(200)
    rows = db.execute(query).scalars().all()
    payloads = []
    for invitation in rows:
        org = db.get(Organization, invitation.organization_id)
        created_user = db.get(User, invitation.created_user_id) if invitation.created_user_id else None
        payloads.append(
            _invitation_payload(invitation)
            | {
                "organization_name": org.organization_name if org else "",
                "created_user": created_user.username if created_user else "",
            }
        )
    return payloads


@router.get("/invitations/preview")
def preview_supplier_invitation(token: str, db: Session = Depends(get_db)) -> dict:
    invitation = _find_invitation(db, token)
    org = db.get(Organization, invitation.organization_id)
    return {
        "email": invitation.email,
        "organization": _org_payload(org) if org else None,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
    }


@router.post("/invitations/accept")
def accept_supplier_invitation(
    payload: SupplierInvitationAccept,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    invitation = _find_invitation(db, payload.token)
    role = db.get(Role, invitation.role_id) if invitation.role_id else None
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier role not found")
    existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    issues = validate_password_policy(payload.password, username=payload.username, email=invitation.email)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=issues)
    user = User(
        username=payload.username,
        full_name=payload.full_name,
        display_name=payload.full_name,
        email=invitation.email,
        hashed_password=get_password_hash(payload.password),
        role_id=role.role_id,
        role=role.role_name,
        department="Supplier Portal",
        is_active=True,
        account_type="supplier",
        user_type="supplier",
        organization_id=invitation.organization_id,
        is_internal=False,
        is_external=True,
        external_user_flag=True,
        approval_status="Pending Approval",
        identity_provider="Platform Native",
        mfa_enabled=True,
    )
    db.add(user)
    db.flush()
    db.add(
        AuthIdentity(
            user_id=user.user_id,
            identity_provider="Platform Native",
            provider_subject=user.username,
            user_type=user.user_type,
            mfa_required=True,
            external_user_flag=True,
        )
    )
    db.add(
        MFAConfiguration(
            user_id=user.user_id,
            method="TOTP",
            is_enabled=True,
            required_by_policy=True,
            secret_encrypted=encrypt_text(f"demo-totp-secret-{user.username}"),
            recovery_codes_encrypted=encrypt_text("demo-recovery-code"),
            verified_at=datetime.now(UTC),
        )
    )
    db.add(SidebarState(user_id=user.user_id, sidebar_collapsed=False))
    db.add(
        UserPreference(
            user_id=user.user_id,
            preference_key="notification_preferences",
            preference_value={"supplier_notifications": True, "document_requests": True, "approval_requests": True},
        )
    )
    invitation.status = "Pending Approval"
    invitation.accepted_at = datetime.now(UTC)
    invitation.created_user_id = user.user_id
    relationship = db.execute(
        select(SupplierRelationship).where(
            SupplierRelationship.external_organization_id == invitation.organization_id
        )
    ).scalar_one_or_none()
    if relationship:
        relationship.primary_contact_user_id = user.user_id
        relationship.onboarding_status = "Pending Approval"
    db.add(
        RealtimeEvent(
            event_type="Supplier Invitation Accepted",
            channel="supplier-onboarding",
            organization_id=invitation.organization_id,
            audience_user_id=invitation.invited_by,
            record_type="ExternalInvitation",
            record_id=str(invitation.invitation_id),
            payload={"email": invitation.email, "username": user.username},
        )
    )
    log_security_event(
        db,
        event_type="SUPPLIER_INVITATION_ACCEPTED",
        user_id=user.user_id,
        request=request,
        details={"organization_id": invitation.organization_id, "invitation_id": invitation.invitation_id},
    )
    db.commit()
    return {"status": "pending_approval"}


@router.post("/invitations/{invitation_id}/approve")
def approve_supplier_invitation(
    invitation_id: int,
    payload: SupplierApprovalUpdate,
    request: Request,
    current_user: User = Depends(require_permission("suppliers.manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    invitation = db.get(ExternalInvitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    user = db.get(User, invitation.created_user_id) if invitation.created_user_id else None
    org = db.get(Organization, invitation.organization_id)
    if not user or not org:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invitation has not been accepted")
    invitation.status = payload.approval_status
    invitation.approved_by = current_user.user_id
    invitation.approved_at = datetime.now(UTC)
    user.approval_status = payload.approval_status
    user.is_active = payload.approval_status == "Approved"
    org.approval_status = payload.approval_status
    relationship = db.execute(
        select(SupplierRelationship).where(SupplierRelationship.external_organization_id == org.organization_id)
    ).scalar_one_or_none()
    if relationship:
        relationship.status = payload.relationship_status
        relationship.onboarding_status = "Approved" if payload.approval_status == "Approved" else payload.approval_status
        relationship.approved_by = current_user.user_id
        relationship.approved_at = datetime.now(UTC)
    log_security_event(
        db,
        event_type="SUPPLIER_INVITATION_APPROVED",
        user_id=current_user.user_id,
        request=request,
        details={"invitation_id": invitation.invitation_id, "target_user_id": user.user_id},
    )
    db.commit()
    return {"status": invitation.status}


@router.get("/dashboard")
def supplier_dashboard(
    current_user: User = Depends(require_permission("supplier.portal")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = require_organization(current_user)
    org = db.get(Organization, org_id)
    relationship = db.execute(
        select(SupplierRelationship).where(SupplierRelationship.external_organization_id == org_id)
    ).scalar_one_or_none()
    tasks = db.execute(
        select(WorkflowTask)
        .where(
            WorkflowTask.organization_id == org_id,
            WorkflowTask.status.in_(["Pending", "Assigned", "In Progress", "Blocked", "Escalated"]),
        )
        .order_by(desc(WorkflowTask.created_at))
        .limit(100)
    ).scalars().all()
    documents = db.execute(
        select(SecureDocument)
        .where(SecureDocument.organization_id == org_id, SecureDocument.is_active.is_(True))
        .order_by(desc(SecureDocument.created_at))
        .limit(50)
    ).scalars().all()
    notifications = db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.user_id)
        .order_by(desc(Notification.created_at))
        .limit(25)
    ).scalars().all()
    events = db.execute(
        select(RealtimeEvent)
        .where(RealtimeEvent.organization_id == org_id)
        .order_by(desc(RealtimeEvent.created_at))
        .limit(25)
    ).scalars().all()
    return {
        "organization": _org_payload(org) if org else None,
        "relationship": {
            "relationship_id": relationship.relationship_id,
            "status": relationship.status,
            "onboarding_status": relationship.onboarding_status,
            "risk_tier": relationship.risk_tier,
        }
        if relationship
        else None,
        "kpis": {
            "open_tasks": len(tasks),
            "pending_documents": sum(1 for doc in documents if doc.access_classification != "Approved"),
            "unread_notifications": sum(1 for item in notifications if not item.is_read),
            "overdue_tasks": sum(1 for task in tasks if task.due_date and task.due_date < datetime.now(UTC)),
        },
        "tasks": [_task_payload(task) for task in tasks],
        "documents": [
            _document_payload(doc, db)
            for doc in documents
        ],
        "notifications": [
            {
                "notification_id": item.notification_id,
                "title": item.title,
                "message": item.message,
                "priority": item.priority,
                "is_read": item.is_read,
                "created_at": item.created_at,
            }
            for item in notifications
        ],
        "activity": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "record_type": event.record_type,
                "record_id": event.record_id,
                "created_at": event.created_at,
                "payload": event.payload,
            }
            for event in events
        ],
    }


@router.post("/documents", status_code=status.HTTP_201_CREATED)
def upload_supplier_document(
    payload: SupplierDocumentUpload,
    request: Request,
    current_user: User = Depends(require_permission("documents.manage")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = require_organization(current_user) if is_external_user(current_user) else current_user.organization_id
    document = SecureDocument(
        record_type=payload.record_type,
        record_id=payload.record_id,
        document_name=payload.document_name,
        document_type=payload.document_type,
        storage_uri_encrypted=encrypt_text(payload.storage_reference) or "",
        checksum_sha256=payload.checksum_sha256,
        uploaded_by=current_user.user_id,
        access_classification="Supplier Submitted",
        organization_id=org_id,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=document.document_id,
            version_number=1,
            document_status="Submitted",
            uploaded_by=current_user.user_id,
            storage_uri_encrypted=document.storage_uri_encrypted,
            checksum_sha256=document.checksum_sha256,
            approval_status="Pending Review",
            extra_metadata={"source": "supplier_portal"},
        )
    )
    db.add(
        DocumentAccess(
            document_id=document.document_id,
            user_id=current_user.user_id,
            action_type="SUPPLIER_UPLOAD",
            ip_address=request_ip(request),
            route=str(request.url.path),
            details={"document_name": document.document_name},
        )
    )
    db.add(
        RealtimeEvent(
            event_type="Supplier Document Uploaded",
            channel="supplier-documents",
            audience_user_id=current_user.user_id,
            organization_id=org_id,
            record_type=payload.record_type,
            record_id=payload.record_id,
            payload={"document_id": document.document_id, "document_name": document.document_name},
        )
    )
    db.commit()
    db.refresh(document)
    return {"document_id": document.document_id, "status": "submitted"}


@router.get("/documents")
def list_supplier_documents(
    current_user: User = Depends(require_any_permission(["suppliers.read", "documents.manage"])),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = (
        select(SecureDocument)
        .where(SecureDocument.is_active.is_(True), SecureDocument.organization_id.is_not(None))
        .order_by(desc(SecureDocument.created_at))
        .limit(250)
    )
    query = apply_org_scope(query, SecureDocument, current_user)
    return [_document_payload(document, db) for document in db.execute(query).scalars().all()]


@router.get("/documents/{document_id}/versions")
def list_supplier_document_versions(
    document_id: int,
    request: Request,
    current_user: User = Depends(require_permission("documents.read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    document = db.get(SecureDocument, document_id)
    if not document or not document.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    ensure_org_access(current_user, document, not_found_detail="Document not found")
    db.add(
        DocumentAccess(
            document_id=document.document_id,
            user_id=current_user.user_id,
            action_type="VERSION_HISTORY_VIEWED",
            ip_address=request_ip(request),
            route=str(request.url.path),
            details={"document_name": document.document_name},
        )
    )
    log_security_event(
        db,
        event_type="SUPPLIER_DOCUMENT_VERSION_VIEW",
        user_id=current_user.user_id,
        request=request,
        details={"document_id": document.document_id},
    )
    rows = db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(desc(DocumentVersion.version_number))
    ).scalars().all()
    db.commit()
    return [
        {
            "version_id": version.version_id,
            "document_id": version.document_id,
            "version_number": version.version_number,
            "document_status": version.document_status,
            "approval_status": version.approval_status,
            "approved_by": version.approved_by,
            "approved_at": version.approved_at,
            "created_at": version.created_at,
            "review_note": (version.extra_metadata or {}).get("review_note", ""),
        }
        for version in rows
    ]


@router.post("/documents/{document_id}/review")
def review_supplier_document(
    document_id: int,
    payload: SupplierDocumentReview,
    request: Request,
    current_user: User = Depends(require_any_permission(["suppliers.manage", "documents.manage"])),
    db: Session = Depends(get_db),
) -> dict:
    if is_external_user(current_user):
        log_security_event(
            db,
            event_type="SUPPLIER_DOCUMENT_REVIEW_DENIED",
            user_id=current_user.user_id,
            request=request,
            success=False,
            details={"document_id": document_id},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal reviewer required")
    allowed_statuses = {"Approved", "Rejected", "Needs Rework", "Hold"}
    if payload.approval_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Approval status must be one of: {', '.join(sorted(allowed_statuses))}",
        )
    document = db.get(SecureDocument, document_id)
    if not document or not document.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    ensure_org_access(current_user, document, not_found_detail="Document not found")

    version = _latest_document_version(db, document.document_id)
    old_value = {
        "access_classification": document.access_classification,
        "approval_status": version.approval_status if version else None,
        "document_status": version.document_status if version else None,
    }
    document.access_classification = payload.approval_status
    if version:
        metadata = dict(version.extra_metadata or {})
        metadata["review_note"] = payload.review_note
        metadata["reviewed_by"] = current_user.username
        version.document_status = payload.approval_status
        version.approval_status = payload.approval_status
        version.approved_by = current_user.user_id
        version.approved_at = datetime.now(UTC)
        version.extra_metadata = metadata

    db.add(
        DocumentAccess(
            document_id=document.document_id,
            user_id=current_user.user_id,
            action_type=f"DOCUMENT_{payload.approval_status.upper().replace(' ', '_')}",
            ip_address=request_ip(request),
            route=str(request.url.path),
            details={
                "document_name": document.document_name,
                "approval_status": payload.approval_status,
                "review_note": payload.review_note,
            },
        )
    )
    supplier_users = db.execute(
        select(User).where(
            User.organization_id == document.organization_id,
            User.is_external.is_(True),
            User.is_active.is_(True),
        )
    ).scalars().all()
    notify_user_ids = {user.user_id for user in supplier_users}
    if document.uploaded_by:
        notify_user_ids.add(document.uploaded_by)
    priority = "High" if payload.approval_status in {"Rejected", "Needs Rework", "Hold"} else "Normal"
    for user_id in notify_user_ids:
        db.add(
            Notification(
                user_id=user_id,
                title=f"[Document {payload.approval_status}] {document.document_name}",
                message=payload.review_note or f"{document.document_name} was reviewed by the operations team.",
                notification_type="Supplier Document Review",
                priority=priority,
                related_record_type="SecureDocument",
                related_record_id=str(document.document_id),
                action_route="/supplier",
                workflow_context={
                    "document_id": document.document_id,
                    "record_type": document.record_type,
                    "record_id": document.record_id,
                    "route_path": "/supplier",
                    "approval_status": payload.approval_status,
                },
                organization_id=document.organization_id,
            )
        )
    db.add(
        RealtimeEvent(
            event_type="Supplier Document Reviewed",
            channel="supplier-documents",
            audience_user_id=document.uploaded_by,
            organization_id=document.organization_id,
            record_type="SecureDocument",
            record_id=str(document.document_id),
            payload={
                "approval_status": payload.approval_status,
                "document_name": document.document_name,
                "review_note": payload.review_note,
            },
        )
    )
    db.add(
        BackgroundJob(
            job_type="Supplier Document Review Notification",
            status="Queued",
            priority=priority,
            organization_id=document.organization_id,
            payload={"document_id": document.document_id, "approval_status": payload.approval_status},
        )
    )
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="SUPPLIER_DOCUMENT_REVIEWED",
        table_name="dim_secure_document",
        record_id=str(document.document_id),
        old_value=old_value,
        new_value={
            "access_classification": document.access_classification,
            "approval_status": payload.approval_status,
            "review_note": payload.review_note,
        },
        entity_type="SecureDocument",
        entity_id=str(document.document_id),
        ip_address=request_ip(request),
    )
    log_security_event(
        db,
        event_type="SUPPLIER_DOCUMENT_REVIEWED",
        user_id=current_user.user_id,
        request=request,
        details={"document_id": document.document_id, "approval_status": payload.approval_status},
    )
    db.commit()
    db.refresh(document)
    return _document_payload(document, db)


@router.post("/tasks/{task_id}/respond")
def respond_to_supplier_task(
    task_id: int,
    payload: SupplierTaskAction,
    current_user: User = Depends(require_permission("tasks.update")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    task = db.get(WorkflowTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    ensure_org_access(current_user, task, not_found_detail="Task not found")
    task.status = payload.status
    task.completed_at = datetime.now(UTC) if payload.status == "Completed" else task.completed_at
    db.add(
        RealtimeEvent(
            event_type="Supplier Task Response",
            channel="supplier-tasks",
            audience_user_id=current_user.user_id,
            organization_id=task.organization_id,
            record_type="WorkflowTask",
            record_id=str(task.task_id),
            payload={"status": payload.status, "response_note": payload.response_note},
        )
    )
    db.commit()
    return {"status": "task_updated"}


@router.post("/signatures", status_code=status.HTTP_201_CREATED)
def create_supplier_signature(
    payload: SignatureRequest,
    request: Request,
    current_user: User = Depends(require_permission("signatures.sign")),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.password, current_user.hashed_password):
        log_security_event(
            db,
            event_type="SIGNATURE_REAUTH_FAILED",
            user_id=current_user.user_id,
            request=request,
            success=False,
            details={"record_type": payload.record_type, "record_id": payload.record_id},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Re-authentication failed")
    org_id = require_organization(current_user) if is_external_user(current_user) else current_user.organization_id
    signed_at = datetime.now(UTC)
    signature_hash = sha256(
        f"{current_user.user_id}|{org_id}|{payload.record_type}|{payload.record_id}|{signed_at.isoformat()}|{payload.reason}".encode()
    ).hexdigest()
    event = SignatureEvent(
        user_id=current_user.user_id,
        organization_id=org_id,
        record_type=payload.record_type,
        record_id=payload.record_id,
        signature_type=payload.signature_type,
        reason=payload.reason,
        meaning=payload.meaning,
        signed_at=signed_at,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        signature_hash=signature_hash,
        prior_state=payload.prior_state,
        new_state=payload.new_state,
    )
    db.add(event)
    db.add(
        RealtimeEvent(
            event_type="Electronic Signature Captured",
            channel="signatures",
            audience_user_id=current_user.user_id,
            organization_id=org_id,
            record_type=payload.record_type,
            record_id=payload.record_id,
            payload={"signature_type": payload.signature_type, "reason": payload.reason},
        )
    )
    log_security_event(
        db,
        event_type="ELECTRONIC_SIGNATURE",
        user_id=current_user.user_id,
        request=request,
        details={"record_type": payload.record_type, "record_id": payload.record_id},
    )
    db.commit()
    db.refresh(event)
    return {"signature_id": event.signature_id, "status": "signed", "signed_at": event.signed_at}


@router.get("/background-jobs")
def list_background_jobs(
    current_user: User = Depends(require_permission("background_jobs.read")),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        select(BackgroundJob.status, func.count(BackgroundJob.job_id)).group_by(BackgroundJob.status)
    ).all()
    recent = db.execute(select(BackgroundJob).order_by(desc(BackgroundJob.created_at)).limit(50)).scalars().all()
    return {
        "summary": [{"status": row[0], "count": row[1]} for row in rows],
        "recent": [
            {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status,
                "priority": job.priority,
                "organization_id": job.organization_id,
                "created_at": job.created_at,
            }
            for job in recent
        ],
    }
