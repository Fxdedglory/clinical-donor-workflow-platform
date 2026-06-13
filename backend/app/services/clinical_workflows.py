from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import ClinicalWorkflowAuditEvent
from app.schemas.clinical import WorkflowOperation, WorkflowPreviewRequest

CONFIRM_GENERATION_HEADER = "X-Confirm-Generation"
WORKFLOW_OPERATIONS_PATH = Path("metadata/workflow_operations.json")
WORKFLOW_AUDIT_SOURCE_COMMIT = "workflow_commit"
WORKFLOW_AUDIT_SOURCE_BACKFILL = "json_backfill"

logger = logging.getLogger(__name__)


def require_generation_confirmation(request: Request) -> bool:
    value = request.headers.get(CONFIRM_GENERATION_HEADER, "")
    if value.strip().lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "confirmation_required",
                "message": f"Commit requests require {CONFIRM_GENERATION_HEADER}: true.",
            },
        )
    return True


def preview_hash(payload: WorkflowPreviewRequest | dict[str, Any]) -> str:
    raw_payload = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    encoded = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json_workflow_operations(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or WORKFLOW_OPERATIONS_PATH
    if not target.exists():
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{target} must contain a JSON array of workflow operations")
    return data


def workflow_operation_to_audit_event(
    operation: WorkflowOperation,
    *,
    source: str = WORKFLOW_AUDIT_SOURCE_COMMIT,
) -> ClinicalWorkflowAuditEvent:
    return ClinicalWorkflowAuditEvent(
        operation_id=operation.operation_id,
        workflow=operation.workflow,
        entity_type=operation.entity_type,
        entity_id=operation.entity_id,
        actor=operation.actor,
        timestamp=operation.timestamp,
        preview_hash=operation.preview_hash,
        commit_confirmed=operation.commit_confirmed,
        status_before=operation.status_before,
        status_after=operation.status_after,
        reason=operation.reason,
        changes_json=operation.changes,
        source=source,
    )


def workflow_audit_event_to_dict(event: ClinicalWorkflowAuditEvent) -> dict[str, Any]:
    created_at = getattr(event, "created_at", None)
    return {
        "operation_id": event.operation_id,
        "workflow": event.workflow,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "actor": event.actor,
        "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else event.timestamp,
        "preview_hash": event.preview_hash,
        "commit_confirmed": event.commit_confirmed,
        "status_before": event.status_before,
        "status_after": event.status_after,
        "reason": event.reason,
        "changes": event.changes_json or {},
        "source": event.source,
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }


def _rollback_if_available(db: Session) -> None:
    rollback = getattr(db, "rollback", None)
    if not callable(rollback):
        return
    try:
        rollback()
    except Exception:
        logger.debug("Workflow audit DB rollback failed.", exc_info=True)


def append_workflow_operation_to_db(
    db: Session,
    operation: WorkflowOperation,
    *,
    source: str = WORKFLOW_AUDIT_SOURCE_COMMIT,
    commit: bool = True,
) -> ClinicalWorkflowAuditEvent:
    event = workflow_operation_to_audit_event(operation, source=source)
    db.add(event)
    db.flush()
    if commit:
        db.commit()
    return event


def read_db_workflow_operations(db: Session) -> list[dict[str, Any]]:
    try:
        rows = list(
            db.execute(
                select(ClinicalWorkflowAuditEvent).order_by(
                    ClinicalWorkflowAuditEvent.timestamp.asc(),
                    ClinicalWorkflowAuditEvent.id.asc(),
                )
            )
            .scalars()
            .all()
        )
    except (SQLAlchemyError, AttributeError, TypeError):
        logger.warning("Unable to read DB workflow audit events; using JSON fallback.", exc_info=True)
        return []
    return [workflow_audit_event_to_dict(row) for row in rows]


def read_workflow_operations(path: Path | None = None, *, db: Session | None = None) -> list[dict[str, Any]]:
    if db is not None:
        db_operations = read_db_workflow_operations(db)
        if db_operations:
            return db_operations
    return read_json_workflow_operations(path)


def append_workflow_operation(
    operation: WorkflowOperation,
    path: Path | None = None,
    *,
    db: Session | None = None,
    source: str = WORKFLOW_AUDIT_SOURCE_COMMIT,
    mirror_json: bool = True,
) -> tuple[WorkflowOperation, Path]:
    target = path or WORKFLOW_OPERATIONS_PATH
    if db is not None:
        try:
            append_workflow_operation_to_db(db, operation, source=source)
        except (SQLAlchemyError, AttributeError, TypeError):
            _rollback_if_available(db)
            logger.warning("Unable to append DB workflow audit event; preserving JSON mirror.", exc_info=True)
    if not mirror_json:
        return operation, target
    target.parent.mkdir(parents=True, exist_ok=True)
    operations = read_json_workflow_operations(target)
    operations.append(operation.model_dump(mode="json"))
    target.write_text(json.dumps(operations, indent=2) + "\n", encoding="utf-8")
    return operation, target


def backfill_workflow_operations_from_json(
    db: Session,
    path: Path | None = None,
    *,
    source: str = WORKFLOW_AUDIT_SOURCE_BACKFILL,
    commit: bool = False,
) -> dict[str, Any]:
    target = path or WORKFLOW_OPERATIONS_PATH
    existing_ids = {str(operation.get("operation_id")) for operation in read_db_workflow_operations(db)}
    inserted = 0
    skipped = 0
    rejected = 0
    for entry in read_json_workflow_operations(target):
        try:
            operation = WorkflowOperation.model_validate(entry)
        except ValueError:
            rejected += 1
            continue
        if operation.operation_id in existing_ids:
            skipped += 1
            continue
        db.add(workflow_operation_to_audit_event(operation, source=source))
        existing_ids.add(operation.operation_id)
        inserted += 1
    if inserted:
        try:
            db.flush()
            if commit:
                db.commit()
        except (SQLAlchemyError, AttributeError, TypeError):
            _rollback_if_available(db)
            raise
    return {
        "source_path": str(target),
        "inserted": inserted,
        "skipped": skipped,
        "rejected": rejected,
        "source_deleted": False,
    }
