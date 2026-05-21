from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select

from app.models import User


def is_external_user(user: User) -> bool:
    return bool(user.is_external or user.external_user_flag or user.account_type in {"supplier", "partner", "external"})


def require_organization(user: User) -> int:
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="External account is not linked to an approved organization.",
        )
    return user.organization_id


def can_cross_organization(user: User) -> bool:
    return not is_external_user(user)


def apply_org_scope(query: Select, model: Any, user: User) -> Select:
    if can_cross_organization(user) or not hasattr(model, "organization_id"):
        return query
    return query.where(model.organization_id == require_organization(user))


def ensure_org_access(user: User, record: Any, *, not_found_detail: str = "Record not found") -> None:
    if can_cross_organization(user) or not hasattr(record, "organization_id"):
        return
    if getattr(record, "organization_id", None) != require_organization(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)


def ensure_external_self_or_org(user: User, target_user: User) -> None:
    if can_cross_organization(user):
        return
    if target_user.user_id == user.user_id:
        return
    if target_user.organization_id == require_organization(user):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
