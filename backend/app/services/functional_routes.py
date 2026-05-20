from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    SOP,
    AIDecision,
    AIRiskRule,
    ChangeControl,
    DonorReview,
    EscalationEvent,
    Notification,
    Role,
    RolePermission,
    RoleWorkspaceConfig,
    User,
    Vendor,
    VendorIncident,
    WorkflowTask,
    WorkflowTimelineEvent,
    WorkflowTransitionEvent,
    WorkflowTransitionRule,
)

ACTIVE_TASK_STATUSES = ["Pending", "Assigned", "In Progress", "Blocked", "Escalated"]
ACTIVE_DONOR_STATES = [
    "Draft Intake",
    "Pending Intake Validation",
    "Pending Clinical Review",
    "Clinical Review In Progress",
    "Pending Additional Information",
    "High Risk Escalation",
    "QA Investigation",
    "CAPA Investigation",
    "Clinical Re-Review",
    "Operations Escalation",
]

ROUTE_DEFINITIONS = [
    {
        "group": "Master Data",
        "items": [
            {"route_path": "/donor", "label": "Donor Master", "permissions": ["donors.read", "donors.create", "donors.review"]},
            {"route_path": "/capa", "label": "CAPA", "permissions": ["change_control.manage", "audit.review"]},
            {"route_path": "/investigation", "label": "Investigation", "permissions": ["change_control.manage", "audit.review"]},
            {"route_path": "/vendor", "label": "Vendor", "permissions": ["vendors.read", "vendors.manage"]},
            {"route_path": "/sop", "label": "SOP", "permissions": ["sop.manage", "training.manage", "audit.review"]},
            {"route_path": "/user", "label": "User", "permissions": ["users.manage"]},
            {"route_path": "/ai-rule", "label": "AI Rule", "permissions": ["risk_rules.manage", "ai_governance.review"]},
        ],
    },
    {
        "group": "Workflow Operations",
        "items": [
            {"route_path": "/workflow", "label": "Workflow", "permissions": ["tasks.read", "tasks.manage", "workflow.analytics"]},
            {"route_path": "/review", "label": "Review", "permissions": ["donors.review", "donors.read"]},
            {"route_path": "/escalation", "label": "Escalation", "permissions": ["escalations.manage", "tasks.manage"]},
            {"route_path": "/incident", "label": "Incident", "permissions": ["vendors.read", "vendors.manage"]},
            {"route_path": "/task", "label": "Task", "permissions": ["tasks.read", "tasks.manage"]},
            {"route_path": "/notification", "label": "Notification", "permissions": ["notifications.read", "notifications.manage"]},
        ],
    },
    {
        "group": "Analytics & Intelligence",
        "items": [
            {"route_path": "/dashboard", "label": "Dashboard", "permissions": ["dashboard.view"]},
            {"route_path": "/operations", "label": "Operations", "permissions": ["dashboard.view", "tasks.manage"]},
            {"route_path": "/workload", "label": "Workload", "permissions": ["tasks.read", "tasks.manage"]},
            {"route_path": "/sla", "label": "SLA", "permissions": ["vendors.read", "vendors.manage"]},
            {"route_path": "/drift-analysis", "label": "Drift Analysis", "permissions": ["ai_governance.review", "workflow.analytics"]},
            {"route_path": "/workflow-intelligence", "label": "Workflow Intelligence", "permissions": ["workflow.analytics", "ai_governance.review"]},
        ],
    },
    {
        "group": "Administration",
        "items": [
            {"route_path": "/admin/users", "label": "Users", "permissions": ["users.manage"]},
            {"route_path": "/admin/roles", "label": "Roles", "permissions": ["roles.manage"]},
            {"route_path": "/admin/workflow-engine", "label": "Workflow Engine", "permissions": ["workflow.configure"]},
            {"route_path": "/admin/workspaces", "label": "Workspaces", "permissions": ["workflow.configure"]},
            {"route_path": "/admin/permissions", "label": "Permissions", "permissions": ["roles.manage"]},
            {"route_path": "/admin/responsibility-center", "label": "Responsibility Center", "permissions": ["system.admin"]},
            {"route_path": "/admin/system-health", "label": "System Health", "permissions": ["system.admin"]},
        ],
    },
]


def permissions_for_user(db: Session, user: User) -> set[str]:
    if not user.role_id:
        return set()
    return {
        row[0]
        for row in db.execute(
            select(RolePermission.permission_name).where(RolePermission.role_id == user.role_id)
        ).all()
    }


