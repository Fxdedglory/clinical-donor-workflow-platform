from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DonorReviewBase(BaseModel):
    donor_id: str = Field(..., examples=["DNR-2026-00042"])
    donor_name: str
    age: int | None = Field(default=None, ge=0, le=120)
    blood_type: str | None = Field(default=None, examples=["O+"])
    infectious_history: bool = False
    travel_risk: bool = False
    missing_required_fields: bool = False
    clinical_notes: str = ""
    attachment_placeholder: str = ""


class DonorReviewCreate(DonorReviewBase):
    reviewer_id: int | None = None


class DonorReviewUpdate(BaseModel):
    donor_name: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    blood_type: str | None = None
    infectious_history: bool | None = None
    travel_risk: bool | None = None
    missing_required_fields: bool | None = None
    clinical_notes: str | None = None
    attachment_placeholder: str | None = None
    intake_status: str | None = None
    reviewer_id: int | None = None
    rejection_reason: str | None = None


class DonorDecision(BaseModel):
    intake_status: str = Field(..., examples=["Approved", "Rejected", "Deferred"])
    reviewer_id: int | None = None
    rejection_reason: str | None = None
    ai_override: bool = False
    ai_override_reason: str | None = None


class DonorReviewRead(DonorReviewBase):
    model_config = ConfigDict(from_attributes=True)

    review_id: int
    risk_flags: list[str]
    risk_score: int
    risk_level: str
    recommended_action: str
    review_priority: str
    intake_status: str
    reviewer_id: int | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None

