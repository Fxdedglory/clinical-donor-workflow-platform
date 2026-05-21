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
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False, default="Clinical Operations")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    account_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal")
    user_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal")
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    external_user_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Approved")
    identity_provider: Mapped[str] = mapped_column(String(80), nullable=False, default="Platform Native")
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_history: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    last_password_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    donor_reviews: Mapped[list["DonorReview"]] = relationship(
        back_populates="reviewer", foreign_keys="DonorReview.reviewer_id"
    )
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


class Organization(Base):
    __tablename__ = "dim_organization"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    organization_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_name: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    organization_type: Mapped[str] = mapped_column(String(80), nullable=False, default="internal")
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Approved")
    contact_email: Mapped[str | None] = mapped_column(String(180), nullable=True)
    mfa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SupplierRelationship(Base):
    __tablename__ = "dim_supplier_relationship"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    relationship_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    internal_organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    external_organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False, default="Supplier")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending Approval")
    onboarding_status: Mapped[str] = mapped_column(String(60), nullable=False, default="Invited")
    risk_tier: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium")
    primary_contact_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AccountType(Base):
    __tablename__ = "dim_account_type"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    account_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_type_name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserPreference(Base):
    __tablename__ = "dim_user_preference"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    preference_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, index=True
    )
    preference_key: Mapped[str] = mapped_column(String(80), nullable=False)
    preference_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SidebarState(Base):
    __tablename__ = "dim_sidebar_state"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    state_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, unique=True
    )
    sidebar_collapsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_route: Mapped[str] = mapped_column(String(240), nullable=False, default="/dashboard")
    recently_viewed: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    pinned_records: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


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
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_actions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    next_possible_states: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    escalation_rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notification_rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_terminal_state: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class WorkflowEscalationRule(Base):
    __tablename__ = "workflow_escalation_rule"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    escalation_rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_state: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_condition: Mapped[str] = mapped_column(String(140), nullable=False)
    threshold_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    target_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    escalation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="High")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkflowNotificationRule(Base):
    __tablename__ = "workflow_notification_rule"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    notification_rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_state: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Normal")
    template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkflowNavigationRoute(Base):
    __tablename__ = "workflow_navigation_route"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    route_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_key: Mapped[str] = mapped_column(String(100), nullable=False)
    route_label: Mapped[str] = mapped_column(String(140), nullable=False)
    preserve_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    donor_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    donor_id_hash: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    donor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    donor_name_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    intake_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Draft Intake")
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    clinical_notes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_placeholder: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    reviewer: Mapped[User | None] = relationship(back_populates="donor_reviews", foreign_keys=[reviewer_id])


class ReferralSource(Base):
    __tablename__ = "dim_referral_source"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    region: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TissueType(Base):
    __tablename__ = "dim_tissue_type"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    tissue_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tissue_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    tissue_category: Mapped[str] = mapped_column(String(80), nullable=False)
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_ischemic_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    preservation_window_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sop_reference: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Disposition(Base):
    __tablename__ = "dim_disposition"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    disposition_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disposition_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EligibilityRule(Base):
    __tablename__ = "dim_eligibility_rule"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    rule_category: Mapped[str] = mapped_column(String(80), nullable=False)
    condition_field: Mapped[str] = mapped_column(String(120), nullable=False)
    condition_operator: Mapped[str] = mapped_column(String(40), nullable=False)
    condition_value: Mapped[str] = mapped_column(String(240), nullable=False)
    outcome: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sop_reference: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InfectiousDiseaseTest(Base):
    __tablename__ = "dim_infectious_disease_test"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    test_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    test_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    pathogen: Mapped[str] = mapped_column(String(80), nullable=False)
    test_method: Mapped[str] = mapped_column(String(80), nullable=False)
    valid_window_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=168)
    rejection_if_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_if_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Donor(Base):
    __tablename__ = "dim_donor"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    donor_pk: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    donor_identifier_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    donor_identifier_hash: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    donor_review_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_donor_review.review_id"), nullable=True
    )
    donor_name: Mapped[str] = mapped_column(String(160), nullable=False)
    donor_name_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    referral_source_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_referral_source.source_id"), nullable=True
    )
    time_of_death: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_organization: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    source_organization_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    donor_history: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    donor_history_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_workflow_state: Mapped[str] = mapped_column(String(120), nullable=False, default="Referral Received")
    eligibility_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    final_disposition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class DonorScreening(Base):
    __tablename__ = "fact_donor_screening"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    screening_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=False, index=True
    )
    referral_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    administrative_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    medical_social_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    infectious_disease_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    tissue_suitability_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    recovery_suitability_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    qa_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    automated_rule_outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    current_decision: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EligibilityDecision(Base):
    __tablename__ = "fact_eligibility_decision"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    decision_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=False, index=True
    )
    rule_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_eligibility_rule.rule_id"), nullable=True
    )
    decision_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    triggered_rules: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    final_disposition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class InfectiousDiseaseResult(Base):
    __tablename__ = "fact_infectious_disease_result"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=False, index=True
    )
    test_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_infectious_disease_test.test_id"), nullable=False
    )
    result_value: Mapped[str] = mapped_column(String(40), nullable=False)
    result_value_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    specimen_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    specimen_window_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    review_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MedicalSocialHistory(Base):
    __tablename__ = "fact_medical_social_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=False, index=True
    )
    cancer_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    neurological_disease: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    autoimmune_disease: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transmissible_disease_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    iv_drug_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    incarceration_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    travel_exposure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    high_risk_behavior: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unknown_history: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    review_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    review_notes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RecoverySuitability(Base):
    __tablename__ = "fact_recovery_suitability"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    recovery_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    donor_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=False, index=True
    )
    tissue_type_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_tissue_type.tissue_type_id"), nullable=False
    )
    refrigeration_timing_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_cooling_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Unknown")
    trauma_contamination: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blood_draw_timing_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    hospital_release_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    recovery_environment: Mapped[str] = mapped_column(String(100), nullable=False, default="Hospital")
    recovery_window_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessingRelease(Base):
    __tablename__ = "fact_processing_release"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    release_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    release_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    donor_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=False, index=True
    )
    tissue_type_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_tissue_type.tissue_type_id"), nullable=False
    )
    sterility_testing: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    bioburden_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    environmental_monitoring: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    packaging_qc: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    labeling_verification: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    traceability_verification: Mapped[str] = mapped_column(String(80), nullable=False, default="Pending")
    chain_of_custody_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deviation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capa_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    release_status: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending QA Review")
    final_disposition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class Deviation(Base):
    __tablename__ = "fact_deviation"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    deviation_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deviation_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    donor_pk: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=True
    )
    release_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deviation_category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="Open")
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class CAPA(Base):
    __tablename__ = "fact_capa"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    capa_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    capa_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    donor_pk: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=True
    )
    deviation_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_deviation.deviation_id"), nullable=True
    )
    release_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False, default="")
    corrective_action_owner: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="Open")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


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


