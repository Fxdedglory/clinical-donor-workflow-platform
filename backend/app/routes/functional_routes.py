from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.services.functional_routes import (
    enterprise_search,
    functional_navigation,
    resolve_route_context,
)

router = APIRouter(prefix="/api/routes", tags=["Functional Route Engine"])


@router.get("/navigation")
def navigation(
    preview_role_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return functional_navigation(db, current_user, preview_role_id)


@router.get("/resolve")
def resolve(
    route: str = Query(default="/"),
    preview_role_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return resolve_route_context(
        db,
        current_user=current_user,
        route=route,
        preview_role_id=preview_role_id,
    )


@router.get("/search")
def search(
    q: str = Query(default="", min_length=0),
    preview_role_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    return enterprise_search(db, current_user=current_user, query=q, preview_role_id=preview_role_id)
