from datetime import datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClinicalAdminWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class ClinicalAdminBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class AdminConfigVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: int
    config_type: str
    config_key: str
    version: int
    status: str
    entity_type: str
    entity_id: str
    snapshot: dict[str, Any]
    change_summary: dict[str, Any]
    effective_from: datetime
    retired_at: datetime | None = None
    created_at: datetime
    created_by: int | None = None
    reason: str = ""


class ClinicalAdminPreviewResponse(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    summary: str
    status_before: str | None = None
    status_after: str | None = None
    current_config: dict[str, Any] = Field(default_factory=dict)
    proposed_config: dict[str, Any] = Field(default_factory=dict)
    changed_fields: list[str] = Field(default_factory=list)
    warnings: list[ClinicalAdminWarning] = Field(default_factory=list)
    blocking_issues: list[ClinicalAdminBlockingIssue] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    commit_required_header: str = "X-Confirm-Generation: true"


class ClinicalAdminCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    config_version: AdminConfigVersionResponse
    entity: dict[str, Any]


class _AdminRequestBase(BaseModel):
    reason: str = "Clinical administration configuration change"

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Reason is required")
        return stripped


class AppointmentTypeAdminPreviewRequest(_AdminRequestBase):
    appointment_type_id: int | None = None
    type_code: str
    name: str
    duration_minutes: int = 60
    category: str = "general"
    active: bool = True
    description: str = ""
    requires_room: bool = True

    @field_validator("type_code", "name", "category")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("description")
    @classmethod
    def optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("duration_minutes")
    @classmethod
    def positive_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Duration must be greater than zero")
        return value


class AppointmentTypeAdminCommitRequest(AppointmentTypeAdminPreviewRequest):
    preview_hash: str | None = None


class ProviderScheduleTemplatePreviewRequest(_AdminRequestBase):
    schedule_template_id: int | None = None
    provider_id: int
    weekday: int | None = None
    date_pattern: str = "weekly"
    start_time: time
    end_time: time
    location: str | None = None
    room_id: int | None = None
    active: bool = True

    @field_validator("date_pattern")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("location")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("weekday")
    @classmethod
    def weekday_range(cls, value: int | None) -> int | None:
        if value is not None and (value < 0 or value > 6):
            raise ValueError("Weekday must be between 0 and 6")
        return value

    @model_validator(mode="after")
    def times_valid(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ProviderScheduleTemplateCommitRequest(ProviderScheduleTemplatePreviewRequest):
    preview_hash: str | None = None


class ScreeningTemplateVersionPreviewRequest(_AdminRequestBase):
    template_key: str
    template_name: str
    version: int | None = None
    required_questions: list[dict[str, Any]] = Field(default_factory=list)
    active: bool = True

    @field_validator("template_key", "template_name")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class ScreeningTemplateVersionCommitRequest(ScreeningTemplateVersionPreviewRequest):
    preview_hash: str | None = None


class _RuleVersionPreviewRequest(_AdminRequestBase):
    rule_key: str
    rule_name: str
    rule_type: str
    severity: str = "medium"
    expression: str = ""
    criteria: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    explanation: str = ""
    version: int | None = None

    @field_validator("rule_key", "rule_name", "rule_type", "severity")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("expression", "explanation")
    @classmethod
    def optional_text(cls, value: str) -> str:
        return value.strip()


class EligibilityRuleVersionPreviewRequest(_RuleVersionPreviewRequest):
    rule_type: str = "eligibility"


class EligibilityRuleVersionCommitRequest(EligibilityRuleVersionPreviewRequest):
    preview_hash: str | None = None


class DeferralRuleVersionPreviewRequest(_RuleVersionPreviewRequest):
    rule_type: str = "deferral"


class DeferralRuleVersionCommitRequest(DeferralRuleVersionPreviewRequest):
    preview_hash: str | None = None


class NoteTemplateAdminPreviewRequest(_AdminRequestBase):
    template_id: int | None = None
    template_key: str
    name: str
    note_type: str = "clinical_note"
    body: str = ""
    sections: list[dict[str, Any]] = Field(default_factory=list)
    active: bool = True

    @field_validator("template_key", "name", "note_type")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("body")
    @classmethod
    def optional_text(cls, value: str) -> str:
        return value.strip()


class NoteTemplateAdminCommitRequest(NoteTemplateAdminPreviewRequest):
    preview_hash: str | None = None


class OrderCatalogAdminPreviewRequest(_AdminRequestBase):
    catalog_item_id: int | None = None
    code: str
    name: str
    order_type: str = "laboratory"
    description: str = ""
    default_priority: str = "routine"
    specimen_type: str | None = None
    active: bool = True

    @field_validator("code", "name", "order_type", "default_priority")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("description")
    @classmethod
    def optional_text_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("specimen_type")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class OrderCatalogAdminCommitRequest(OrderCatalogAdminPreviewRequest):
    preview_hash: str | None = None


class BillingCodeCatalogPreviewRequest(_AdminRequestBase):
    code_id: int | None = None
    code: str
    code_type: str = "internal"
    description: str
    default_amount: float = 0.0
    active: bool = True

    @field_validator("code", "code_type", "description")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @field_validator("default_amount")
    @classmethod
    def nonnegative_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Default amount must be non-negative")
        return round(value, 2)


class BillingCodeCatalogCommitRequest(BillingCodeCatalogPreviewRequest):
    preview_hash: str | None = None


class QualityCategoryPreviewRequest(_AdminRequestBase):
    category_id: int | None = None
    category_key: str
    category: str
    severity_mapping: dict[str, Any] = Field(default_factory=dict)
    closure_required: bool = False
    approval_required: bool = False
    active: bool = True

    @field_validator("category_key", "category")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class QualityCategoryCommitRequest(QualityCategoryPreviewRequest):
    preview_hash: str | None = None


class ApprovalPathStepRequest(BaseModel):
    step_order: int = 1
    role: str | None = None
    permission: str | None = None
    required: bool = True
    active: bool = True

    @field_validator("role", "permission")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("step_order")
    @classmethod
    def positive_step(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("step_order must be greater than zero")
        return value


class ApprovalPathPreviewRequest(_AdminRequestBase):
    path_id: int | None = None
    workflow: str
    path_name: str
    steps: list[ApprovalPathStepRequest] = Field(default_factory=list)
    active: bool = True

    @field_validator("workflow", "path_name")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped

    @model_validator(mode="after")
    def steps_required(self):
        if not self.steps:
            raise ValueError("At least one approval step is required")
        return self


class ApprovalPathCommitRequest(ApprovalPathPreviewRequest):
    preview_hash: str | None = None


class NotificationTemplatePreviewRequest(_AdminRequestBase):
    notification_template_id: int | None = None
    workflow: str
    channel: str = "in_app"
    subject: str
    body: str
    active: bool = True

    @field_validator("workflow", "channel", "subject", "body")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class NotificationTemplateCommitRequest(NotificationTemplatePreviewRequest):
    preview_hash: str | None = None


class ClinicalRbacRoleResponse(BaseModel):
    role: str
    permissions: list[str] = Field(default_factory=list)
    can_read_admin: bool = False
    can_manage_admin: bool = False
    external: bool = False


class ClinicalRbacOverviewResponse(BaseModel):
    read_permissions: list[str] = Field(default_factory=list)
    manage_permissions: list[str] = Field(default_factory=list)
    roles: list[ClinicalRbacRoleResponse] = Field(default_factory=list)


class ClinicalAdminDashboardResponse(BaseModel):
    total_config_versions: int
    active_config_versions: int
    configuration_counts: dict[str, int] = Field(default_factory=dict)
    recent_versions: list[AdminConfigVersionResponse] = Field(default_factory=list)
    recent_audit_operations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[ClinicalAdminWarning] = Field(default_factory=list)
