from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_any_permission, require_permission
from app.auth.security import verify_password
from app.database import get_db
from app.models import (
    AuditLog,
    BackgroundJob,
    DocumentAccess,
    DocumentVersion,
    ExternalStatusMapping,
    Notification,
    Organization,
    PartnerComplaint,
    PartnerDocument,
    PartnerMessage,
    PartnerSubmission,
    PartnerSubmissionStatus,
    PartnerTaskResponse,
    RealtimeEvent,
    Role,
    SecureDocument,
    SignatureEvent,
    SupplierRelationship,
    User,
    WorkflowTask,
)
from app.services.audit import log_audit
from app.services.encryption import encrypt_text
from app.services.security_audit import log_security_event, request_ip
from app.services.tenant_access import (
    apply_org_scope,
    ensure_org_access,
    is_external_user,
    require_organization,
)

router = APIRouter(prefix="/api/partners", tags=["Partner Portal"])

PARTNER_STATUSES = [
    "Submitted",
    "Intake Review",
    "Under Clinical Review",
    "Under QA Review",
    "Information Requested",
    "Approved",
    "Rejected",
    "Closed",
]

DEFAULT_STATUS_MAP = {
    "Referral Received": "Submitted",
    "Pending Intake Validation": "Intake Review",
    "Pending Administrative Screen": "Intake Review",
    "Pending Clinical Review": "Under Clinical Review",
    "Pending Medical Social History Review": "Under Clinical Review",
    "Pending Infectious Disease Review": "Under Clinical Review",
    "Pending Tissue Suitability Review": "Under Clinical Review",
    "Pending QA Review": "Under QA Review",
    "QA Investigation": "Under QA Review",
    "CAPA Investigation": "Under QA Review",
    "Awaiting External Review": "Information Requested",
    "Pending Additional Information": "Information Requested",
    "Approved": "Approved",
    "Release Approved": "Approved",
    "Rejected": "Rejected",
    "Closed": "Closed",
}


class PartnerSubmissionCreate(BaseModel):
    submission_type: str
    title: str
    description: str
    product_or_tissue: str | None = None
    batch_or_reference: str | None = None
    priority: str = "Standard"
    contact_email: str | None = None
    attestation: bool = True


class PartnerComplaintCreate(BaseModel):
    product_or_batch: str
    issue_category: str
    severity: str = "Medium"
    description: str
    impact_assessment: str = ""
    contact_email: str | None = None


class PartnerDocumentUpload(BaseModel):
    document_name: str
    document_type: str
    document_category: str = "Submission Evidence"
    storage_reference: str = "partner://pending-upload/document.pdf"
    checksum_sha256: str | None = None
    submission_id: int | None = None
    complaint_id: int | None = None


class PartnerTaskResponseCreate(BaseModel):
    status: str = "Submitted"
    response_note: str = ""
    attachment_document_id: int | None = None


class PartnerMessageCreate(BaseModel):
    subject: str
    body: str
    submission_id: int | None = None
    complaint_id: int | None = None
    attachment_document_id: int | None = None


class PartnerSignatureCreate(BaseModel):
    record_type: str
    record_id: str
    reason: str
    password: str
    meaning: str = "I certify this partner submission is accurate and attributable to my authenticated identity."


