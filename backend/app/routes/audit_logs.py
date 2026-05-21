from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.models import AuditLog, SecurityAudit, User
from app.schemas import AuditLogRead

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    table_name: str | None = None,
    action_type: str | None = None,
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("audit.review")),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    query = select(AuditLog)
    if table_name:
        query = query.where(AuditLog.table_name == table_name)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    query = query.order_by(desc(AuditLog.timestamp)).limit(limit)
    return list(db.execute(query).scalars().all())


@router.get("/security")
def list_security_audit(
    event_type: str | None = None,
    success: bool | None = None,
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("security.audit")),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(SecurityAudit)
    if event_type:
        query = query.where(SecurityAudit.event_type == event_type)
    if success is not None:
        query = query.where(SecurityAudit.success.is_(success))
    rows = db.execute(query.order_by(desc(SecurityAudit.timestamp)).limit(limit)).scalars().all()
    return [
        {
            "event_id": row.event_id,
            "user_id": row.user_id,
            "event_type": row.event_type,
            "timestamp": row.timestamp,
            "ip_address": row.ip_address,
            "device": row.device,
            "route": row.route,
            "success": row.success,
            "details": row.details,
        }
        for row in rows
    ]

