from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
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
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False, default="Partner")
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


class ExternalStatusMapping(Base):
    __tablename__ = "dim_external_status_mapping"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    mapping_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    internal_state: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    external_status: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PartnerSubmission(Base):
    __tablename__ = "dim_partner_submission"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    submission_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    submitted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    submission_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    partner_visible_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Submitted", index=True)
    internal_state: Mapped[str] = mapped_column(String(120), nullable=False, default="Pending Intake Validation")
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="Standard")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    product_or_tissue: Mapped[str | None] = mapped_column(String(120), nullable=True)
    batch_or_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estimated_completion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class PartnerSubmissionStatus(Base):
    __tablename__ = "fact_partner_submission_status"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    status_event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_partner_submission.submission_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    to_status: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    internal_state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    partner_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PartnerMessage(Base):
    __tablename__ = "fact_partner_message"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_partner_submission.submission_id"), nullable=True, index=True
    )
    complaint_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_partner_complaint.complaint_id"), nullable=True, index=True
    )
    sender_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    audience: Mapped[str] = mapped_column(String(40), nullable=False, default="Partner")
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_document_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_secure_document.document_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PartnerComplaint(Base):
    __tablename__ = "fact_partner_complaint"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    complaint_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    submitted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    product_or_batch: Mapped[str] = mapped_column(String(160), nullable=False)
    issue_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="Medium", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact_assessment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contact_email: Mapped[str | None] = mapped_column(String(180), nullable=True)
    partner_visible_status: Mapped[str] = mapped_column(String(80), nullable=False, default="Submitted", index=True)
    internal_state: Mapped[str] = mapped_column(String(120), nullable=False, default="Pending QA Review")
    investigation_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_deviation.deviation_id"), nullable=True
    )
    capa_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_capa.capa_id"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PartnerDocument(Base):
    __tablename__ = "dim_partner_document"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    partner_document_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_secure_document.document_id"), nullable=False, unique=True, index=True
    )
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_partner_submission.submission_id"), nullable=True, index=True
    )
    complaint_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_partner_complaint.complaint_id"), nullable=True, index=True
    )
    document_category: Mapped[str] = mapped_column(String(80), nullable=False, default="Submission Evidence")
    request_status: Mapped[str] = mapped_column(String(60), nullable=False, default="Submitted")
    partner_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class PartnerTaskResponse(Base):
    __tablename__ = "fact_partner_task_response"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_workflow_task.task_id"), nullable=False, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_organization.organization_id"), nullable=False, index=True
    )
    responded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    response_status: Mapped[str] = mapped_column(String(60), nullable=False, default="Submitted")
    response_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachment_document_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_secure_document.document_id"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


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


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    patient_pk: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    donor_reference: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    middle_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sex_at_birth: Mapped[str] = mapped_column(String(40), nullable=False)
    gender_identity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    address_line1: Mapped[str | None] = mapped_column(String(180), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(180), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_registration")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    contacts: Mapped[list["PatientContact"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    insurance_profiles: Mapped[list["PatientInsurance"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    consents: Mapped[list["PatientConsent"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")
    screening_sessions: Mapped[list["ClinicalScreeningSession"]] = relationship(back_populates="patient")
    encounters: Mapped[list["ClinicalEncounter"]] = relationship(back_populates="patient")
    allergies: Mapped[list["ClinicalPatientAllergy"]] = relationship(back_populates="patient")
    medications: Mapped[list["ClinicalPatientMedication"]] = relationship(back_populates="patient")
    orders: Mapped[list["ClinicalOrder"]] = relationship(back_populates="patient")
    care_plans: Mapped[list["ClinicalCarePlan"]] = relationship(back_populates="patient")
    billing_accounts: Mapped[list["ClinicalBillingAccount"]] = relationship(back_populates="patient")
    insurance_verifications: Mapped[list["ClinicalInsuranceVerification"]] = relationship(back_populates="patient")
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="patient")
    claims: Mapped[list["ClinicalClaim"]] = relationship(back_populates="patient")
    payments: Mapped[list["ClinicalPayment"]] = relationship(back_populates="patient")


class PatientContact(Base):
    __tablename__ = "patient_contacts"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    contact_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    contact_type: Mapped[str] = mapped_column(String(80), nullable=False, default="emergency")
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_relationship: Mapped[str | None] = mapped_column("relationship", String(80), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_registration")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="contacts")

    @property
    def relationship(self) -> str | None:
        return self.contact_relationship


class PatientInsurance(Base):
    __tablename__ = "patient_insurance"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    insurance_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    payer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    member_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    group_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plan_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="primary")
    eligibility_status: Mapped[str] = mapped_column(String(80), nullable=False, default="not_verified")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_registration")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="insurance_profiles")
    billing_accounts: Mapped[list["ClinicalBillingAccount"]] = relationship(back_populates="primary_insurance")
    insurance_verifications: Mapped[list["ClinicalInsuranceVerification"]] = relationship(back_populates="patient_insurance")
    claims: Mapped[list["ClinicalClaim"]] = relationship(back_populates="patient_insurance")


class PatientConsent(Base):
    __tablename__ = "patient_consents"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    consent_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(120), nullable=False)
    consent_status: Mapped[str] = mapped_column(String(40), nullable=False, default="captured")
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_by_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_registration")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="consents")


