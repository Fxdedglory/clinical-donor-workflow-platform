from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DonorReview
from app.schemas import RiskAnalysisRequest, RiskAnalysisResponse
from app.services.ai_governance import governed_analysis

router = APIRouter(prefix="/api/risk-analysis", tags=["AI Risk Analysis"])


@router.post("", response_model=RiskAnalysisResponse)
def analyze_payload(payload: RiskAnalysisRequest, db: Session = Depends(get_db)) -> RiskAnalysisResponse:
    analysis = governed_analysis(db, **payload.model_dump())
    return RiskAnalysisResponse(
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        recommended_action=analysis.recommended_action,
        flagged_conditions=analysis.flagged_conditions,
        review_priority=analysis.review_priority,
        triggered_rules=analysis.triggered_rules,
        score_contributions=analysis.score_contributions,
        escalation_reasons=analysis.escalation_reasons,
        workflow_impact=analysis.workflow_impact,
        confidence_level=analysis.confidence_level,
        historical_comparison=analysis.historical_comparison,
    )


@router.get("/{review_id}", response_model=RiskAnalysisResponse)
def analyze_existing_review(review_id: int, db: Session = Depends(get_db)) -> RiskAnalysisResponse:
    donor = db.get(DonorReview, review_id)
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor review not found")
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
    return RiskAnalysisResponse(
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
        recommended_action=analysis.recommended_action,
        flagged_conditions=analysis.flagged_conditions,
        review_priority=analysis.review_priority,
        triggered_rules=analysis.triggered_rules,
        score_contributions=analysis.score_contributions,
        escalation_reasons=analysis.escalation_reasons,
        workflow_impact=analysis.workflow_impact,
        confidence_level=analysis.confidence_level,
        historical_comparison=analysis.historical_comparison,
    )

