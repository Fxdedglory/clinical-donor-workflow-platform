from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DonorReview, WorkflowTask
from app.schemas import DonorDecision, DonorReviewCreate, DonorReviewRead, DonorReviewUpdate
from app.services.audit import log_audit, serialize_model
from app.services.risk_engine import analyze_donor_risk
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


def apply_risk_analysis(donor: DonorReview) -> None:
    analysis = analyze_donor_risk(
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
    intake_status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DonorReview]:
    query = select(DonorReview)
    if intake_status:
        query = query.where(DonorReview.intake_status == intake_status)
    if risk_level:
        query = query.where(DonorReview.risk_level == risk_level)
    query = query.order_by(desc(DonorReview.risk_score), DonorReview.created_at).limit(limit).offset(offset)
    return list(db.execute(query).scalars().all())


@router.get("/{review_id}", response_model=DonorReviewRead)
def get_donor(review_id: int, db: Session = Depends(get_db)) -> DonorReview:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")
    return donor


@router.post("", response_model=DonorReviewRead, status_code=status.HTTP_201_CREATED)
def create_donor(payload: DonorReviewCreate, db: Session = Depends(get_db)) -> DonorReview:
    donor = DonorReview(**payload.model_dump())
    apply_risk_analysis(donor)
    db.add(donor)
    db.flush()
    create_task(
        db,
        task_type="Donor Review Task",
        title=f"Review donor eligibility for {donor.donor_id}",
        description=donor.recommended_action,
        related_record_id=str(donor.review_id),
        related_record_type="DonorReview",
        assigned_role_name="Clinical Reviewer",
        assigned_to_user_id=payload.reviewer_id,
        priority=donor.review_priority,
        due_date=datetime.now(UTC) + timedelta(hours=24 if donor.risk_score >= 50 else 48),
    )
    log_audit(
        db,
        user_id=payload.reviewer_id,
        action_type="CREATE_DONOR_INTAKE",
        table_name="fact_donor_review",
        record_id=str(donor.review_id),
        old_value=None,
        new_value=serialize_model(donor, AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(donor)
    return donor


@router.patch("/{review_id}", response_model=DonorReviewRead)
def update_donor(
    review_id: int, payload: DonorReviewUpdate, db: Session = Depends(get_db)
) -> DonorReview:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")

    old_value = serialize_model(donor, AUDIT_FIELDS)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(donor, field, value)

    if RISK_FIELDS.intersection(updates):
        apply_risk_analysis(donor)

    if updates.get("intake_status") in {"Approved", "Rejected", "Deferred"}:
        donor.reviewed_at = datetime.now(UTC)

    db.flush()
    log_audit(
        db,
        user_id=donor.reviewer_id,
        action_type="UPDATE_DONOR_REVIEW",
        table_name="fact_donor_review",
        record_id=str(donor.review_id),
        old_value=old_value,
        new_value=serialize_model(donor, AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(donor)
    return donor


@router.post("/{review_id}/decision", response_model=DonorReviewRead)
def record_decision(
    review_id: int, payload: DonorDecision, db: Session = Depends(get_db)
) -> DonorReview:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")

    old_value = serialize_model(donor, AUDIT_FIELDS)
    donor.intake_status = payload.intake_status
    donor.reviewer_id = payload.reviewer_id or donor.reviewer_id
    donor.rejection_reason = payload.rejection_reason
    donor.reviewed_at = datetime.now(UTC)
    db.flush()
    tasks = db.execute(
        select(WorkflowTask).where(
            WorkflowTask.related_record_type == "DonorReview",
            WorkflowTask.related_record_id == str(donor.review_id),
            WorkflowTask.status != "Completed",
        )
    ).scalars().all()
    for task in tasks:
        task.status = "Completed"
        task.completed_at = donor.reviewed_at

    log_audit(
        db,
        user_id=donor.reviewer_id,
        action_type=f"DONOR_{payload.intake_status.upper()}",
        table_name="fact_donor_review",
        record_id=str(donor.review_id),
        old_value=old_value,
        new_value=serialize_model(donor, AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(donor)
    return donor

