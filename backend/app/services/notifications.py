from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, Role, User


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    priority: str = "Normal",
    workflow_task_id: int | None = None,
    related_record_type: str | None = None,
    related_record_id: str | None = None,
    action_route: str | None = None,
    workflow_context: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        workflow_task_id=workflow_task_id,
        related_record_type=related_record_type,
        related_record_id=related_record_id,
        action_route=action_route,
        workflow_context=workflow_context or {},
    )
    db.add(notification)
    return notification


def notify_role(
    db: Session,
    *,
    role_name: str,
    title: str,
    message: str,
    notification_type: str,
    priority: str = "Normal",
    workflow_task_id: int | None = None,
    related_record_type: str | None = None,
    related_record_id: str | None = None,
    action_route: str | None = None,
    workflow_context: dict | None = None,
) -> list[Notification]:
    role = db.execute(select(Role).where(Role.role_name == role_name)).scalar_one_or_none()
    if not role:
        return []
    users = db.execute(
        select(User).where(User.role_id == role.role_id, User.is_active.is_(True))
    ).scalars().all()
    return [
        create_notification(
            db,
            user_id=user.user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            workflow_task_id=workflow_task_id,
            related_record_type=related_record_type,
            related_record_id=related_record_id,
            action_route=action_route,
            workflow_context=workflow_context,
        )
        for user in users
    ]