def active_role(db: Session, current_user: User, preview_role_id: int | None = None) -> tuple[Role, bool]:
    actual_role = db.get(Role, current_user.role_id) if current_user.role_id else None
    if not actual_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current user has no role")
    if not preview_role_id or preview_role_id == actual_role.role_id:
        return actual_role, False
    permissions = permissions_for_user(db, current_user)
    if "system.admin" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Preview requires system admin")
    preview_role = db.get(Role, preview_role_id)
    if not preview_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview role not found")
    return preview_role, True


def _role_permissions(db: Session, role: Role) -> set[str]:
    return {
        row[0]
        for row in db.execute(
            select(RolePermission.permission_name).where(RolePermission.role_id == role.role_id)
        ).all()
    }


def _has_any(permissions: set[str], required: list[str]) -> bool:
    return "system.admin" in permissions or not required or any(item in permissions for item in required)


def functional_navigation(db: Session, current_user: User, preview_role_id: int | None = None) -> dict[str, Any]:
    role, is_preview = active_role(db, current_user, preview_role_id)
    permissions = _role_permissions(db, role)
    groups = []
    for group in ROUTE_DEFINITIONS:
        items = [
            item
            for item in group["items"]
            if _has_any(permissions, item.get("permissions", []))
        ]
        if items:
            groups.append({"group": group["group"], "items": items})
    return {
        "active_role": role.role_name,
        "active_role_id": role.role_id,
        "actual_role": current_user.role,
        "is_preview": is_preview,
        "groups": groups,
        "default_route": default_route_for_role(role.role_name, groups),
    }


def default_route_for_role(role_name: str, groups: list[dict[str, Any]] | None = None) -> str:
    defaults = {
        "System Administrator": "/admin/workflow-engine",
        "Donor Intake Coordinator": "/donor",
        "Clinical Reviewer": "/review",
        "Quality Assurance Specialist": "/investigation",
        "Vendor Operations Analyst": "/sla",
        "Operations Manager": "/operations",
        "Business Technology Analyst": "/workflow-intelligence",
    }
    default = defaults.get(role_name)
    if default:
        return default
    if groups:
        return groups[0]["items"][0]["route_path"]
    return "/dashboard"


def normalize_route(route: str | None, *, role_name: str, groups: list[dict[str, Any]] | None = None) -> str:
    if not route or route == "/":
        return default_route_for_role(role_name, groups)
    route = route.strip()
    if not route.startswith("/"):
        route = f"/{route}"
    if len(route) > 1:
        route = route.rstrip("/")
    return route


def route_path_for_record(
    record_type: str | None,
    record_id: str | None,
    *,
    role_name: str | None = None,
    workflow_state: str | None = None,
    task_id: int | None = None,
    capa_required: bool | None = None,
) -> str:
    if not record_type or not record_id:
        return "/dashboard"
    if record_type == "WorkflowTask":
        return f"/task/{record_id}"
    if record_type == "DonorReview":
        if role_name == "Donor Intake Coordinator" and workflow_state in {
            "Draft Intake",
            "Pending Intake Validation",
            "Pending Additional Information",
        }:
            return f"/donor/{record_id}"
        return f"/review/{record_id}"
    if record_type == "ChangeControl":
        prefix = "capa" if capa_required else "investigation"
        return f"/{prefix}/{record_id}"
    if record_type == "VendorIncident":
        return f"/incident/{record_id}"
    if record_type == "Vendor":
        return f"/vendor/{record_id}"
    if record_type == "SOP":
        return f"/sop/{record_id}"
    if record_type == "User":
        return f"/user/{record_id}"
    if record_type == "AIRiskRule":
        return f"/ai-rule/{record_id}"
    if record_type == "EscalationEvent":
        return f"/escalation/{record_id}"
    if task_id:
        return f"/task/{task_id}"
    return f"/workflow/{record_id}"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _model_dict(model: Any, fields: list[str]) -> dict[str, Any]:
    return {field: _serialize_value(getattr(model, field)) for field in fields}


def _safe_user(user: User) -> dict[str, Any]:
    return _model_dict(
        user,
        ["user_id", "username", "full_name", "email", "role_id", "role", "department", "is_active", "last_login", "created_at"],
    )


def _route_parts(route_path: str) -> tuple[str, str | None]:
    parts = [part for part in route_path.split("/") if part]
    if not parts:
        return "dashboard", None
    key = parts[0]
    if key == "admin" and len(parts) > 1:
        return f"admin/{parts[1]}", parts[2] if len(parts) > 2 else None
    return key, parts[1] if len(parts) > 1 else None


