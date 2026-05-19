from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EscalationEvent, WorkflowTask
from app.services.notifications import notify_role


def evaluate_overdue_tasks(db: Session) -> list[EscalationEvent]:
    now = datetime.now(UTC)
    tasks = db.execute(
        select(WorkflowTask).where(
            WorkflowTask.due_date.is_not(None),
            WorkflowTask.due_date < now,
            WorkflowTask.status.in_(["Pending", "Assigned", "In Progress", "Blocked"]),
        )
    ).scalars().all()

    created: list[EscalationEvent] = []
    for task in tasks:
        existing = db.execute(
            select(EscalationEvent).where(
                EscalationEvent.related_task_id == task.task_id,
                EscalationEvent.status == "Open",
            )
        ).scalar_one_or_none()
        if existing:
            continue
        task.status = "Escalated"
        task.priority = "Critical"
        task.escalation_level += 1
        event = EscalationEvent(
            related_task_id=task.task_id,
            escalation_type="Overdue Task",
            trigger_reason=f"{task.task_type} exceeded due date {task.due_date.isoformat()}",
            status="Open",
        )
        db.add(event)
        notify_role(
            db,
            role_name="Operations Manager",
            title="Task Escalated",
            message=f"{task.title} is overdue and has been escalated.",
            notification_type="Escalation",
            priority="Critical",
        )
        created.append(event)
    return created

