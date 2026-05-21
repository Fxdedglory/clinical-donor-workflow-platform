from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Role,
    RoleDashboardWidget,
    RoleNavigationConfig,
    RoleWorkspaceConfig,
    WorkflowAssignmentRule,
    WorkflowEscalationRule,
    WorkflowNavigationRoute,
    WorkflowNotificationRule,
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
        "notification_types": ["Intake Rejected", "Missing Documentation", "Urgent Intake Assignment", "SLA Nearing Breach"],
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
        "notification_types": ["New Investigation", "SOP Deviation", "Unresolved CAPA", "Unresolved Escalation"],
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
    "Business Technology Analyst": {
        "workspace_name": "AI Governance and Workflow Intelligence Workspace",
        "workspace_purpose": "Govern AI-assisted workflow rules, explainability, overrides, drift signals, bottlenecks, and operational intelligence.",
        "default_queue": "AI Governance Review Queue",
        "visible_tabs": [
            _tab("AI Risk Dashboard", "ai_risk_dashboard", "ai_governance.review"),
            _tab("Workflow Intelligence", "workflow_intelligence", "workflow.analytics"),
            _tab("AI Governance", "ai_governance", "ai_governance.review"),
            _tab("Risk Rule Configuration", "risk_rule_configuration", "risk_rules.manage"),
            _tab("Workflow Analytics", "workflow_analytics", "workflow.analytics"),
            _tab("Escalation Analytics", "escalation_analytics", "workflow.analytics"),
            _tab("AI Audit Review", "ai_audit_review", "audit.review"),
            _tab("Operational Trends", "operational_trends", "workflow.analytics"),
        ],
        "widgets": [
            ("false_positive_rate", "False Positive Rate", "metric"),
            ("false_negative_rate", "False Negative Rate", "metric"),
            ("human_override_frequency", "Human Override Frequency", "metric"),
            ("escalated_ai_decisions", "Escalated AI Decisions", "metric"),
            ("avg_risk_score", "Avg Risk Score", "metric"),
            ("high_risk_trend", "High-Risk Trend", "metric"),
            ("rule_trigger_frequency", "Rule Trigger Frequency", "metric"),
            ("risk_distribution_heatmap", "Risk Distribution Heatmap", "visual"),
            ("workflow_bottleneck_sankey", "Workflow Bottleneck Sankey", "visual"),
            ("human_override_trend", "Human Override Trend", "visual"),
            ("sla_prediction_accuracy", "SLA Prediction Accuracy", "visual"),
            ("escalation_root_cause_matrix", "Escalation Root Cause Matrix", "visual"),
            ("workflow_queue_heatmap", "Workflow Queue Heatmap", "visual"),
            ("operational_recommendations", "Operational Recommendations", "table"),
        ],
        "workbench_columns": [
            "decision_id",
            "donor_id",
            "risk_score",
            "recommendation",
            "workflow_stage",
            "human_override",
            "final_decision",
            "created_at",
        ],
        "notification_types": [
            "AI Anomaly",
            "AI Override",
            "Rule Performance",
            "Workflow Bottleneck",
            "SLA Prediction",
        ],
        "theme_config": {"accent": "#0f766e", "density": "intelligence"},
    },
    "Supplier External User": {
        "workspace_name": "Supplier Collaboration Portal",
        "workspace_purpose": "Complete organization-scoped supplier tasks, upload requested evidence, and provide attributable approvals.",
        "default_queue": "Supplier Collaboration Queue",
        "visible_tabs": [
            _tab("Supplier Portal", "supplier_portal", "supplier.portal"),
            _tab("Assigned Tasks", "supplier_task_queue", "tasks.read"),
            _tab("Requested Documents", "requested_documents", "documents.manage"),
            _tab("Pending Approvals", "pending_approvals", "signatures.sign"),
            _tab("Notifications", "supplier_notifications", "notifications.read"),
        ],
        "widgets": [
            ("open_supplier_tasks", "Open Supplier Tasks", "metric"),
            ("pending_documents", "Pending Documents", "metric"),
            ("pending_approvals", "Pending Approvals", "metric"),
            ("sla_response_risk", "SLA Response Risk", "metric"),
            ("escalated_requests", "Escalated Requests", "metric"),
            ("supplier_task_queue", "Supplier Task Queue", "table"),
            ("requested_documents", "Requested Documents", "table"),
            ("pending_approvals", "Pending Approvals", "table"),
            ("supplier_notifications", "Supplier Notifications", "table"),
        ],
        "workbench_columns": [
            "task_id",
            "task_type",
            "title",
            "priority",
            "status",
            "workflow_state",
            "due_date",
        ],
        "notification_types": [
            "Document Request",
            "Supplier Approval",
            "Supplier Review",
            "External CAPA Response",
            "Workflow Notification",
        ],
        "theme_config": {"accent": "#127c75", "density": "external_collaboration"},
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
    {
        "state_name": "Draft Intake",
        "category": "Intake",
        "owner": "Donor Intake Coordinator",
        "allowed_roles": ["Donor Intake Coordinator"],
        "allowed_actions": ["save_draft", "upload_documentation", "validate_intake", "submit_to_clinical_review", "escalate_intake_issue"],
        "next": ["Pending Intake Validation", "Pending Clinical Review", "Pending Additional Information", "Operations Escalation"],
        "sla_hours": 24,
        "terminal": False,
    },
    {
        "state_name": "Pending Intake Validation",
        "category": "Intake",
        "owner": "Donor Intake Coordinator",
        "allowed_roles": ["Donor Intake Coordinator"],
        "allowed_actions": ["validate_intake", "submit_intake", "request_additional_documentation", "escalate_intake_issue"],
        "next": ["Pending Clinical Review", "Pending Additional Information", "Operations Escalation"],
        "sla_hours": 18,
        "terminal": False,
    },
    {
        "state_name": "Pending Clinical Review",
        "category": "Clinical",
        "owner": "Clinical Reviewer",
        "allowed_roles": ["Clinical Reviewer"],
        "allowed_actions": ["start_clinical_review", "approve_donor", "reject_donor", "escalate_to_qa", "request_additional_information", "override_ai_recommendation"],
        "next": ["Clinical Review In Progress", "Approved", "Rejected", "QA Investigation", "Pending Additional Information"],
        "sla_hours": 24,
        "terminal": False,
    },
    {
        "state_name": "Clinical Review In Progress",
        "category": "Clinical",
        "owner": "Clinical Reviewer",
        "allowed_roles": ["Clinical Reviewer"],
        "allowed_actions": ["approve_donor", "reject_donor", "escalate_to_qa", "request_additional_information", "override_ai_recommendation"],
        "next": ["Approved", "Rejected", "QA Investigation", "Pending Additional Information"],
        "sla_hours": 18,
        "terminal": False,
    },
    {
        "state_name": "Pending Additional Information",
        "category": "Intake",
        "owner": "Donor Intake Coordinator",
        "allowed_roles": ["Donor Intake Coordinator", "Clinical Reviewer"],
        "allowed_actions": ["upload_documentation", "submit_to_clinical_review", "escalate_intake_issue"],
        "next": ["Pending Clinical Review", "Operations Escalation"],
        "sla_hours": 24,
        "terminal": False,
    },
    {
        "state_name": "High Risk Escalation",
        "category": "Clinical",
        "owner": "Quality Assurance Specialist",
        "allowed_roles": ["Clinical Reviewer", "Quality Assurance Specialist", "Operations Manager"],
        "allowed_actions": ["escalate_to_qa", "open_investigation", "approve_escalations"],
        "next": ["QA Investigation", "Operations Escalation"],
        "sla_hours": 8,
        "terminal": False,
    },
    {
        "state_name": "QA Investigation",
        "category": "Quality",
        "owner": "Quality Assurance Specialist",
        "allowed_roles": ["Quality Assurance Specialist"],
        "allowed_actions": ["approve_workflow", "reject_workflow", "open_capa", "request_re_review", "escalate_investigation"],
        "next": ["Approved", "Rejected", "CAPA Investigation", "Clinical Re-Review", "Operations Escalation"],
        "sla_hours": 48,
        "terminal": False,
    },
    {
        "state_name": "CAPA Investigation",
        "category": "Quality",
        "owner": "Quality Assurance Specialist",
        "allowed_roles": ["Quality Assurance Specialist"],
        "allowed_actions": ["create_capa", "request_re_review", "close_investigation", "escalate_investigation"],
        "next": ["Clinical Re-Review", "Closed", "Operations Escalation"],
        "sla_hours": 120,
        "terminal": False,
    },
    {
        "state_name": "Clinical Re-Review",
        "category": "Clinical",
        "owner": "Clinical Reviewer",
        "allowed_roles": ["Clinical Reviewer"],
        "allowed_actions": ["approve_donor", "reject_donor", "escalate_to_qa", "override_ai_recommendation"],
        "next": ["Approved", "Rejected", "QA Investigation"],
        "sla_hours": 24,
        "terminal": False,
    },
    {
        "state_name": "Operations Escalation",
        "category": "Operations",
        "owner": "Operations Manager",
        "allowed_roles": ["Operations Manager"],
        "allowed_actions": ["reassign_tasks", "override_priorities", "approve_escalations", "resolve_bottleneck", "force_workflow_transition"],
        "next": ["Pending Clinical Review", "QA Investigation", "Closed"],
        "sla_hours": 8,
        "terminal": False,
    },
    {"state_name": "Vendor SLA Investigation", "category": "Vendor", "owner": "Vendor Operations Analyst", "allowed_roles": ["Vendor Operations Analyst"], "allowed_actions": ["open_incident", "escalate_vendor_issue", "resolve_incident", "assign_vendor_investigation", "request_vendor_update"], "next": ["Operations Escalation", "Closed"], "sla_hours": 24, "terminal": False},
    {"state_name": "Approved", "category": "Terminal", "owner": None, "allowed_roles": [], "allowed_actions": [], "next": ["Closed"], "sla_hours": 0, "terminal": True},
    {"state_name": "Rejected", "category": "Terminal", "owner": None, "allowed_roles": [], "allowed_actions": [], "next": ["Closed"], "sla_hours": 0, "terminal": True},
    {"state_name": "Closed", "category": "Terminal", "owner": None, "allowed_roles": [], "allowed_actions": [], "next": [], "sla_hours": 0, "terminal": True},
]