def _route_group(route_key: str) -> str:
    if route_key.startswith("admin/"):
        return "Administration"
    if route_key in {"donor", "capa", "investigation", "vendor", "sop", "user", "ai-rule"}:
        return "Master Data"
    if route_key in {"workflow", "review", "escalation", "incident", "task", "notification"}:
        return "Workflow Operations"
    return "Analytics & Intelligence"


def _route_label(route_key: str) -> str:
    labels = {
        "donor": "Donor Master",
        "capa": "CAPA",
        "investigation": "Investigation",
        "vendor": "Vendor",
        "sop": "SOP",
        "user": "User",
        "ai-rule": "AI Rule",
        "workflow": "Workflow",
        "review": "Review",
        "escalation": "Escalation",
        "incident": "Incident",
        "task": "Task",
        "notification": "Notification",
        "dashboard": "Dashboard",
        "operations": "Operations",
        "workload": "Workload",
        "sla": "SLA",
        "drift-analysis": "Drift Analysis",
        "workflow-intelligence": "Workflow Intelligence",
        "admin/users": "User Administration",
        "admin/roles": "Role Administration",
        "admin/workflow-engine": "Workflow Engine",
        "admin/workspaces": "Workspace Configuration",
        "admin/permissions": "Permissions",
        "admin/responsibility-center": "Responsibility Center",
        "admin/system-health": "System Health",
    }
    return labels.get(route_key, route_key.replace("-", " ").replace("/", " / ").title())


def _task_query_for_role(db: Session, role: Role) -> list[WorkflowTask]:
    query = select(WorkflowTask).where(WorkflowTask.status.in_(ACTIVE_TASK_STATUSES))
    if role.role_name not in {"Operations Manager", "System Administrator", "Business Technology Analyst"}:
        query = query.where(WorkflowTask.assigned_role_id == role.role_id)
    return list(db.execute(query.order_by(WorkflowTask.due_date, desc(WorkflowTask.created_at)).limit(250)).scalars().all())


def _collection_rows(db: Session, route_key: str, role: Role, current_user: User) -> list[dict[str, Any]]:
    if route_key == "donor":
        donors = db.execute(select(DonorReview).order_by(desc(DonorReview.created_at)).limit(150)).scalars().all()
        return [
            _model_dict(donor, ["review_id", "donor_id", "donor_name", "age", "blood_type", "risk_score", "risk_level", "intake_status", "created_at"])
            | {"route_path": f"/donor/{donor.review_id}"}
            for donor in donors
        ]
    if route_key == "review":
        donors = db.execute(
            select(DonorReview)
            .where(DonorReview.intake_status.in_(ACTIVE_DONOR_STATES))
            .order_by(desc(DonorReview.risk_score), DonorReview.created_at)
            .limit(150)
        ).scalars().all()
        return [
            _model_dict(donor, ["review_id", "donor_id", "donor_name", "risk_score", "risk_level", "review_priority", "intake_status", "created_at"])
            | {"route_path": f"/review/{donor.review_id}"}
            for donor in donors
        ]
    if route_key in {"workflow", "task", "workload"}:
        return [
            _model_dict(task, ["task_id", "task_type", "title", "priority", "status", "workflow_state", "queue_name", "due_date", "related_record_type", "related_record_id"])
            | {"route_path": f"/task/{task.task_id}"}
            for task in _task_query_for_role(db, role)
        ]
    if route_key in {"capa", "investigation"}:
        query = select(ChangeControl)
        if route_key == "capa":
            query = query.where(ChangeControl.capa_required.is_(True))
        changes = db.execute(query.order_by(desc(ChangeControl.created_at)).limit(150)).scalars().all()
        return [
            _model_dict(change, ["change_id", "request_id", "risk_level", "approval_status", "capa_required", "implementation_due_date", "created_at"])
            | {"route_path": route_path_for_record("ChangeControl", str(change.change_id), capa_required=change.capa_required)}
            for change in changes
        ]
    if route_key in {"vendor", "sla"}:
        vendors = db.execute(select(Vendor).order_by(Vendor.vendor_name).limit(150)).scalars().all()
        return [
            _model_dict(vendor, ["vendor_id", "vendor_name", "system_name", "criticality", "sla_target_percent", "business_owner", "status"])
            | {"route_path": f"/vendor/{vendor.vendor_id}"}
            for vendor in vendors
        ]
    if route_key == "incident":
        incidents = db.execute(select(VendorIncident).order_by(desc(VendorIncident.opened_at)).limit(150)).scalars().all()
        return [
            _model_dict(incident, ["incident_id", "ticket_number", "title", "severity", "status", "sla_breached", "opened_at", "ticket_age_hours"])
            | {"route_path": f"/incident/{incident.incident_id}"}
            for incident in incidents
        ]
    if route_key == "sop":
        sops = db.execute(select(SOP).order_by(SOP.sop_code).limit(150)).scalars().all()
        return [
            _model_dict(sop, ["sop_id", "sop_code", "title", "version", "effective_date", "status", "revision_notes"])
            | {"route_path": f"/sop/{sop.sop_id}"}
            for sop in sops
        ]
    if route_key == "user":
        users = db.execute(select(User).order_by(User.full_name).limit(150)).scalars().all()
        return [_safe_user(user) | {"route_path": f"/user/{user.user_id}"} for user in users]
    if route_key == "ai-rule":
        rules = db.execute(select(AIRiskRule).order_by(AIRiskRule.rule_name).limit(150)).scalars().all()
        return [
            _model_dict(rule, ["rule_id", "rule_name", "risk_category", "condition_type", "condition_operator", "condition_value", "risk_score_delta", "severity", "auto_escalate", "is_active"])
            | {"route_path": f"/ai-rule/{rule.rule_id}"}
            for rule in rules
        ]
    if route_key == "escalation":
        escalations = db.execute(select(EscalationEvent).order_by(desc(EscalationEvent.created_at)).limit(150)).scalars().all()
        return [
            _model_dict(event, ["escalation_id", "related_task_id", "escalation_type", "trigger_reason", "created_at", "resolved_at", "status"])
            | {"route_path": f"/escalation/{event.escalation_id}"}
            for event in escalations
        ]
    if route_key == "notification":
        notifications = db.execute(
            select(Notification)
            .where(Notification.user_id == current_user.user_id)
            .order_by(desc(Notification.created_at))
            .limit(150)
        ).scalars().all()
        return [
            _model_dict(notification, ["notification_id", "title", "notification_type", "priority", "related_record_type", "related_record_id", "is_read", "created_at"])
            | {"route_path": f"/notification/{notification.notification_id}"}
            for notification in notifications
        ]
    return []


