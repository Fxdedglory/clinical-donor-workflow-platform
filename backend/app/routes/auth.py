from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.auth.security import (
    create_access_token,
    create_mfa_challenge_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    password_needs_rehash,
    validate_password_policy,
    verify_password,
)
from app.core.config import settings
from app.database import get_db
from app.models import (
    MFAConfiguration,
    PasswordResetToken,
    SidebarState,
    User,
    UserPreference,
    UserSessionRecord,
)
from app.schemas.auth import RefreshTokenRequest, TokenResponse, UserSession
from app.services.audit import log_audit
from app.services.email import EmailMessage, EmailType, send_email
from app.services.security_audit import (
    hash_token,
    log_security_event,
    new_session_id,
    request_device,
    request_ip,
    revoke_session,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])

MFA_REQUIRED_ROLES = {
    "System Administrator",
    "Business Technology Analyst",
    "Operations Manager",
    "Quality Assurance Specialist",
}
ACCESS_COOKIE = "cdwp_access_token"
REFRESH_COOKIE = "cdwp_refresh_token"


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    display_name: str | None = None
    email: str | None = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class MFAVerifyRequest(BaseModel):
    mfa_token: str
    code: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class AccessRequest(BaseModel):
    full_name: str
    email: str
    organization_name: str
    request_type: Literal["Partner", "Supplier"] = "Partner"
    organization_type: str | None = None
    requested_role: str | None = None
    business_reason: str


class PreferenceUpdate(BaseModel):
    sidebar_collapsed: bool | None = None
    last_route: str | None = None
    recently_viewed: list[dict] | None = None
    pinned_records: list[dict] | None = None
    notification_preferences: dict | None = None
    theme_preferences: dict | None = None


def _session_for_user(db: Session, user: User) -> UserSession:
    role_name = user.role_ref.role_name if user.role_ref else user.role
    permissions = get_user_permissions(db, user)
    return UserSession(
        user_id=user.user_id,
        username=user.username or "",
        full_name=user.full_name,
        display_name=user.display_name,
        email=user.email,
        role_name=role_name,
        permissions=permissions,
        last_login=user.last_login,
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    for cookie_name in [ACCESS_COOKIE, REFRESH_COOKIE]:
        response.delete_cookie(cookie_name, path="/", samesite=settings.cookie_samesite, secure=settings.cookie_secure)


def _raw_access_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1]
    return request.cookies.get(ACCESS_COOKIE)


def _mfa_required_for(db: Session, user: User) -> bool:
    config = db.execute(
        select(MFAConfiguration).where(MFAConfiguration.user_id == user.user_id)
    ).scalar_one_or_none()
    return bool(user.mfa_enabled or (config and config.required_by_policy) or user.role in MFA_REQUIRED_ROLES)


def _create_session_response(
    db: Session,
    *,
    user: User,
    request: Request,
    response: Response,
) -> TokenResponse:
    session = _session_for_user(db, user)
    session_id = new_session_id()
    refresh_token = create_refresh_token(subject=session.username, session_id=session_id)
    access_token = create_access_token(
        subject=session.username,
        role=session.role_name,
        permissions=session.permissions,
        session_id=session_id,
    )
    db.add(
        UserSessionRecord(
            session_id=session_id,
            user_id=user.user_id,
            refresh_token_hash=hash_token(refresh_token),
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent"),
            device=request_device(request),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.refresh_token_expire_minutes),
        )
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_minutes=settings.access_token_expire_minutes,
        user=session,
    )


def _password_policy_or_422(password: str, user: User) -> None:
    issues = validate_password_policy(password, username=user.username, email=user.email)
    if issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=issues)


def _update_password_hash(user: User, password: str) -> None:
    history = list(user.password_history or [])
    if user.hashed_password:
        history = [user.hashed_password, *history][:5]
    user.hashed_password = get_password_hash(password)
    user.password_history = history
    user.password_changed_at = datetime.now(UTC)
    user.password_expires_at = datetime.now(UTC) + timedelta(days=settings.password_expiration_days)


def _sidebar_state_for(db: Session, user: User) -> SidebarState:
    state = db.execute(select(SidebarState).where(SidebarState.user_id == user.user_id)).scalar_one_or_none()
    if state:
        return state
    state = SidebarState(user_id=user.user_id)
    db.add(state)
    db.flush()
    return state


def _preference_for(db: Session, user: User, key: str) -> UserPreference:
    preference = db.execute(
        select(UserPreference).where(
            UserPreference.user_id == user.user_id,
            UserPreference.preference_key == key,
        )
    ).scalar_one_or_none()
    if preference:
        return preference
    preference = UserPreference(user_id=user.user_id, preference_key=key, preference_value={})
    db.add(preference)
    db.flush()
    return preference


