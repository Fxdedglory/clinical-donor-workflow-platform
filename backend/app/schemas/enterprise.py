from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    role_name: str
    description: str


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: str
    password: str
    role_id: int
    department: str = "Clinical Operations"
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    password: str | None = None
    role_id: int | None = None
    department: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str | None
    full_name: str
    email: str
    role_id: int | None
    role: str
    department: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime


class WorkflowTaskCreate(BaseModel):
    task_type: str
    title: str
    description: str = ""
    assigned_to_user_id: int | None = None
    assigned_role_id: int | None = None
    priority: str = "Routine"
    status: str = "Assigned"
    workflow_state: str = "Assigned"
    queue_name: str = "General Work Queue"
    due_date: datetime | None = None
    related_record_id: str
    related_record_type: str
    escalation_level: int = 0


class WorkflowTaskUpdate(BaseModel):
    assigned_to_user_id: int | None = None
    assigned_role_id: int | None = None
    priority: str | None = None
    status: str | None = None
    workflow_state: str | None = None
    queue_name: str | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    escalation_level: int | None = None


class WorkflowTaskRead(WorkflowTaskCreate):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    created_at: datetime
    completed_at: datetime | None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: str
    related_record_type: str | None
    related_record_id: str | None
    action_route: str | None
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: str = "Normal"
    related_record_type: str | None = None
    related_record_id: str | None = None
    action_route: str | None = None


class EscalationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    escalation_id: int
    related_task_id: int
    escalation_type: str
    trigger_reason: str
    created_at: datetime
    resolved_at: datetime | None
    status: str


class TrainingAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    sop_id: int
    assigned_to_user_id: int | None
    assigned_role_id: int | None
    assigned_date: datetime
    due_date: datetime
    acknowledgment_status: str


class TrainingAssignmentCreate(BaseModel):
    sop_id: int
    assigned_to_user_id: int | None = None
    assigned_role_id: int | None = None
    due_date: datetime
    acknowledgment_status: str = "Assigned"


class TrainingCompletionCreate(BaseModel):
    assignment_id: int
    completed_by_user_id: int
    attestation_text: str = "I acknowledge this SOP revision and related workflow responsibilities."


class RoleResponsibilityRead(BaseModel):
    role_name: str
    job_description: str
    responsibilities: list[str]
    assigned_workflows: list[str]
    operational_kpis: list[str]


class RoleWorkspaceConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_id: int
    role_id: int
    workspace_name: str
    workspace_purpose: str
    dashboard_layout: dict
    visible_tabs: list[dict]
    enabled_widgets: list[str]
    workbench_columns: list[str]
    default_queue: str
    notification_types: list[str]
    theme_config: dict
    updated_at: datetime


class RoleWorkspaceConfigUpdate(BaseModel):
    workspace_name: str | None = None
    workspace_purpose: str | None = None
    dashboard_layout: dict | None = None
    visible_tabs: list[dict] | None = None
    enabled_widgets: list[str] | None = None
    workbench_columns: list[str] | None = None
    default_queue: str | None = None
    notification_types: list[str] | None = None
    theme_config: dict | None = None


class RoleNavigationConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nav_id: int
    role_id: int
    tab_label: str
    page_key: str
    sort_order: int
    is_visible: bool
    required_permission: str | None


class RoleDashboardWidgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    widget_id: int
    role_id: int
    widget_key: str
    widget_title: str
    widget_type: str
    config: dict
    sort_order: int
    is_enabled: bool


class WorkflowTransitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: int
    action_name: str
    action_label: str
    from_state: str
    to_state: str
    source_role_id: int | None
    target_role_id: int | None
    task_type: str
    notification_type: str
    audit_action: str
    sla_hours: int
    is_active: bool


class WorkflowTransitionRequest(BaseModel):
    action_name: str
    related_record_type: str
    related_record_id: str
    task_id: int | None = None
    note: str = ""


class WorkspaceResponse(BaseModel):
    active_role: str
    active_role_id: int
    actual_role: str
    is_preview: bool
    workspace: RoleWorkspaceConfigRead
    navigation: list[RoleNavigationConfigRead]
    widgets: list[RoleDashboardWidgetRead]
    kpis: dict
    widget_data: dict
    allowed_actions: list[WorkflowTransitionRead]
    queue: list[WorkflowTaskRead]
    notifications: list[NotificationRead]
