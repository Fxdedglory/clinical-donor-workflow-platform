from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_permission
from app.database import get_db
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationRead
from app.services.notifications import create_notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == current_user.user_id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    return list(db.execute(query.order_by(desc(Notification.created_at)).limit(limit)).scalars().all())


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    count = db.execute(
        select(func.count(Notification.notification_id)).where(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
    ).scalar()
    return {"unread_count": int(count or 0)}


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def post_notification(
    payload: NotificationCreate,
    _: User = Depends(require_permission("notifications.manage")),
    db: Session = Depends(get_db),
) -> Notification:
    notification = create_notification(db, **payload.model_dump())
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification

