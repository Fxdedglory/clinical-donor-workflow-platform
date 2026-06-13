from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QualityWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class QualityBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class QualityEventLinkRequest(BaseModel):
    entity_type: str
    entity_id: str
    label: str | None = None

    @field_validator("entity_type", "entity_id")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("label")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class QualityEventCreatePreviewRequest(BaseModel):
    patient_id: str | None = None
    appointment_id: int | None = None
    screening_session_id: int | None = None
    encounter_id: int | None = None
    order_id: int | None = None
    order_result_id: int | None = None
    care_plan_id: int | None = None
    charge_id: int | None = None
    claim_id: int | None = None
    payment_id: int | None = None
    denial_id: int | None = None
    deviation_id: int | None = None
    capa_id: int | None = None
    category: str
    severity: str
    status: str = "open"
    owner: str | None = None
    due_date: date | None = None
    source_module: str = "clinical_quality"
    description: str
    links: list[QualityEventLinkRequest] = Field(default_factory=list)
    reason: str = "Create quality event"

    @field_validator("patient_id", "owner")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("category", "severity", "status", "source_module", "description", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class QualityEventCreateRequest(QualityEventCreatePreviewRequest):
    preview_hash: str | None = None


class QualityInvestigationPreviewRequest(BaseModel):
    note: str
    evidence_summary: str | None = None
    owner: str | None = None
    finding: str | None = None
    root_cause_category: str | None = None
    corrective_action_recommendation: str | None = None
    follow_up_due_date: date | None = None
    status_after: str = "investigation"
    reason: str = "Add quality investigation"

    @field_validator("note", "status_after", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("evidence_summary", "owner", "finding", "root_cause_category", "corrective_action_recommendation")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class QualityInvestigationCommitRequest(QualityInvestigationPreviewRequest):
    preview_hash: str | None = None


class QualityCapaLinkPreviewRequest(BaseModel):
    existing_capa_id: int | None = None
    create_planned_capa: bool = False
    root_cause: str | None = None
    corrective_action_owner: str | None = None
    due_date: date | None = None
    reason: str = "Link CAPA to quality event"

    @field_validator("root_cause", "corrective_action_owner")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @model_validator(mode="after")
    def capa_source_required(self):
        if self.existing_capa_id is None and not self.create_planned_capa:
            raise ValueError("Select an existing CAPA or request a planned CAPA link")
        return self


class QualityCapaLinkCommitRequest(QualityCapaLinkPreviewRequest):
    preview_hash: str | None = None


class QualityClosePreviewRequest(BaseModel):
    resolution_summary: str
    closure_reason: str
    reason: str = "Close quality event"

    @field_validator("resolution_summary", "closure_reason", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class QualityCloseCommitRequest(QualityClosePreviewRequest):
    preview_hash: str | None = None


class AdverseEventPreviewRequest(BaseModel):
    patient_id: str
    quality_event_id: int | None = None
    screening_session_id: int | None = None
    encounter_id: int | None = None
    order_id: int | None = None
    order_result_id: int | None = None
    care_plan_id: int | None = None
    event_type: str
    severity: str
    event_at: datetime
    description: str
    immediate_action_taken: str = ""
    reporter: str
    follow_up_required: bool = False
    status: str = "open"
    reason: str = "Create adverse event"

    @field_validator(
        "patient_id",
        "event_type",
        "severity",
        "description",
        "reporter",
        "status",
        "reason",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("immediate_action_taken")
    @classmethod
    def optional_text(cls, value: str) -> str:
        return value.strip()


class AdverseEventCommitRequest(AdverseEventPreviewRequest):
    preview_hash: str | None = None


class ComplianceExportPreviewRequest(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    modules: list[str] = Field(default_factory=list)
    actor: str | None = None
    workflow: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    include_quality_history: bool = True
    reason: str = "Generate compliance export"

    @field_validator("modules")
    @classmethod
    def clean_modules(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("actor", "workflow", "entity_type", "entity_id")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @model_validator(mode="after")
    def date_range_valid(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


class ComplianceExportCommitRequest(ComplianceExportPreviewRequest):
    preview_hash: str | None = None


class QualityStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    event_id: int
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    changed_by: int | None = None
    reason: str
    notes: str


class QualityEventLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    link_id: int
    event_id: int
    entity_type: str
    entity_id: str
    label: str | None = None
    created_at: datetime
    created_by: int | None = None


class QualityInvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: int
    event_id: int
    note: str
    evidence_summary: str | None = None
    owner: str | None = None
    finding: str | None = None
    root_cause_category: str | None = None
    corrective_action_recommendation: str | None = None
    follow_up_due_date: date | None = None
    created_at: datetime
    created_by: int | None = None


class QualityApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: int
    event_id: int
    approval_type: str
    status: str
    approved_at: datetime | None = None
    approved_by: int | None = None
    comments: str | None = None
    created_at: datetime
    created_by: int | None = None


class QualityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    event_number: str
    patient_pk: int | None = None
    patient_id: str | None = None
    patient_name: str | None = None
    appointment_id: int | None = None
    appointment_number: str | None = None
    screening_session_id: int | None = None
    screening_session_number: str | None = None
    encounter_id: int | None = None
    encounter_number: str | None = None
    order_id: int | None = None
    order_number: str | None = None
    order_result_id: int | None = None
    order_result_summary: str | None = None
    care_plan_id: int | None = None
    care_plan_number: str | None = None
    charge_id: int | None = None
    charge_number: str | None = None
    claim_id: int | None = None
    claim_number: str | None = None
    payment_id: int | None = None
    payment_reference: str | None = None
    denial_id: int | None = None
    denial_code: str | None = None
    deviation_id: int | None = None
    deviation_code: str | None = None
    capa_id: int | None = None
    capa_code: str | None = None
    category: str
    severity: str
    status: str
    owner: str | None = None
    due_date: date | None = None
    source_module: str
    description: str
    resolution_summary: str | None = None
    closure_reason: str | None = None
    closed_at: datetime | None = None
    closed_by: int | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    investigations: list[QualityInvestigationResponse] = Field(default_factory=list)
    approvals: list[QualityApprovalResponse] = Field(default_factory=list)
    links: list[QualityEventLinkResponse] = Field(default_factory=list)
    status_history: list[QualityStatusHistoryResponse] = Field(default_factory=list)


class QualityEventListResponse(BaseModel):
    events: list[QualityEventResponse] = Field(default_factory=list)
    total: int


class AdverseEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    adverse_event_id: int
    adverse_event_number: str
    quality_event_id: int | None = None
    quality_event_number: str | None = None
    patient_pk: int
    patient_id: str
    patient_name: str
    screening_session_id: int | None = None
    screening_session_number: str | None = None
    encounter_id: int | None = None
    encounter_number: str | None = None
    order_id: int | None = None
    order_number: str | None = None
    order_result_id: int | None = None
    order_result_summary: str | None = None
    care_plan_id: int | None = None
    care_plan_number: str | None = None
    event_type: str
    severity: str
    event_at: datetime
    description: str
    immediate_action_taken: str
    reporter: str
    follow_up_required: bool
    status: str
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class AdverseEventListResponse(BaseModel):
    adverse_events: list[AdverseEventResponse] = Field(default_factory=list)
    total: int


class ComplianceExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    export_id: int
    export_number: str
    date_from: date | None = None
    date_to: date | None = None
    modules: list[str] = Field(default_factory=list)
    criteria: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    status: str
    generated_at: datetime
    generated_by: int | None = None
    created_at: datetime
    created_by: int | None = None


class ComplianceExportListResponse(BaseModel):
    exports: list[ComplianceExportResponse] = Field(default_factory=list)
    total: int


class QualityPreviewResponse(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    blocking_issues: list[QualityBlockingIssue] = Field(default_factory=list)
    warnings: list[QualityWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class QualityCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    event: QualityEventResponse | None = None
    adverse_event: AdverseEventResponse | None = None
    compliance_export: ComplianceExportResponse | None = None


class AuditEvidenceResponse(BaseModel):
    operations: list[dict[str, Any]] = Field(default_factory=list)
    quality_status_history: list[dict[str, Any]] = Field(default_factory=list)
    compliance_exports: list[ComplianceExportResponse] = Field(default_factory=list)
    total_operations: int
    total_quality_history: int
    total_exports: int


class QualityDashboardResponse(BaseModel):
    total_events: int
    open_events: int
    overdue_events: int
    adverse_events_open: int
    pending_approval_events: int
    compliance_exports: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    recent_events: list[QualityEventResponse] = Field(default_factory=list)
    recent_audit_operations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[QualityWarning] = Field(default_factory=list)
