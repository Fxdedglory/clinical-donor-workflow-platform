from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SchedulingConflict(BaseModel):
    conflict_type: str
    entity_type: str
    entity_id: str
    message: str
    blocking: bool = True


class SchedulingWarning(BaseModel):
    warning_type: str
    message: str
    field: str | None = None


class SchedulingResourceItem(BaseModel):
    id: int
    code: str
    name: str
    category: str
    status: str


class SchedulingResourceResponse(BaseModel):
    providers: list[SchedulingResourceItem] = Field(default_factory=list)
    rooms: list[SchedulingResourceItem] = Field(default_factory=list)
    equipment: list[SchedulingResourceItem] = Field(default_factory=list)


class AppointmentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_type_id: int
    type_code: str
    name: str
    default_duration_minutes: int
    requires_room: bool
    status: str


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: int
    appointment_number: str
    patient_id: str
    patient_pk: int
    patient_name: str = ""
    provider_id: int
    provider_name: str = ""
    room_id: int | None = None
    room_name: str | None = None
    appointment_type_id: int
    appointment_type_name: str = ""
    equipment_ids: list[int] = Field(default_factory=list)
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    reason: str
    cancellation_reason: str | None = None
    no_show_reason: str | None = None
    check_in_time: datetime | None = None
    created_at: datetime
    created_by: int | None = None
    updated_at: datetime
    updated_by: int | None = None
    source: str
    version: int


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentResponse]
    total: int


class AppointmentCreatePreviewRequest(BaseModel):
    patient_id: str
    provider_id: int
    room_id: int | None = None
    appointment_type_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str
    equipment_ids: list[int] = Field(default_factory=list)

    @field_validator("patient_id", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field is required")
        return stripped


class AppointmentCreateRequest(AppointmentCreatePreviewRequest):
    preview_hash: str | None = None


class AppointmentReschedulePreviewRequest(BaseModel):
    scheduled_start: datetime
    scheduled_end: datetime
    provider_id: int | None = None
    room_id: int | None = None
    appointment_type_id: int | None = None
    equipment_ids: list[int] | None = None
    reason: str = "Reschedule appointment"

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Reason is required")
        return stripped


class AppointmentRescheduleRequest(AppointmentReschedulePreviewRequest):
    preview_hash: str | None = None


class AppointmentCancelPreviewRequest(BaseModel):
    cancellation_reason: str
    reason: str = "Cancel appointment"

    @field_validator("cancellation_reason")
    @classmethod
    def required_cancellation_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Cancellation reason is required")
        return stripped


class AppointmentCancelRequest(AppointmentCancelPreviewRequest):
    preview_hash: str | None = None


class AppointmentCheckInPreviewRequest(BaseModel):
    check_in_time: datetime | None = None
    reason: str = "Check in appointment"


class AppointmentCheckInRequest(AppointmentCheckInPreviewRequest):
    preview_hash: str | None = None


class AppointmentNoShowPreviewRequest(BaseModel):
    no_show_reason: str
    reason: str = "Mark appointment no-show"

    @field_validator("no_show_reason")
    @classmethod
    def required_no_show_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("No-show reason is required")
        return stripped


class AppointmentNoShowRequest(AppointmentNoShowPreviewRequest):
    preview_hash: str | None = None


class AppointmentPreviewResponse(BaseModel):
    workflow: str
    entity_type: str = "appointment"
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    conflicts: list[SchedulingConflict] = Field(default_factory=list)
    warnings: list[SchedulingWarning] = Field(default_factory=list)
    summary: str
    changes: dict[str, object] = Field(default_factory=dict)
    selected_patient: str | None = None
    selected_provider: str | None = None
    selected_room: str | None = None
    selected_equipment: list[str] = Field(default_factory=list)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None


class AppointmentCommitResponse(BaseModel):
    appointment: AppointmentResponse
    operation_id: str
    audit_path: str