def _get_donor(db: Session, record_id: str) -> DonorReview | None:
    if record_id.isdigit():
        donor = db.get(DonorReview, int(record_id))
        if donor:
            return donor
    return db.execute(select(DonorReview).where(DonorReview.donor_id == record_id)).scalar_one_or_none()


def _load_entity(db: Session, route_key: str, record_id: str) -> tuple[Any | None, str | None, str | None]:
    if route_key in {"donor", "review"}:
        return _get_donor(db, record_id), "DonorReview", record_id
    if route_key in {"workflow", "task"} and record_id.isdigit():
        return db.get(WorkflowTask, int(record_id)), "WorkflowTask", record_id
    if route_key in {"capa", "investigation"} and record_id.isdigit():
        return db.get(ChangeControl, int(record_id)), "ChangeControl", record_id
    if route_key == "vendor" and record_id.isdigit():
        return db.get(Vendor, int(record_id)), "Vendor", record_id
    if route_key == "incident" and record_id.isdigit():
        return db.get(VendorIncident, int(record_id)), "VendorIncident", record_id
    if route_key == "sop" and record_id.isdigit():
        return db.get(SOP, int(record_id)), "SOP", record_id
    if route_key == "user" and record_id.isdigit():
        return db.get(User, int(record_id)), "User", record_id
    if route_key == "ai-rule" and record_id.isdigit():
        return db.get(AIRiskRule, int(record_id)), "AIRiskRule", record_id
    if route_key == "escalation" and record_id.isdigit():
        return db.get(EscalationEvent, int(record_id)), "EscalationEvent", record_id
    if route_key == "notification" and record_id.isdigit():
        return db.get(Notification, int(record_id)), "Notification", record_id
    return None, None, None