class ClinicalProvider(Base):
    __tablename__ = "clinical_providers"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    provider_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(80), nullable=False, default="Clinician")
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="provider")


class ClinicalRoom(Base):
    __tablename__ = "clinical_rooms"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    room_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    room_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="room")


class ClinicalEquipment(Base):
    __tablename__ = "clinical_equipment"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    equipment_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    equipment_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    equipment_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    appointment_resources: Mapped[list["AppointmentResource"]] = relationship(back_populates="equipment")


class AppointmentType(Base):
    __tablename__ = "appointment_types"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    appointment_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="general", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requires_room: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="appointment_type")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    appointment_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_providers.provider_id"), nullable=False, index=True
    )
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_rooms.room_id"), nullable=True, index=True
    )
    appointment_type_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointment_types.appointment_type_id"), nullable=False, index=True
    )
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="scheduled", index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    no_show_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_scheduling")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="appointments")
    provider: Mapped[ClinicalProvider] = relationship(back_populates="appointments")
    room: Mapped[ClinicalRoom | None] = relationship(back_populates="appointments")
    appointment_type: Mapped[AppointmentType] = relationship(back_populates="appointments")
    resources: Mapped[list["AppointmentResource"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["AppointmentStatusHistory"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )
    screening_sessions: Mapped[list["ClinicalScreeningSession"]] = relationship(back_populates="appointment")
    encounters: Mapped[list["ClinicalEncounter"]] = relationship(back_populates="appointment")
    orders: Mapped[list["ClinicalOrder"]] = relationship(back_populates="appointment")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        parts = [self.patient.first_name, self.patient.middle_name, self.patient.last_name]
        return " ".join(part for part in parts if part)

    @property
    def provider_name(self) -> str:
        return self.provider.full_name if self.provider else ""

    @property
    def room_name(self) -> str | None:
        return self.room.room_name if self.room else None

    @property
    def appointment_type_name(self) -> str:
        return self.appointment_type.name if self.appointment_type else ""

    @property
    def equipment_ids(self) -> list[int]:
        return [resource.equipment_id for resource in self.resources]


class AppointmentResource(Base):
    __tablename__ = "appointment_resources"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    appointment_resource_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointments.appointment_id"), nullable=False, index=True
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_equipment.equipment_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    appointment: Mapped[Appointment] = relationship(back_populates="resources")
    equipment: Mapped[ClinicalEquipment] = relationship(back_populates="appointment_resources")


class AppointmentStatusHistory(Base):
    __tablename__ = "appointment_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointments.appointment_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    appointment: Mapped[Appointment] = relationship(back_populates="status_history")


class ClinicalScreeningSession(Base):
    __tablename__ = "clinical_screening_sessions"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    donor_pk: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=True, index=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointments.appointment_id"), nullable=True, index=True
    )
    template_id: Mapped[str] = mapped_column(String(80), nullable=False, default="minimal_donor_screening_v1")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="not_started", index=True)
    current_outcome: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    supervisor_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_screening")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="screening_sessions")
    donor: Mapped["Donor | None"] = relationship()
    appointment: Mapped[Appointment | None] = relationship(back_populates="screening_sessions")
    answers: Mapped[list["ClinicalScreeningAnswer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    vitals: Mapped[list["ClinicalScreeningVitals"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    outcomes: Mapped[list["ClinicalScreeningOutcome"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    deferrals: Mapped[list["ClinicalDeferral"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    status_history: Mapped[list["ClinicalScreeningStatusHistory"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    encounters: Mapped[list["ClinicalEncounter"]] = relationship(back_populates="screening_session")
    orders: Mapped[list["ClinicalOrder"]] = relationship(back_populates="screening_session")
    care_plans: Mapped[list["ClinicalCarePlan"]] = relationship(back_populates="screening_session")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        parts = [self.patient.first_name, self.patient.middle_name, self.patient.last_name]
        return " ".join(part for part in parts if part)

    @property
    def appointment_number(self) -> str | None:
        return self.appointment.appointment_number if self.appointment else None


class ClinicalScreeningAnswer(Base):
    __tablename__ = "clinical_screening_answers"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    answer_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=False, index=True
    )
    question_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    answer_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    session: Mapped[ClinicalScreeningSession] = relationship(back_populates="answers")


class ClinicalScreeningVitals(Base):
    __tablename__ = "clinical_screening_vitals"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    vitals_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=False, index=True
    )
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    blood_pressure_systolic: Mapped[int] = mapped_column(Integer, nullable=False)
    blood_pressure_diastolic: Mapped[int] = mapped_column(Integer, nullable=False)
    pulse: Mapped[int] = mapped_column(Integer, nullable=False)
    respiration_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oxygen_saturation: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    captured_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    session: Mapped[ClinicalScreeningSession] = relationship(back_populates="vitals")


