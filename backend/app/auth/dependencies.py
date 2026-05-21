from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database import get_db
from app.models import RolePermission, User, UserSessionRecord
from app.services.security_audit import log_security_event, touch_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_user_permissions(db: Session, user: User) -> list[str]:
    if not user.role_id:
        return []
    rows = db.execute(
        select(RolePermission.permission_name).where(RolePermission.role_id == user.role_id)
    ).all()
    return [row[0] for row in rows]


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    raw_token = token or request.cookies.get("cdwp_access_token")
    if not raw_token:
        raise credentials_exception

    try:
        payload = decode_token(raw_token)
    except ValueError as exc:
        log_security_event(
            db,
            event_type="AUTH_TOKEN_INVALID",
            request=request,
            route=str(request.url.path),
            success=False,
        )
        db.commit()
        raise credentials_exception from exc

    if payload.get("type") != "access":
        raise credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception

    user = db.execute(select(User).where(User.username == subject)).scalar_one_or_none()
    if user is None or not user.is_active or user.approval_status not in {"Approved", "Active"}:
        raise credentials_exception

    session_id = payload.get("sid")
    if session_id:
        session = db.get(UserSessionRecord, session_id)
        now = datetime.now(UTC)
        if (
            session is None
            or session.user_id != user.user_id
            or not session.is_active
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            log_security_event(
                db,
                event_type="SESSION_INVALID",
                user_id=user.user_id,
                request=request,
                route=str(request.url.path),
                success=False,
            )
            db.commit()
            raise credentials_exception
        touch_session(session)
        db.commit()
    return user


def require_permission(permission_name: str) -> Callable:
    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        permissions = set(get_user_permissions(db, current_user))
        if permission_name not in permissions and "system.admin" not in permissions:
            log_security_event(
                db,
                event_type="ACCESS_DENIED",
                user_id=current_user.user_id,
                request=request,
                route=str(request.url.path),
                success=False,
                details={"permission": permission_name},
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_name}",
            )
        return current_user

    return dependency
