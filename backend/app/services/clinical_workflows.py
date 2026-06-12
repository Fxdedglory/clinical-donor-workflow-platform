from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, status

from app.schemas.clinical import WorkflowOperation, WorkflowPreviewRequest

CONFIRM_GENERATION_HEADER = "X-Confirm-Generation"
WORKFLOW_OPERATIONS_PATH = Path("metadata/workflow_operations.json")


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


def read_workflow_operations(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or WORKFLOW_OPERATIONS_PATH
    if not target.exists():
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{target} must contain a JSON array of workflow operations")
    return data


def append_workflow_operation(
    operation: WorkflowOperation,
    path: Path | None = None,
) -> tuple[WorkflowOperation, Path]:
    target = path or WORKFLOW_OPERATIONS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    operations = read_workflow_operations(target)
    operations.append(operation.model_dump(mode="json"))
    target.write_text(json.dumps(operations, indent=2) + "\n", encoding="utf-8")
    return operation, target
