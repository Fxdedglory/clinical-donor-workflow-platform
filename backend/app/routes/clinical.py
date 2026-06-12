from fastapi import APIRouter, Depends, Request, status

from app.schemas.clinical import (
    ClinicalModuleRead,
    ClinicalStatusRead,
    WorkflowCommitRequest,
    WorkflowCommitResponse,
    WorkflowOperation,
    WorkflowPreviewRequest,
    WorkflowPreviewResponse,
    WorkflowValidationIssue,
)
from app.services.clinical_workflows import (
    append_workflow_operation,
    preview_hash,
    require_generation_confirmation,
)

router = APIRouter(prefix="/api/clinical", tags=["Clinical Platform Foundation"])

CLINICAL_MODULES = [
    ClinicalModuleRead(
        module_id="dashboard",
        label="Clinical Dashboard",
        route="/clinical/dashboard",
        api_namespace="/api/clinical",
        status="foundation_pending",
        workflows=["Operational overview", "Workflow operation activity"],
    ),
    ClinicalModuleRead(
        module_id="patients",
        label="Patients / Donors",
        route="/clinical/patients",
        api_namespace="/api/clinical/patients",
        status="active",
        workflows=["Create patient/donor", "Edit demographics", "Capture consent", "Add contact", "Add insurance"],
    ),
    ClinicalModuleRead(
        module_id="scheduling",
        label="Scheduling",
        route="/clinical/scheduling",
        api_namespace="/api/clinical/scheduling",
        status="active",
        workflows=[
            "Book appointment",
            "Reschedule appointment",
            "Cancel appointment",
            "Check in appointment",
            "Mark no-show",
        ],
    ),
    ClinicalModuleRead(
        module_id="screening",
        label="Donor Screening",
        route="/clinical/screening",
        api_namespace="/api/clinical/screening",
        status="active",
        workflows=[
            "Start screening",
            "Commit questionnaire",
            "Capture vitals",
            "Preview eligibility",
            "Commit screening result",
            "Supervisor override",
        ],
    ),
    ClinicalModuleRead(
        module_id="encounters",
        label="Encounters",
        route="/clinical/encounters",
        api_namespace="/api/clinical/encounters",
        status="active",
        workflows=[
            "Create encounter",
            "Save draft note",
            "Sign and lock note",
            "Amend signed note",
            "Add diagnosis/problem",
            "Add allergy",
            "Add medication",
        ],
    ),
    ClinicalModuleRead(
        module_id="orders",
        label="Orders / Results",
        route="/clinical/orders",
        api_namespace="/api/clinical/orders",
        status="active",
        workflows=["Create order", "Receive result", "Correct result", "Acknowledge critical result", "Cancel order"],
    ),
    ClinicalModuleRead(
        module_id="care_plans",
        label="Care Plans",
        route="/clinical/care-plans",
        api_namespace="/api/clinical/care-plans",
        status="planned_workflow",
        workflows=["Create care plan", "Update progress", "Close care plan"],
    ),
    ClinicalModuleRead(
        module_id="billing",
        label="Billing",
        route="/clinical/billing",
        api_namespace="/api/clinical/billing",
        status="planned_workflow",
        workflows=["Capture charges", "Preview claim", "Commit claim"],
    ),
    ClinicalModuleRead(
        module_id="quality",
        label="Quality",
        route="/clinical/quality",
        api_namespace="/api/clinical/quality",
        status="planned_workflow",
        workflows=["Create quality event", "Create CAPA", "Export audit evidence"],
    ),
    ClinicalModuleRead(
        module_id="reports",
        label="Reports",
        route="/clinical/reports",
        api_namespace="/api/clinical/reports",
        status="planned_workflow",
        workflows=["Screening outcomes", "Audit activity", "Operational exports"],
    ),
    ClinicalModuleRead(
        module_id="admin",
        label="Clinical Admin",
        route="/clinical/admin",
        api_namespace="/api/clinical/admin",
        status="planned_workflow",
        workflows=["Manage templates", "Manage rules", "Manage approval paths"],
    ),
]


def _validation_issues(payload: WorkflowPreviewRequest) -> list[WorkflowValidationIssue]:
    issues: list[WorkflowValidationIssue] = []
    if not payload.workflow.strip():
        issues.append(WorkflowValidationIssue(field="workflow", message="Workflow is required.", severity="error"))
    if not payload.entity_type.strip():
        issues.append(WorkflowValidationIssue(field="entity_type", message="Entity type is required.", severity="error"))
    if not payload.changes and not payload.payload:
        issues.append(
            WorkflowValidationIssue(
                field="changes",
                message="No workflow changes were supplied for preview.",
                severity="warning",
            )
        )
    return issues


def _validation_status(issues: list[WorkflowValidationIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "failed"
    if any(issue.severity == "warning" for issue in issues):
        return "warning"
    return "passed"


@router.get("/status", response_model=ClinicalStatusRead)
def clinical_status() -> ClinicalStatusRead:
    return ClinicalStatusRead(status="foundation_ready", modules_count=len(CLINICAL_MODULES))


@router.get("/modules", response_model=list[ClinicalModuleRead])
def clinical_modules() -> list[ClinicalModuleRead]:
    return CLINICAL_MODULES


@router.post("/workflows/preview", response_model=WorkflowPreviewResponse)
def preview_workflow(payload: WorkflowPreviewRequest) -> WorkflowPreviewResponse:
    issues = _validation_issues(payload)
    entity_id = payload.entity_id or "draft"
    return WorkflowPreviewResponse(
        workflow=payload.workflow,
        entity_type=payload.entity_type,
        entity_id=entity_id,
        preview_hash=preview_hash(payload),
        validation_status=_validation_status(issues),
        validation_issues=issues,
        summary=f"Preview generated for {payload.workflow} on {payload.entity_type} {entity_id}.",
        changes=payload.changes,
    )


@router.post(
    "/workflows/commit",
    response_model=WorkflowCommitResponse,
    status_code=status.HTTP_201_CREATED,
)
def commit_workflow(
    payload: WorkflowCommitRequest,
    request: Request,
    _: bool = Depends(require_generation_confirmation),
) -> WorkflowCommitResponse:
    preview_value = payload.preview_hash or preview_hash(payload)
    operation = WorkflowOperation(
        workflow=payload.workflow,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id or "draft",
        actor=payload.actor,
        preview_hash=preview_value,
        status_before=payload.status_before,
        status_after=payload.status_after,
        reason=payload.reason,
        changes=payload.changes,
    )
    operation, audit_path = append_workflow_operation(operation)
    return WorkflowCommitResponse(
        status="committed",
        operation_id=operation.operation_id,
        audit_path=str(audit_path),
        operation=operation,
    )
