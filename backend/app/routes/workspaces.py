from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_permission
from app.database import get_db
from app.models import (
    Role,
    RoleDashboardWidget,
    RoleNavigationConfig,
    RoleWorkspaceConfig,
    User,
    WorkflowStateMachine,
    WorkflowTransitionEvent,
    WorkflowTransitionRule,
)
from app.schemas import (
    RoleDashboardWidgetRead,
    RoleNavigationConfigRead,
    RoleWorkspaceConfigRead,
    RoleWorkspaceConfigUpdate,
    WorkflowStateMachineRead,
    WorkflowTransitionEventRead,
    WorkflowTransitionRead,
    WorkflowTransitionRequest,
    WorkspaceResponse,
)
from app.services.audit import log_audit, serialize_model
from app.services.security_audit import log_security_event
from app.services.workflow_orchestration import recent_transition_events
from app.services.workspace_engine import execute_transition, workspace_payload

router = APIRouter(prefix="/api/workspaces", tags=["Role-Centered Workspaces"])

WORKSPACE_FIELDS = [
    "workspace_name",
    "workspace_purpose",
    "dashboard_layout",
    "visible_tabs",
    "enabled_widgets",
    "workbench_columns",
    "default_queue",
    "notification_types",
    "theme_config",
]


@router.get("/me", response_model=WorkspaceResponse)
def my_workspace(
    preview_role_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return workspace_payload(db, current_user=current_user, preview_role_id=preview_role_id)


@router.post("/transition")
def transition(
    payload: WorkflowTransitionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result = execute_transition(
        db,
        current_user=current_user,
        action_name=payload.action_name,
        related_record_type=payload.related_record_type,
        related_record_id=payload.related_record_id,
        task_id=payload.task_id,
        note=payload.note,
        metadata=payload.metadata,
    )
    log_security_event(
        db,
        event_type="WORKFLOW_TRANSITION",
        user_id=current_user.user_id,
        request=request,
        details={
            "action_name": payload.action_name,
            "record_type": payload.related_record_type,
            "record_id": payload.related_record_id,
            "from_state": result.get("from_state"),
            "to_state": result.get("to_state"),
            "electronic_signature": bool(payload.metadata.get("reviewer_signature") if payload.metadata else False),
        },
    )
    db.commit()
    return result


@router.get("/configs", response_model=list[RoleWorkspaceConfigRead])
def list_workspace_configs(
    _: User = Depends(require_permission("workflow.configure")),
    db: Session = Depends(get_db),
) -> list[RoleWorkspaceConfig]:
    return list(
        db.execute(
            select(RoleWorkspaceConfig)
            .join(Role, Role.role_id == RoleWorkspaceConfig.role_id)
            .order_by(Role.role_name)
        ).scalars().all()
    )


@router.patch("/configs/{config_id}", response_model=RoleWorkspaceConfigRead)
def update_workspace_config(
    config_id: int,
    payload: RoleWorkspaceConfigUpdate,
    current_user: User = Depends(require_permission("workflow.configure")),
    db: Session = Depends(get_db),
) -> RoleWorkspaceConfig:
    config = db.get(RoleWorkspaceConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace config not found")
    old_value = serialize_model(config, WORKSPACE_FIELDS)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    db.flush()
    log_audit(
        db,
        user_id=current_user.user_id,
        action_type="UPDATE_WORKSPACE_CONFIG",
        table_name="role_workspace_config",
        record_id=str(config.config_id),
        old_value=old_value,
        new_value=serialize_model(config, WORKSPACE_FIELDS),
        entity_type="RoleWorkspaceConfig",
        entity_id=str(config.config_id),
    )
    db.commit()
    db.refresh(config)
    return config


@router.get("/navigation", response_model=list[RoleNavigationConfigRead])
def list_navigation_config(
    _: User = Depends(require_permission("workflow.configure")),
    db: Session = Depends(get_db),
) -> list[RoleNavigationConfig]:
    return list(
        db.execute(
            select(RoleNavigationConfig)
            .join(Role, Role.role_id == RoleNavigationConfig.role_id)
            .order_by(Role.role_name, RoleNavigationConfig.sort_order)
        ).scalars().all()
    )


@router.get("/widgets", response_model=list[RoleDashboardWidgetRead])
def list_dashboard_widgets(
    _: User = Depends(require_permission("workflow.configure")),
    db: Session = Depends(get_db),
) -> list[RoleDashboardWidget]:
    return list(
        db.execute(
            select(RoleDashboardWidget)
            .join(Role, Role.role_id == RoleDashboardWidget.role_id)
            .order_by(Role.role_name, RoleDashboardWidget.sort_order)
        ).scalars().all()
    )


@router.get("/transitions", response_model=list[WorkflowTransitionRead])
def list_transition_rules(
    _: User = Depends(require_permission("workflow.configure")),
    db: Session = Depends(get_db),
) -> list[WorkflowTransitionRule]:
    return list(db.execute(select(WorkflowTransitionRule).order_by(WorkflowTransitionRule.action_name)).scalars().all())


@router.get("/states", response_model=list[WorkflowStateMachineRead])
def list_workflow_states(
    _: User = Depends(require_permission("workflow.configure")),
    db: Session = Depends(get_db),
) -> list[WorkflowStateMachine]:
    return list(db.execute(select(WorkflowStateMachine).order_by(WorkflowStateMachine.sort_order)).scalars().all())


@router.get("/transition-events", response_model=list[WorkflowTransitionEventRead])
def list_transition_events(
    record_type: str | None = Query(default=None),
    record_id: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    _: User = Depends(require_permission("audit.review")),
    db: Session = Depends(get_db),
) -> list[WorkflowTransitionEvent]:
    return recent_transition_events(db, record_type=record_type, record_id=record_id, limit=limit)
