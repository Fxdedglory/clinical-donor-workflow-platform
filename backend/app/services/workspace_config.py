from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Role,
    RoleDashboardWidget,
    RoleNavigationConfig,
    RoleWorkspaceConfig,
    WorkflowAssignmentRule,
    WorkflowStateMachine,
    WorkflowTransitionRule,
)


def _tab(label: str, page_key: str, permission: str | None = None) -> dict[str, str | None]:
    return {"label": label, "page_key": page_key, "required_permission": permission}


WORKSPACE_DEFINITIONS: dict[str, dict] = {
    "Donor Intake Coordinator": {
        "workspace_name": "Donor Intake Operations Workspace",
        "workspace_purpose": "Validate donor intake packets, resolve missing documentation, and route complete cases to clinical review.",
        "default_queue": "My Intake Workbench",
        "visible_tabs": [
            _tab("Intake Dashboard", "role_dashboard", "dashboard.view"),
            _tab("Intake Queue", "intake_queue", "donors.read"),
            _tab("Intake Tasks", "role_tasks", "tasks.read"),
            _tab("Donor Intake Form", "donor_intake_form", "donors.create"),
            _tab("My Escalations", "role_escalations", "tasks.read"),
        ],
        "widgets": [
            ("pending_intake_packages", "Pending Intake Packages", "metric"),
            ("incomplete_submissions", "Incomplete Submissions", "metric"),
            ("avg_intake_completion", "Avg Intake Completion Time", "metric"),
            ("intake_sla_status", "Intake SLA Status", "metric"),
            ("urgent_donor_intakes", "Urgent Donor Intakes", "metric"),
            ("intake_queue", "Intake Queue", "table"),
            ("missing_documentation", "Missing Documentation", "table"),
            ("sla_countdown", "SLA Countdown", "table"),
        ],
        "workbench_columns": [
            "donor_id",
            "donor_name",
            "submission_status",
            "missing_documents",
            "priority",
            "assigned_date",
            "due_date",
        ],
        "notification_types": ["Intake Rejected", "Missing Documentation", "Urgent Intake Assignment"],
        "theme_config": {"accent": "#127c75", "density": "focused"},
    },
    "Clinical Reviewer": {
        "workspace_name": "Clinical Review Workspace",
        "workspace_purpose": "Review donor eligibility, investigate AI risk signals, and escalate clinical exceptions.",
        "default_queue": "Clinical Review Workbench",
        "visible_tabs": [
            _tab("Clinical Dashboard", "role_dashboard", "dashboard.view"),
            _tab("Review Queue", "clinical_review_queue", "donors.review"),
            _tab("High Risk Cases", "high_risk_cases", "donors.review"),
            _tab("Escalations", "role_escalations", "tasks.read"),
            _tab("My Tasks", "role_tasks", "tasks.read"),
        ],
        "widgets": [
            ("pending_clinical_reviews", "Pending Clinical Reviews", "metric"),
            ("high_risk_donors", "High Risk Donors", "metric"),
            ("avg_review_turnaround", "Avg Review Turnaround", "metric"),
            ("escalated_cases", "Escalated Cases", "metric"),
            ("sla_risk_cases", "SLA Risk Cases", "metric"),
            ("high_risk_queue", "High Risk Queue", "table"),
            ("review_sla_timer", "Review SLA Timer", "table"),
            ("escalation_feed", "Escalation Feed", "table"),
        ],
        "workbench_columns": [
            "donor_id",
            "risk_score",
            "infectious_flags",
            "workflow_status",
            "sla_timer",
            "escalation_status",
            "assigned_date",
        ],
        "notification_types": ["New Donor Assigned", "SLA Nearing Breach", "Escalated Review"],
        "theme_config": {"accent": "#2b6cb0", "density": "clinical"},
    },
    "Quality Assurance Specialist": {
        "workspace_name": "Quality Assurance Workspace",
        "workspace_purpose": "Own investigations, CAPA follow-up, deviations, SOP compliance, and audit exceptions.",
        "default_queue": "QA Investigation Workbench",
        "visible_tabs": [
            _tab("QA Dashboard", "role_dashboard", "dashboard.view"),
            _tab("Investigations", "qa_investigations", "change_control.manage"),
            _tab("CAPA Queue", "capa_queue", "change_control.manage"),
            _tab("Deviations", "deviations", "audit.review"),
            _tab("SOP Compliance", "sop_compliance", "training.manage"),
        ],
        "widgets": [
            ("open_investigations", "Open Investigations", "metric"),
            ("capa_aging", "CAPA Aging", "metric"),
            ("sop_deviations", "SOP Deviations", "metric"),
            ("audit_exceptions", "Audit Exceptions", "metric"),
            ("compliance_risk_score", "Compliance Risk Score", "metric"),
            ("investigation_queue", "Investigation Queue", "table"),
            ("sop_compliance", "SOP Compliance", "table"),
            ("capa_aging_widget", "CAPA Aging", "table"),
            ("deviation_heatmap", "Deviation Heatmap", "table"),
        ],
        "workbench_columns": [
            "request_id",
            "risk_level",
            "approval_status",
            "capa_required",
            "implementation_due_date",
            "workflow_state",
        ],
        "notification_types": ["New Investigation", "SOP Deviation", "Unresolved CAPA"],
        "theme_config": {"accent": "#6b46c1", "density": "compliance"},
    },
    "Vendor Operations Analyst": {
        "workspace_name": "Vendor Operations Workspace",
        "workspace_purpose": "Monitor vendor-supported systems, manage SLA incidents, and coordinate vendor escalations.",
        "default_queue": "Vendor Operations Workbench",
        "visible_tabs": [
            _tab("Vendor Dashboard", "role_dashboard", "dashboard.view"),
            _tab("SLA Monitor", "sla_monitor", "vendors.manage"),
            _tab("Incident Queue", "incident_queue", "vendors.manage"),
            _tab("Vendor Escalations", "role_escalations", "tasks.read"),
            _tab("My Tasks", "role_tasks", "tasks.read"),
        ],
        "widgets": [
            ("vendor_uptime", "Vendor Uptime", "metric"),
            ("open_incidents", "Open Incidents", "metric"),
            ("sla_breaches", "SLA Breaches", "metric"),
            ("avg_resolution_time", "Avg Resolution Time", "metric"),
            ("critical_outages", "Critical Outages", "metric"),
            ("live_sla_monitor", "Live SLA Monitor", "table"),
            ("incident_heatmap", "Incident Heatmap", "table"),
            ("vendor_status_feed", "Vendor Status Feed", "table"),
            ("escalation_timeline", "Escalation Timeline", "table"),
        ],
        "workbench_columns": [
            "ticket_number",
            "vendor",
            "severity",
            "status",
            "sla_breached",
            "ticket_age_hours",
            "due_date",
        ],
        "notification_types": ["SLA Breach", "Outage Alert", "Critical Escalation"],
        "theme_config": {"accent": "#c05621", "density": "operations"},
    },
    "Operations Manager": {
        "workspace_name": "Enterprise Operations Command Center",
        "workspace_purpose": "Oversee cross-functional backlog, staffing load, escalations, throughput, and SLA health.",
        "default_queue": "Enterprise Queue Management",
        "visible_tabs": [
            _tab("Enterprise Operations", "role_dashboard", "dashboard.view"),
            _tab("Workforce Analytics", "workforce_analytics", "tasks.manage"),
            _tab("Escalation Center", "role_escalations", "escalations.manage"),
            _tab("Enterprise SLA", "enterprise_sla", "vendors.read"),
            _tab("Queue Management", "queue_management", "tasks.manage"),
        ],
        "widgets": [
            ("enterprise_backlog", "Enterprise Backlog", "metric"),
            ("escalated_workflows", "Escalated Workflows", "metric"),
            ("staffing_load", "Staffing Load", "metric"),
            ("sla_compliance", "SLA Compliance", "metric"),
            ("workflow_throughput", "Workflow Throughput", "metric"),
            ("enterprise_queue_health", "Enterprise Queue Health", "table"),
            ("workforce_utilization", "Workforce Utilization", "table"),
            ("escalation_feed", "Escalation Feed", "table"),
            ("bottleneck_analysis", "Bottleneck Analysis", "table"),
        ],
        "workbench_columns": [
            "task_id",
            "queue_name",
            "owner_role",
            "priority",
            "status",
            "workflow_state",
            "due_date",
        ],
        "notification_types": ["Enterprise Bottleneck", "Staffing Overload", "Unresolved Escalation"],
        "theme_config": {"accent": "#243141", "density": "command_center"},
    },
    "System Administrator": {
        "workspace_name": "Platform Governance Workspace",
        "workspace_purpose": "Govern users, roles, workspace configuration, workflow rules, audit administration, and integrations.",
        "default_queue": "Platform Governance Queue",
        "visible_tabs": [
            _tab("User Administration", "admin_users", "users.manage"),
            _tab("Role Configuration", "admin_roles", "roles.manage"),
            _tab("Workspace Configuration", "workspace_configuration", "workflow.configure"),
            _tab("Workflow Configuration", "workflow_configuration", "workflow.configure"),
            _tab("Audit Administration", "audit_administration", "audit.review"),
            _tab("Responsibility Center", "responsibility_center", "system.admin"),
            _tab("System Health", "system_health", "system.admin"),
            _tab("Integration Management", "integration_management", "system.admin"),
        ],
        "widgets": [
            ("active_users", "Active Users", "metric"),
            ("configured_roles", "Configured Roles", "metric"),
            ("workspace_configs", "Workspace Configurations", "metric"),
            ("workflow_rules", "Workflow Rules", "metric"),
            ("audit_events", "Audit Events", "metric"),
            ("workspace_matrix", "Workspace Matrix", "table"),
            ("role_governance", "Role Governance", "table"),
            ("system_health", "System Health", "table"),
        ],
        "workbench_columns": ["role", "workspace", "visible_tabs", "widgets", "default_queue"],
        "notification_types": ["System", "Audit", "Configuration"],
        "theme_config": {"accent": "#0b2738", "density": "governance"},
    },
}

