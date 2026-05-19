from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.auth.security import get_password_hash
from app.database import get_db
from app.models import Role, RoleResponsibility, User
from app.schemas import RoleRead, RoleResponsibilityRead, UserCreate, UserRead, UserUpdate
from app.services.audit import log_audit, serialize_model

router = APIRouter(prefix="/api/admin", tags=["System Administration"])

USER_FIELDS = ["username", "full_name", "email", "role_id", "role", "department", "is_active"]


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    _: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> list[Role]:
    return list(db.execute(select(Role).order_by(Role.role_name)).scalars().all())


@router.get("/role-responsibilities", response_model=list[RoleResponsibilityRead])
def role_responsibilities(
    _: User = Depends(require_permission("dashboard.view")),
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
        user.hashed_password = get_password_hash(updates.pop("password"))
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
    db.commit()
    db.refresh(user)
    return user