def _external_status(db: Session, internal_state: str) -> str:
    row = db.execute(
        select(ExternalStatusMapping).where(
            ExternalStatusMapping.internal_state == internal_state,
            ExternalStatusMapping.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if row:
        return row.external_status
    return DEFAULT_STATUS_MAP.get(internal_state, "Under Review")


def _relationship_payload(relationship: SupplierRelationship | None) -> dict | None:
    if not relationship:
        return None
    return {
        "relationship_id": relationship.relationship_id,
        "relationship_type": relationship.relationship_type,
        "status": relationship.status,
        "onboarding_status": relationship.onboarding_status,
        "risk_tier": relationship.risk_tier,
    }


def _submission_payload(submission: PartnerSubmission, *, internal: bool = False) -> dict:
    payload = {
        "submission_id": submission.submission_id,
        "submission_code": submission.submission_code,
        "submission_type": submission.submission_type,
        "title": submission.title,
        "status": submission.partner_visible_status,
        "priority": submission.priority,
        "description": submission.description,
        "product_or_tissue": submission.product_or_tissue,
        "batch_or_reference": submission.batch_or_reference,
        "estimated_completion_at": submission.estimated_completion_at,
        "submitted_at": submission.submitted_at,
        "closed_at": submission.closed_at,
    }
    if internal:
        payload["organization_id"] = submission.organization_id
        payload["internal_state"] = submission.internal_state
        payload["details"] = submission.details
    return payload


def _complaint_payload(complaint: PartnerComplaint, *, internal: bool = False) -> dict:
    payload = {
        "complaint_id": complaint.complaint_id,
        "complaint_code": complaint.complaint_code,
        "product_or_batch": complaint.product_or_batch,
        "issue_category": complaint.issue_category,
        "severity": complaint.severity,
        "description": complaint.description,
        "impact_assessment": complaint.impact_assessment,
        "status": complaint.partner_visible_status,
        "submitted_at": complaint.submitted_at,
        "closed_at": complaint.closed_at,
    }
    if internal:
        payload["organization_id"] = complaint.organization_id
        payload["internal_state"] = complaint.internal_state
        payload["investigation_id"] = complaint.investigation_id
        payload["capa_id"] = complaint.capa_id
        payload["details"] = complaint.details
    return payload


def _json_ready(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _task_payload(task: WorkflowTask) -> dict:
    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "review_status": _partner_task_status(task),
        "due_date": task.due_date,
        "related_record_type": task.related_record_type,
        "related_record_id": task.related_record_id,
    }


def _partner_task_status(task: WorkflowTask) -> str:
    if task.status in {"Completed", "Closed"}:
        return "Closed"
    if task.status in {"In Progress", "Submitted"}:
        return "Under Review"
    if task.status in {"Blocked", "Escalated"}:
        return "Pending Partner Response"
    return "Open"


def _document_payload(document: SecureDocument, db: Session) -> dict:
    version = db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.document_id)
        .order_by(desc(DocumentVersion.version_number))
        .limit(1)
    ).scalar_one_or_none()
    partner_document = db.execute(
        select(PartnerDocument).where(PartnerDocument.document_id == document.document_id)
    ).scalar_one_or_none()
    metadata = version.extra_metadata if version and isinstance(version.extra_metadata, dict) else {}
    return {
        "document_id": document.document_id,
        "partner_document_id": partner_document.partner_document_id if partner_document else None,
        "document_name": document.document_name,
        "document_type": document.document_type,
        "document_category": partner_document.document_category if partner_document else document.document_type,
        "request_status": partner_document.request_status if partner_document else document.access_classification,
        "approval_status": version.approval_status if version else document.access_classification,
        "review_note": metadata.get("review_note", ""),
        "record_type": document.record_type,
        "record_id": document.record_id,
        "created_at": document.created_at,
    }


def _submission_by_ref(db: Session, submission_ref: str) -> PartnerSubmission | None:
    if submission_ref.isdigit():
        return db.get(PartnerSubmission, int(submission_ref))
    return db.execute(
        select(PartnerSubmission).where(PartnerSubmission.submission_code == submission_ref)
    ).scalar_one_or_none()


def _complaint_by_ref(db: Session, complaint_ref: str) -> PartnerComplaint | None:
    if complaint_ref.isdigit():
        return db.get(PartnerComplaint, int(complaint_ref))
    return db.execute(
        select(PartnerComplaint).where(PartnerComplaint.complaint_code == complaint_ref)
    ).scalar_one_or_none()


def _message_payload(message: PartnerMessage) -> dict:
    return {
        "message_id": message.message_id,
        "subject": message.subject,
        "body": message.body,
        "audience": message.audience,
        "submission_id": message.submission_id,
        "complaint_id": message.complaint_id,
        "created_at": message.created_at,
        "is_read": message.is_read,
    }


def _first_user_for_role(db: Session, role_name: str) -> User | None:
    role = db.execute(select(Role).where(Role.role_name == role_name)).scalar_one_or_none()
    if not role:
        return None
    return db.execute(
        select(User)
        .where(User.role_id == role.role_id, User.is_active.is_(True), User.is_external.is_(False))
        .order_by(User.user_id)
        .limit(1)
    ).scalar_one_or_none()