WORKFLOW_STATES = [
    ("Draft Intake", "Intake", "Donor Intake Coordinator", False),
    ("Pending Intake Review", "Intake", "Donor Intake Coordinator", False),
    ("Pending Clinical Review", "Clinical", "Clinical Reviewer", False),
    ("Clinical Escalation", "Clinical", "Operations Manager", False),
    ("Pending QA Review", "Quality", "Quality Assurance Specialist", False),
    ("CAPA Investigation", "Quality", "Quality Assurance Specialist", False),
    ("Vendor SLA Investigation", "Vendor", "Vendor Operations Analyst", False),
    ("Approved", "Terminal", None, True),
    ("Rejected", "Terminal", None, True),
    ("Closed", "Terminal", None, True),
]

WORKFLOW_TRANSITIONS = [
    ("submit_to_clinical_review", "Submit for Clinical Review", "Draft Intake", "Pending Clinical Review", "Donor Intake Coordinator", "Clinical Reviewer", "Donor Review Task", "New Donor Assigned", "SUBMIT_TO_CLINICAL_REVIEW", 24),
    ("request_additional_documentation", "Request Additional Documentation", "Pending Intake Review", "Pending Intake Review", "Donor Intake Coordinator", "Donor Intake Coordinator", "Intake Documentation Task", "Missing Documentation", "REQUEST_ADDITIONAL_DOCUMENTATION", 24),
    ("escalate_intake_issue", "Escalate Intake Issue", "Pending Intake Review", "Clinical Escalation", "Donor Intake Coordinator", "Operations Manager", "Intake Escalation", "Enterprise Bottleneck", "ESCALATE_INTAKE_ISSUE", 8),
    ("approve_donor", "Approve Donor", "Pending Clinical Review", "Pending QA Review", "Clinical Reviewer", "Quality Assurance Specialist", "QA Approval Review", "New Investigation", "APPROVE_DONOR_TO_QA", 48),
    ("reject_donor", "Reject Donor", "Pending Clinical Review", "Rejected", "Clinical Reviewer", None, "Donor Rejection Closure", "Intake Rejected", "REJECT_DONOR", 0),
    ("escalate_case", "Escalate Case", "Pending Clinical Review", "Clinical Escalation", "Clinical Reviewer", "Operations Manager", "Clinical Escalation", "Escalated Review", "ESCALATE_CLINICAL_CASE", 8),
    ("request_qa_review", "Request QA Review", "Pending Clinical Review", "Pending QA Review", "Clinical Reviewer", "Quality Assurance Specialist", "QA Investigation Task", "New Investigation", "REQUEST_QA_REVIEW", 48),
    ("request_additional_information", "Request Additional Information", "Pending Clinical Review", "Pending Intake Review", "Clinical Reviewer", "Donor Intake Coordinator", "Intake Follow-up Task", "Missing Documentation", "REQUEST_ADDITIONAL_INFORMATION", 24),
    ("open_investigation", "Open Investigation", "Pending QA Review", "CAPA Investigation", "Quality Assurance Specialist", "Quality Assurance Specialist", "CAPA Investigation", "Unresolved CAPA", "OPEN_QA_INVESTIGATION", 72),
    ("create_capa", "Create CAPA", "CAPA Investigation", "CAPA Investigation", "Quality Assurance Specialist", "Quality Assurance Specialist", "CAPA Follow-up", "Unresolved CAPA", "CREATE_CAPA", 120),
    ("approve_workflow", "Approve Workflow", "Pending QA Review", "Approved", "Quality Assurance Specialist", None, "Workflow Approval", "System", "APPROVE_WORKFLOW", 0),
    ("reject_workflow", "Reject Workflow", "Pending QA Review", "Rejected", "Quality Assurance Specialist", None, "Workflow Rejection", "System", "REJECT_WORKFLOW", 0),
    ("request_re_review", "Request Re-Review", "Pending QA Review", "Pending Clinical Review", "Quality Assurance Specialist", "Clinical Reviewer", "Clinical Re-Review", "New Donor Assigned", "REQUEST_RE_REVIEW", 24),
    ("close_investigation", "Close Investigation", "CAPA Investigation", "Closed", "Quality Assurance Specialist", None, "Investigation Closure", "System", "CLOSE_INVESTIGATION", 0),
    ("open_incident", "Open Incident", "Vendor SLA Investigation", "Vendor SLA Investigation", "Vendor Operations Analyst", "Vendor Operations Analyst", "SLA Investigation Task", "SLA Breach", "OPEN_VENDOR_INCIDENT", 24),
    ("escalate_vendor_issue", "Escalate Vendor Issue", "Vendor SLA Investigation", "Clinical Escalation", "Vendor Operations Analyst", "Operations Manager", "Vendor Escalation", "Critical Escalation", "ESCALATE_VENDOR_ISSUE", 8),
    ("resolve_incident", "Resolve Incident", "Vendor SLA Investigation", "Closed", "Vendor Operations Analyst", None, "Vendor Resolution", "System", "RESOLVE_VENDOR_INCIDENT", 0),
    ("assign_vendor_investigation", "Assign Vendor Investigation", "Vendor SLA Investigation", "Vendor SLA Investigation", "Vendor Operations Analyst", "Vendor Operations Analyst", "Vendor Investigation", "SLA Breach", "ASSIGN_VENDOR_INVESTIGATION", 24),
    ("request_vendor_update", "Request Vendor Update", "Vendor SLA Investigation", "Vendor SLA Investigation", "Vendor Operations Analyst", "Vendor Operations Analyst", "Vendor Update Request", "Outage Alert", "REQUEST_VENDOR_UPDATE", 8),
    ("reassign_tasks", "Reassign Tasks", "Clinical Escalation", "Pending Clinical Review", "Operations Manager", "Clinical Reviewer", "Manager Reassignment", "New Donor Assigned", "REASSIGN_TASKS", 24),
    ("override_priorities", "Override Priorities", "Clinical Escalation", "Clinical Escalation", "Operations Manager", "Operations Manager", "Priority Override", "Enterprise Bottleneck", "OVERRIDE_PRIORITIES", 8),
    ("approve_escalations", "Approve Escalations", "Clinical Escalation", "Pending QA Review", "Operations Manager", "Quality Assurance Specialist", "Escalation Approval", "New Investigation", "APPROVE_ESCALATION", 24),
    ("resolve_bottleneck", "Resolve Operational Bottleneck", "Clinical Escalation", "Closed", "Operations Manager", None, "Bottleneck Resolution", "System", "RESOLVE_BOTTLENECK", 0),
]


