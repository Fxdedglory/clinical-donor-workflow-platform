from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import ChangeControl, User
from app.schemas import ChangeControlCreate, ChangeControlRead, ChangeControlUpdate
from app.services.audit import log_audit, serialize_model
from app.services.workflows import create_task

router = APIRouter(prefix="/api/change-control", tags=["QMS Change Control"])

AUDIT_FIELDS = [
    "request_id",
    "requested_by_id",
    "sop_id",
    "reason",
    "risk_level",
    "approval_status",
    "capa_required",
    "investigation_notes",
    "implementation_due_date",
    "approved_at",
]


@router.get("", response_model=list[ChangeControlRead])
def list_change_requests(
    approval_status: str | None = None,
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("qms.manage")),
    db: Session = Depends(get_db),
) -> list[ChangeControl]:
    query = select(ChangeControl)
    if approval_status:
        query = query.where(ChangeControl.approval_status == approval_status)
    query = query.order_by(desc(ChangeControl.created_at)).limit(limit)
    return list(db.execute(query).scalars().all())


@router.post("", response_model=ChangeControlRead, status_code=status.HTTP_201_CREATED)
def create_change_request(
    payload: ChangeControlCreate,
    current_user: User = Depends(require_permission("qms.manage")),
    db: Session = Depends(get_db),
) -> ChangeControl:
    request = ChangeControl(**payload.model_dump())
    db.add(request)
    db.flush()
    create_task(
        db,
        task_type="SOP Deviation Investigation",
        title=f"QMS review for {request.request_id}",
        description=request.reason,
        related_record_id=str(request.change_id),
        related_record_type="ChangeControl",
        assigned_role_name="Quality Assurance Specialist",
        priority=request.risk_level,
        workflow_state="CAPA Investigation" if request.capa_required else "QA Investigation",
        queue_name="QA Investigation Workbench",
        due_date=request.implementation_due_date,
    )
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="CREATE_CHANGE_REQUEST",
        table_name="fact_change_control",
        record_id=str(request.change_id),
        old_value=None,
        new_value=serialize_model(request, AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(request)
    return request


@router.patch("/{change_id}", response_model=ChangeControlRead)
def update_change_request(
    change_id: int,
    payload: ChangeControlUpdate,
    current_user: User = Depends(require_permission("qms.manage")),
    db: Session = Depends(get_db),
) -> ChangeControl:
    request = db.get(ChangeControl, change_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")

    old_value = serialize_model(request, AUDIT_FIELDS)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(request, field, value)

    if updates.get("approval_status") == "Approved" and not request.approved_at:
        request.approved_at = datetime.now(UTC)

    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_CHANGE_REQUEST",
        table_name="fact_change_control",
        record_id=str(request.change_id),
        old_value=old_value,
        new_value=serialize_model(request, AUDIT_FIELDS),
    )
    db.commit()
    db.refresh(request)
    return request