class ClinicalScreeningOutcome(Base):
    __tablename__ = "clinical_screening_outcomes"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=False, index=True
    )
    proposed_outcome: Mapped[str | None] = mapped_column(String(80), nullable=True)
    committed_outcome: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    original_outcome: Mapped[str | None] = mapped_column(String(80), nullable=True)
    override_outcome: Mapped[str | None] = mapped_column(String(80), nullable=True)
    deferral_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    supervisor_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocking_issues: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    rule_results: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    session: Mapped[ClinicalScreeningSession] = relationship(back_populates="outcomes")


class ClinicalDeferral(Base):
    __tablename__ = "clinical_deferrals"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    deferral_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deferral_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=False, index=True
    )
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    donor_pk: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_donor.donor_pk"), nullable=True, index=True
    )
    deferral_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    session: Mapped[ClinicalScreeningSession] = relationship(back_populates="deferrals")
    patient: Mapped[Patient] = relationship()
    donor: Mapped["Donor | None"] = relationship()

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)


class ClinicalScreeningStatusHistory(Base):
    __tablename__ = "clinical_screening_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    to_status: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    session: Mapped[ClinicalScreeningSession] = relationship(back_populates="status_history")


class ClinicalNoteTemplate(Base):
    __tablename__ = "clinical_note_templates"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    template_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    note_type: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_note", index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sections: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    notes: Mapped[list["ClinicalEncounterNote"]] = relationship(back_populates="template")


class ClinicalEncounter(Base):
    __tablename__ = "clinical_encounters"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    encounter_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    encounter_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointments.appointment_id"), nullable=True, index=True
    )
    screening_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=True, index=True
    )
    encounter_type: Mapped[str] = mapped_column(String(80), nullable=False, default="donor_screening", index=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft", index=True)
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_encounters")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="encounters")
    appointment: Mapped[Appointment | None] = relationship(back_populates="encounters")
    screening_session: Mapped[ClinicalScreeningSession | None] = relationship(back_populates="encounters")
    notes: Mapped[list["ClinicalEncounterNote"]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan"
    )
    diagnoses: Mapped[list["ClinicalEncounterDiagnosis"]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ClinicalEncounterStatusHistory"]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan"
    )
    orders: Mapped[list["ClinicalOrder"]] = relationship(back_populates="encounter")
    care_plans: Mapped[list["ClinicalCarePlan"]] = relationship(back_populates="encounter")
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="encounter")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        parts = [self.patient.first_name, self.patient.middle_name, self.patient.last_name]
        return " ".join(part for part in parts if part)

    @property
    def appointment_number(self) -> str | None:
        return self.appointment.appointment_number if self.appointment else None

    @property
    def screening_session_number(self) -> str | None:
        return self.screening_session.session_number if self.screening_session else None

    @property
    def allergies(self) -> list["ClinicalPatientAllergy"]:
        return self.patient.allergies if self.patient else []

    @property
    def medications(self) -> list["ClinicalPatientMedication"]:
        return self.patient.medications if self.patient else []


class ClinicalEncounterNote(Base):
    __tablename__ = "clinical_encounter_notes"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=False, index=True
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_note_templates.template_id"), nullable=True, index=True
    )
    note_type: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_note", index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False, default="Clinical encounter note")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_addendum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    amended_from_note_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounter_notes.note_id"), nullable=True, index=True
    )
    amendment_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    encounter: Mapped[ClinicalEncounter] = relationship(back_populates="notes")
    template: Mapped[ClinicalNoteTemplate | None] = relationship(back_populates="notes")

    @property
    def template_name(self) -> str | None:
        return self.template.name if self.template else None

    @property
    def locked(self) -> bool:
        return self.status in {"signed", "amended"}


class ClinicalEncounterDiagnosis(Base):
    __tablename__ = "clinical_encounter_diagnoses"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    diagnosis_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(220), nullable=False)
    diagnosis_type: Mapped[str] = mapped_column(String(80), nullable=False, default="problem", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    encounter: Mapped[ClinicalEncounter] = relationship(back_populates="diagnoses")


class ClinicalPatientAllergy(Base):
    __tablename__ = "clinical_patient_allergies"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    allergy_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    allergen: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    reaction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="allergies")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)


class ClinicalPatientMedication(Base):
    __tablename__ = "clinical_patient_medications"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    medication_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    medication_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    dose: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    route: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    frequency: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="medications")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)


class ClinicalEncounterStatusHistory(Base):
    __tablename__ = "clinical_encounter_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    to_status: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    encounter: Mapped[ClinicalEncounter] = relationship(back_populates="status_history")


