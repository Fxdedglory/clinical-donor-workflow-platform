from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DonorReview
from app.schemas import RiskAnalysisRequest, RiskAnalysisResponse
from app.services.risk_engine import analyze_donor_risk

router = APIRouter(prefix="/api/risk-analysis", tags=["AI Risk Analysis"])


@router.post("", response_model=RiskAnalysisResponse)
def analyze_payload(payload: RiskAnalysisRequest) -> RiskAnalysisResponse:
    analysis = analyze_donor_risk(**payload.model_dump())
    return RiskAnalysisResponse(
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        recommended_action=analysis.recommended_action,
        flagged_conditions=analysis.flagged_conditions,
        review_priority=analysis.review_priority,
    )


@router.get("/{review_id}", response_model=RiskAnalysisResponse)
def analyze_existing_review(review_id: int, db: Session = Depends(get_db)) -> RiskAnalysisResponse:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")
    analysis = analyze_donor_risk(
        donor_name=donor.donor_name,
        age=donor.age,
        blood_type=donor.blood_type,
        infectious_history=donor.infectious_history,
        travel_risk=donor.travel_risk,
        missing_required_fields=donor.missing_required_fields,
        clinical_notes=donor.clinical_notes,
    )
    return RiskAnalysisResponse(
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        recommended_action=analysis.recommended_action,
        flagged_conditions=analysis.flagged_conditions,
        review_priority=analysis.review_priority,
    )

