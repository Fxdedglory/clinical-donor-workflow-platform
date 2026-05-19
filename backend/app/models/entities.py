from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

OPERATIONAL_SCHEMA = "operational"


class User(Base):
    __tablename__ = "dim_user"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False, default="Clinical Operations")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    donor_reviews: Mapped[list["DonorReview"]] = relationship(back_populates="reviewer")
    role_ref: Mapped["Role | None"] = relationship(back_populates="users")


class Role(Base):
    __tablename__ = "dim_role"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    users: Mapped[list[User]] = relationship(back_populates="role_ref")
    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    responsibilities: Mapped[list["RoleResponsibility"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    workspace_config: Mapped["RoleWorkspaceConfig | None"] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    navigation_items: Mapped[list["RoleNavigationConfig"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    dashboard_widgets: Mapped[list["RoleDashboardWidget"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "bridge_role_permission"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), primary_key=True
    )
    permission_name: Mapped[str] = mapped_column(String(120), primary_key=True)

    role: Mapped[Role] = relationship(back_populates="permissions")


class RoleResponsibility(Base):
    __tablename__ = "dim_role_responsibility"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    responsibility_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=False
    )
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assigned_workflows: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    operational_kpis: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    role: Mapped[Role] = relationship(back_populates="responsibilities")


class RoleWorkspaceConfig(Base):
    __tablename__ = "role_workspace_config"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    config_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=False, unique=True
    )
    workspace_name: Mapped[str] = mapped_column(String(140), nullable=False)
    workspace_purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dashboard_layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    visible_tabs: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    enabled_widgets: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    workbench_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    default_queue: Mapped[str] = mapped_column(String(120), nullable=False)
    notification_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    theme_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    role: Mapped[Role] = relationship(back_populates="workspace_config")


class RoleNavigationConfig(Base):
    __tablename__ = "role_navigation_config"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    nav_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=False
    )
    tab_label: Mapped[str] = mapped_column(String(100), nullable=False)
    page_key: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    required_permission: Mapped[str | None] = mapped_column(String(120), nullable=True)

    role: Mapped[Role] = relationship(back_populates="navigation_items")


class RoleDashboardWidget(Base):
    __tablename__ = "role_dashboard_widget"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    widget_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=False
    )
    widget_key: Mapped[str] = mapped_column(String(100), nullable=False)
    widget_title: Mapped[str] = mapped_column(String(140), nullable=False)
    widget_type: Mapped[str] = mapped_column(String(60), nullable=False, default="metric")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    role: Mapped[Role] = relationship(back_populates="dashboard_widgets")


class WorkflowStateMachine(Base):
    __tablename__ = "workflow_state_machine"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    state_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    state_category: Mapped[str] = mapped_column(String(80), nullable=False)
    owning_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WorkflowTransitionRule(Base):
    __tablename__ = "workflow_transition_rule"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    transition_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    action_label: Mapped[str] = mapped_column(String(140), nullable=False)
    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    source_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    target_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    audit_action: Mapped[str] = mapped_column(String(100), nullable=False)
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkflowAssignmentRule(Base):
    __tablename__ = "workflow_assignment_rule"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    assignment_rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    from_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    to_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority_rule: Mapped[str] = mapped_column(String(100), nullable=False, default="inherit")
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Vendor(Base):
    __tablename__ = "dim_vendor"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    system_name: Mapped[str] = mapped_column(String(120), nullable=False)
    criticality: Mapped[str] = mapped_column(String(40), nullable=False, default="Tier 2")
    sla_target_percent: Mapped[float] = mapped_column(Float, nullable=False, default=99.5)
    business_owner: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Active")

    incidents: Mapped[list["VendorIncident"]] = relationship(back_populates="vendor")


class SOP(Base):
    __tablename__ = "dim_sop"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    sop_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sop_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Effective")
    revision_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class RiskCategory(Base):
    __tablename__ = "dim_risk_category"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    risk_category_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    min_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    default_action: Mapped[str] = mapped_column(String(80), nullable=False)


class AIRiskRule(Base):
    __tablename__ = "dim_ai_risk_rule"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    risk_category: Mapped[str] = mapped_column(String(60), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(80), nullable=False)
    condition_operator: Mapped[str] = mapped_column(String(40), nullable=False)
    condition_value: Mapped[str] = mapped_column(String(240), nullable=False)
    risk_score_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    auto_escalate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AIModelVersion(Base):
    __tablename__ = "dim_ai_model_version"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    model_version_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    deployment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Active")
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class DonorReview(Base):
    __tablename__ = "fact_donor_review"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    donor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    infectious_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    travel_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    missing_required_fields: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False, default="Low")
    recommended_action: Mapped[str] = mapped_column(String(80), nullable=False, default="Approve")
    review_priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Routine")
    intake_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending")
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachment_placeholder: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewer: Mapped[User | None] = relationship(back_populates="donor_reviews")


class AIDecision(Base):
    __tablename__ = "fact_ai_decision"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    decision_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_ai_model_version.model_version_id"), nullable=True
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(120), nullable=False)
    triggered_rules: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    workflow_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    escalation_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    workflow_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    human_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_decision: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AIOverrideEvent(Base):
    __tablename__ = "fact_ai_override_event"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    override_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_ai_decision.decision_id"), nullable=False
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    override_reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_decision: Mapped[str] = mapped_column(String(120), nullable=False)
    new_decision: Mapped[str] = mapped_column(String(80), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class WorkflowTimelineEvent(Base):
    __tablename__ = "fact_workflow_timeline_event"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    timeline_event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    related_record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    related_record_id: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_summary: Mapped[str] = mapped_column(String(240), nullable=False)
    event_detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class AuditLog(Base):
    __tablename__ = "fact_audit_log"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    table_name: Mapped[str] = mapped_column(String(120), nullable=False)
    record_id: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class ChangeControl(Base):
    __tablename__ = "fact_change_control"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    change_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    requested_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    sop_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_sop.sop_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Draft")
    capa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    investigation_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    implementation_due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VendorIncident(Base):
    __tablename__ = "fact_vendor_incident"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_vendor.vendor_id"), nullable=False
    )
    ticket_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    uptime_percent: Mapped[float] = mapped_column(Float, nullable=False, default=99.9)
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_age_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    resolution_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    vendor: Mapped[Vendor] = relationship(back_populates="incidents")


class WorkflowTask(Base):
    __tablename__ = "fact_workflow_task"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    assigned_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Routine")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending")
    workflow_state: Mapped[str] = mapped_column(String(100), nullable=False, default="Assigned")
    queue_name: Mapped[str] = mapped_column(String(120), nullable=False, default="General Work Queue")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    related_record_id: Mapped[str] = mapped_column(String(80), nullable=False)
    related_record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Notification(Base):
    __tablename__ = "fact_notification"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Normal")
    related_record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_record_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action_route: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EscalationEvent(Base):
    __tablename__ = "fact_escalation_event"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    escalation_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    related_task_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_workflow_task.task_id"), nullable=False
    )
    escalation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")


class SOPTrainingAssignment(Base):
    __tablename__ = "fact_sop_training_assignment"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sop_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_sop.sop_id"), nullable=False
    )
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    assigned_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    assigned_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledgment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Assigned")


class TrainingCompletion(Base):
    __tablename__ = "fact_training_completion"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    completion_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_sop_training_assignment.assignment_id"),
        nullable=False,
    )
    completed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False
    )
    completion_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledgment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Acknowledged")
    attestation_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