class ClinicalOrderCatalogItem(Base):
    __tablename__ = "clinical_order_catalog_items"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    catalog_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    order_type: Mapped[str] = mapped_column(String(80), nullable=False, default="laboratory", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_priority: Mapped[str] = mapped_column(String(40), nullable=False, default="routine")
    specimen_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    orders: Mapped[list["ClinicalOrder"]] = relationship(back_populates="catalog_item")


class ClinicalOrder(Base):
    __tablename__ = "clinical_orders"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=True, index=True
    )
    screening_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=True, index=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointments.appointment_id"), nullable=True, index=True
    )
    catalog_item_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_catalog_items.catalog_item_id"),
        nullable=False,
        index=True,
    )
    order_type: Mapped[str] = mapped_column(String(80), nullable=False, default="laboratory", index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="routine", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ordered", index=True)
    clinical_indication: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ordering_provider: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_orders")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="orders")
    encounter: Mapped[ClinicalEncounter | None] = relationship(back_populates="orders")
    screening_session: Mapped[ClinicalScreeningSession | None] = relationship(back_populates="orders")
    appointment: Mapped[Appointment | None] = relationship(back_populates="orders")
    catalog_item: Mapped[ClinicalOrderCatalogItem] = relationship(back_populates="orders")
    results: Mapped[list["ClinicalOrderResult"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    acknowledgements: Mapped[list["ClinicalOrderResultAcknowledgement"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ClinicalOrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    care_plans: Mapped[list["ClinicalCarePlan"]] = relationship(back_populates="order")
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="order")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        parts = [self.patient.first_name, self.patient.middle_name, self.patient.last_name]
        return " ".join(part for part in parts if part)

    @property
    def encounter_number(self) -> str | None:
        return self.encounter.encounter_number if self.encounter else None

    @property
    def screening_session_number(self) -> str | None:
        return self.screening_session.session_number if self.screening_session else None

    @property
    def appointment_number(self) -> str | None:
        return self.appointment.appointment_number if self.appointment else None

    @property
    def catalog_code(self) -> str:
        return self.catalog_item.code if self.catalog_item else ""

    @property
    def catalog_name(self) -> str:
        return self.catalog_item.name if self.catalog_item else ""

    @property
    def has_critical_unacknowledged(self) -> bool:
        acknowledged_result_ids = {
            acknowledgement.result_id
            for acknowledgement in self.acknowledgements
            if acknowledgement.result_id is not None
        }
        acknowledged_order = any(acknowledgement.result_id is None for acknowledgement in self.acknowledgements)
        return any(
            result.critical_flag
            and result.result_status != "cancelled"
            and not acknowledged_order
            and result.result_id not in acknowledged_result_ids
            for result in self.results
        )

    @property
    def result_flag(self) -> str:
        active_results = [result for result in self.results if result.result_status != "cancelled"]
        if any(result.critical_flag for result in active_results):
            return "critical"
        if any(result.abnormal_flag for result in active_results):
            return "abnormal"
        if active_results:
            return "normal"
        return "pending"


class ClinicalOrderResult(Base):
    __tablename__ = "clinical_order_results"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=False, index=True
    )
    result_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    result_value: Mapped[str] = mapped_column(String(180), nullable=False)
    result_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(160), nullable=True)
    result_status: Mapped[str] = mapped_column(String(40), nullable=False, default="normal", index=True)
    abnormal_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    critical_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resulted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    resulted_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    corrected_from_result_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_results.result_id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    order: Mapped[ClinicalOrder] = relationship(back_populates="results")
    care_plans: Mapped[list["ClinicalCarePlan"]] = relationship(back_populates="order_result")
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="order_result")

    @property
    def requires_acknowledgement(self) -> bool:
        return self.critical_flag and self.result_status != "cancelled"


class ClinicalOrderResultAcknowledgement(Base):
    __tablename__ = "clinical_order_result_acknowledgements"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    acknowledgement_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=False, index=True
    )
    result_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_results.result_id"), nullable=True, index=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    acknowledged_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    acknowledgement_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    order: Mapped[ClinicalOrder] = relationship(back_populates="acknowledgements")


class ClinicalOrderStatusHistory(Base):
    __tablename__ = "clinical_order_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    order: Mapped[ClinicalOrder] = relationship(back_populates="status_history")


class ClinicalCarePlan(Base):
    __tablename__ = "clinical_care_plans"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    care_plan_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=True, index=True
    )
    screening_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=True, index=True
    )
    order_result_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_results.result_id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    plan_type: Mapped[str] = mapped_column(String(80), nullable=False, default="case_management", index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="routine", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_care_plans")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="care_plans")
    encounter: Mapped[ClinicalEncounter | None] = relationship(back_populates="care_plans")
    screening_session: Mapped[ClinicalScreeningSession | None] = relationship(back_populates="care_plans")
    order: Mapped[ClinicalOrder | None] = relationship(back_populates="care_plans")
    order_result: Mapped[ClinicalOrderResult | None] = relationship(back_populates="care_plans")
    goals: Mapped[list["ClinicalCarePlanGoal"]] = relationship(
        back_populates="care_plan", cascade="all, delete-orphan"
    )
    interventions: Mapped[list["ClinicalCarePlanIntervention"]] = relationship(
        back_populates="care_plan", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["ClinicalCarePlanTask"]] = relationship(
        back_populates="care_plan", cascade="all, delete-orphan"
    )
    progress_notes: Mapped[list["ClinicalCarePlanProgressNote"]] = relationship(
        back_populates="care_plan", cascade="all, delete-orphan"
    )
    team_members: Mapped[list["ClinicalCarePlanTeamMember"]] = relationship(
        back_populates="care_plan", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ClinicalCarePlanStatusHistory"]] = relationship(
        back_populates="care_plan", cascade="all, delete-orphan"
    )
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="care_plan")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        parts = [self.patient.first_name, self.patient.middle_name, self.patient.last_name]
        return " ".join(part for part in parts if part)

    @property
    def encounter_number(self) -> str | None:
        return self.encounter.encounter_number if self.encounter else None

    @property
    def screening_session_number(self) -> str | None:
        return self.screening_session.session_number if self.screening_session else None

    @property
    def order_number(self) -> str | None:
        return self.order.order_number if self.order else None

    @property
    def order_result_summary(self) -> str | None:
        if not self.order_result:
            return None
        return f"{self.order_result.result_name}: {self.order_result.result_value}"

    @property
    def result_flag(self) -> str:
        if self.order_result:
            if self.order_result.critical_flag:
                return "critical"
            if self.order_result.abnormal_flag:
                return "abnormal"
            return self.order_result.result_status
        return self.order.result_flag if self.order else "none"

    @property
    def has_critical_unacknowledged(self) -> bool:
        return self.order.has_critical_unacknowledged if self.order else False


