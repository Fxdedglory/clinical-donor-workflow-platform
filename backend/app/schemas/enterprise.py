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
    display_name: str | None = None
    email: str | None = None
    password: str | None = None
    role_id: int | None = None
    department: str | None = None
    is_active: bool | None = None
    account_type: str | None = None
    user_type: str | None = None
    organization_id: int | None = None
    is_internal: bool | None = None
    is_external: bool | None = None
    external_user_flag: bool | None = None
    approval_status: str | None = None
    identity_provider: str | None = None
    mfa_enabled: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str | None
    full_name: str
    display_name: str | None = None
    email: str
    role_id: int | None
    role: str
    department: str
    is_active: bool
    account_type: str = "internal"
    user_type: str = "internal"
    organization_id: int | None = None
    is_internal: bool = True
    is_external: bool = False
    external_user_flag: bool = False
    approval_status: str = "Approved"
    identity_provider: str = "Platform Native"
    mfa_enabled: bool = False
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
    workflow_task_id: int | None
    related_record_type: str | None
    related_record_id: str | None
    action_route: str | None
    workflow_context: dict
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: str
    priority: str = "Normal"
    workflow_task_id: int | None = None
    related_record_type: str | None = None
    related_record_id: str | None = None
    action_route: str | None = None
    workflow_context: dict | None = None


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
    metadata: dict | None = None


class WorkflowStateMachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state_id: int
    state_name: str
    state_category: str
    owning_role_id: int | None
    allowed_roles: list[str]
    allowed_actions: list[str]
    next_possible_states: list[str]
    sla_hours: int
    escalation_rules: dict
    notification_rules: dict
    is_terminal: bool
    is_terminal_state: bool
    sort_order: int


class WorkflowTransitionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: int
    record_id: str
    record_type: str
    from_state: str
    to_state: str
    action_taken: str
    performed_by: int | None
    timestamp: datetime
    notes: str
    decision_context: dict


class WorkflowRouteResponse(BaseModel):
    route_path: str
    page_key: str
    route_label: str
    record_type: str | None = None
    record_id: str | None = None
    workflow_state: str | None = None
    notification_id: int | None = None
    task_id: int | None = None


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


class AIRiskRuleCreate(BaseModel):
    rule_name: str
    risk_category: str
    condition_type: str
    condition_operator: str
    condition_value: str
    risk_score_delta: int
    severity: str
    auto_escalate: bool = False
    is_active: bool = True


class AIRiskRuleUpdate(BaseModel):
    risk_category: str | None = None
    condition_type: str | None = None
    condition_operator: str | None = None
    condition_value: str | None = None
    risk_score_delta: int | None = None
    severity: str | None = None
    auto_escalate: bool | None = None
    is_active: bool | None = None


class AIRiskRuleRead(AIRiskRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    rule_id: int
    created_by: int | None
    approved_by: int | None
    created_at: datetime


class AIModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_version_id: int
    version_name: str
    deployment_date: datetime
    status: str
    change_summary: str
    created_by: int | None
    approved_by: int | None


class AIDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: int
    donor_id: str
    model_version_id: int | None
    risk_score: int
    recommendation: str
    triggered_rules: list[dict]
    workflow_stage: str
    confidence_level: float
    escalation_reasons: list[str]
    workflow_impact: str
    created_at: datetime
    reviewed_by: int | None
    human_override: bool
    override_reason: str | None
    final_decision: str | None


class AIOverrideEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    override_id: int
    decision_id: int
    reviewer_id: int | None
    override_reason: str
    previous_decision: str
    new_decision: str
    timestamp: datetime


class WorkflowTimelineEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timeline_event_id: int
    related_record_type: str
    related_record_id: str
    event_type: str
    event_summary: str
    event_detail: dict
    created_by: int | None
    created_at: datetime


class RuleSimulationRequest(BaseModel):
    condition_type: str = "age"
    condition_operator: str = "gt"
    condition_value: str = "70"
    risk_score_delta: int = 20
    sample_size: int = 120
