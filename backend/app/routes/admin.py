from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.auth.security import get_password_hash, validate_password_policy
from app.database import get_db
from app.models import Role, RoleResponsibility, User
from app.schemas import RoleRead, RoleResponsibilityRead, UserCreate, UserRead, UserUpdate
from app.services.audit import log_audit, serialize_model
from app.services.security_audit import log_security_event
from app.services.system_health import collect_system_health

router = APIRouter(prefix="/api/admin", tags=["System Administration"])

USER_FIELDS = [
    "username",
    "full_name",
    "display_name",
    "email",
    "role_id",
    "role",
    "department",
    "is_active",
    "account_type",
    "user_type",
    "organization_id",
    "is_internal",
    "is_external",
    "external_user_flag",
    "approval_status",
    "identity_provider",
    "mfa_enabled",
]


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> list[Role]:
    return list(db.execute(select(Role).order_by(Role.role_name)).scalars().all())


@router.get("/role-responsibilities", response_model=list[RoleResponsibilityRead])
def role_responsibilities(
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> list[RoleResponsibilityRead]:
    rows = db.execute(
        select(Role.role_name, RoleResponsibility)
        .join(RoleResponsibility, RoleResponsibility.role_id == Role.role_id)
        .order_by(Role.role_name)
    ).all()
    return [
        RoleResponsibilityRead(
            role_name=role_name,
            job_description=item.job_description,
            responsibilities=item.responsibilities,
            assigned_workflows=item.assigned_workflows,
            operational_kpis=item.operational_kpis,
        )
        for role_name, item in rows
    ]


@router.get("/system-health")
def system_health(
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> dict:
    payload = collect_system_health(db)
    db.commit()
    return payload


@router.get("/users", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.execute(select(User).order_by(User.role, User.full_name)).scalars().all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> User:
    role = db.get(Role, payload.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    password_issues = validate_password_policy(payload.password, username=payload.username, email=payload.email)
    if password_issues:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_issues)

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role_id=payload.role_id,
        role=role.role_name,
        department=payload.department,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="CREATE_USER",
        table_name="dim_user",
        record_id=str(user.user_id),
        old_value=None,
        new_value=serialize_model(user, USER_FIELDS),
    )
    log_security_event(
        db,
        event_type="USER_CREATED",
        user_id=current_user.user_id,
        details={"target_user_id": user.user_id, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    old_value = serialize_model(user, USER_FIELDS)
    updates = payload.model_dump(exclude_unset=True)
    if "password" in updates:
        new_password = updates.pop("password")
        password_issues = validate_password_policy(new_password, username=user.username, email=user.email)
        if password_issues:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_issues)
        user.password_history = [user.hashed_password, *(user.password_history or [])][:5] if user.hashed_password else []
        user.hashed_password = get_password_hash(new_password)
    if "role_id" in updates and updates["role_id"] is not None:
        role = db.get(Role, updates["role_id"])
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        user.role = role.role_name
    for field, value in updates.items():
        setattr(user, field, value)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_USER",
        table_name="dim_user",
        record_id=str(user.user_id),
        old_value=old_value,
        new_value=serialize_model(user, USER_FIELDS),
    )
    log_security_event(
        db,
        event_type="USER_MODIFIED",
        user_id=current_user.user_id,
        details={"target_user_id": user.user_id, "fields": sorted(updates.keys())},
    )
    db.commit()
    db.refresh(user)
    return user
