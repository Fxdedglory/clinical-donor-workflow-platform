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
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
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
        )
        for user in users
    ]

