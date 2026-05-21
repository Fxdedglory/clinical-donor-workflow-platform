from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog
from app.services.encryption import mask_sensitive_payload


def _public_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_model(model: Any, fields: list[str]) -> dict[str, Any]:
    return mask_sensitive_payload({field: _public_value(getattr(model, field)) for field in fields})


def log_audit(
    db: Session,
    *,
    user_id: int | None,
    action_type: str,
    table_name: str,
    record_id: str,
    old_value: dict | None,
    new_value: dict | None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action_type=action_type,
        table_name=table_name,
        record_id=record_id,
        entity_type=entity_type or table_name,
        entity_id=entity_id or record_id,
        old_value=mask_sensitive_payload(old_value),
        new_value=mask_sensitive_payload(new_value),
        ip_address=ip_address,
    )
    db.add(entry)
    return entry

