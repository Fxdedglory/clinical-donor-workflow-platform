from fastapi import APIRouter, Depends, Request, status
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_user_permissions
from app.database import get_db
from app.models import User
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
from app.services.clinical_patients import actor_label
from app.services.clinical_phi import is_external_user

router = APIRouter(prefix="/api/clinical", tags=["Clinical Platform Foundation"])
GENERIC_WORKFLOW_COMMIT_PERMISSIONS = {"system.admin", "clinical_admin.manage"}

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
        status="active",
        workflows=["Create care plan", "Add goal", "Add intervention", "Add task", "Update progress", "Close care plan"],
    ),
    ClinicalModuleRead(
        module_id="billing",
        label="Billing",
        route="/clinical/billing",
        api_namespace="/api/clinical/billing",
        status="active",
        workflows=["Verify insurance", "Capture charge", "Create claim draft", "Post payment", "Capture denial"],
    ),
    ClinicalModuleRead(
        module_id="quality",
        label="Quality",
        route="/clinical/quality",
        api_namespace="/api/clinical/quality",
        status="active",
        workflows=[
            "Create quality event",
            "Create adverse event",
            "Add investigation",
            "Link CAPA",
            "Close quality event",
            "Export audit evidence",
        ],
    ),
    ClinicalModuleRead(
        module_id="reports",
        label="Reports",
        route="/clinical/reports",
        api_namespace="/api/clinical/reports",
        status="active",
        workflows=[
            "Dashboard aggregates",
            "Patient throughput",
            "Scheduling utilization",
            "Screening outcomes",
            "Deferral trends",
            "Encounter volume",
            "Orders and results",
            "Care plan aging",
            "Billing work queue",
            "Quality trends",
            "Audit activity",
            "Analytics export preview",
            "Analytics export commit",
        ],
    ),
    ClinicalModuleRead(
        module_id="admin",
        label="Clinical Admin",
        route="/clinical/admin",
        api_namespace="/api/clinical/admin",
        status="active",
        workflows=[
            "Manage appointment types",
            "Manage provider schedule templates",
            "Version screening templates and rules",
            "Manage note templates and order catalog",
            "Manage billing codes and quality categories",
            "Manage approval paths and notification templates",
            "Review RBAC overview",
        ],
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


def require_generic_workflow_commit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if is_external_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="External users cannot use the generic clinical workflow commit endpoint.",
        )
    permissions = set(getattr(current_user, "permissions", []) or [])
    if permissions.isdisjoint(GENERIC_WORKFLOW_COMMIT_PERMISSIONS):
        permissions |= set(get_user_permissions(db, current_user))
    if permissions.isdisjoint(GENERIC_WORKFLOW_COMMIT_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Generic workflow commit requires clinical admin or system admin permission.",
        )
    return current_user


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
    current_user: User = Depends(require_generic_workflow_commit),
    db: Session = Depends(get_db),
    _: bool = Depends(require_generation_confirmation),
) -> WorkflowCommitResponse:
    preview_value = payload.preview_hash or preview_hash(payload)
    operation = WorkflowOperation(
        workflow=payload.workflow,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id or "draft",
        actor=actor_label(current_user),
        preview_hash=preview_value,
        status_before=payload.status_before,
        status_after=payload.status_after,
        reason=payload.reason,
        changes={
            "generic_foundation_commit": True,
            "module_specific_commit_preferred": True,
            "requested_actor": payload.actor,
            "changes": payload.changes,
        },
    )
    operation, audit_path = append_workflow_operation(operation, db=db)
    return WorkflowCommitResponse(
        status="committed",
        operation_id=operation.operation_id,
        audit_path=str(audit_path),
        operation=operation,
    )
