from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database import get_db
from app.models import RolePermission, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_user_permissions(db: Session, user: User) -> list[str]:
    if not user.role_id:
        return []
    rows = db.execute(
        select(RolePermission.permission_name).where(RolePermission.role_id == user.role_id)
    ).all()
    return [row[0] for row in rows]


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise credentials_exception from exc

    if payload.get("type") != "access":
        raise credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception

    user = db.execute(select(User).where(User.username == subject)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_permission(permission_name: str) -> Callable:
    def dependency(
        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        permissions = set(get_user_permissions(db, current_user))
        if permission_name not in permissions and "system.admin" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_name}",
            )
        return current_user

    return dependency