def _preference_payload(db: Session, user: User) -> dict:
    state = _sidebar_state_for(db, user)
    preferences = {
        row.preference_key: row.preference_value
        for row in db.execute(select(UserPreference).where(UserPreference.user_id == user.user_id)).scalars()
    }
    return {
        "sidebar_collapsed": state.sidebar_collapsed,
        "last_route": state.last_route,
        "recently_viewed": state.recently_viewed,
        "pinned_records": state.pinned_records,
        "notification_preferences": preferences.get(
            "notification_preferences",
            {
                "digest": True,
                "sla_alerts": True,
                "qms_alerts": True,
                "ai_governance_alerts": True,
            },
        ),
        "theme_preferences": preferences.get("theme_preferences", {"mode": "light"}),
    }


@router.post("/login", response_model=None)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict | TokenResponse:
    user = db.execute(select(User).where(User.username == form_data.username)).scalar_one_or_none()
    now = datetime.now(UTC)
    if user and user.locked_until and user.locked_until > now:
        log_security_event(
            db,
            event_type="LOGIN_LOCKED",
            user_id=user.user_id,
            request=request,
            success=False,
            details={"username": form_data.username},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account temporarily locked")

    if (
        not user
        or not user.is_active
        or user.is_archived
        or not verify_password(form_data.password, user.hashed_password)
    ):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.max_failed_login_attempts:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
            log_security_event(
                db,
                event_type="FAILED_LOGIN",
                user_id=user.user_id,
                request=request,
                success=False,
                details={"username": form_data.username, "failed_count": user.failed_login_count},
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.approval_status not in {"Approved", "Active"}:
        log_security_event(
            db,
            event_type="LOGIN_BLOCKED_APPROVAL_STATUS",
            user_id=user.user_id,
            request=request,
            success=False,
            details={"approval_status": user.approval_status},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User approval is not active")

    if password_needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(form_data.password)

    user.failed_login_count = 0
    user.locked_until = None
    old_login = user.last_login.isoformat() if user.last_login else None
    user.last_login = now

    if _mfa_required_for(db, user):
        log_security_event(
            db,
            event_type="MFA_CHALLENGE_CREATED",
            user_id=user.user_id,
            request=request,
            details={"method": "TOTP_OR_EMAIL_OTP"},
        )
        send_email(
            db,
            EmailMessage(
                to_email=user.email,
                subject="Clinical Donor Workflow MFA verification",
                body="A sign-in attempt requires MFA verification. Use your authenticator or approved OTP method.",
                email_type=EmailType.MFA_VERIFICATION,
                metadata={"method": "TOTP_OR_EMAIL_OTP"},
            ),
            user_id=user.user_id,
            request=request,
        )
        db.commit()
        return {
            "mfa_required": True,
            "mfa_token": create_mfa_challenge_token(subject=user.username or ""),
            "methods": ["totp", "email_otp"],
            "message": "MFA verification required.",
        }

    token_payload = _create_session_response(db, user=user, request=request, response=response)
    log_audit(
        db,
        user_id=user.user_id,
        action_type="USER_LOGIN",
        table_name="dim_user",
        record_id=str(user.user_id),
        old_value={"last_login": old_login},
        new_value={"last_login": user.last_login.isoformat(), "username": user.username},
        ip_address=request_ip(request),
    )
    log_security_event(db, event_type="LOGIN", user_id=user.user_id, request=request)
    db.commit()
    return token_payload


@router.post("/mfa/verify", response_model=TokenResponse)
def verify_mfa(
    payload: MFAVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        token_payload = decode_token(payload.mfa_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA challenge") from exc
    if token_payload.get("type") != "mfa":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA challenge")
    user = db.execute(select(User).where(User.username == token_payload.get("sub"))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    if payload.code != settings.mfa_dev_bypass_code:
        log_security_event(
            db,
            event_type="MFA_VERIFICATION_FAILED",
            user_id=user.user_id,
            request=request,
            success=False,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    config = db.execute(
        select(MFAConfiguration).where(MFAConfiguration.user_id == user.user_id)
    ).scalar_one_or_none()
    if config:
        config.is_enabled = True
        config.verified_at = datetime.now(UTC)
    user.mfa_enabled = True
    user.last_login = datetime.now(UTC)
    token_response = _create_session_response(db, user=user, request=request, response=response)
    log_security_event(
        db,
        event_type="MFA_VERIFICATION",
        user_id=user.user_id,
        request=request,
        details={"method": config.method if config else "TOTP"},
    )
    db.commit()
    return token_response


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    refresh = payload.refresh_token if payload else request.cookies.get(REFRESH_COOKIE)
    if not refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        token_payload = decode_token(refresh)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.execute(select(User).where(User.username == token_payload.get("sub"))).scalar_one_or_none()
    session_id = token_payload.get("sid")
    session_record = db.get(UserSessionRecord, session_id) if session_id else None
    if (
        not user
        or not user.is_active
        or not session_record
        or not session_record.is_active
        or session_record.revoked_at is not None
        or session_record.refresh_token_hash != hash_token(refresh)
        or session_record.expires_at <= datetime.now(UTC)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive session")

    session = _session_for_user(db, user)
    new_refresh = create_refresh_token(subject=session.username, session_id=session_record.session_id)
    access = create_access_token(
        subject=session.username,
        role=session.role_name,
        permissions=session.permissions,
        session_id=session_record.session_id,
    )
    session_record.refresh_token_hash = hash_token(new_refresh)
    session_record.last_seen_at = datetime.now(UTC)
    session_record.expires_at = datetime.now(UTC) + timedelta(minutes=settings.refresh_token_expire_minutes)
    _set_auth_cookies(response, access, new_refresh)
    log_security_event(db, event_type="TOKEN_REFRESH", user_id=user.user_id, request=request)
    db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in_minutes=settings.access_token_expire_minutes,
        user=session,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    token = _raw_access_token(request)
    if token:
        try:
            payload = decode_token(token)
            revoke_session(db, db.get(UserSessionRecord, payload.get("sid")))
        except ValueError:
            pass
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="USER_LOGOUT",
        table_name="dim_user",
        record_id=str(current_user.user_id),
        old_value=None,
        new_value={"username": current_user.username},
        ip_address=request_ip(request),
    )
    log_security_event(db, event_type="LOGOUT", user_id=current_user.user_id, request=request)
    _clear_auth_cookies(response)
    db.commit()
    return {"status": "logged_out"}


@router.post("/logout-all")
def logout_all_sessions(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    sessions = db.execute(
        select(UserSessionRecord).where(
            UserSessionRecord.user_id == current_user.user_id,
            UserSessionRecord.is_active.is_(True),
        )
    ).scalars()
    for session in sessions:
        revoke_session(db, session)
    _clear_auth_cookies(response)
    log_security_event(db, event_type="SESSION_REVOCATION", user_id=current_user.user_id, request=request)
    db.commit()
    return {"status": "sessions_revoked"}


@router.get("/me", response_model=UserSession)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserSession:
    return _session_for_user(db, current_user)


@router.get("/me/preferences")
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    payload = _preference_payload(db, current_user)
    db.commit()
    return payload


@router.patch("/me/preferences")
def update_preferences(
    payload: PreferenceUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    state = _sidebar_state_for(db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    if "sidebar_collapsed" in updates:
        state.sidebar_collapsed = bool(updates["sidebar_collapsed"])
    if updates.get("last_route"):
        state.last_route = updates["last_route"]
    if "recently_viewed" in updates and updates["recently_viewed"] is not None:
        state.recently_viewed = updates["recently_viewed"][:12]
    if "pinned_records" in updates and updates["pinned_records"] is not None:
        state.pinned_records = updates["pinned_records"][:20]
    if "notification_preferences" in updates and updates["notification_preferences"] is not None:
        preference = _preference_for(db, current_user, "notification_preferences")
        preference.preference_value = updates["notification_preferences"]
    if "theme_preferences" in updates and updates["theme_preferences"] is not None:
        preference = _preference_for(db, current_user, "theme_preferences")
        preference.preference_value = updates["theme_preferences"]

    log_security_event(
        db,
        event_type="USER_PREFERENCE_UPDATE",
        user_id=current_user.user_id,
        request=request,
        details={"fields": sorted(updates.keys())},
    )
    db.commit()
    return _preference_payload(db, current_user)


@router.patch("/me", response_model=UserSession)
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSession:
    old_value = {
        "full_name": current_user.full_name,
        "display_name": current_user.display_name,
        "email": current_user.email,
    }
    if payload.email and payload.email != current_user.email:
        existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        current_user.email = payload.email
    if payload.full_name:
        current_user.full_name = payload.full_name
    if payload.display_name is not None:
        current_user.display_name = payload.display_name or None
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_PROFILE",
        table_name="dim_user",
        record_id=str(current_user.user_id),
        old_value=old_value,
        new_value={
            "full_name": current_user.full_name,
            "display_name": current_user.display_name,
            "email": current_user.email,
        },
        ip_address=request_ip(request),
    )
    log_security_event(db, event_type="PROFILE_UPDATE", user_id=current_user.user_id, request=request)
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
        log_security_event(
            db,
            event_type="PASSWORD_CHANGE_FAILED",
            user_id=current_user.user_id,
            request=request,
            success=False,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    _password_policy_or_422(payload.new_password, current_user)
    for old_hash in [current_user.hashed_password, *(current_user.password_history or [])]:
        if old_hash and verify_password(payload.new_password, old_hash):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="New password cannot reuse recent passwords.",
            )
    _update_password_hash(current_user, payload.new_password)
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_PASSWORD",
        table_name="dim_user",
        record_id=str(current_user.user_id),
        old_value=None,
        new_value={"username": current_user.username},
        ip_address=request_ip(request),
    )
    log_security_event(db, event_type="PASSWORD_CHANGE", user_id=current_user.user_id, request=request)
    db.commit()
    return {"status": "password_updated"}


@router.post("/password-reset/request")
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    demo_token = None
    if user and user.is_active:
        reset = PasswordResetToken(
            user_id=user.user_id,
            token_hash=f"pending_{uuid4().hex}",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        db.add(reset)
        db.flush()
        demo_token = create_password_reset_token(subject=user.username or "", reset_id=reset.reset_id)
        reset.token_hash = hash_token(demo_token)
        log_security_event(
            db,
            event_type="PASSWORD_RESET_REQUEST",
            user_id=user.user_id,
            request=request,
            details={"reset_id": reset.reset_id},
        )
        reset_url = f"{settings.app_base_url.rstrip('/')}/reset-password?token={demo_token}"
        send_email(
            db,
            EmailMessage(
                to_email=user.email,
                subject="Clinical Donor Workflow password reset",
                body=(
                    "A password reset was requested for your Clinical Donor Workflow account. "
                    f"Use this single-use link within 30 minutes: {reset_url}"
                ),
                email_type=EmailType.PASSWORD_RESET,
                metadata={"reset_id": reset.reset_id},
            ),
            user_id=user.user_id,
            request=request,
        )
    db.commit()
    response = {"status": "If the email matches an account in our system, a reset link will be sent."}
    if demo_token and settings.app_env != "prod":
        response["demo_reset_token"] = demo_token
    return response


EXTERNAL_ACCESS_ROLE_BY_REQUEST_TYPE = {
    "Partner": "Partner External User",
    "Supplier": "Supplier External User",
}


@router.post("/access-request/")
@router.post("/access-request")
def request_access(
    payload: AccessRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    request_type = payload.request_type
    auto_assigned_role = EXTERNAL_ACCESS_ROLE_BY_REQUEST_TYPE[request_type]
    log_security_event(
        db,
        event_type="ACCESS_REQUEST_SUBMITTED",
        user_id=existing.user_id if existing else None,
        request=request,
        route="/api/auth/access-request",
        details={
            "full_name": payload.full_name,
            "email": payload.email,
            "organization_name": payload.organization_name,
            "request_type": request_type,
            "organization_type": request_type,
            "auto_assigned_role": auto_assigned_role,
            "requested_role_ignored": payload.requested_role if payload.requested_role != auto_assigned_role else None,
            "business_reason": payload.business_reason,
            "existing_user": bool(existing),
            "future_identity_provider": "Microsoft Entra ID / Entra B2B",
        },
    )
    db.commit()
    return {
        "status": "access_request_received",
        "message": f"Your {request_type.lower()} access request has been recorded for administrator review.",
    }


@router.post("/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        token_payload = decode_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token") from exc
    if token_payload.get("type") != "password_reset":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token")
    reset = db.get(PasswordResetToken, token_payload.get("reset_id"))
    user = db.execute(select(User).where(User.username == token_payload.get("sub"))).scalar_one_or_none()
    if (
        not reset
        or not user
        or reset.user_id != user.user_id
        or reset.used_at is not None
        or reset.expires_at <= datetime.now(UTC)
        or reset.token_hash != hash_token(payload.token)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token")
    _password_policy_or_422(payload.new_password, user)
    _update_password_hash(user, payload.new_password)
    user.last_password_reset_at = datetime.now(UTC)
    reset.used_at = datetime.now(UTC)
    sessions = db.execute(select(UserSessionRecord).where(UserSessionRecord.user_id == user.user_id)).scalars()
    for session in sessions:
        revoke_session(db, session)
    log_security_event(
        db,
        event_type="PASSWORD_RESET_COMPLETED",
        user_id=user.user_id,
        request=request,
        details={"reset_id": reset.reset_id},
    )
    db.commit()
    return {"status": "password_reset_completed"}
