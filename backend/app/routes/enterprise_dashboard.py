from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import User
from app.services.enterprise_dashboard import enterprise_metrics

router = APIRouter(prefix="/api/enterprise-dashboard", tags=["Enterprise Dashboards"])


@router.get("")
def dashboard(
    _: User = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
) -> dict:
    return enterprise_metrics(db)