def _entity_payload(entity: Any, entity_type: str) -> dict[str, Any]:
    field_map = {
        "DonorReview": ["review_id", "donor_id", "donor_name", "age", "blood_type", "infectious_history", "travel_risk", "missing_required_fields", "risk_score", "risk_level", "recommended_action", "review_priority", "intake_status", "reviewer_id", "clinical_notes", "attachment_placeholder", "rejection_reason", "created_at", "updated_at", "reviewed_at"],
        "WorkflowTask": ["task_id", "task_type", "title", "description", "assigned_to_user_id", "assigned_role_id", "priority", "status", "workflow_state", "queue_name", "due_date", "created_at", "completed_at", "related_record_type", "related_record_id", "escalation_level"],
        "ChangeControl": ["change_id", "request_id", "requested_by_id", "sop_id", "reason", "risk_level", "approval_status", "capa_required", "investigation_notes", "implementation_due_date", "created_at", "approved_at"],
        "Vendor": ["vendor_id", "vendor_name", "system_name", "criticality", "sla_target_percent", "business_owner", "status"],
        "VendorIncident": ["incident_id", "vendor_id", "ticket_number", "title", "severity", "status", "uptime_percent", "sla_breached", "opened_at", "resolved_at", "ticket_age_hours", "resolution_minutes", "impact_summary"],
        "SOP": ["sop_id", "sop_code", "title", "version", "effective_date", "approved_by_id", "status", "revision_notes"],
        "User": ["user_id", "username", "full_name", "email", "role_id", "role", "department", "is_active", "last_login", "created_at"],
        "AIRiskRule": ["rule_id", "rule_name", "risk_category", "condition_type", "condition_operator", "condition_value", "risk_score_delta", "severity", "auto_escalate", "is_active", "created_by", "approved_by", "created_at"],
        "EscalationEvent": ["escalation_id", "related_task_id", "escalation_type", "trigger_reason", "created_at", "resolved_at", "status"],
        "Notification": ["notification_id", "title", "message", "notification_type", "priority", "workflow_task_id", "related_record_type", "related_record_id", "action_route", "workflow_context", "is_read", "created_at"],
    }
    return _model_dict(entity, field_map[entity_type])


def _workflow_target(entity: Any, entity_type: str) -> tuple[str | None, str | None, int | None, str | None]:
    if entity_type == "WorkflowTask":
        return entity.related_record_type, entity.related_record_id, entity.task_id, entity.workflow_state
    if entity_type == "DonorReview":
        return "DonorReview", str(entity.review_id), None, entity.intake_status
    if entity_type == "ChangeControl":
        state = "CAPA Investigation" if entity.capa_required else "QA Investigation"
        return "ChangeControl", str(entity.change_id), None, state
    if entity_type == "VendorIncident":
        return "VendorIncident", str(entity.incident_id), None, "Vendor SLA Investigation"
    if entity_type == "EscalationEvent":
        return "EscalationEvent", str(entity.escalation_id), None, "Operations Escalation"
    if entity_type == "Notification":
        return entity.related_record_type, entity.related_record_id, entity.workflow_task_id, None
    return None, None, None, None


def _active_tasks_for_record(db: Session, record_type: str | None, record_id: str | None) -> list[WorkflowTask]:
    if not record_type or not record_id:
        return []
    return list(
        db.execute(
            select(WorkflowTask)
            .where(
                WorkflowTask.related_record_type == record_type,
                WorkflowTask.related_record_id == str(record_id),
                WorkflowTask.status.in_(ACTIVE_TASK_STATUSES),
            )
            .order_by(WorkflowTask.due_date, desc(WorkflowTask.created_at))
        ).scalars().all()
    )


def _allowed_actions(
    db: Session,
    *,
    role: Role,
    permissions: set[str],
    workflow_state: str | None,
    record_type: str | None,
    record_id: str | None,
    task_id: int | None,
) -> list[dict[str, Any]]:
    if not workflow_state or not record_type or not record_id:
        return []
    states = {workflow_state}
    if workflow_state in {"Clinical Review In Progress", "Clinical Re-Review"}:
        states.add("Pending Clinical Review")
    rules = db.execute(
        select(WorkflowTransitionRule)
        .where(
            WorkflowTransitionRule.is_active.is_(True),
            WorkflowTransitionRule.from_state.in_(states),
        )
        .order_by(WorkflowTransitionRule.action_label)
    ).scalars().all()
    actions = []
    for rule in rules:
        if "system.admin" not in permissions and rule.source_role_id != role.role_id:
            continue
        actions.append(
            {
                "action_name": rule.action_name,
                "action_label": rule.action_label,
                "from_state": rule.from_state,
                "to_state": rule.to_state,
                "task_type": rule.task_type,
                "sla_hours": rule.sla_hours,
                "record_type": record_type,
                "record_id": record_id,
                "task_id": task_id,
            }
        )
    return actions


