from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ClinicalModuleRead(BaseModel):
    module_id: str
    label: str
    route: str
    api_namespace: str
    status: Literal["foundation_pending", "planned_workflow", "active"]
    workflows: list[str] = Field(default_factory=list)


class ClinicalStatusRead(BaseModel):
    status: str
    modules_count: int
    preview_commit_pattern: str = "Draft -> Validate -> Preview -> Commit"
    commit_header: str = "X-Confirm-Generation: true"
    audit_target: str = "metadata/workflow_operations.json"


class WorkflowValidationIssue(BaseModel):
    field: str
    message: str
    severity: Literal["info", "warning", "error"] = "info"


class WorkflowPreviewRequest(BaseModel):
    workflow: str
    entity_type: str
    entity_id: str | None = None
    actor: str = "system"
    status_before: str | None = None
    status_after: str | None = None
    reason: str = ""
    changes: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowPreviewResponse(BaseModel):
    preview_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow: str
    entity_type: str
    entity_id: str
    preview_hash: str
    validation_status: Literal["passed", "warning", "failed"]
    validation_issues: list[WorkflowValidationIssue] = Field(default_factory=list)
    commit_required_header: str = "X-Confirm-Generation: true"
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class WorkflowCommitRequest(WorkflowPreviewRequest):
    preview_hash: str | None = None


class WorkflowOperation(BaseModel):
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow: str
    entity_type: str
    entity_id: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    preview_hash: str
    commit_confirmed: bool = True
    status_before: str | None = None
    status_after: str | None = None
    reason: str = ""
    changes: dict[str, Any] = Field(default_factory=dict)


class WorkflowCommitResponse(BaseModel):
    status: Literal["committed"]
    operation_id: str
    audit_path: str
    operation: WorkflowOperation
