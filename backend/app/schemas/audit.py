from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_id: int
    user_id: int | None
    action_type: str
    table_name: str
    record_id: str
    entity_type: str | None = None
    entity_id: str | None = None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    ip_address: str | None = None
    timestamp: datetime

