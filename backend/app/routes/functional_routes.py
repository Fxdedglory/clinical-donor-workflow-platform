from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.services.functional_routes import (
    enterprise_search,
    functional_navigation,
    resolve_route_context,
)
from app.services.security_audit import log_security_event

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
    request: Request,
    route: str = Query(default="/"),
    preview_role_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    context = resolve_route_context(
        db,
        current_user=current_user,
        route=route,
        preview_role_id=preview_role_id,
    )
    if context.get("kind") == "detail":
        log_security_event(
            db,
            event_type="ROUTE_DETAIL_ACCESS",
            user_id=current_user.user_id,
            request=request,
            details={
                "route": context.get("route_path"),
                "entity_type": context.get("entity_type"),
                "record_id": context.get("record_id"),
            },
        )
        db.commit()
    return context


@router.get("/search")
def search(
    q: str = Query(default="", min_length=0),
    preview_role_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    return enterprise_search(db, current_user=current_user, query=q, preview_role_id=preview_role_id)