class ClinicalCarePlanGoal(Base):
    __tablename__ = "clinical_care_plan_goals"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    goal_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=False, index=True
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    priority: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    care_plan: Mapped[ClinicalCarePlan] = relationship(back_populates="goals")


class ClinicalCarePlanIntervention(Base):
    __tablename__ = "clinical_care_plan_interventions"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    intervention_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=False, index=True
    )
    intervention: Mapped[str] = mapped_column(Text, nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(80), nullable=False, default="follow_up", index=True)
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="planned", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    care_plan: Mapped[ClinicalCarePlan] = relationship(back_populates="interventions")


class ClinicalCarePlanTask(Base):
    __tablename__ = "clinical_care_plan_tasks"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="routine", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    care_plan: Mapped[ClinicalCarePlan] = relationship(back_populates="tasks")
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="care_plan_task")


class ClinicalCarePlanProgressNote(Base):
    __tablename__ = "clinical_care_plan_progress_notes"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    progress_note_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=False, index=True
    )
    progress_note: Mapped[str] = mapped_column(Text, nullable=False)
    status_update: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    care_plan: Mapped[ClinicalCarePlan] = relationship(back_populates="progress_notes")


class ClinicalCarePlanTeamMember(Base):
    __tablename__ = "clinical_care_plan_team_members"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    team_member_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=False, index=True
    )
    member_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(80), nullable=False, default="care_team", index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    care_plan: Mapped[ClinicalCarePlan] = relationship(back_populates="team_members")


class ClinicalCarePlanStatusHistory(Base):
    __tablename__ = "clinical_care_plan_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    care_plan_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    care_plan: Mapped[ClinicalCarePlan] = relationship(back_populates="status_history")


class ClinicalBillingAccount(Base):
    __tablename__ = "clinical_billing_accounts"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    account_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    primary_insurance_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patient_insurance.insurance_id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    total_charges: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_payments: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_adjustments: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient] = relationship(back_populates="billing_accounts")
    primary_insurance: Mapped[PatientInsurance | None] = relationship(back_populates="billing_accounts")
    charges: Mapped[list["ClinicalCharge"]] = relationship(back_populates="billing_account")
    claims: Mapped[list["ClinicalClaim"]] = relationship(back_populates="billing_account")
    payments: Mapped[list["ClinicalPayment"]] = relationship(back_populates="billing_account")
    status_history: Mapped[list["ClinicalBillingStatusHistory"]] = relationship(back_populates="billing_account")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)

    @property
    def payer_name(self) -> str | None:
        return self.primary_insurance.payer_name if self.primary_insurance else None


class ClinicalInsuranceVerification(Base):
    __tablename__ = "clinical_insurance_verifications"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    verification_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    patient_insurance_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patient_insurance.insurance_id"), nullable=True, index=True
    )
    verification_status: Mapped[str] = mapped_column(String(80), nullable=False, default="verified", index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    payer_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    plan_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    member_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    group_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    coverage_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    patient: Mapped[Patient] = relationship(back_populates="insurance_verifications")
    patient_insurance: Mapped[PatientInsurance | None] = relationship(back_populates="insurance_verifications")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)


class ClinicalCharge(Base):
    __tablename__ = "clinical_charges"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    charge_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    charge_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    billing_account_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_billing_accounts.account_id"), nullable=False, index=True
    )
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=True, index=True
    )
    order_result_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_results.result_id"), nullable=True, index=True
    )
    care_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=True, index=True
    )
    care_plan_task_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plan_tasks.task_id"), nullable=True, index=True
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    code_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="captured", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    billing_account: Mapped[ClinicalBillingAccount] = relationship(back_populates="charges")
    patient: Mapped[Patient] = relationship(back_populates="charges")
    encounter: Mapped[ClinicalEncounter | None] = relationship(back_populates="charges")
    order: Mapped[ClinicalOrder | None] = relationship(back_populates="charges")
    order_result: Mapped[ClinicalOrderResult | None] = relationship(back_populates="charges")
    care_plan: Mapped[ClinicalCarePlan | None] = relationship(back_populates="charges")
    care_plan_task: Mapped[ClinicalCarePlanTask | None] = relationship(back_populates="charges")
    claim_lines: Mapped[list["ClinicalClaimLine"]] = relationship(back_populates="charge")
    status_history: Mapped[list["ClinicalBillingStatusHistory"]] = relationship(back_populates="charge")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)

    @property
    def account_number(self) -> str:
        return self.billing_account.account_number if self.billing_account else ""

    @property
    def encounter_number(self) -> str | None:
        return self.encounter.encounter_number if self.encounter else None

    @property
    def order_number(self) -> str | None:
        return self.order.order_number if self.order else None

    @property
    def order_result_summary(self) -> str | None:
        if not self.order_result:
            return None
        return f"{self.order_result.result_name}: {self.order_result.result_value}"

    @property
    def care_plan_number(self) -> str | None:
        return self.care_plan.care_plan_number if self.care_plan else None

    @property
    def care_plan_task_title(self) -> str | None:
        return self.care_plan_task.title if self.care_plan_task else None


