from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role, WorkflowTask
from app.services.notifications import notify_role


def get_role_id(db: Session, role_name: str) -> int | None:
    role = db.execute(select(Role).where(Role.role_name == role_name)).scalar_one_or_none()
    return role.role_id if role else None


def create_task(
    db: Session,
    *,
    task_type: str,
    title: str,
    related_record_id: str,
    related_record_type: str,
    assigned_role_name: str | None = None,
    assigned_to_user_id: int | None = None,
    description: str = "",
    priority: str = "Routine",
    status: str = "Assigned",
    due_date: datetime | None = None,
) -> WorkflowTask:
    assigned_role_id = get_role_id(db, assigned_role_name) if assigned_role_name else None
    task = WorkflowTask(
        task_type=task_type,
        title=title,
        description=description,
        assigned_to_user_id=assigned_to_user_id,
        assigned_role_id=assigned_role_id,
        priority=priority,
        status=status,
        due_date=due_date,
        related_record_id=related_record_id,
        related_record_type=related_record_type,
    )
    db.add(task)
    if assigned_role_name:
        notify_role(
            db,
            role_name=assigned_role_name,
            title=f"New {task_type}",
            message=title,
            notification_type="Task Assignment",
            priority=priority,
        )
    return task


def complete_task(task: WorkflowTask) -> None:
    task.status = "Completed"
    task.completed_at = datetime.now(UTC)

