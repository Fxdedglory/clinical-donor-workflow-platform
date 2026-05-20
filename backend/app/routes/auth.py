from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.config import settings
from app.database import get_db
from app.models import User
from app.schemas.auth import RefreshTokenRequest, TokenResponse, UserSession
from app.services.audit import log_audit

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


def _session_for_user(db: Session, user: User) -> UserSession:
    role_name = user.role_ref.role_name if user.role_ref else user.role
    permissions = get_user_permissions(db, user)
    return UserSession(
        user_id=user.user_id,
        username=user.username or "",
        full_name=user.full_name,
        email=user.email,
        role_name=role_name,
        permissions=permissions,
        last_login=user.last_login,
    )


def _token_response(db: Session, user: User) -> TokenResponse:
    session = _session_for_user(db, user)
    return TokenResponse(
        access_token=create_access_token(
            subject=session.username,
            role=session.role_name,
            permissions=session.permissions,
        ),
        refresh_token=create_refresh_token(subject=session.username),
        expires_in_minutes=settings.access_token_expire_minutes,
        user=session,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.execute(select(User).where(User.username == form_data.username)).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    old_login = user.last_login.isoformat() if user.last_login else None
    user.last_login = datetime.now(UTC)
    log_audit(
        db,
        user_id=user.user_id,
        action_type="USER_LOGIN",
        table_name="dim_user",
        record_id=str(user.user_id),
        old_value={"last_login": old_login},
        new_value={"last_login": user.last_login.isoformat(), "username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(user)
    return _token_response(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.execute(select(User).where(User.username == token_payload.get("sub"))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return _token_response(db, user)


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="USER_LOGOUT",
        table_name="dim_user",
        record_id=str(current_user.user_id),
        old_value=None,
        new_value={"username": current_user.username},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "logged_out"}


@router.get("/me", response_model=UserSession)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserSession:
    return _session_for_user(db, current_user)


@router.patch("/me", response_model=UserSession)
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSession:
    old_value = {"full_name": current_user.full_name, "email": current_user.email}
    if payload.email and payload.email != current_user.email:
        existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        current_user.email = payload.email
    if payload.full_name:
        current_user.full_name = payload.full_name
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_PROFILE",
        table_name="dim_user",
        record_id=str(current_user.user_id),
        old_value=old_value,
        new_value={"full_name": current_user.full_name, "email": current_user.email},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(current_user)
    return _session_for_user(db, current_user)


@router.patch("/me/password")
def update_password(
    payload: PasswordUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(payload.new_password)
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_PASSWORD",
        table_name="dim_user",
        record_id=str(current_user.user_id),
        old_value=None,
        new_value={"username": current_user.username},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "password_updated"}
