from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import User
from app.services.dashboard import get_dashboard_metrics

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(
    _: User = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
) -> dict:
    return get_dashboard_metrics(db)

