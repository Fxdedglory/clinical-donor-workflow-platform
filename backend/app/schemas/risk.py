from pydantic import BaseModel, Field


class RiskAnalysisRequest(BaseModel):
    donor_name: str | None = Field(default=None)
    age: int | None = Field(default=None, ge=0, le=120)
    blood_type: str | None = None
    infectious_history: bool = False
    travel_risk: bool = False
    missing_required_fields: bool = False
    clinical_notes: str = ""


class RiskAnalysisResponse(BaseModel):
    risk_score: int
    risk_level: str
    recommended_action: str
    flagged_conditions: list[str]
    review_priority: str
    triggered_rules: list[dict] = Field(default_factory=list)
    score_contributions: list[dict] = Field(default_factory=list)
    escalation_reasons: list[str] = Field(default_factory=list)
    workflow_impact: str = ""
    confidence_level: float = 0.0
    historical_comparison: dict = Field(default_factory=dict)