def _timeline(db: Session, record_type: str | None, record_id: str | None) -> list[dict[str, Any]]:
    if not record_type or not record_id:
        return []
    rows: list[dict[str, Any]] = []
    events = db.execute(
        select(WorkflowTimelineEvent)
        .where(
            WorkflowTimelineEvent.related_record_type == record_type,
            WorkflowTimelineEvent.related_record_id == str(record_id),
        )
        .order_by(WorkflowTimelineEvent.created_at)
        .limit(100)
    ).scalars().all()
    rows.extend(
        {
            "timestamp": item.created_at.isoformat(),
            "event_type": item.event_type,
            "summary": item.event_summary,
            "detail": item.event_detail,
        }
        for item in events
    )
    transitions = db.execute(
        select(WorkflowTransitionEvent)
        .where(
            WorkflowTransitionEvent.record_type == record_type,
            WorkflowTransitionEvent.record_id == str(record_id),
        )
        .order_by(WorkflowTransitionEvent.timestamp)
        .limit(100)
    ).scalars().all()
    rows.extend(
        {
            "timestamp": item.timestamp.isoformat(),
            "event_type": "Transition",
            "summary": f"{item.action_taken}: {item.from_state} -> {item.to_state}",
            "detail": item.decision_context,
        }
        for item in transitions
    )
    tasks = _active_tasks_for_record(db, record_type, record_id)
    rows.extend(
        {
            "timestamp": task.created_at.isoformat(),
            "event_type": "Active Task",
            "summary": f"{task.task_type}: {task.status}",
            "detail": {"task_id": task.task_id, "queue": task.queue_name, "due_date": task.due_date.isoformat() if task.due_date else None},
        }
        for task in tasks
    )
    return sorted(rows, key=lambda row: row["timestamp"])


def _related_records(db: Session, entity: Any, entity_type: str) -> dict[str, list[dict[str, Any]]]:
    record_type, record_id, _, _ = _workflow_target(entity, entity_type)
    related: dict[str, list[dict[str, Any]]] = {"workflows": [], "investigations": [], "capas": [], "incidents": [], "ai_decisions": [], "escalations": []}
    if record_type and record_id:
        related["workflows"] = [
            _model_dict(task, ["task_id", "task_type", "priority", "status", "workflow_state", "queue_name", "due_date"])
            | {"route_path": f"/task/{task.task_id}"}
            for task in db.execute(
                select(WorkflowTask)
                .where(WorkflowTask.related_record_type == record_type, WorkflowTask.related_record_id == record_id)
                .order_by(desc(WorkflowTask.created_at))
                .limit(25)
            ).scalars().all()
        ]
    if entity_type == "DonorReview":
        related["ai_decisions"] = [
            _model_dict(decision, ["decision_id", "donor_id", "risk_score", "recommendation", "workflow_stage", "human_override", "final_decision", "created_at"])
            for decision in db.execute(
                select(AIDecision)
                .where(AIDecision.donor_id == entity.donor_id)
                .order_by(desc(AIDecision.created_at))
                .limit(25)
            ).scalars().all()
        ]
    if entity_type == "Vendor":
        related["incidents"] = [
            _model_dict(incident, ["incident_id", "ticket_number", "title", "severity", "status", "sla_breached", "opened_at"])
            | {"route_path": f"/incident/{incident.incident_id}"}
            for incident in db.execute(
                select(VendorIncident)
                .where(VendorIncident.vendor_id == entity.vendor_id)
                .order_by(desc(VendorIncident.opened_at))
                .limit(25)
            ).scalars().all()
        ]
    if entity_type == "SOP":
        changes = db.execute(
            select(ChangeControl)
            .where(ChangeControl.sop_id == entity.sop_id)
            .order_by(desc(ChangeControl.created_at))
            .limit(25)
        ).scalars().all()
        related["investigations"] = [
            _model_dict(change, ["change_id", "request_id", "risk_level", "approval_status", "capa_required", "created_at"])
            | {"route_path": route_path_for_record("ChangeControl", str(change.change_id), capa_required=change.capa_required)}
            for change in changes
        ]
    if entity_type == "User":
        related["workflows"] = [
            _model_dict(task, ["task_id", "task_type", "priority", "status", "workflow_state", "queue_name", "due_date"])
            | {"route_path": f"/task/{task.task_id}"}
            for task in db.execute(
                select(WorkflowTask)
                .where(WorkflowTask.assigned_to_user_id == entity.user_id)
                .order_by(desc(WorkflowTask.created_at))
                .limit(25)
            ).scalars().all()
        ]
    if entity_type == "EscalationEvent":
        task = db.get(WorkflowTask, entity.related_task_id)
        if task:
            related["workflows"] = [
                _model_dict(task, ["task_id", "task_type", "priority", "status", "workflow_state", "queue_name", "due_date"])
                | {"route_path": f"/task/{task.task_id}"}
            ]
    return {key: value for key, value in related.items() if value}