def _role_id(db: Session, role_name: str) -> int | None:
    role = db.execute(select(Role).where(Role.role_name == role_name)).scalar_one_or_none()
    return role.role_id if role else None


def _target_role_for_submission(submission_type: str) -> str:
    if "quality" in submission_type.lower() or "compliance" in submission_type.lower():
        return "Quality Assurance Specialist"
    if "recovery" in submission_type.lower():
        return "Operations Manager"
    return "Donor Intake Coordinator"


def _create_partner_task(
    db: Session,
    *,
    organization_id: int,
    title: str,
    description: str,
    task_type: str,
    related_record_type: str,
    related_record_id: str,
    target_role: str,
    priority: str,
) -> WorkflowTask:
    assignee = _first_user_for_role(db, target_role)
    task = WorkflowTask(
        task_type=task_type,
        title=title,
        description=description,
        assigned_to_user_id=assignee.user_id if assignee else None,
        assigned_role_id=_role_id(db, target_role),
        priority=priority,
        status="Assigned",
        workflow_state="Partner Intake Review" if task_type != "Quality Complaint Review" else "Pending QA Review",
        queue_name=f"{target_role} Partner Intake",
        due_date=datetime.now(UTC) + timedelta(hours=24 if priority in {"High", "Critical"} else 72),
        related_record_type=related_record_type,
        related_record_id=related_record_id,
        organization_id=organization_id,
    )
    db.add(task)
    db.flush()
    if assignee:
        db.add(
            Notification(
                user_id=assignee.user_id,
                title=f"[Partner] {title}",
                message=description,
                notification_type=task_type,
                priority=priority,
                workflow_task_id=task.task_id,
                related_record_type=related_record_type,
                related_record_id=related_record_id,
                action_route="/admin/partners",
                workflow_context={
                    "task_id": task.task_id,
                    "route_path": "/admin/partners",
                    "external_boundary": "partner_portal",
                },
                organization_id=organization_id,
            )
        )
    return task


def _partner_org(current_user: User) -> int:
    return require_organization(current_user)


