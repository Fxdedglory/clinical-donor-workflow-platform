from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vendor, VendorIncident
from app.schemas import VendorIncidentCreate, VendorIncidentRead, VendorIncidentUpdate, VendorRead
from app.services.audit import log_audit, serialize_model
from app.services.workflows import create_task

router = APIRouter(prefix="/api/vendors", tags=["Vendor SLA"])

INCIDENT_AUDIT_FIELDS = [
    "vendor_id",
    "ticket_number",
    "title",
    "severity",
    "status",
    "uptime_percent",
    "sla_breached",
    "opened_at",
    "resolved_at",
    "ticket_age_hours",
    "resolution_minutes",
    "impact_summary",
]


@router.get("", response_model=list[VendorRead])
def list_vendors(db: Session = Depends(get_db)) -> list[Vendor]:
    return list(db.execute(select(Vendor).order_by(Vendor.vendor_name)).scalars().all())


@router.get("/incidents", response_model=list[VendorIncidentRead])
def list_vendor_incidents(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[VendorIncident]:
    query = select(VendorIncident)
    if status_filter:
        query = query.where(VendorIncident.status == status_filter)
    query = query.order_by(desc(VendorIncident.opened_at)).limit(limit)
    return list(db.execute(query).scalars().all())


@router.post("/incidents", response_model=VendorIncidentRead, status_code=status.HTTP_201_CREATED)
def create_vendor_incident(
    payload: VendorIncidentCreate, db: Session = Depends(get_db)
) -> VendorIncident:
    incident = VendorIncident(**payload.model_dump())
    db.add(incident)
    db.flush()
    if incident.sla_breached:
        create_task(
            db,
            task_type="SLA Investigation Task",
            title=f"Investigate SLA breach {incident.ticket_number}",
            description=incident.impact_summary,
            related_record_id=str(incident.incident_id),
            related_record_type="VendorIncident",
            assigned_role_name="Vendor Operations Analyst",
            priority="Critical" if incident.severity == "Critical" else "High",
            workflow_state="Vendor SLA Investigation",
            queue_name="Vendor Operations Workbench",
            due_date=incident.opened_at,
        )
    log_audit(
        db,
        user_id=None,
        action_type="CREATE_VENDOR_INCIDENT",
        table_name="fact_vendor_incident",
        record_id=str(incident.incident_id),
        old_value=None,
        new_value=serialize_model(incident, INCIDENT_AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/incidents/{incident_id}", response_model=VendorIncidentRead)
def update_vendor_incident(
    incident_id: int, payload: VendorIncidentUpdate, db: Session = Depends(get_db)
) -> VendorIncident:
    incident = db.get(VendorIncident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor incident not found")

    old_value = serialize_model(incident, INCIDENT_AUDIT_FIELDS)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, field, value)

    db.flush()
    log_audit(
        db,
        user_id=None,
        action_type="UPDATE_VENDOR_INCIDENT",
        table_name="fact_vendor_incident",
        record_id=str(incident.incident_id),
        old_value=old_value,
        new_value=serialize_model(incident, INCIDENT_AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(incident)
    return incident

