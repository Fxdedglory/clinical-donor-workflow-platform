from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BillingWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class BillingBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class InsuranceVerificationPreviewRequest(BaseModel):
    patient_id: str
    patient_insurance_id: int | None = None
    verification_status: str = "verified"
    verified_at: datetime | None = None
    payer_name: str | None = None
    plan_name: str | None = None
    member_id: str | None = None
    group_number: str | None = None
    coverage_start: date | None = None
    coverage_end: date | None = None
    notes: str | None = None
    reason: str = "Verify insurance"

    @field_validator("patient_id", "verification_status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("payer_name", "plan_name", "member_id", "group_number", "notes")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class InsuranceVerificationCommitRequest(InsuranceVerificationPreviewRequest):
    preview_hash: str | None = None


class ChargeCapturePreviewRequest(BaseModel):
    patient_id: str
    encounter_id: int | None = None
    order_id: int | None = None
    order_result_id: int | None = None
    care_plan_id: int | None = None
    care_plan_task_id: int | None = None
    service_date: date
    code: str
    code_type: str = "internal"
    description: str
    quantity: float = 1.0
    unit_amount: float
    status: str = "captured"
    reason: str = "Capture charge"

    @field_validator("patient_id", "code", "code_type", "description", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Quantity must be greater than zero")
        return round(value, 2)

    @field_validator("unit_amount")
    @classmethod
    def nonnegative_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Unit amount must be non-negative")
        return round(value, 2)


class ChargeCaptureCommitRequest(ChargeCapturePreviewRequest):
    preview_hash: str | None = None


class ClaimDraftPreviewRequest(BaseModel):
    patient_id: str | None = None
    charge_ids: list[int] = Field(default_factory=list, min_length=1)
    patient_insurance_id: int | None = None
    status: str = "ready_for_review"
    diagnosis_code: str | None = None
    reason: str = "Create claim draft"

    @field_validator("patient_id", "diagnosis_code")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class ClaimDraftCommitRequest(ClaimDraftPreviewRequest):
    preview_hash: str | None = None


class PaymentPostPreviewRequest(BaseModel):
    claim_id: int
    payment_amount: float
    adjustment_amount: float = 0.0
    payment_method: str = "eft"
    payer_type: str = "insurance"
    reference_number: str | None = None
    posted_at: datetime | None = None
    notes: str | None = None
    reason: str = "Post payment"

    @field_validator("payment_method", "payer_type", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("reference_number", "notes")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("payment_amount", "adjustment_amount")
    @classmethod
    def nonnegative_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Amount must be non-negative")
        return round(value, 2)

    @model_validator(mode="after")
    def payment_or_adjustment_required(self):
        if self.payment_amount + self.adjustment_amount <= 0:
            raise ValueError("Payment or adjustment amount is required")
        return self


class PaymentPostCommitRequest(PaymentPostPreviewRequest):
    preview_hash: str | None = None


class DenialCapturePreviewRequest(BaseModel):
    claim_id: int
    claim_line_id: int | None = None
    denial_code: str | None = None
    denial_reason: str
    status: str = "open"
    assigned_to: str | None = None
    due_date: date | None = None
    resolution_notes: str | None = None
    reason: str = "Capture denial"

    @field_validator("denial_reason", "status", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("denial_code", "assigned_to", "resolution_notes")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class DenialCaptureCommitRequest(DenialCapturePreviewRequest):
    preview_hash: str | None = None


class BillingStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    billing_account_id: int | None = None
    claim_id: int | None = None
    charge_id: int | None = None
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    changed_by: int | None = None
    reason: str
    notes: str


class InsuranceVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verification_id: int
    patient_pk: int
    patient_id: str
    patient_name: str
    patient_insurance_id: int | None = None
    verification_status: str
    verified_at: datetime | None = None
    verified_by: int | None = None
    payer_name: str | None = None
    plan_name: str | None = None
    member_id: str | None = None
    group_number: str | None = None
    coverage_start: date | None = None
    coverage_end: date | None = None
    notes: str | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class ChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    charge_id: int
    charge_number: str
    billing_account_id: int
    account_number: str
    patient_pk: int
    patient_id: str
    patient_name: str
    encounter_id: int | None = None
    encounter_number: str | None = None
    order_id: int | None = None
    order_number: str | None = None
    order_result_id: int | None = None
    order_result_summary: str | None = None
    care_plan_id: int | None = None
    care_plan_number: str | None = None
    care_plan_task_id: int | None = None
    care_plan_task_title: str | None = None
    service_date: date
    code: str
    code_type: str
    description: str
    quantity: float
    unit_amount: float
    total_amount: float
    status: str
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class ClaimLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_id: int
    claim_id: int
    charge_id: int
    charge_number: str
    line_number: int
    code: str
    code_type: str
    description: str
    quantity: float
    unit_amount: float
    line_amount: float
    diagnosis_code: str | None = None
    status: str
    created_at: datetime
    created_by: int | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: int
    claim_id: int
    claim_number: str
    billing_account_id: int
    account_number: str
    patient_pk: int
    patient_id: str
    patient_name: str
    payment_amount: float
    adjustment_amount: float
    payment_method: str
    payer_type: str
    reference_number: str | None = None
    posted_at: datetime
    posted_by: int | None = None
    notes: str | None = None
    created_at: datetime
    created_by: int | None = None


class DenialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    denial_id: int
    claim_id: int
    claim_number: str
    claim_line_id: int | None = None
    denial_code: str | None = None
    denial_reason: str
    status: str
    assigned_to: str | None = None
    due_date: date | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    resolved_by: int | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim_id: int
    claim_number: str
    billing_account_id: int
    account_number: str
    patient_pk: int
    patient_id: str
    patient_name: str
    patient_insurance_id: int | None = None
    payer_name: str | None = None
    status: str
    total_amount: float
    paid_amount: float
    adjustment_amount: float
    balance: float
    submitted_at: datetime | None = None
    submitted_by: int | None = None
    closed_at: datetime | None = None
    closed_by: int | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    lines: list[ClaimLineResponse] = Field(default_factory=list)
    payments: list[PaymentResponse] = Field(default_factory=list)
    denials: list[DenialResponse] = Field(default_factory=list)
    status_history: list[BillingStatusHistoryResponse] = Field(default_factory=list)


class BillingAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    account_number: str
    patient_pk: int
    patient_id: str
    patient_name: str
    primary_insurance_id: int | None = None
    payer_name: str | None = None
    status: str
    total_charges: float
    total_payments: float
    total_adjustments: float
    balance: float
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    charges: list[ChargeResponse] = Field(default_factory=list)
    claims: list[ClaimResponse] = Field(default_factory=list)
    payments: list[PaymentResponse] = Field(default_factory=list)
    status_history: list[BillingStatusHistoryResponse] = Field(default_factory=list)


class BillingListResponse(BaseModel):
    accounts: list[BillingAccountResponse] = Field(default_factory=list)
    total: int


class ChargeListResponse(BaseModel):
    charges: list[ChargeResponse] = Field(default_factory=list)
    total: int


class ClaimListResponse(BaseModel):
    claims: list[ClaimResponse] = Field(default_factory=list)
    total: int


class BillingWorkQueueResponse(BaseModel):
    accounts: list[BillingAccountResponse] = Field(default_factory=list)
    charges: list[ChargeResponse] = Field(default_factory=list)
    claims: list[ClaimResponse] = Field(default_factory=list)
    payments: list[PaymentResponse] = Field(default_factory=list)
    denials: list[DenialResponse] = Field(default_factory=list)
    insurance_verifications: list[InsuranceVerificationResponse] = Field(default_factory=list)


class BillingPreviewResponse(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    blocking_issues: list[BillingBlockingIssue] = Field(default_factory=list)
    warnings: list[BillingWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class BillingCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    account: BillingAccountResponse | None = None
    insurance_verification: InsuranceVerificationResponse | None = None
    charge: ChargeResponse | None = None
    claim: ClaimResponse | None = None
    payment: PaymentResponse | None = None
    denial: DenialResponse | None = None