class WorkflowTransitionEvent(Base):
    __tablename__ = "workflow_transition_event"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    transition_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(120), nullable=False)
    performed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decision_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


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
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

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
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


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
    workflow_task_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_workflow_task.task_id"), nullable=True
    )
    related_record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_record_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action_route: Mapped[str | None] = mapped_column(String(120), nullable=True)
    workflow_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
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


class DeploymentEnvironment(Base):
    __tablename__ = "dim_deployment_environment"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    environment_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    environment_name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    database_url_masked: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployed_version: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserApprovalStatus(Base):
    __tablename__ = "dim_user_approval_status"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    approval_status_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status_name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthIdentity(Base):
    __tablename__ = "dim_auth_identity"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    identity_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, index=True
    )
    identity_provider: Mapped[str] = mapped_column(String(80), nullable=False, default="Platform Native")
    provider_subject: Mapped[str] = mapped_column(String(180), nullable=False)
    user_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal")
    mfa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    external_user_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_authenticated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserSessionRecord(Base):
    __tablename__ = "dim_user_session"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device: Mapped[str | None] = mapped_column(String(180), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MFAConfiguration(Base):
    __tablename__ = "dim_mfa_configuration"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    mfa_config_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, unique=True
    )
    method: Mapped[str] = mapped_column(String(40), nullable=False, default="TOTP")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_by_policy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_codes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SecurityAudit(Base):
    __tablename__ = "fact_security_audit"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device: Mapped[str | None] = mapped_column(String(180), nullable=True)
    route: Mapped[str | None] = mapped_column(String(240), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SystemHealth(Base):
    __tablename__ = "fact_system_health"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    health_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Unknown")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class SecurityIncident(Base):
    __tablename__ = "fact_security_incident"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_key: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, default="Security Alert")
    source_event_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_security_audit.event_id"), nullable=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class SecureDocument(Base):
    __tablename__ = "dim_secure_document"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    document_name: Mapped[str] = mapped_column(String(180), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_uri_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(96), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    access_classification: Mapped[str] = mapped_column(String(40), nullable=False, default="Protected")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class DocumentVersion(Base):
    __tablename__ = "dim_document_version"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_secure_document.document_id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    document_status: Mapped[str] = mapped_column(String(60), nullable=False, default="Submitted")
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    storage_uri_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(96), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(60), nullable=False, default="Pending Review")
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class DocumentAccess(Base):
    __tablename__ = "fact_document_access"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    access_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_secure_document.document_id"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    route: Mapped[str | None] = mapped_column(String(240), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class PasswordResetToken(Base):
    __tablename__ = "fact_password_reset_token"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    reset_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalInvitation(Base):
    __tablename__ = "dim_external_invitation"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    invitation_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    invited_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_role.role_id"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Pending Acceptance")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class SignatureEvent(Base):
    __tablename__ = "fact_signature_event"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    signature_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, index=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True, index=True
    )
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    signature_type: Mapped[str] = mapped_column(String(80), nullable=False, default="Workflow Approval")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    prior_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class BackgroundJob(Base):
    __tablename__ = "fact_background_job"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Queued", index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Normal")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RealtimeEvent(Base):
    __tablename__ = "fact_realtime_event"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(100), nullable=False, default="operations")
    audience_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True, index=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True, index=True
    )
    record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    record_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingRecord(Base):
    __tablename__ = "dim_training_record"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    training_record_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=False, index=True
    )
    sop_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_sop.sop_id"), nullable=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="Assigned")
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    competency_status: Mapped[str] = mapped_column(String(60), nullable=False, default="Pending Validation")
    validated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    validation_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ValidationEvidence(Base):
    __tablename__ = "fact_validation_evidence"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    change_control_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_change_control.change_id"), nullable=True, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="Draft")
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class DataExportEvent(Base):
    __tablename__ = "fact_data_export"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    export_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True, index=True
    )
    export_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    route: Mapped[str | None] = mapped_column(String(240), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

