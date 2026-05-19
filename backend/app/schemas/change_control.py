from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChangeControlCreate(BaseModel):
    request_id: str
    requested_by_id: int | None = None
    sop_id: int | None = None
    reason: str
    risk_level: str
    approval_status: str = "Draft"
    capa_required: bool = False
    investigation_notes: str = ""
    implementation_due_date: datetime | None = None


class ChangeControlUpdate(BaseModel):
    reason: str | None = None
    risk_level: str | None = None
    approval_status: str | None = None
    capa_required: bool | None = None
    investigation_notes: str | None = None
    implementation_due_date: datetime | None = None
    approved_at: datetime | None = None


class ChangeControlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    change_id: int
    request_id: str
    requested_by_id: int | None
    sop_id: int | None
    reason: str
    risk_level: str
    approval_status: str
    capa_required: bool
    investigation_notes: str
    implementation_due_date: datetime | None
    created_at: datetime
    approved_at: datetime | None