def _role_lens(db: Session, role: Role, route_key: str, workflow_state: str | None) -> dict[str, Any]:
    config = db.execute(
        select(RoleWorkspaceConfig).where(RoleWorkspaceConfig.role_id == role.role_id)
    ).scalar_one_or_none()
    focus_by_role = {
        "Donor Intake Coordinator": "Intake readiness, documentation completeness, and clinical routing.",
        "Clinical Reviewer": "Clinical eligibility, AI recommendation review, and donor disposition.",
        "Quality Assurance Specialist": "QMS compliance, deviation investigation, CAPA, and audit traceability.",
        "Vendor Operations Analyst": "Vendor-supported system performance, incident response, and SLA control.",
        "Operations Manager": "Cross-functional backlog, staffing load, SLA exposure, and escalation resolution.",
        "Business Technology Analyst": "AI governance, workflow intelligence, explainability, and optimization.",
        "System Administrator": "Platform governance, configuration, permissions, and system health.",
    }
    return {
        "role": role.role_name,
        "focus": focus_by_role.get(role.role_name, "Operational context for this enterprise function."),
        "default_queue": config.default_queue if config else "",
        "workspace": config.workspace_name if config else "",
        "route_key": route_key,
        "workflow_state": workflow_state,
    }


def _analytics_context(db: Session, route_key: str, role: Role) -> dict[str, Any]:
    tasks = _task_query_for_role(db, role)
    task_rows = [
        {
            "queue": task.queue_name,
            "status": task.status,
            "workflow_state": task.workflow_state,
            "priority": task.priority,
            "volume": 1,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        for task in tasks
    ]
    state_counts = db.execute(
        select(DonorReview.intake_status, func.count(DonorReview.review_id))
        .group_by(DonorReview.intake_status)
        .order_by(DonorReview.intake_status)
    ).all()
    incident_counts = db.execute(
        select(VendorIncident.severity, func.count(VendorIncident.incident_id))
        .group_by(VendorIncident.severity)
    ).all()
    return {
        "task_heatmap": task_rows,
        "workflow_sankey": [
            {"source": task.task_type, "target": task.workflow_state, "value": 1}
            for task in tasks[:120]
        ],
        "donor_state_distribution": [{"state": row[0], "count": row[1]} for row in state_counts],
        "incident_severity": [{"severity": row[0], "count": row[1]} for row in incident_counts],
    }


def resolve_route_context(
    db: Session,
    *,
    current_user: User,
    route: str | None,
    preview_role_id: int | None = None,
) -> dict[str, Any]:
    nav = functional_navigation(db, current_user, preview_role_id)
    role = db.get(Role, nav["active_role_id"])
    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active role unavailable")
    permissions = _role_permissions(db, role)
    route_path = normalize_route(route, role_name=role.role_name, groups=nav["groups"])
    route_key, record_id = _route_parts(route_path)
    route_group = _route_group(route_key)
    label = _route_label(route_key)

    entity = None
    entity_type = None
    entity_payload = None
    record_type = None
    workflow_record_id = None
    task_id = None
    workflow_state = None

    if record_id:
        entity, entity_type, _ = _load_entity(db, route_key, record_id)
        if not entity or not entity_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Functional route record not found")
        if entity_type == "Notification" and entity.user_id != current_user.user_id and "system.admin" not in permissions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        entity_payload = _entity_payload(entity, entity_type)
        record_type, workflow_record_id, task_id, workflow_state = _workflow_target(entity, entity_type)
        if entity_type == "WorkflowTask":
            workflow_state = entity.workflow_state
        if record_type and workflow_record_id:
            tasks = _active_tasks_for_record(db, record_type, workflow_record_id)
            if tasks and not task_id:
                task_id = tasks[0].task_id
                workflow_state = workflow_state or tasks[0].workflow_state

    kind = "detail" if record_id else "analytics" if route_group == "Analytics & Intelligence" else "collection"
    if route_group == "Administration":
        kind = "admin"

    records = [] if record_id else _collection_rows(db, route_key, role, current_user)
    actions = _allowed_actions(
        db,
        role=role,
        permissions=permissions,
        workflow_state=workflow_state,
        record_type=record_type,
        record_id=workflow_record_id,
        task_id=task_id,
    )
    breadcrumbs = [
        {"label": route_group, "route_path": None},
        {"label": label, "route_path": f"/{route_key}"},
    ]
    if record_id:
        breadcrumbs.append({"label": record_id, "route_path": route_path})

    return {
        "route_path": route_path,
        "route_key": route_key,
        "route_group": route_group,
        "label": label,
        "kind": kind,
        "record_id": record_id,
        "entity_type": entity_type,
        "entity": entity_payload,
        "records": records,
        "record_count": len(records),
        "workflow": {
            "record_type": record_type,
            "record_id": workflow_record_id,
            "task_id": task_id,
            "workflow_state": workflow_state,
        },
        "actions": actions,
        "timeline": _timeline(db, record_type, workflow_record_id),
        "related_records": _related_records(db, entity, entity_type) if entity and entity_type else {},
        "role_lens": _role_lens(db, role, route_key, workflow_state),
        "breadcrumbs": breadcrumbs,
        "analytics": _analytics_context(db, route_key, role),
        "navigation": nav,
        "page_key": page_key_for_route(route_key, role.role_name),
    }


def page_key_for_route(route_key: str, role_name: str) -> str:
    mapping = {
        "dashboard": "role_dashboard",
        "operations": "role_dashboard",
        "workload": "role_tasks",
        "sla": "vendor_dashboard",
        "workflow-intelligence": "workflow_intelligence",
        "drift-analysis": "operational_trends",
        "admin/users": "admin_users",
        "admin/roles": "admin_roles",
        "admin/workflow-engine": "workflow_configuration",
        "admin/workspaces": "workspace_configuration",
        "admin/permissions": "admin_roles",
        "admin/responsibility-center": "responsibility_center",
        "admin/system-health": "system_health",
    }
    if route_key == "dashboard" and role_name == "Business Technology Analyst":
        return "ai_risk_dashboard"
    return mapping.get(route_key, route_key)


def _search_result(title: str, subtitle: str, route_path: str, entity_type: str) -> dict[str, str]:
    return {
        "title": title,
        "subtitle": subtitle,
        "route_path": route_path,
        "entity_type": entity_type,
    }


def enterprise_search(db: Session, *, current_user: User, query: str, preview_role_id: int | None = None) -> list[dict[str, str]]:
    role, _ = active_role(db, current_user, preview_role_id)
    permissions = _role_permissions(db, role)
    query = query.strip()
    if len(query) < 2:
        return []
    like = f"%{query}%"
    results: list[dict[str, str]] = []
    if _has_any(permissions, ["donors.read", "donors.review", "donors.create"]):
        donors = db.execute(
            select(DonorReview)
            .where(or_(DonorReview.donor_id.ilike(like), DonorReview.donor_name.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                donor.donor_id,
                f"{donor.donor_name} | {donor.intake_status} | risk {donor.risk_score}",
                f"/donor/{donor.review_id}",
                "Donor",
            )
            for donor in donors
        )
    if _has_any(permissions, ["change_control.manage", "audit.review"]):
        changes = db.execute(
            select(ChangeControl)
            .where(or_(ChangeControl.request_id.ilike(like), ChangeControl.reason.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                change.request_id,
                f"{change.approval_status} | {change.risk_level}",
                route_path_for_record("ChangeControl", str(change.change_id), capa_required=change.capa_required),
                "CAPA" if change.capa_required else "Investigation",
            )
            for change in changes
        )
    if _has_any(permissions, ["vendors.read", "vendors.manage"]):
        incidents = db.execute(
            select(VendorIncident)
            .where(or_(VendorIncident.ticket_number.ilike(like), VendorIncident.title.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                incident.ticket_number,
                f"{incident.title} | {incident.severity} | {incident.status}",
                f"/incident/{incident.incident_id}",
                "Incident",
            )
            for incident in incidents
        )
        vendors = db.execute(
            select(Vendor)
            .where(or_(Vendor.vendor_name.ilike(like), Vendor.system_name.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                vendor.vendor_name,
                f"{vendor.system_name} | {vendor.criticality}",
                f"/vendor/{vendor.vendor_id}",
                "Vendor",
            )
            for vendor in vendors
        )
    if _has_any(permissions, ["risk_rules.manage", "ai_governance.review"]):
        rules = db.execute(select(AIRiskRule).where(AIRiskRule.rule_name.ilike(like)).limit(8)).scalars().all()
        results.extend(
            _search_result(rule.rule_name, f"{rule.condition_type} {rule.condition_operator} {rule.condition_value}", f"/ai-rule/{rule.rule_id}", "AI Rule")
            for rule in rules
        )
    if _has_any(permissions, ["users.manage"]):
        users = db.execute(
            select(User)
            .where(or_(User.username.ilike(like), User.full_name.ilike(like), User.email.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(_search_result(user.full_name, f"{user.username} | {user.role}", f"/user/{user.user_id}", "User") for user in users)
    if _has_any(permissions, ["tasks.read", "tasks.manage"]):
        tasks = db.execute(select(WorkflowTask).where(WorkflowTask.title.ilike(like)).limit(8)).scalars().all()
        results.extend(
            _search_result(task.title, f"{task.workflow_state} | {task.queue_name}", f"/task/{task.task_id}", "Task")
            for task in tasks
        )
    return results[:25]
