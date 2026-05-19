from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogRead

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    table_name: str | None = None,
    action_type: str | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    query = select(AuditLog)
    if table_name:
        query = query.where(AuditLog.table_name == table_name)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    query = query.order_by(desc(AuditLog.timestamp)).limit(limit)
    return list(db.execute(query).scalars().all())

