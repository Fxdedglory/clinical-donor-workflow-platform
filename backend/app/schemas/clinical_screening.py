from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCREENING_STATUSES = Literal[
    "not_started",
    "in_progress",
    "pending_eligibility",
    "requires_supervisor_review",
    "eligible",
    "eligible_with_conditions",
    "temporarily_deferred",
    "permanently_deferred",
    "cancelled",
]

SCREENING_OUTCOMES = Literal[
    "eligible",
    "eligible_with_conditions",
    "temporarily_deferred",
    "permanently_deferred",
    "requires_supervisor_review",
]


class ScreeningWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class ScreeningBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class EligibilityRuleResult(BaseModel):
    rule_id: int | None = None
    rule_name: str
    rule_category: str
    outcome: str
    severity: str
    requires_review: bool = False
    explanation: str
    source: str = "clinical_screening"


class ScreeningQuestion(BaseModel):
    question_key: str
    label: str
    answer_type: str = "boolean"
    required: bool = True
    risk_when: Any | None = None
    guidance: str = ""


class ScreeningTemplateResponse(BaseModel):
    template_id: str
    name: str
    version: str
    questions: list[ScreeningQuestion]


class ScreeningSessionCreatePreviewRequest(BaseModel):
    patient_id: str
    appointment_id: int | None = None
    template_id: str = "minimal_donor_screening_v1"
    reason: str = "Start donor screening session"

    @field_validator("patient_id", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class ScreeningSessionCreateRequest(ScreeningSessionCreatePreviewRequest):
    preview_hash: str | None = None


class ScreeningAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    question_key: str
    answer_value: dict[str, Any]
    notes: str
    created_at: datetime
    updated_at: datetime


class ScreeningVitalsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vitals_id: int
    height_cm: float | None = None
    weight_kg: float
    temperature_c: float
    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    pulse: int
    respiration_rate: int | None = None
    oxygen_saturation: float | None = None
    captured_at: datetime
    captured_by: int | None = None
    notes: str


class DeferralResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deferral_id: int
    deferral_number: str
    session_id: int
    patient_pk: int
    patient_id: str
    donor_pk: int | None = None
    deferral_type: str
    reason: str
    starts_at: datetime
    ends_at: datetime | None = None
    status: str
    created_at: datetime
    created_by: int | None = None


class ScreeningOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outcome_id: int
    proposed_outcome: str | None = None
    committed_outcome: str | None = None
    original_outcome: str | None = None
    override_outcome: str | None = None
    deferral_type: str | None = None
    supervisor_review_required: bool
    blocking_issues: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    rule_results: list[dict[str, Any]] = Field(default_factory=list)
    reason: str
    created_at: datetime
    created_by: int | None = None


class ScreeningSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    session_number: str
    patient_pk: int
    patient_id: str
    patient_name: str = ""
    donor_pk: int | None = None
    appointment_id: int | None = None
    appointment_number: str | None = None
    template_id: str
    status: str
    current_outcome: str | None = None
    supervisor_review_required: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    reason: str
    source: str
    version: int
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    answers: list[ScreeningAnswerResponse] = Field(default_factory=list)
    vitals: list[ScreeningVitalsResponse] = Field(default_factory=list)
    outcomes: list[ScreeningOutcomeResponse] = Field(default_factory=list)
    deferrals: list[DeferralResponse] = Field(default_factory=list)


class ScreeningSessionListResponse(BaseModel):
    sessions: list[ScreeningSessionResponse]
    total: int


class ScreeningSessionPreviewResponse(BaseModel):
    workflow: str
    entity_type: str = "screening_session"
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    blocking_issues: list[ScreeningBlockingIssue] = Field(default_factory=list)
    warnings: list[ScreeningWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class ScreeningQuestionnairePreviewRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class ScreeningQuestionnaireCommitRequest(ScreeningQuestionnairePreviewRequest):
    preview_hash: str | None = None
    reason: str = "Commit donor screening questionnaire"


class ScreeningVitalsPreviewRequest(BaseModel):
    height_cm: float | None = None
    weight_kg: float | None = None
    temperature_c: float | None = None
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    pulse: int | None = None
    respiration_rate: int | None = None
    oxygen_saturation: float | None = None
    captured_at: datetime | None = None
    notes: str = ""


class ScreeningVitalsCommitRequest(ScreeningVitalsPreviewRequest):
    preview_hash: str | None = None
    reason: str = "Commit donor screening vitals"


class EligibilityPreviewRequest(BaseModel):
    category: str | None = None
    reason: str = "Preview donor eligibility"


class EligibilityPreviewResponse(BaseModel):
    workflow: str = "screening.eligibility_preview"
    entity_type: str = "screening_session"
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    proposed_outcome: str
    blocking_issues: list[ScreeningBlockingIssue] = Field(default_factory=list)
    warnings: list[ScreeningWarning] = Field(default_factory=list)
    rules_evaluated: list[EligibilityRuleResult] = Field(default_factory=list)
    missing_required_answers: list[str] = Field(default_factory=list)
    missing_required_vitals: list[str] = Field(default_factory=list)
    recommended_deferral_type: str | None = None
    supervisor_review_required: bool = False
    summary: str
    existing_engine_outcome: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)


class ScreeningResultCommitRequest(BaseModel):
    outcome: SCREENING_OUTCOMES
    reason: str
    preview_hash: str | None = None
    deferral_type: Literal["temporary", "permanent"] | None = None
    deferral_ends_at: datetime | None = None

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Reason is required")
        return stripped


class ScreeningOverridePreviewRequest(BaseModel):
    original_outcome: SCREENING_OUTCOMES
    override_outcome: SCREENING_OUTCOMES
    reason: str

    @field_validator("reason")
    @classmethod
    def required_override_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Override reason is required")
        return stripped


class ScreeningOverrideCommitRequest(ScreeningOverridePreviewRequest):
    preview_hash: str | None = None


class ScreeningCommitResponse(BaseModel):
    session: ScreeningSessionResponse
    operation_id: str
    audit_path: str
    deferral: DeferralResponse | None = None