class ClinicalClaim(Base):
    __tablename__ = "clinical_claims"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    claim_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    billing_account_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_billing_accounts.account_id"), nullable=False, index=True
    )
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    patient_insurance_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patient_insurance.insurance_id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready_for_review", index=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    adjustment_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    billing_account: Mapped[ClinicalBillingAccount] = relationship(back_populates="claims")
    patient: Mapped[Patient] = relationship(back_populates="claims")
    patient_insurance: Mapped[PatientInsurance | None] = relationship(back_populates="claims")
    lines: Mapped[list["ClinicalClaimLine"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    payments: Mapped[list["ClinicalPayment"]] = relationship(back_populates="claim")
    denials: Mapped[list["ClinicalDenial"]] = relationship(back_populates="claim")
    status_history: Mapped[list["ClinicalBillingStatusHistory"]] = relationship(back_populates="claim")

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)

    @property
    def account_number(self) -> str:
        return self.billing_account.account_number if self.billing_account else ""

    @property
    def payer_name(self) -> str | None:
        return self.patient_insurance.payer_name if self.patient_insurance else None


class ClinicalClaimLine(Base):
    __tablename__ = "clinical_claim_lines"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    line_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_claims.claim_id"), nullable=False, index=True
    )
    charge_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_charges.charge_id"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    code_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    line_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    diagnosis_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready_for_review", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    claim: Mapped[ClinicalClaim] = relationship(back_populates="lines")
    charge: Mapped[ClinicalCharge] = relationship(back_populates="claim_lines")
    denials: Mapped[list["ClinicalDenial"]] = relationship(back_populates="claim_line")

    @property
    def charge_number(self) -> str:
        return self.charge.charge_number if self.charge else str(self.charge_id)


class ClinicalPayment(Base):
    __tablename__ = "clinical_payments"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_claims.claim_id"), nullable=False, index=True
    )
    billing_account_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_billing_accounts.account_id"), nullable=False, index=True
    )
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    payment_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    adjustment_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payment_method: Mapped[str] = mapped_column(String(80), nullable=False, default="eft")
    payer_type: Mapped[str] = mapped_column(String(80), nullable=False, default="insurance")
    reference_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    posted_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    claim: Mapped[ClinicalClaim] = relationship(back_populates="payments")
    billing_account: Mapped[ClinicalBillingAccount] = relationship(back_populates="payments")
    patient: Mapped[Patient] = relationship(back_populates="payments")

    @property
    def claim_number(self) -> str:
        return self.claim.claim_number if self.claim else str(self.claim_id)

    @property
    def account_number(self) -> str:
        return self.billing_account.account_number if self.billing_account else str(self.billing_account_id)

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)


class ClinicalDenial(Base):
    __tablename__ = "clinical_denials"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    denial_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_claims.claim_id"), nullable=False, index=True
    )
    claim_line_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_claim_lines.line_id"), nullable=True, index=True
    )
    denial_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    denial_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    claim: Mapped[ClinicalClaim] = relationship(back_populates="denials")
    claim_line: Mapped[ClinicalClaimLine | None] = relationship(back_populates="denials")

    @property
    def claim_number(self) -> str:
        return self.claim.claim_number if self.claim else str(self.claim_id)


class ClinicalBillingStatusHistory(Base):
    __tablename__ = "clinical_billing_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_account_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_billing_accounts.account_id"), nullable=True, index=True
    )
    claim_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_claims.claim_id"), nullable=True, index=True
    )
    charge_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_charges.charge_id"), nullable=True, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    billing_account: Mapped[ClinicalBillingAccount | None] = relationship(back_populates="status_history")
    claim: Mapped[ClinicalClaim | None] = relationship(back_populates="status_history")
    charge: Mapped[ClinicalCharge | None] = relationship(back_populates="status_history")