WORKFLOW_TRANSITIONS = [
    ("save_draft", "Save Draft", "Draft Intake", "Draft Intake", "Donor Intake Coordinator", "Donor Intake Coordinator", "Draft Intake Task", "Urgent Intake Assignment", "SAVE_DRAFT_INTAKE", 24),
    ("upload_documentation", "Upload Documentation", "Draft Intake", "Pending Intake Validation", "Donor Intake Coordinator", "Donor Intake Coordinator", "Documentation Validation Task", "Missing Documentation", "UPLOAD_DOCUMENTATION", 18),
    ("validate_intake", "Validate Intake", "Draft Intake", "Pending Intake Validation", "Donor Intake Coordinator", "Donor Intake Coordinator", "Intake Validation Task", "Urgent Intake Assignment", "VALIDATE_INTAKE", 18),
    ("submit_intake", "Submit Intake", "Pending Intake Validation", "Pending Clinical Review", "Donor Intake Coordinator", "Clinical Reviewer", "Donor Review Task", "New Donor Assigned", "SUBMIT_INTAKE", 24),
    ("submit_to_clinical_review", "Submit for Clinical Review", "Draft Intake", "Pending Clinical Review", "Donor Intake Coordinator", "Clinical Reviewer", "Donor Review Task", "New Donor Assigned", "SUBMIT_TO_CLINICAL_REVIEW", 24),
    ("request_additional_documentation", "Request Additional Documentation", "Pending Intake Validation", "Pending Additional Information", "Donor Intake Coordinator", "Donor Intake Coordinator", "Missing Documentation Queue", "Missing Documentation", "REQUEST_ADDITIONAL_DOCUMENTATION", 24),
    ("escalate_intake_issue", "Escalate Intake Issue", "Pending Intake Validation", "Operations Escalation", "Donor Intake Coordinator", "Operations Manager", "Intake Escalation", "Enterprise Bottleneck", "ESCALATE_INTAKE_ISSUE", 8),
    ("start_clinical_review", "Start Clinical Review", "Pending Clinical Review", "Clinical Review In Progress", "Clinical Reviewer", "Clinical Reviewer", "Clinical Review Task", "New Donor Assigned", "START_CLINICAL_REVIEW", 18),
    ("approve_donor", "Approve Donor", "Pending Clinical Review", "Approved", "Clinical Reviewer", None, "Donor Approval Closure", "System", "APPROVE_DONOR", 0),
    ("reject_donor", "Reject Donor", "Pending Clinical Review", "Rejected", "Clinical Reviewer", None, "Donor Rejection Closure", "Intake Rejected", "REJECT_DONOR", 0),
    ("escalate_to_qa", "Escalate to QA", "Pending Clinical Review", "QA Investigation", "Clinical Reviewer", "Quality Assurance Specialist", "QA Investigation Task", "New Investigation", "ESCALATE_TO_QA", 48),
    ("escalate_case", "Escalate Case", "Pending Clinical Review", "QA Investigation", "Clinical Reviewer", "Quality Assurance Specialist", "QA Investigation Task", "Escalated Review", "ESCALATE_CLINICAL_CASE", 48),
    ("request_qa_review", "Request QA Review", "Pending Clinical Review", "QA Investigation", "Clinical Reviewer", "Quality Assurance Specialist", "QA Investigation Task", "New Investigation", "REQUEST_QA_REVIEW", 48),
    ("request_additional_information", "Request Additional Information", "Pending Clinical Review", "Pending Additional Information", "Clinical Reviewer", "Donor Intake Coordinator", "Intake Follow-up Task", "Missing Documentation", "REQUEST_ADDITIONAL_INFORMATION", 24),
    ("override_ai_recommendation", "Override AI Recommendation", "Pending Clinical Review", "Clinical Review In Progress", "Clinical Reviewer", "Business Technology Analyst", "AI Override Review", "AI Override", "OVERRIDE_AI_RECOMMENDATION", 24),
    ("open_investigation", "Open Investigation", "QA Investigation", "QA Investigation", "Quality Assurance Specialist", "Quality Assurance Specialist", "QA Investigation Task", "New Investigation", "OPEN_QA_INVESTIGATION", 48),
    ("open_capa", "Open CAPA", "QA Investigation", "CAPA Investigation", "Quality Assurance Specialist", "Quality Assurance Specialist", "CAPA Investigation", "Unresolved CAPA", "OPEN_CAPA", 120),
    ("create_capa", "Create CAPA", "CAPA Investigation", "CAPA Investigation", "Quality Assurance Specialist", "Quality Assurance Specialist", "CAPA Follow-up", "Unresolved CAPA", "CREATE_CAPA", 120),
    ("approve_workflow", "Approve Workflow", "QA Investigation", "Approved", "Quality Assurance Specialist", None, "Workflow Approval", "System", "APPROVE_WORKFLOW", 0),
    ("reject_workflow", "Reject Workflow", "QA Investigation", "Rejected", "Quality Assurance Specialist", None, "Workflow Rejection", "System", "REJECT_WORKFLOW", 0),
    ("request_re_review", "Request Re-Review", "QA Investigation", "Clinical Re-Review", "Quality Assurance Specialist", "Clinical Reviewer", "Clinical Re-Review", "New Donor Assigned", "REQUEST_RE_REVIEW", 24),
    ("escalate_investigation", "Escalate Investigation", "QA Investigation", "Operations Escalation", "Quality Assurance Specialist", "Operations Manager", "QA Escalation", "Unresolved Escalation", "ESCALATE_QA_INVESTIGATION", 8),
    ("close_investigation", "Close Investigation", "CAPA Investigation", "Closed", "Quality Assurance Specialist", None, "Investigation Closure", "System", "CLOSE_INVESTIGATION", 0),
    ("open_incident", "Open Incident", "Vendor SLA Investigation", "Vendor SLA Investigation", "Vendor Operations Analyst", "Vendor Operations Analyst", "SLA Investigation Task", "SLA Breach", "OPEN_VENDOR_INCIDENT", 24),
    ("escalate_vendor_issue", "Escalate Vendor Issue", "Vendor SLA Investigation", "Operations Escalation", "Vendor Operations Analyst", "Operations Manager", "Vendor Escalation", "Critical Escalation", "ESCALATE_VENDOR_ISSUE", 8),
    ("resolve_incident", "Resolve Incident", "Vendor SLA Investigation", "Closed", "Vendor Operations Analyst", None, "Vendor Resolution", "System", "RESOLVE_VENDOR_INCIDENT", 0),
    ("assign_vendor_investigation", "Assign Vendor Investigation", "Vendor SLA Investigation", "Vendor SLA Investigation", "Vendor Operations Analyst", "Vendor Operations Analyst", "Vendor Investigation", "SLA Breach", "ASSIGN_VENDOR_INVESTIGATION", 24),
    ("request_vendor_update", "Request Vendor Update", "Vendor SLA Investigation", "Vendor SLA Investigation", "Vendor Operations Analyst", "Vendor Operations Analyst", "Vendor Update Request", "Outage Alert", "REQUEST_VENDOR_UPDATE", 8),
    ("reassign_tasks", "Reassign Tasks", "Operations Escalation", "Pending Clinical Review", "Operations Manager", "Clinical Reviewer", "Manager Reassignment", "New Donor Assigned", "REASSIGN_TASKS", 24),
    ("override_priorities", "Override Priorities", "Operations Escalation", "Operations Escalation", "Operations Manager", "Operations Manager", "Priority Override", "Enterprise Bottleneck", "OVERRIDE_PRIORITIES", 8),
    ("approve_escalations", "Approve Escalations", "Operations Escalation", "QA Investigation", "Operations Manager", "Quality Assurance Specialist", "Escalation Approval", "New Investigation", "APPROVE_ESCALATION", 24),
    ("force_workflow_transition", "Force Workflow Transition", "Operations Escalation", "QA Investigation", "Operations Manager", "Quality Assurance Specialist", "Forced Workflow Transition", "Unresolved Escalation", "FORCE_WORKFLOW_TRANSITION", 24),
    ("resolve_bottleneck", "Resolve Operational Bottleneck", "Operations Escalation", "Closed", "Operations Manager", None, "Bottleneck Resolution", "System", "RESOLVE_BOTTLENECK", 0),
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
    for index, state_def in enumerate(WORKFLOW_STATES, start=1):
        state_name = state_def["state_name"]
        category = state_def["category"]
        owner_role_name = state_def["owner"]
        is_terminal = state_def["terminal"]
        owner = roles.get(owner_role_name) if owner_role_name else None
        state = existing_states.get(state_name)
        escalation_rules = {
            "threshold_hours": state_def["sla_hours"],
            "target_role": "Operations Manager" if not is_terminal else None,
            "trigger": "sla_breach_or_stagnation",
        }
        notification_rules = {
            "on_enter": state_def["allowed_roles"],
            "sla_warning_hours": max(1, int(state_def["sla_hours"] / 2)) if state_def["sla_hours"] else 0,
        }
        if state:
            state.state_category = category
            state.owning_role_id = owner.role_id if owner else None
            state.allowed_roles = state_def["allowed_roles"]
            state.allowed_actions = state_def["allowed_actions"]
            state.next_possible_states = state_def["next"]
            state.sla_hours = state_def["sla_hours"]
            state.escalation_rules = escalation_rules
            state.notification_rules = notification_rules
            state.is_terminal = is_terminal
            state.is_terminal_state = is_terminal
            state.sort_order = index
        else:
            db.add(
                WorkflowStateMachine(
                    state_name=state_name,
                    state_category=category,
                    owning_role_id=owner.role_id if owner else None,
                    allowed_roles=state_def["allowed_roles"],
                    allowed_actions=state_def["allowed_actions"],
                    next_possible_states=state_def["next"],
                    sla_hours=state_def["sla_hours"],
                    escalation_rules=escalation_rules,
                    notification_rules=notification_rules,
                    is_terminal=is_terminal,
                    is_terminal_state=is_terminal,
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

    db.execute(delete(WorkflowEscalationRule))
    for state_def in WORKFLOW_STATES:
        if state_def["terminal"] or not state_def["sla_hours"]:
            continue
        target_role = roles.get("Operations Manager")
        db.add(
            WorkflowEscalationRule(
                workflow_state=state_def["state_name"],
                trigger_condition="sla_breach_or_workflow_stagnation",
                threshold_hours=state_def["sla_hours"],
                target_role_id=target_role.role_id if target_role else None,
                escalation_type=f"{state_def['category']} SLA Escalation",
                priority="Critical" if state_def["sla_hours"] <= 8 else "High",
                is_active=True,
            )
        )

    db.execute(delete(WorkflowNotificationRule))
    for transition in WORKFLOW_TRANSITIONS:
        _, action_label, _, to_state, _, target_role_name, _, notification_type, _, sla_hours = transition
        target_role = roles.get(target_role_name) if target_role_name else None
        if not target_role:
            continue
        db.add(
            WorkflowNotificationRule(
                workflow_state=to_state,
                event_type=action_label,
                target_role_id=target_role.role_id,
                notification_type=notification_type,
                priority="Critical" if sla_hours <= 8 and sla_hours > 0 else "High" if sla_hours else "Normal",
                template=f"{action_label} routed a workflow record to {to_state}.",
                is_active=True,
            )
        )

    route_definitions = [
        ("Donor Intake Coordinator", "DonorReview", "Draft Intake", "donor_intake_form", "Draft Intake"),
        ("Donor Intake Coordinator", "DonorReview", "Pending Intake Validation", "intake_queue", "Intake Queue"),
        ("Donor Intake Coordinator", "DonorReview", "Pending Additional Information", "intake_queue", "Missing Documentation Queue"),
        ("Clinical Reviewer", "DonorReview", "Pending Clinical Review", "clinical_review_queue", "Clinical Review Queue"),
        ("Clinical Reviewer", "DonorReview", "Clinical Review In Progress", "clinical_review_queue", "Clinical Review Workbench"),
        ("Clinical Reviewer", "DonorReview", "Clinical Re-Review", "clinical_review_queue", "Clinical Re-Review"),
        ("Clinical Reviewer", "DonorReview", "QA Investigation", "high_risk_cases", "High Risk Cases"),
        ("Quality Assurance Specialist", "DonorReview", "QA Investigation", "qa_investigations", "QA Investigation"),
        ("Quality Assurance Specialist", "DonorReview", "CAPA Investigation", "capa_queue", "CAPA Queue"),
        ("Operations Manager", "DonorReview", "Operations Escalation", "role_escalations", "Escalation Center"),
        ("Operations Manager", "WorkflowTask", "Operations Escalation", "queue_management", "Queue Management"),
        ("Vendor Operations Analyst", "VendorIncident", "Vendor SLA Investigation", "incident_queue", "Incident Queue"),
        ("Business Technology Analyst", "DonorReview", "Pending Clinical Review", "ai_audit_review", "AI Audit Review"),
        ("Business Technology Analyst", "DonorReview", "QA Investigation", "ai_audit_review", "AI Audit Review"),
        ("Business Technology Analyst", "AIDecision", None, "ai_audit_review", "AI Decision Trace"),
    ]
    db.execute(delete(WorkflowNavigationRoute))
    for role_name, record_type, workflow_state, page_key, route_label in route_definitions:
        role = roles.get(role_name)
        if not role:
            continue
        db.add(
            WorkflowNavigationRoute(
                role_id=role.role_id,
                record_type=record_type,
                workflow_state=workflow_state,
                page_key=page_key,
                route_label=route_label,
                preserve_context=True,
                is_active=True,
            )
        )

    db.flush()
