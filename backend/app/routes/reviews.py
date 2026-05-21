from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import DonorReview, User
from app.schemas import DonorReviewRead

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])

ACTIVE_DONOR_STATES = [
    "Draft Intake",
    "Pending Intake Validation",
    "Pending Clinical Review",
    "Clinical Review In Progress",
    "Pending Additional Information",
    "High Risk Escalation",
    "QA Investigation",
    "CAPA Investigation",
    "Clinical Re-Review",
    "Operations Escalation",
]


@router.get("", response_model=list[DonorReviewRead])
def list_reviews(
    queue: str = Query(default="active", pattern="^(active|closed|all)$"),
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("donors.read")),
    db: Session = Depends(get_db),
) -> list[DonorReview]:
    query = select(DonorReview)
    if queue == "active":
        query = query.where(DonorReview.intake_status.in_(ACTIVE_DONOR_STATES))
    elif queue == "closed":
        query = query.where(DonorReview.intake_status.in_(["Approved", "Rejected"]))
    query = query.order_by(desc(DonorReview.risk_score), DonorReview.created_at).limit(limit)
    return list(db.execute(query).scalars().all())

