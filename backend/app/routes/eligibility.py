from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import Donor, User
from app.services.eligibility_engine import (
    eligibility_analytics,
    eligibility_record_bundle,
    evaluate_donor_eligibility,
)

router = APIRouter(prefix="/api/eligibility", tags=["Donor Eligibility Decision Engine"])


@router.get("/analytics")
def analytics(
    current_user: User = Depends(require_permission("eligibility.read")),
    db: Session = Depends(get_db),
) -> dict:
    return eligibility_analytics(db)


@router.get("/donors/{donor_pk}/bundle")
def donor_bundle(
    donor_pk: int,
    current_user: User = Depends(require_permission("eligibility.read")),
    db: Session = Depends(get_db),
) -> dict:
    donor = db.get(Donor, donor_pk)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")
    return eligibility_record_bundle(db, donor)


@router.post("/donors/{donor_pk}/evaluate")
def evaluate_donor(
    donor_pk: int,
    category: str | None = None,
    current_user: User = Depends(require_permission("eligibility.review")),
    db: Session = Depends(get_db),
) -> dict:
    donor = db.get(Donor, donor_pk)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")
    result = evaluate_donor_eligibility(db, donor, category=category, user_id=current_user.user_id)
    db.commit()
    return result
