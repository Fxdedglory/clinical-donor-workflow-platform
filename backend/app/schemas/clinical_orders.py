from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ORDER_STATUSES = Literal["draft", "ordered", "in_progress", "resulted", "cancelled"]
RESULT_STATUSES = Literal["normal", "abnormal", "critical", "corrected", "cancelled"]


class OrderWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class OrderBlockingIssue(BaseModel):
    issue_type: str
    message: str
    field: str | None = None


class OrderCatalogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    catalog_item_id: int
    code: str
    name: str
    order_type: str
    description: str = ""
    default_priority: str = "routine"
    specimen_type: str | None = None
    active: bool
    created_at: datetime
    updated_at: datetime


class OrderCreatePreviewRequest(BaseModel):
    patient_id: str
    encounter_id: int | None = None
    screening_session_id: int | None = None
    appointment_id: int | None = None
    catalog_item_id: int
    order_type: str | None = None
    priority: str = "routine"
    clinical_indication: str = ""
    ordering_provider: str = ""
    ordered_at: datetime | None = None
    reason: str = "Create clinical order"

    @field_validator("patient_id", "priority", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class OrderCreateRequest(OrderCreatePreviewRequest):
    preview_hash: str | None = None


class OrderStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: int
    order_id: int
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    changed_by: int | None = None
    reason: str
    notes: str


class OrderResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result_id: int
    order_id: int
    result_name: str
    result_value: str
    result_unit: str | None = None
    reference_range: str | None = None
    result_status: str
    abnormal_flag: bool
    critical_flag: bool
    requires_acknowledgement: bool
    resulted_at: datetime
    resulted_by: int | None = None
    notes: str
    corrected_from_result_id: int | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None


class OrderAcknowledgementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    acknowledgement_id: int
    order_id: int
    result_id: int | None = None
    acknowledged_at: datetime
    acknowledged_by: int | None = None
    acknowledgement_note: str
    created_at: datetime
    created_by: int | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    order_number: str
    patient_pk: int
    patient_id: str
    patient_name: str = ""
    encounter_id: int | None = None
    encounter_number: str | None = None
    screening_session_id: int | None = None
    screening_session_number: str | None = None
    appointment_id: int | None = None
    appointment_number: str | None = None
    catalog_item_id: int
    catalog_code: str
    catalog_name: str
    order_type: str
    priority: str
    status: str
    result_flag: str
    has_critical_unacknowledged: bool
    clinical_indication: str
    ordering_provider: str
    ordered_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by: int | None = None
    cancellation_reason: str | None = None
    source: str
    version: int
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    results: list[OrderResultResponse] = Field(default_factory=list)
    acknowledgements: list[OrderAcknowledgementResponse] = Field(default_factory=list)
    status_history: list[OrderStatusHistoryResponse] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class OrderPreviewResponse(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    blocking_issues: list[OrderBlockingIssue] = Field(default_factory=list)
    warnings: list[OrderWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class OrderResultPreviewRequest(BaseModel):
    result_name: str
    result_value: str
    result_unit: str | None = None
    reference_range: str | None = None
    result_status: RESULT_STATUSES = "normal"
    abnormal_flag: bool = False
    critical_flag: bool = False
    resulted_at: datetime | None = None
    notes: str = ""
    corrected_from_result_id: int | None = None
    reason: str = "Enter order result"

    @field_validator("result_name", "result_value", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class OrderResultCommitRequest(OrderResultPreviewRequest):
    preview_hash: str | None = None


class OrderAcknowledgePreviewRequest(BaseModel):
    result_id: int | None = None
    acknowledgement_note: str = ""
    reason: str = "Acknowledge critical result"

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Reason is required")
        return stripped


class OrderAcknowledgeCommitRequest(OrderAcknowledgePreviewRequest):
    preview_hash: str | None = None


class OrderCancelPreviewRequest(BaseModel):
    cancellation_reason: str
    reason: str = "Cancel clinical order"

    @field_validator("cancellation_reason", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class OrderCancelCommitRequest(OrderCancelPreviewRequest):
    preview_hash: str | None = None


class OrderCommitResponse(BaseModel):
    status: Literal["committed"] = "committed"
    operation_id: str
    audit_path: str
    order: OrderResponse | None = None
    result: OrderResultResponse | None = None
    acknowledgement: OrderAcknowledgementResponse | None = None
