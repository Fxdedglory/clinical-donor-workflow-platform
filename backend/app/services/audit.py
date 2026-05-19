from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def _public_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_model(model: Any, fields: list[str]) -> dict[str, Any]:
    return {field: _public_value(getattr(model, field)) for field in fields}


def log_audit(
    db: Session,
    *,
    user_id: int | None,
    action_type: str,
    table_name: str,
    record_id: str,
    old_value: dict | None,
    new_value: dict | None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action_type=action_type,
        table_name=table_name,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)
    return entry