@router.get("/dashboard")
def partner_dashboard(
    current_user: User = Depends(require_permission("partner.portal")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = _partner_org(current_user)
    org = db.get(Organization, org_id)
    relationship = db.execute(
        select(SupplierRelationship).where(SupplierRelationship.external_organization_id == org_id)
    ).scalar_one_or_none()
    submissions = db.execute(
        select(PartnerSubmission)
        .where(PartnerSubmission.organization_id == org_id, PartnerSubmission.is_archived.is_(False))
        .order_by(desc(PartnerSubmission.submitted_at))
        .limit(75)
    ).scalars().all()
    complaints = db.execute(
        select(PartnerComplaint)
        .where(PartnerComplaint.organization_id == org_id, PartnerComplaint.is_archived.is_(False))
        .order_by(desc(PartnerComplaint.submitted_at))
        .limit(50)
    ).scalars().all()
    tasks = db.execute(
        select(WorkflowTask)
        .where(
            WorkflowTask.organization_id == org_id,
            WorkflowTask.status.in_(["Pending", "Assigned", "In Progress", "Blocked", "Escalated", "Submitted"]),
        )
        .order_by(desc(WorkflowTask.created_at))
        .limit(75)
    ).scalars().all()
    documents = db.execute(
        select(SecureDocument)
        .join(PartnerDocument, PartnerDocument.document_id == SecureDocument.document_id, isouter=True)
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
    messages = db.execute(
        select(PartnerMessage)
        .where(PartnerMessage.organization_id == org_id)
        .order_by(desc(PartnerMessage.created_at))
        .limit(25)
    ).scalars().all()
    return {
        "organization": {
            "organization_id": org.organization_id if org else None,
            "organization_name": org.organization_name if org else "",
            "organization_type": org.organization_type if org else "Partner",
            "approval_status": org.approval_status if org else "Approved",
            "contact_email": org.contact_email if org else "",
        },
        "relationship": _relationship_payload(relationship),
        "kpis": {
            "open_submissions": sum(1 for item in submissions if item.partner_visible_status not in {"Closed", "Approved", "Rejected"}),
            "pending_review": sum(1 for item in submissions if item.partner_visible_status in {"Intake Review", "Under Clinical Review", "Under QA Review"}),
            "info_requested": sum(1 for task in tasks if _partner_task_status(task) == "Pending Partner Response"),
            "approved": sum(1 for item in submissions if item.partner_visible_status == "Approved"),
            "closed": sum(1 for item in submissions if item.partner_visible_status == "Closed"),
        },
        "submissions": [_submission_payload(item) for item in submissions],
        "complaints": [_complaint_payload(item) for item in complaints],
        "tasks": [_task_payload(task) for task in tasks],
        "documents": [_document_payload(document, db) for document in documents],
        "messages": [_message_payload(message) for message in messages],
        "notifications": [
            {
                "notification_id": item.notification_id,
                "title": item.title,
                "message": item.message,
                "priority": item.priority,
                "is_read": item.is_read,
                "created_at": item.created_at,
                "action_route": item.action_route,
            }
            for item in notifications
        ],
    }


@router.get("/submissions")
def list_partner_submissions(
    current_user: User = Depends(require_any_permission(["partner.portal", "partners.read"])),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(PartnerSubmission).where(PartnerSubmission.is_archived.is_(False)).order_by(desc(PartnerSubmission.submitted_at))
    query = apply_org_scope(query, PartnerSubmission, current_user)
    internal = not is_external_user(current_user)
    return [_submission_payload(item, internal=internal) for item in db.execute(query.limit(250)).scalars().all()]


@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def create_partner_submission(
    payload: PartnerSubmissionCreate,
    request: Request,
    current_user: User = Depends(require_permission("partner.portal")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = _partner_org(current_user)
    if not payload.attestation:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Submission attestation is required")
    internal_state = "Pending Intake Validation"
    external_status = _external_status(db, internal_state)
    submission = PartnerSubmission(
        submission_code=f"SUB-TMP-{sha256(f'{org_id}-{datetime.now(UTC).isoformat()}'.encode()).hexdigest()[:12]}",
        organization_id=org_id,
        submitted_by_user_id=current_user.user_id,
        submission_type=payload.submission_type,
        title=payload.title,
        partner_visible_status=external_status,
        internal_state=internal_state,
        priority=payload.priority,
        description=payload.description,
        product_or_tissue=payload.product_or_tissue,
        batch_or_reference=payload.batch_or_reference,
        estimated_completion_at=datetime.now(UTC) + timedelta(days=3),
        details={"contact_email": payload.contact_email, "attestation": payload.attestation},
    )
    db.add(submission)
    db.flush()
    submission.submission_code = f"SUB-{datetime.now(UTC).year}-{submission.submission_id:04d}"
    db.add(
        PartnerSubmissionStatus(
            submission_id=submission.submission_id,
            from_status=None,
            to_status=external_status,
            internal_state=internal_state,
            changed_by_user_id=current_user.user_id,
            note="Partner submission received.",
            partner_visible=True,
        )
    )
    target_role = _target_role_for_submission(payload.submission_type)
    task = _create_partner_task(
        db,
        organization_id=org_id,
        title=f"Review partner submission {submission.submission_code}",
        description=payload.description,
        task_type="Partner Submission Review",
        related_record_type="PartnerSubmission",
        related_record_id=str(submission.submission_id),
        target_role=target_role,
        priority=payload.priority,
    )
    db.add(
        Notification(
            user_id=current_user.user_id,
            title=f"[Submitted] {submission.submission_code}",
            message="Your submission has been received and is in intake review.",
            notification_type="Partner Submission",
            priority="Normal",
            workflow_task_id=task.task_id,
            related_record_type="PartnerSubmission",
            related_record_id=str(submission.submission_id),
            action_route=f"/partner/submission/{submission.submission_code}",
            workflow_context={"route_path": f"/partner/submission/{submission.submission_code}", "status": external_status},
            organization_id=org_id,
        )
    )
    db.add(
        RealtimeEvent(
            event_type="Partner Submission Created",
            channel="partner-portal",
            audience_user_id=current_user.user_id,
            organization_id=org_id,
            record_type="PartnerSubmission",
            record_id=str(submission.submission_id),
            payload={"submission_code": submission.submission_code, "status": external_status},
        )
    )
    db.add(
        BackgroundJob(
            job_type="Partner Submission Routing",
            status="Queued",
            priority=payload.priority,
            organization_id=org_id,
            payload={"submission_id": submission.submission_id, "target_role": target_role},
        )
    )
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="PARTNER_SUBMISSION_CREATED",
        table_name="dim_partner_submission",
        record_id=str(submission.submission_id),
        old_value=None,
        new_value=_json_ready(_submission_payload(submission, internal=True)),
        entity_type="PartnerSubmission",
        entity_id=str(submission.submission_id),
        ip_address=request_ip(request),
    )
    log_security_event(
        db,
        event_type="PARTNER_SUBMISSION_CREATED",
        user_id=current_user.user_id,
        request=request,
        details={"submission_id": submission.submission_id, "organization_id": org_id},
    )
    db.commit()
    db.refresh(submission)
    return _submission_payload(submission)


@router.get("/submissions/{submission_ref}")
def get_partner_submission(
    submission_ref: str,
    current_user: User = Depends(require_any_permission(["partner.portal", "partners.read"])),
    db: Session = Depends(get_db),
) -> dict:
    submission = _submission_by_ref(db, submission_ref)
    if not submission or submission.is_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    ensure_org_access(current_user, submission, not_found_detail="Submission not found")
    history = db.execute(
        select(PartnerSubmissionStatus)
        .where(PartnerSubmissionStatus.submission_id == submission.submission_id)
        .order_by(desc(PartnerSubmissionStatus.changed_at))
    ).scalars().all()
    messages = db.execute(
        select(PartnerMessage)
        .where(PartnerMessage.submission_id == submission.submission_id)
        .order_by(desc(PartnerMessage.created_at))
    ).scalars().all()
    return _submission_payload(submission, internal=not is_external_user(current_user)) | {
        "status_history": [
            {
                "from_status": row.from_status,
                "to_status": row.to_status,
                "changed_at": row.changed_at,
                "note": row.note,
            }
            for row in history
            if row.partner_visible or not is_external_user(current_user)
        ],
        "messages": [_message_payload(message) for message in messages],
    }


@router.get("/complaints/{complaint_ref}")
def get_partner_complaint(
    complaint_ref: str,
    current_user: User = Depends(require_any_permission(["partner.portal", "partners.read"])),
    db: Session = Depends(get_db),
) -> dict:
    complaint = _complaint_by_ref(db, complaint_ref)
    if not complaint or complaint.is_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    ensure_org_access(current_user, complaint, not_found_detail="Complaint not found")
    messages = db.execute(
        select(PartnerMessage)
        .where(PartnerMessage.complaint_id == complaint.complaint_id)
        .order_by(desc(PartnerMessage.created_at))
    ).scalars().all()
    documents = db.execute(
        select(SecureDocument)
        .join(PartnerDocument, PartnerDocument.document_id == SecureDocument.document_id)
        .where(PartnerDocument.complaint_id == complaint.complaint_id, SecureDocument.is_active.is_(True))
        .order_by(desc(SecureDocument.created_at))
    ).scalars().all()
    return _complaint_payload(complaint, internal=not is_external_user(current_user)) | {
        "messages": [_message_payload(message) for message in messages],
        "documents": [_document_payload(document, db) for document in documents],
    }


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
def create_partner_complaint(
    payload: PartnerComplaintCreate,
    request: Request,
    current_user: User = Depends(require_permission("partner.portal")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = _partner_org(current_user)
    internal_state = "Pending QA Review"
    external_status = _external_status(db, internal_state)
    complaint = PartnerComplaint(
        complaint_code=f"QC-TMP-{sha256(f'{org_id}-{datetime.now(UTC).isoformat()}'.encode()).hexdigest()[:12]}",
        organization_id=org_id,
        submitted_by_user_id=current_user.user_id,
        product_or_batch=payload.product_or_batch,
        issue_category=payload.issue_category,
        severity=payload.severity,
        description=payload.description,
        impact_assessment=payload.impact_assessment,
        contact_email=payload.contact_email,
        partner_visible_status=external_status,
        internal_state=internal_state,
    )
    db.add(complaint)
    db.flush()
    complaint.complaint_code = f"QC-{datetime.now(UTC).year}-{complaint.complaint_id:04d}"
    task = _create_partner_task(
        db,
        organization_id=org_id,
        title=f"Review quality complaint {complaint.complaint_code}",
        description=payload.description,
        task_type="Quality Complaint Review",
        related_record_type="PartnerComplaint",
        related_record_id=str(complaint.complaint_id),
        target_role="Quality Assurance Specialist",
        priority="Critical" if payload.severity in {"Critical", "High"} else "High",
    )
    db.add(
        Notification(
            user_id=current_user.user_id,
            title=f"[Quality Complaint] {complaint.complaint_code}",
            message="Your quality complaint was received and routed for QA review.",
            notification_type="Partner Complaint",
            priority="High",
            workflow_task_id=task.task_id,
            related_record_type="PartnerComplaint",
            related_record_id=str(complaint.complaint_id),
            action_route=f"/partner/complaint/{complaint.complaint_code}",
            workflow_context={"route_path": f"/partner/complaint/{complaint.complaint_code}", "status": external_status},
            organization_id=org_id,
        )
    )
    db.add(
        RealtimeEvent(
            event_type="Partner Quality Complaint Created",
            channel="partner-portal",
            audience_user_id=current_user.user_id,
            organization_id=org_id,
            record_type="PartnerComplaint",
            record_id=str(complaint.complaint_id),
            payload={"complaint_code": complaint.complaint_code, "severity": complaint.severity},
        )
    )
    db.add(
        BackgroundJob(
            job_type="Partner Complaint QA Routing",
            status="Queued",
            priority=complaint.severity,
            organization_id=org_id,
            payload={"complaint_id": complaint.complaint_id},
        )
    )
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="PARTNER_COMPLAINT_CREATED",
        table_name="fact_partner_complaint",
        record_id=str(complaint.complaint_id),
        old_value=None,
        new_value=_json_ready(_complaint_payload(complaint, internal=True)),
        entity_type="PartnerComplaint",
        entity_id=str(complaint.complaint_id),
        ip_address=request_ip(request),
    )
    log_security_event(
        db,
        event_type="PARTNER_COMPLAINT_CREATED",
        user_id=current_user.user_id,
        request=request,
        details={"complaint_id": complaint.complaint_id, "organization_id": org_id},
    )
    db.commit()
    db.refresh(complaint)
    return _complaint_payload(complaint)


@router.get("/complaints")
def list_partner_complaints(
    current_user: User = Depends(require_any_permission(["partner.portal", "partners.read"])),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(PartnerComplaint).where(PartnerComplaint.is_archived.is_(False)).order_by(desc(PartnerComplaint.submitted_at))
    query = apply_org_scope(query, PartnerComplaint, current_user)
    internal = not is_external_user(current_user)
    return [_complaint_payload(item, internal=internal) for item in db.execute(query.limit(250)).scalars().all()]


@router.post("/documents", status_code=status.HTTP_201_CREATED)
def upload_partner_document(
    payload: PartnerDocumentUpload,
    request: Request,
    current_user: User = Depends(require_permission("partner.portal")),
    db: Session = Depends(get_db),
) -> dict:
    org_id = _partner_org(current_user)
    if payload.submission_id:
        submission = db.get(PartnerSubmission, payload.submission_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        ensure_org_access(current_user, submission, not_found_detail="Submission not found")
        record_type = "PartnerSubmission"
        record_id = str(submission.submission_id)
    elif payload.complaint_id:
        complaint = db.get(PartnerComplaint, payload.complaint_id)
        if not complaint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        ensure_org_access(current_user, complaint, not_found_detail="Complaint not found")
        record_type = "PartnerComplaint"
        record_id = str(complaint.complaint_id)
    else:
        record_type = "PartnerDocumentRequest"
        record_id = f"ORG-{org_id}"
    document = SecureDocument(
        record_type=record_type,
        record_id=record_id,
        document_name=payload.document_name,
        document_type=payload.document_type,
        storage_uri_encrypted=encrypt_text(payload.storage_reference) or "",
        checksum_sha256=payload.checksum_sha256,
        uploaded_by=current_user.user_id,
        access_classification="Partner Submitted",
        organization_id=org_id,
    )
    db.add(document)
    db.flush()
    db.add(
        PartnerDocument(
            organization_id=org_id,
            document_id=document.document_id,
            submission_id=payload.submission_id,
            complaint_id=payload.complaint_id,
            document_category=payload.document_category,
            request_status="Submitted",
        )
    )
    db.add(
        DocumentVersion(
            document_id=document.document_id,
            version_number=1,
            document_status="Submitted",
            uploaded_by=current_user.user_id,
            storage_uri_encrypted=document.storage_uri_encrypted,
            checksum_sha256=document.checksum_sha256,
            approval_status="Pending Review",
            extra_metadata={"source": "partner_portal", "document_category": payload.document_category},
        )
    )
    db.add(
        DocumentAccess(
            document_id=document.document_id,
            user_id=current_user.user_id,
            action_type="PARTNER_UPLOAD",
            ip_address=request_ip(request),
            route=str(request.url.path),
            details={"document_name": document.document_name},
        )
    )
    db.add(
        RealtimeEvent(
            event_type="Partner Document Uploaded",
            channel="partner-documents",
            audience_user_id=current_user.user_id,
            organization_id=org_id,
            record_type=record_type,
            record_id=record_id,
            payload={"document_id": document.document_id, "document_name": document.document_name},
        )
    )
    log_security_event(
        db,
        event_type="PARTNER_DOCUMENT_UPLOADED",
        user_id=current_user.user_id,
        request=request,
        details={"document_id": document.document_id, "organization_id": org_id},
    )
    db.commit()
    db.refresh(document)
    return _document_payload(document, db)


@router.post("/tasks/{task_id}/respond")
def respond_to_partner_task(
    task_id: int,
    payload: PartnerTaskResponseCreate,
    current_user: User = Depends(require_permission("partner.portal")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    task = db.get(WorkflowTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    ensure_org_access(current_user, task, not_found_detail="Task not found")
    task.status = "Submitted" if payload.status == "Submitted" else payload.status
    db.add(
        PartnerTaskResponse(
            task_id=task.task_id,
            organization_id=require_organization(current_user),
            responded_by_user_id=current_user.user_id,
            response_status=payload.status,
            response_note=payload.response_note,
            attachment_document_id=payload.attachment_document_id,
        )
    )
    db.add(
        RealtimeEvent(
            event_type="Partner Task Response",
            channel="partner-tasks",
            audience_user_id=current_user.user_id,
            organization_id=task.organization_id,
            record_type="WorkflowTask",
            record_id=str(task.task_id),
            payload={"status": payload.status, "response_note": payload.response_note},
        )
    )
    db.commit()
    return {"status": "response_recorded"}


@router.post("/messages", status_code=status.HTTP_201_CREATED)
def create_partner_message(
    payload: PartnerMessageCreate,
    request: Request,
    current_user: User = Depends(require_any_permission(["partner.portal", "partners.manage", "partners.read"])),
    db: Session = Depends(get_db),
) -> dict:
    org_id = require_organization(current_user) if is_external_user(current_user) else None
    if payload.submission_id:
        submission = db.get(PartnerSubmission, payload.submission_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        ensure_org_access(current_user, submission, not_found_detail="Submission not found")
        org_id = submission.organization_id
    if payload.complaint_id:
        complaint = db.get(PartnerComplaint, payload.complaint_id)
        if not complaint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
        ensure_org_access(current_user, complaint, not_found_detail="Complaint not found")
        org_id = complaint.organization_id
    if not org_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message requires partner context")
    message = PartnerMessage(
        organization_id=org_id,
        submission_id=payload.submission_id,
        complaint_id=payload.complaint_id,
        sender_user_id=current_user.user_id,
        audience="Internal" if is_external_user(current_user) else "Partner",
        subject=payload.subject,
        body=payload.body,
        attachment_document_id=payload.attachment_document_id,
    )
    db.add(message)
    db.flush()
    db.add(
        RealtimeEvent(
            event_type="Partner Message Created",
            channel="partner-messages",
            audience_user_id=current_user.user_id,
            organization_id=org_id,
            record_type="PartnerMessage",
            record_id=str(message.message_id),
            payload={"subject": payload.subject, "audience": message.audience},
        )
    )
    log_security_event(
        db,
        event_type="PARTNER_MESSAGE_CREATED",
        user_id=current_user.user_id,
        request=request,
        details={"organization_id": org_id, "audience": message.audience},
    )
    db.commit()
    db.refresh(message)
    return _message_payload(message)


@router.post("/signatures", status_code=status.HTTP_201_CREATED)
def create_partner_signature(
    payload: PartnerSignatureCreate,
    request: Request,
    current_user: User = Depends(require_permission("partner.portal")),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.password, current_user.hashed_password):
        log_security_event(
            db,
            event_type="PARTNER_SIGNATURE_REAUTH_FAILED",
            user_id=current_user.user_id,
            request=request,
            success=False,
            details={"record_type": payload.record_type, "record_id": payload.record_id},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Re-authentication failed")
    org_id = _partner_org(current_user)
    signed_at = datetime.now(UTC)
    signature_hash = sha256(
        f"partner|{current_user.user_id}|{org_id}|{payload.record_type}|{payload.record_id}|{signed_at.isoformat()}|{payload.reason}".encode()
    ).hexdigest()
    event = SignatureEvent(
        user_id=current_user.user_id,
        organization_id=org_id,
        record_type=payload.record_type,
        record_id=payload.record_id,
        signature_type="Partner Submission Attestation",
        reason=payload.reason,
        meaning=payload.meaning,
        signed_at=signed_at,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        signature_hash=signature_hash,
        prior_state="Draft",
        new_state="Submitted",
    )
    db.add(event)
    log_security_event(
        db,
        event_type="PARTNER_ELECTRONIC_SIGNATURE",
        user_id=current_user.user_id,
        request=request,
        details={"record_type": payload.record_type, "record_id": payload.record_id},
    )
    db.commit()
    db.refresh(event)
    return {"signature_id": event.signature_id, "status": "signed", "signed_at": event.signed_at}


@router.get("/admin/overview")
def partner_admin_overview(
    current_user: User = Depends(require_any_permission(["partners.manage", "suppliers.manage"])),
    db: Session = Depends(get_db),
) -> dict:
    organizations = db.execute(
        select(Organization)
        .where(Organization.organization_type.in_(["Supplier", "Partner", "Recovery Organization", "Auditor", "Customer"]))
        .order_by(Organization.organization_name)
    ).scalars().all()
    submissions = db.execute(select(PartnerSubmission).order_by(desc(PartnerSubmission.submitted_at)).limit(100)).scalars().all()
    complaints = db.execute(select(PartnerComplaint).order_by(desc(PartnerComplaint.submitted_at)).limit(100)).scalars().all()
    tasks = db.execute(
        select(WorkflowTask)
        .where(WorkflowTask.related_record_type.in_(["PartnerSubmission", "PartnerComplaint"]))
        .order_by(desc(WorkflowTask.created_at))
        .limit(100)
    ).scalars().all()
    pending_docs = db.execute(
        select(func.count(SecureDocument.document_id)).where(SecureDocument.access_classification.in_(["Partner Submitted", "Needs Rework", "Hold"]))
    ).scalar() or 0
    audit_count = db.execute(
        select(func.count(AuditLog.audit_id)).where(AuditLog.action_type.like("PARTNER_%"))
    ).scalar() or 0
    return {
        "kpis": {
            "partner_organizations": len(organizations),
            "open_submissions": sum(1 for item in submissions if item.partner_visible_status not in {"Approved", "Rejected", "Closed"}),
            "open_complaints": sum(1 for item in complaints if item.partner_visible_status not in {"Closed", "Rejected"}),
            "pending_documents": int(pending_docs),
            "partner_audit_events": int(audit_count),
        },
        "organizations": [
            {
                "organization_id": org.organization_id,
                "organization_name": org.organization_name,
                "organization_type": org.organization_type,
                "approval_status": org.approval_status,
                "contact_email": org.contact_email,
                "is_active": org.is_active,
            }
            for org in organizations
        ],
        "submissions": [_submission_payload(item, internal=True) for item in submissions],
        "complaints": [_complaint_payload(item, internal=True) for item in complaints],
        "tasks": [_task_payload(task) for task in tasks],
    }
