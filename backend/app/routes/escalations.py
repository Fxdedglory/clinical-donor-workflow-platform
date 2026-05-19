from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import EscalationEvent, User
from app.schemas import EscalationEventRead
from app.services.audit import log_audit
from app.services.escalations import evaluate_overdue_tasks

router = APIRouter(prefix="/api/escalations", tags=["Escalation Engine"])


@router.get("", response_model=list[EscalationEventRead])
def list_escalations(
    _: User = Depends(require_permission("escalations.manage")),
    db: Session = Depends(get_db),
) -> list[EscalationEvent]:
    return list(
        db.execute(select(EscalationEvent).order_by(desc(EscalationEvent.created_at))).scalars().all()
    )


@router.post("/evaluate", response_model=list[EscalationEventRead])
def evaluate(
    current_user: User = Depends(require_permission("escalations.manage")),
    db: Session = Depends(get_db),
) -> list[EscalationEvent]:
    created = evaluate_overdue_tasks(db)
    for event in created:
        db.flush()
        log_audit(
            db,
            user_id=current_user.user_id,
            action_type="CREATE_ESCALATION",
            table_name="fact_escalation_event",
            record_id=str(event.escalation_id),
            old_value=None,
            new_value={"trigger_reason": event.trigger_reason, "status": event.status},
        )
    db.commit()
    return created


@router.patch("/{escalation_id}/resolve", response_model=EscalationEventRead)
def resolve(
    escalation_id: int,
    current_user: User = Depends(require_permission("escalations.manage")),
    db: Session = Depends(get_db),
) -> EscalationEvent:
    event = db.get(EscalationEvent, escalation_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found")
    event.status = "Resolved"
    event.resolved_at = datetime.now(UTC)
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="RESOLVE_ESCALATION",
        table_name="fact_escalation_event",
        record_id=str(event.escalation_id),
        old_value={"status": "Open"},
        new_value={"status": "Resolved"},
    )
    db.commit()
    db.refresh(event)
    return event

