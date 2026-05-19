from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard import get_dashboard_metrics

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db)) -> dict:
    return get_dashboard_metrics(db)

