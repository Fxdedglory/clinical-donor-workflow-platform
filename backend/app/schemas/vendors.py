from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_id: int
    vendor_name: str
    system_name: str
    criticality: str
    sla_target_percent: float
    business_owner: str
    status: str


class VendorIncidentCreate(BaseModel):
    vendor_id: int
    ticket_number: str
    title: str
    severity: str
    status: str = "Open"
    uptime_percent: float = 99.9
    sla_breached: bool = False
    opened_at: datetime
    resolved_at: datetime | None = None
    ticket_age_hours: float = 0
    resolution_minutes: int | None = None
    impact_summary: str = ""


class VendorIncidentUpdate(BaseModel):
    title: str | None = None
    severity: str | None = None
    status: str | None = None
    uptime_percent: float | None = None
    sla_breached: bool | None = None
    resolved_at: datetime | None = None
    ticket_age_hours: float | None = None
    resolution_minutes: int | None = None
    impact_summary: str | None = None


class VendorIncidentRead(VendorIncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    incident_id: int

