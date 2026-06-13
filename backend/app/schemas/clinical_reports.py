from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime as dt_datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.clinical_phi import DEFAULT_AGGREGATE_EXPORT_PROFILE, normalize_export_profile


class ReportMetricCard(BaseModel):
    label: str
    value: int | float
    tone: Literal["neutral", "success", "warning", "danger"] = "neutral"
    unit: str | None = None


class ReportSeriesPoint(BaseModel):
    label: str
    value: int | float
    date: dt_date | None = None
    group: str | None = None


class ReportWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class ReportBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class ReportFilterRequest(BaseModel):
    date_from: dt_date | None = None
    date_to: dt_date | None = None
    status: str | None = None
    module: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    actor: str | None = None
    workflow: str | None = None
    export_profile: str = DEFAULT_AGGREGATE_EXPORT_PROFILE

    @field_validator("status", "module", "entity_type", "entity_id", "actor", "workflow")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("export_profile")
    @classmethod
    def valid_export_profile(cls, value: str) -> str:
        return normalize_export_profile(value, default=DEFAULT_AGGREGATE_EXPORT_PROFILE)

    @model_validator(mode="after")
    def date_range_valid(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


class _ReportBase(BaseModel):
    date_from: dt_date | None = None
    date_to: dt_date | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    metrics: list[ReportMetricCard] = Field(default_factory=list)
    warnings: list[ReportWarning] = Field(default_factory=list)


class PatientThroughputReportResponse(_ReportBase):
    status_counts: dict[str, int] = Field(default_factory=dict)
    registrations_by_date: list[ReportSeriesPoint] = Field(default_factory=list)
    duplicate_warning_count: int = 0


class SchedulingUtilizationReportResponse(_ReportBase):
    provider_utilization: list[dict[str, Any]] = Field(default_factory=list)
    appointment_type_breakdown: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)


class ScreeningOutcomesReportResponse(_ReportBase):
    status_counts: dict[str, int] = Field(default_factory=dict)
    outcome_counts: dict[str, int] = Field(default_factory=dict)
    supervisor_review_count: int = 0
    override_count: int = 0


class DeferralReportResponse(_ReportBase):
    status_counts: dict[str, int] = Field(default_factory=dict)
    type_counts: dict[str, int] = Field(default_factory=dict)
    reason_counts: dict[str, int] = Field(default_factory=dict)
    patient_context: list[dict[str, Any]] = Field(default_factory=list)


class EncounterVolumeReportResponse(_ReportBase):
    status_counts: dict[str, int] = Field(default_factory=dict)
    note_status_counts: dict[str, int] = Field(default_factory=dict)
    signing_activity: list[ReportSeriesPoint] = Field(default_factory=list)


class OrdersResultsReportResponse(_ReportBase):
    order_status_counts: dict[str, int] = Field(default_factory=dict)
    result_status_counts: dict[str, int] = Field(default_factory=dict)


class CarePlanAgingReportResponse(_ReportBase):
    status_counts: dict[str, int] = Field(default_factory=dict)
    task_status_counts: dict[str, int] = Field(default_factory=dict)
    priority_counts: dict[str, int] = Field(default_factory=dict)


class BillingWorkQueueReportResponse(_ReportBase):
    claim_status_counts: dict[str, int] = Field(default_factory=dict)
    charge_status_counts: dict[str, int] = Field(default_factory=dict)
    denial_status_counts: dict[str, int] = Field(default_factory=dict)
    balances: dict[str, float] = Field(default_factory=dict)


class QualityTrendsReportResponse(_ReportBase):
    severity_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)


class AuditActivityReportResponse(_ReportBase):
    total_operations: int = 0
    workflow_counts: dict[str, int] = Field(default_factory=dict)
    actor_counts: dict[str, int] = Field(default_factory=dict)
    entity_type_counts: dict[str, int] = Field(default_factory=dict)
    operations: list[dict[str, Any]] = Field(default_factory=list)


class ClinicalReportsDashboardResponse(BaseModel):
    date_from: dt_date | None = None
    date_to: dt_date | None = None
    metrics: list[ReportMetricCard] = Field(default_factory=list)
    module_counts: dict[str, int | float] = Field(default_factory=dict)
    recent_audit_operations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[ReportWarning] = Field(default_factory=list)


class AnalyticsExportPreviewRequest(ReportFilterRequest):
    modules: list[str] = Field(default_factory=list)
    export_format: Literal["json", "csv"] = "json"
    include_detail: bool = False
    reason: str = "Generate analytics export"

    @field_validator("modules")
    @classmethod
    def clean_modules(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Reason is required")
        return stripped


class AnalyticsExportCommitRequest(AnalyticsExportPreviewRequest):
    preview_hash: str | None = None


class AnalyticsExportItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int | None = None
    module: str
    report_name: str
    row_count: int
    payload_metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    export_id: int | None = None
    export_number: str
    modules: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    date_from: dt_date | None = None
    date_to: dt_date | None = None
    export_format: str
    row_counts: dict[str, int] = Field(default_factory=dict)
    payload_metadata: dict[str, Any] = Field(default_factory=dict)
    status: str
    generated_at: dt_datetime
    generated_by: int | None = None
    items: list[AnalyticsExportItemResponse] = Field(default_factory=list)


class AnalyticsExportPreviewResponse(BaseModel):
    workflow: str = "reports.analytics_export"
    entity_type: str = "clinical_report_export"
    entity_id: str = "preview"
    preview_hash: str
    summary: str
    modules: list[str] = Field(default_factory=list)
    date_from: dt_date | None = None
    date_to: dt_date | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    row_counts: dict[str, int] = Field(default_factory=dict)
    export_format: str = "json"
    export_profile: str = DEFAULT_AGGREGATE_EXPORT_PROFILE
    warnings: list[ReportWarning] = Field(default_factory=list)
    blocking_issues: list[ReportBlockingIssue] = Field(default_factory=list)
    commit_required_header: str = "X-Confirm-Generation: true"


class AnalyticsExportCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    export: AnalyticsExportResponse