class ClinicalQualityEvent(Base):
    __tablename__ = "clinical_quality_events"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    patient_pk: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=True, index=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.appointments.appointment_id"), nullable=True, index=True
    )
    screening_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=True, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=True, index=True
    )
    order_result_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_results.result_id"), nullable=True, index=True
    )
    care_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=True, index=True
    )
    charge_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_charges.charge_id"), nullable=True, index=True
    )
    claim_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_claims.claim_id"), nullable=True, index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_payments.payment_id"), nullable=True, index=True
    )
    denial_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_denials.denial_id"), nullable=True, index=True
    )
    deviation_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_deviation.deviation_id"), nullable=True, index=True
    )
    capa_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.fact_capa.capa_id"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    source_module: Mapped[str] = mapped_column(String(80), nullable=False, default="clinical_quality", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patient: Mapped[Patient | None] = relationship()
    appointment: Mapped[Appointment | None] = relationship()
    screening_session: Mapped[ClinicalScreeningSession | None] = relationship()
    encounter: Mapped[ClinicalEncounter | None] = relationship()
    order: Mapped[ClinicalOrder | None] = relationship()
    order_result: Mapped[ClinicalOrderResult | None] = relationship()
    care_plan: Mapped[ClinicalCarePlan | None] = relationship()
    charge: Mapped[ClinicalCharge | None] = relationship()
    claim: Mapped[ClinicalClaim | None] = relationship()
    payment: Mapped[ClinicalPayment | None] = relationship()
    denial: Mapped[ClinicalDenial | None] = relationship()
    deviation: Mapped["Deviation | None"] = relationship()
    capa: Mapped["CAPA | None"] = relationship()
    investigations: Mapped[list["ClinicalQualityInvestigation"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["ClinicalQualityApproval"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    links: Mapped[list["ClinicalQualityEventLink"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ClinicalQualityStatusHistory"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    @property
    def patient_id(self) -> str | None:
        return self.patient.patient_id if self.patient else None

    @property
    def patient_name(self) -> str | None:
        if not self.patient:
            return None
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)

    @property
    def appointment_number(self) -> str | None:
        return self.appointment.appointment_number if self.appointment else None

    @property
    def screening_session_number(self) -> str | None:
        return self.screening_session.session_number if self.screening_session else None

    @property
    def encounter_number(self) -> str | None:
        return self.encounter.encounter_number if self.encounter else None

    @property
    def order_number(self) -> str | None:
        return self.order.order_number if self.order else None

    @property
    def order_result_summary(self) -> str | None:
        if not self.order_result:
            return None
        return f"{self.order_result.result_name}: {self.order_result.result_value}"

    @property
    def care_plan_number(self) -> str | None:
        return self.care_plan.care_plan_number if self.care_plan else None

    @property
    def charge_number(self) -> str | None:
        return self.charge.charge_number if self.charge else None

    @property
    def claim_number(self) -> str | None:
        return self.claim.claim_number if self.claim else None

    @property
    def payment_reference(self) -> str | None:
        return self.payment.reference_number if self.payment else None

    @property
    def denial_code(self) -> str | None:
        return self.denial.denial_code if self.denial else None

    @property
    def deviation_code(self) -> str | None:
        return self.deviation.deviation_code if self.deviation else None

    @property
    def capa_code(self) -> str | None:
        return self.capa.capa_code if self.capa else None


class ClinicalAdverseEvent(Base):
    __tablename__ = "clinical_adverse_events"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    adverse_event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    adverse_event_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    quality_event_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_quality_events.event_id"), nullable=True, index=True
    )
    patient_pk: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.patients.patient_pk"), nullable=False, index=True
    )
    screening_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_screening_sessions.session_id"), nullable=True, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_encounters.encounter_id"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_orders.order_id"), nullable=True, index=True
    )
    order_result_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_order_results.result_id"), nullable=True, index=True
    )
    care_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_care_plans.care_plan_id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    immediate_action_taken: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reporter: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    quality_event: Mapped[ClinicalQualityEvent | None] = relationship()
    patient: Mapped[Patient] = relationship()
    screening_session: Mapped[ClinicalScreeningSession | None] = relationship()
    encounter: Mapped[ClinicalEncounter | None] = relationship()
    order: Mapped[ClinicalOrder | None] = relationship()
    order_result: Mapped[ClinicalOrderResult | None] = relationship()
    care_plan: Mapped[ClinicalCarePlan | None] = relationship()

    @property
    def patient_id(self) -> str:
        return self.patient.patient_id if self.patient else str(self.patient_pk)

    @property
    def patient_name(self) -> str:
        if not self.patient:
            return ""
        return " ".join(part for part in [self.patient.first_name, self.patient.middle_name, self.patient.last_name] if part)

    @property
    def quality_event_number(self) -> str | None:
        return self.quality_event.event_number if self.quality_event else None

    @property
    def screening_session_number(self) -> str | None:
        return self.screening_session.session_number if self.screening_session else None

    @property
    def encounter_number(self) -> str | None:
        return self.encounter.encounter_number if self.encounter else None

    @property
    def order_number(self) -> str | None:
        return self.order.order_number if self.order else None

    @property
    def order_result_summary(self) -> str | None:
        if not self.order_result:
            return None
        return f"{self.order_result.result_name}: {self.order_result.result_value}"

    @property
    def care_plan_number(self) -> str | None:
        return self.care_plan.care_plan_number if self.care_plan else None


class ClinicalQualityEventLink(Base):
    __tablename__ = "clinical_quality_event_links"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    link_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_quality_events.event_id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(220), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    event: Mapped[ClinicalQualityEvent] = relationship(back_populates="links")


class ClinicalQualityInvestigation(Base):
    __tablename__ = "clinical_quality_investigations"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    investigation_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_quality_events.event_id"), nullable=False, index=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    corrective_action_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    event: Mapped[ClinicalQualityEvent] = relationship(back_populates="investigations")