def ensure_workspace_definitions(db: Session, roles: dict[str, Role]) -> None:
    for role_name, definition in WORKSPACE_DEFINITIONS.items():
        role = roles.get(role_name)
        if not role:
            continue
        config = db.execute(
            select(RoleWorkspaceConfig).where(RoleWorkspaceConfig.role_id == role.role_id)
        ).scalar_one_or_none()
        visible_tabs = definition["visible_tabs"]
        enabled_widgets = [item[0] for item in definition["widgets"]]
        payload = {
            "workspace_name": definition["workspace_name"],
            "workspace_purpose": definition["workspace_purpose"],
            "dashboard_layout": {"type": "role_department", "sections": ["kpis", "widgets", "workbench"]},
            "visible_tabs": visible_tabs,
            "enabled_widgets": enabled_widgets,
            "workbench_columns": definition["workbench_columns"],
            "default_queue": definition["default_queue"],
            "notification_types": definition["notification_types"],
            "theme_config": definition["theme_config"],
        }
        if config:
            for field, value in payload.items():
                setattr(config, field, value)
        else:
            db.add(RoleWorkspaceConfig(role_id=role.role_id, **payload))

        db.execute(delete(RoleNavigationConfig).where(RoleNavigationConfig.role_id == role.role_id))
        for index, tab in enumerate(visible_tabs, start=1):
            db.add(
                RoleNavigationConfig(
                    role_id=role.role_id,
                    tab_label=tab["label"],
                    page_key=tab["page_key"],
                    sort_order=index,
                    is_visible=True,
                    required_permission=tab.get("required_permission"),
                )
            )

        db.execute(delete(RoleDashboardWidget).where(RoleDashboardWidget.role_id == role.role_id))
        for index, (key, title, widget_type) in enumerate(definition["widgets"], start=1):
            db.add(
                RoleDashboardWidget(
                    role_id=role.role_id,
                    widget_key=key,
                    widget_title=title,
                    widget_type=widget_type,
                    config={"department": role_name, "source": "workspace_engine"},
                    sort_order=index,
                    is_enabled=True,
                )
            )

    existing_states = {
        item.state_name: item for item in db.execute(select(WorkflowStateMachine)).scalars().all()
    }
    for index, (state_name, category, owner_role_name, is_terminal) in enumerate(WORKFLOW_STATES, start=1):
        owner = roles.get(owner_role_name) if owner_role_name else None
        state = existing_states.get(state_name)
        if state:
            state.state_category = category
            state.owning_role_id = owner.role_id if owner else None
            state.is_terminal = is_terminal
            state.sort_order = index
        else:
            db.add(
                WorkflowStateMachine(
                    state_name=state_name,
                    state_category=category,
                    owning_role_id=owner.role_id if owner else None,
                    is_terminal=is_terminal,
                    sort_order=index,
                )
            )

    existing_transitions = {
        item.action_name: item for item in db.execute(select(WorkflowTransitionRule)).scalars().all()
    }
    for transition in WORKFLOW_TRANSITIONS:
        (
            action_name,
            action_label,
            from_state,
            to_state,
            source_role_name,
            target_role_name,
            task_type,
            notification_type,
            audit_action,
            sla_hours,
        ) = transition
        source_role = roles.get(source_role_name) if source_role_name else None
        target_role = roles.get(target_role_name) if target_role_name else None
        rule = existing_transitions.get(action_name)
        payload = {
            "action_label": action_label,
            "from_state": from_state,
            "to_state": to_state,
            "source_role_id": source_role.role_id if source_role else None,
            "target_role_id": target_role.role_id if target_role else None,
            "task_type": task_type,
            "notification_type": notification_type,
            "audit_action": audit_action,
            "sla_hours": sla_hours,
            "is_active": True,
        }
        if rule:
            for field, value in payload.items():
                setattr(rule, field, value)
        else:
            db.add(WorkflowTransitionRule(action_name=action_name, **payload))

    if not db.execute(select(WorkflowAssignmentRule.assignment_rule_id).limit(1)).first():
        for transition in WORKFLOW_TRANSITIONS:
            action_name, _, _, _, source_role_name, target_role_name, task_type, _, _, sla_hours = transition
            source_role = roles.get(source_role_name) if source_role_name else None
            target_role = roles.get(target_role_name) if target_role_name else None
            db.add(
                WorkflowAssignmentRule(
                    trigger_type=action_name,
                    from_role_id=source_role.role_id if source_role else None,
                    to_role_id=target_role.role_id if target_role else None,
                    task_type=task_type,
                    priority_rule="inherit_or_escalate",
                    sla_hours=sla_hours,
                    is_active=True,
                )
            )

    db.flush()
