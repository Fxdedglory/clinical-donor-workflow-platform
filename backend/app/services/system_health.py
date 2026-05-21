from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SecurityAudit, SystemHealth, UserSessionRecord

SERVICE_STARTED_AT = datetime.now(UTC)


def _mask_database_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    return f"{scheme}://***:***@{rest.split('@', 1)[1]}"


def collect_system_health(db: Session) -> dict:
    checks: list[dict] = []
    started = perf_counter()
    try:
        db.execute(text("SELECT 1"))
        db_latency = int((perf_counter() - started) * 1000)
        checks.append({"component": "Database", "status": "Healthy", "latency_ms": db_latency})
    except Exception as exc:  # pragma: no cover - defensive health reporting
        checks.append({"component": "Database", "status": "Degraded", "latency_ms": None, "detail": str(exc)})

    active_sessions = db.execute(
        select(func.count(UserSessionRecord.session_id)).where(
            UserSessionRecord.is_active.is_(True),
            UserSessionRecord.revoked_at.is_(None),
            UserSessionRecord.expires_at > datetime.now(UTC),
        )
    ).scalar_one()
    failed_logins = db.execute(
        select(func.count(SecurityAudit.event_id)).where(SecurityAudit.event_type == "FAILED_LOGIN")
    ).scalar_one()

    checks.extend(
        [
            {"component": "Authentication", "status": "Healthy", "active_sessions": active_sessions},
            {"component": "Email", "status": "Configured", "provider": settings.email_provider},
            {"component": "Document Storage", "status": "Configured", "mode": "signed_links"},
            {"component": "Backup Policy", "status": "Configured", "encrypted": bool(settings.backup_encryption_key)},
        ]
    )

    for row in checks:
        db.add(
            SystemHealth(
                component_name=row["component"],
                status=row["status"],
                latency_ms=row.get("latency_ms"),
                details={key: value for key, value in row.items() if key not in {"component", "status", "latency_ms"}},
            )
        )

    return {
        "status": "Healthy" if all(row["status"] != "Degraded" for row in checks) else "Degraded",
        "environment": settings.app_env,
        "base_url": settings.app_base_url,
        "version": settings.app_version,
        "database_url_masked": _mask_database_url(settings.database_url),
        "uptime_seconds": int((datetime.now(UTC) - SERVICE_STARTED_AT).total_seconds()),
        "active_sessions": active_sessions,
        "failed_login_events": failed_logins,
        "checks": checks,
    }
