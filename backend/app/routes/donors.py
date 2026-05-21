from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import DonorReview, User
from app.schemas import DonorDecision, DonorReviewCreate, DonorReviewRead, DonorReviewUpdate
from app.services.ai_governance import (
    governed_analysis,
    record_ai_decision,
)
from app.services.audit import log_audit, serialize_model
from app.services.encryption import protect_donor_review
from app.services.security_audit import log_security_event, request_ip
from app.services.workflow_orchestration import execute_workflow_transition
from app.services.workflows import create_task

router = APIRouter(prefix="/api/donors", tags=["Donors"])

AUDIT_FIELDS = [
    "donor_id",
    "donor_name",
    "age",
    "blood_type",
    "infectious_history",
    "travel_risk",
    "missing_required_fields",
    "risk_flags",
    "risk_score",
    "risk_level",
    "recommended_action",
    "review_priority",
    "intake_status",
    "reviewer_id",
    "clinical_notes",
    "rejection_reason",
]

RISK_FIELDS = {
    "donor_name",
    "age",
    "blood_type",
    "infectious_history",
    "travel_risk",
    "missing_required_fields",
    "clinical_notes",
}


def apply_risk_analysis(db: Session, donor: DonorReview) -> None:
    analysis = governed_analysis(
        db,
        donor_name=donor.donor_name,
        age=donor.age,
        blood_type=donor.blood_type,
        infectious_history=donor.infectious_history,
        travel_risk=donor.travel_risk,
        missing_required_fields=donor.missing_required_fields,
        clinical_notes=donor.clinical_notes,
    )
    donor.risk_score = analysis.risk_score
    donor.risk_level = analysis.risk_level
    donor.risk_flags = analysis.flagged_conditions
    donor.recommended_action = analysis.recommended_action
    donor.review_priority = analysis.review_priority


@router.get("", response_model=list[DonorReviewRead])
def list_donors(
    request: Request,
    intake_status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_permission("donors.read")),
    db: Session = Depends(get_db),
) -> list[DonorReview]:
    query = select(DonorReview)
    if intake_status:
        query = query.where(DonorReview.intake_status == intake_status)
    if risk_level:
        query = query.where(DonorReview.risk_level == risk_level)
    query = query.order_by(desc(DonorReview.risk_score), DonorReview.created_at).limit(limit).offset(offset)
    donors = list(db.execute(query).scalars().all())
    log_security_event(
        db,
        event_type="DONOR_LIST_ACCESS",
        user_id=current_user.user_id,
        request=request,
        details={"limit": limit, "offset": offset, "intake_status": intake_status, "risk_level": risk_level},
    )
    db.commit()
    return donors


@router.get("/{review_id}", response_model=DonorReviewRead)
def get_donor(
    review_id: int,
    request: Request,
    current_user: User = Depends(require_permission("donors.read")),
    db: Session = Depends(get_db),
) -> DonorReview:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")
    log_security_event(
        db,
        event_type="SENSITIVE_RECORD_ACCESS",
        user_id=current_user.user_id,
        request=request,
        details={"record_type": "DonorReview", "record_id": review_id},
    )
    db.commit()
    return donor


@router.post("", response_model=DonorReviewRead, status_code=status.HTTP_201_CREATED)
def create_donor(
    payload: DonorReviewCreate,
    request: Request,
    current_user: User = Depends(require_permission("donors.create")),
    db: Session = Depends(get_db),
) -> DonorReview:
    donor = DonorReview(**payload.model_dump())
    donor.intake_status = "Draft Intake"
    apply_risk_analysis(db, donor)
    protect_donor_review(donor)
    db.add(donor)
    db.flush()
    record_ai_decision(db, donor, workflow_stage="Draft Intake", reviewed_by=current_user.user_id)
    create_task(
        db,
        task_type="Intake Packet Validation",
        title=f"Validate donor intake packet for {donor.donor_id}",
        description="Complete intake readiness review before clinical routing.",
        related_record_id=str(donor.review_id),
        related_record_type="DonorReview",
        assigned_role_name="Donor Intake Coordinator",
        assigned_to_user_id=payload.reviewer_id or current_user.user_id,
        priority=donor.review_priority,
        workflow_state="Draft Intake",
        queue_name="My Intake Workbench",
        due_date=datetime.now(UTC) + timedelta(hours=24 if donor.risk_score >= 50 else 48),
    )
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="CREATE_DONOR_INTAKE",
        table_name="fact_donor_review",
        record_id=str(donor.review_id),
        old_value=None,
        new_value=serialize_model(donor, AUDIT_FIELDS),
        ip_address=request_ip(request),
    )
    log_security_event(
        db,
        event_type="DONOR_CREATE",
        user_id=current_user.user_id,
        request=request,
        details={"record_id": donor.review_id, "donor_id": donor.donor_id},
    )
    db.commit()
    db.refresh(donor)
    return donor


@router.patch("/{review_id}", response_model=DonorReviewRead)
def update_donor(
    review_id: int,
    payload: DonorReviewUpdate,
    request: Request,
    current_user: User = Depends(require_permission("donors.review")),
    db: Session = Depends(get_db),
) -> DonorReview:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")

    old_value = serialize_model(donor, AUDIT_FIELDS)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(donor, field, value)
    protect_donor_review(donor)

    if RISK_FIELDS.intersection(updates):
        apply_risk_analysis(db, donor)
        db.flush()
        record_ai_decision(db, donor, workflow_stage=donor.intake_status, reviewed_by=current_user.user_id)

    if updates.get("intake_status") in {"Approved", "Rejected", "Deferred"}:
        donor.reviewed_at = datetime.now(UTC)

    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_DONOR_REVIEW",
        table_name="fact_donor_review",
        record_id=str(donor.review_id),
        old_value=old_value,
        new_value=serialize_model(donor, AUDIT_FIELDS),
        ip_address=request_ip(request),
    )
    log_security_event(
        db,
        event_type="DONOR_UPDATE",
        user_id=current_user.user_id,
        request=request,
        details={"record_id": donor.review_id, "fields": sorted(updates.keys())},
    )
    db.commit()
    db.refresh(donor)
    return donor


@router.post("/{review_id}/decision", response_model=DonorReviewRead)
def record_decision(
    review_id: int,
    payload: DonorDecision,
    request: Request,
    current_user: User = Depends(require_permission("donors.review")),
    db: Session = Depends(get_db),
) -> DonorReview:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")

    action_map = {
        "Approved": "approve_donor",
        "Rejected": "reject_donor",
        "Pending Additional Information": "request_additional_information",
        "Deferred": "request_additional_information",
        "Under Review": "request_additional_information",
        "QA Investigation": "escalate_to_qa",
    }
    action_name = action_map.get(payload.intake_status)
    if not action_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported donor decision")

    execute_workflow_transition(
        db,
        current_user=current_user,
        action_name=action_name,
        related_record_type="DonorReview",
        related_record_id=str(review_id),
        note=payload.rejection_reason or payload.ai_override_reason or "",
        metadata={
            "final_decision": payload.intake_status,
            "reviewer_id": payload.reviewer_id,
            "human_override": payload.ai_override,
            "override_reason": payload.ai_override_reason,
        },
    )
    log_security_event(
        db,
        event_type="DONOR_DECISION",
        user_id=current_user.user_id,
        request=request,
        details={
            "record_id": review_id,
            "decision": payload.intake_status,
            "ai_override": payload.ai_override,
        },
    )
    db.commit()
    refreshed = db.get(DonorReview, review_id)
    if not refreshed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")
    return refreshed