class ClinicalQualityApproval(Base):
    __tablename__ = "clinical_quality_approvals"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_quality_events.event_id"), nullable=False, index=True
    )
    approval_type: Mapped[str] = mapped_column(String(80), nullable=False, default="closure", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="approved", index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )

    event: Mapped[ClinicalQualityEvent] = relationship(back_populates="approvals")


class ClinicalComplianceExport(Base):
    __tablename__ = "clinical_compliance_exports"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    export_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    export_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    modules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evidence_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="generated", index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    generated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )


class ClinicalQualityStatusHistory(Base):
    __tablename__ = "clinical_quality_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_quality_events.event_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    event: Mapped[ClinicalQualityEvent] = relationship(back_populates="status_history")


class ClinicalAdminConfigVersion(Base):
    __tablename__ = "clinical_admin_config_versions"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    config_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    change_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ClinicalProviderScheduleTemplate(Base):
    __tablename__ = "clinical_provider_schedule_templates"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    schedule_template_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_providers.provider_id"), nullable=False, index=True
    )
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    date_pattern: Mapped[str] = mapped_column(String(80), nullable=False, default="weekly", index=True)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_rooms.room_id"), nullable=True, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    provider: Mapped[ClinicalProvider] = relationship()
    room: Mapped[ClinicalRoom | None] = relationship()

    @property
    def provider_name(self) -> str:
        return self.provider.full_name if self.provider else ""

    @property
    def room_name(self) -> str | None:
        return self.room.room_name if self.room else None


class ClinicalScreeningTemplateVersion(Base):
    __tablename__ = "clinical_screening_template_versions"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    template_version_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    required_questions: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ClinicalEligibilityRuleVersion(Base):
    __tablename__ = "clinical_eligibility_rule_versions"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    rule_version_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(80), nullable=False, default="eligibility", index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="medium", index=True)
    expression: Mapped[str] = mapped_column(Text, nullable=False, default="")
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ClinicalDeferralRuleVersion(Base):
    __tablename__ = "clinical_deferral_rule_versions"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    rule_version_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(80), nullable=False, default="deferral", index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="medium", index=True)
    expression: Mapped[str] = mapped_column(Text, nullable=False, default="")
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ClinicalBillingCodeCatalog(Base):
    __tablename__ = "clinical_billing_code_catalog"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    code_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    code_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ClinicalQualityCategory(Base):
    __tablename__ = "clinical_quality_categories"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    severity_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    closure_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ClinicalQualitySeverityMatrix(Base):
    __tablename__ = "clinical_quality_severity_matrix"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    matrix_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    severity: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    response_sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    investigation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ClinicalAdminApprovalPath(Base):
    __tablename__ = "clinical_admin_approval_paths"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    path_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    path_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    steps: Mapped[list["ClinicalAdminApprovalStep"]] = relationship(
        back_populates="path", cascade="all, delete-orphan"
    )


class ClinicalAdminApprovalStep(Base):
    __tablename__ = "clinical_admin_approval_steps"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    step_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    path_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_admin_approval_paths.path_id"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    permission: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    path: Mapped[ClinicalAdminApprovalPath] = relationship(back_populates="steps")


class ClinicalNotificationTemplate(Base):
    __tablename__ = "clinical_notification_templates"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    notification_template_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False, default="in_app", index=True)
    subject: Mapped[str] = mapped_column(String(220), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ClinicalAdminStatusHistory(Base):
    __tablename__ = "clinical_admin_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    config_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    config_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ClinicalWorkflowAuditEvent(Base):
    __tablename__ = "clinical_workflow_audit_events"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operation_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    workflow: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    preview_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    commit_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    status_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    changes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="workflow_commit", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class ClinicalWorkflowAuditMirrorEvent(Base):
    __tablename__ = "clinical_workflow_audit_mirror_events"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    mirror_event_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operation_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    mirror_mode: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    mirror_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    payload_profile: Mapped[str] = mapped_column(String(80), nullable=False, default="audit_metadata", index=True)
    mirrored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    mirror_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    mirror_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    mirror_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class ClinicalReportExport(Base):
    __tablename__ = "clinical_report_exports"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    export_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    export_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    modules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    export_format: Mapped[str] = mapped_column(String(20), nullable=False, default="json", index=True)
    row_counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="generated", index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    generated_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    items: Mapped[list["ClinicalReportExportItem"]] = relationship(
        back_populates="export", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ClinicalReportStatusHistory"]] = relationship(
        back_populates="export", cascade="all, delete-orphan"
    )


class ClinicalReportExportItem(Base):
    __tablename__ = "clinical_report_export_items"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    export_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_report_exports.export_id"), nullable=False, index=True
    )
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    report_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    export: Mapped[ClinicalReportExport] = relationship(back_populates="items")


class ClinicalReportStatusHistory(Base):
    __tablename__ = "clinical_report_status_history"
    __table_args__ = {"schema": OPERATIONAL_SCHEMA}

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    export_id: Mapped[int] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.clinical_report_exports.export_id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey(f"{OPERATIONAL_SCHEMA}.dim_user.user_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    export: Mapped[ClinicalReportExport] = relationship(back_populates="status_history")


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

