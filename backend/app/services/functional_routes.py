from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    CAPA,
    SOP,
    AIDecision,
    AIRiskRule,
    AuditLog,
    ChangeControl,
    Deviation,
    Donor,
    DonorReview,
    DonorScreening,
    EligibilityRule,
    EscalationEvent,
    InfectiousDiseaseTest,
    MedicalSocialHistory,
    Notification,
    Organization,
    PartnerComplaint,
    PartnerDocument,
    PartnerSubmission,
    ProcessingRelease,
    RecoverySuitability,
    Role,
    RolePermission,
    RoleWorkspaceConfig,
    SecureDocument,
    SignatureEvent,
    TissueType,
    User,
    Vendor,
    VendorIncident,
    WorkflowTask,
    WorkflowTimelineEvent,
    WorkflowTransitionEvent,
    WorkflowTransitionRule,
)
from app.services.eligibility_engine import eligibility_analytics, eligibility_record_bundle
from app.services.tenant_access import (
    apply_org_scope,
    ensure_external_self_or_org,
    ensure_org_access,
    is_external_user,
)

ACTIVE_TASK_STATUSES = ["Pending", "Assigned", "In Progress", "Blocked", "Escalated"]
ACTIVE_DONOR_STATES = [
    "Referral Received",
    "Intake In Progress",
    "Pending Administrative Screen",
    "Pending Medical Social History Review",
    "Pending Infectious Disease Review",
    "Pending Tissue Suitability Review",
    "Pending Recovery Suitability Review",
    "Pending Medical Director Review",
    "Pending QA Review",
    "Recovery Authorized",
    "Processing Hold",
    "Pending Processing Release",
    "Draft Intake",
    "Pending Intake Validation",
    "Pending Clinical Review",
]

ROUTE_DEFINITIONS = [
    {
        "group": "Records",
        "items": [
            {"route_path": "/donor", "label": "Donors", "permissions": ["donors.read", "donors.create", "donors.review"]},
            {"route_path": "/eligibility-rule", "label": "Eligibility Rules", "permissions": ["eligibility.manage", "risk_rules.manage", "ai_governance.review"]},
            {"route_path": "/infectious-disease-test", "label": "Infectious Disease Tests", "permissions": ["eligibility.read", "donors.review"]},
            {"route_path": "/tissue-type", "label": "Tissue Types", "permissions": ["eligibility.read", "donors.review", "release.manage"]},
            {"route_path": "/capa", "label": "CAPA", "permissions": ["qms.manage", "change_control.manage", "audit.review"]},
            {"route_path": "/deviation", "label": "Deviation", "permissions": ["qms.manage", "change_control.manage", "audit.review"]},
            {"route_path": "/release", "label": "Processing Release", "permissions": ["release.manage", "qms.manage", "audit.review"]},
            {"route_path": "/investigation", "label": "Investigation", "permissions": ["qms.manage", "change_control.manage", "audit.review"]},
            {"route_path": "/vendor", "label": "Vendor", "permissions": ["vendors.read", "vendors.manage"]},
            {"route_path": "/sop", "label": "SOP", "permissions": ["sop.manage", "training.manage", "audit.review"]},
            {"route_path": "/user", "label": "User", "permissions": ["users.manage"]},
            {"route_path": "/ai-rule", "label": "AI Rule", "permissions": ["risk_rules.manage", "ai_governance.review"]},
        ],
    },
    {
        "group": "My Work",
        "items": [
            {"route_path": "/workflow", "label": "Workflow", "permissions": ["tasks.read", "tasks.manage", "workflow.analytics"]},
            {"route_path": "/referral", "label": "Referral", "permissions": ["donors.create", "donors.read"]},
            {"route_path": "/screening", "label": "Screening", "permissions": ["eligibility.read", "donors.review", "donors.read"]},
            {"route_path": "/medical-review", "label": "Medical Review", "permissions": ["donors.review", "eligibility.review"]},
            {"route_path": "/qa-review", "label": "QA Review", "permissions": ["qms.manage", "release.manage", "audit.review"]},
            {"route_path": "/recovery", "label": "Recovery Suitability", "permissions": ["eligibility.review", "donors.review", "release.manage"]},
            {"route_path": "/processing-release", "label": "Processing Release", "permissions": ["release.manage", "qms.manage"]},
            {"route_path": "/escalation", "label": "Escalation", "permissions": ["escalations.manage", "tasks.manage"]},
            {"route_path": "/incident", "label": "Incident", "permissions": ["vendors.read", "vendors.manage"]},
            {"route_path": "/task", "label": "Task", "permissions": ["tasks.read", "tasks.manage"]},
            {"route_path": "/notification", "label": "Notification", "permissions": ["notifications.read", "notifications.manage"]},
            {"route_path": "/partner", "label": "Partner Portal", "permissions": ["partner.portal"]},
            {"route_path": "/partner/submission", "label": "Submissions", "permissions": ["partner.portal", "partners.read"]},
            {"route_path": "/partner/complaint", "label": "Quality Complaints", "permissions": ["partner.portal", "partners.read"]},
            {"route_path": "/partner/documents", "label": "Documents", "permissions": ["partner.portal", "partners.read"]},
        ],
    },
    {
        "group": "Dashboard",
        "items": [
            {"route_path": "/dashboard", "label": "Dashboard", "permissions": ["dashboard.view"]},
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
            {"route_path": "/admin/audit-logs", "label": "Audit Logs", "permissions": ["audit.review"]},
            {"route_path": "/admin/partners", "label": "Partners", "permissions": ["partners.manage", "suppliers.manage"]},
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
        "System Administrator": "/admin/users",
        "Donor Intake Coordinator": "/dashboard",
        "Clinical Reviewer": "/dashboard",
        "Quality Assurance Specialist": "/dashboard",
        "Vendor Operations Analyst": "/dashboard",
        "Operations Manager": "/dashboard",
        "Business Technology Analyst": "/dashboard",
        "Partner External User": "/partner",
        "Supplier External User": "/partner",
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
    if record_type == "Donor":
        return f"/donor/{record_id}"
    if record_type == "DonorScreening":
        return f"/screening/{record_id}"
    if record_type == "MedicalSocialHistory":
        return f"/medical-review/{record_id}"
    if record_type == "RecoverySuitability":
        return f"/recovery/{record_id}"
    if record_type == "ProcessingRelease":
        return f"/processing-release/{record_id}"
    if record_type == "Deviation":
        return f"/deviation/{record_id}"
    if record_type == "CAPA":
        return f"/capa/{record_id}"
    if record_type == "EligibilityRule":
        return f"/eligibility-rule/{record_id}"
    if record_type == "InfectiousDiseaseTest":
        return f"/infectious-disease-test/{record_id}"
    if record_type == "TissueType":
        return f"/tissue-type/{record_id}"
    if record_type == "DonorReview":
        if role_name == "Donor Intake Coordinator" and workflow_state in {
            "Draft Intake",
            "Pending Intake Validation",
            "Pending Additional Information",
        }:
            return f"/donor/{record_id}"
        return f"/review/{record_id}"
    if record_type == "ChangeControl":
        return f"/investigation/{record_id}"
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
    if record_type == "SecureDocument":
        return f"/partner/documents/{record_id}"
    if record_type == "Organization":
        return f"/admin/partners/{record_id}"
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
    if key == "partner" and len(parts) > 1:
        return f"partner/{parts[1]}", parts[2] if len(parts) > 2 else None
    return key, parts[1] if len(parts) > 1 else None


def _route_group(route_key: str) -> str:
    if route_key.startswith("admin/"):
        return "Administration"
    if route_key in {
        "donor",
        "eligibility-rule",
        "infectious-disease-test",
        "tissue-type",
        "capa",
        "deviation",
        "release",
        "investigation",
        "vendor",
        "sop",
        "user",
        "ai-rule",
    }:
        return "Records"
    if route_key in {
        "workflow",
        "review",
        "referral",
        "screening",
        "medical-review",
        "qa-review",
        "recovery",
        "processing-release",
        "escalation",
        "incident",
        "task",
        "notification",
        "partner",
        "partner/submission",
        "partner/complaint",
        "partner/documents",
        "supplier",
        "supplier-documents",
        "supplier-approvals",
    }:
        return "My Work"
    return "Dashboard"


def _route_label(route_key: str) -> str:
    labels = {
        "donor": "Donors",
        "eligibility-rule": "Eligibility Rule",
        "infectious-disease-test": "Infectious Disease Test",
        "tissue-type": "Tissue Type",
        "capa": "CAPA",
        "deviation": "Deviation",
        "release": "Processing Release",
        "investigation": "Investigation",
        "vendor": "Vendor",
        "sop": "SOP",
        "user": "User",
        "ai-rule": "AI Rule",
        "workflow": "Workflows",
        "review": "Clinical Review",
        "referral": "Referral",
        "screening": "Screening",
        "medical-review": "Medical Review",
        "qa-review": "QA Review",
        "recovery": "Recovery Suitability",
        "processing-release": "Processing Release",
        "escalation": "Escalation",
        "incident": "Incident",
        "task": "Task",
        "notification": "Notification",
        "partner": "Partner Portal",
        "partner/submission": "Submissions",
        "partner/complaint": "Quality Complaints",
        "partner/documents": "Documents",
        "supplier": "Partner Portal",
        "supplier-documents": "Partner Documents",
        "supplier-approvals": "Partner Approvals",
        "dashboard": "Dashboard",
        "operations": "Dashboard",
        "workload": "Dashboard",
        "sla": "SLA",
        "drift-analysis": "Drift Analysis",
        "workflow-intelligence": "Workflow Intelligence",
        "admin/users": "User Administration",
        "admin/roles": "Role Administration",
        "admin/workflow-engine": "Workflow Engine",
        "admin/workspaces": "Workspace Configuration",
        "admin/permissions": "Permissions",
        "admin/audit-logs": "Audit Logs",
        "admin/partners": "Partner Administration",
        "admin/suppliers": "Partner Administration",
        "admin/responsibility-center": "Responsibility Center",
        "admin/system-health": "System Health",
    }
    return labels.get(route_key, route_key.replace("-", " ").replace("/", " / ").title())


def _task_query_for_role(db: Session, role: Role, current_user: User | None = None) -> list[WorkflowTask]:
    query = select(WorkflowTask).where(WorkflowTask.status.in_(ACTIVE_TASK_STATUSES))
    if role.role_name not in {"Operations Manager", "System Administrator", "Business Technology Analyst"}:
        query = query.where(WorkflowTask.assigned_role_id == role.role_id)
    if current_user:
        query = apply_org_scope(query, WorkflowTask, current_user)
        if is_external_user(current_user):
            query = query.where(
                or_(
                    WorkflowTask.assigned_to_user_id == current_user.user_id,
                    WorkflowTask.assigned_role_id == current_user.role_id,
                )
            )
    return list(db.execute(query.order_by(WorkflowTask.due_date, desc(WorkflowTask.created_at)).limit(250)).scalars().all())


def _collection_rows(db: Session, route_key: str, role: Role, current_user: User) -> list[dict[str, Any]]:
    if route_key in {"partner", "supplier"}:
        return [
            _model_dict(
                task,
                [
                    "task_id",
                    "task_type",
                    "title",
                    "priority",
                    "status",
                    "workflow_state",
                    "queue_name",
                    "due_date",
                    "related_record_type",
                    "related_record_id",
                ],
            )
            | {"route_path": f"/task/{task.task_id}"}
            for task in _task_query_for_role(db, role, current_user)
        ]
    if route_key == "supplier-documents":
        query = select(SecureDocument).where(SecureDocument.is_active.is_(True)).order_by(desc(SecureDocument.created_at)).limit(200)
        query = apply_org_scope(query, SecureDocument, current_user)
        return [
            _model_dict(
                document,
                [
                    "document_id",
                    "record_type",
                    "record_id",
                    "document_name",
                    "document_type",
                    "access_classification",
                    "created_at",
                ],
            )
            | {"route_path": f"/partner/documents/{document.document_id}"}
            for document in db.execute(query).scalars().all()
        ]
    if route_key == "supplier-approvals":
        query = select(SignatureEvent).order_by(desc(SignatureEvent.signed_at)).limit(200)
        query = apply_org_scope(query, SignatureEvent, current_user)
        return [
            _model_dict(
                signature,
                [
                    "signature_id",
                    "record_type",
                    "record_id",
                    "signature_type",
                    "reason",
                    "signed_at",
                    "prior_state",
                    "new_state",
                ],
            )
            for signature in db.execute(query).scalars().all()
        ]
    if route_key == "partner/submission":
        query = (
            select(PartnerSubmission)
            .where(PartnerSubmission.is_archived.is_(False))
            .order_by(desc(PartnerSubmission.submitted_at))
            .limit(200)
        )
        query = apply_org_scope(query, PartnerSubmission, current_user)
        return [
            _model_dict(
                submission,
                [
                    "submission_id",
                    "submission_code",
                    "submission_type",
                    "title",
                    "partner_visible_status",
                    "priority",
                    "product_or_tissue",
                    "batch_or_reference",
                    "estimated_completion_at",
                    "submitted_at",
                ],
            )
            | {"route_path": f"/partner/submission/{submission.submission_code}"}
            for submission in db.execute(query).scalars().all()
        ]
    if route_key == "partner/complaint":
        query = (
            select(PartnerComplaint)
            .where(PartnerComplaint.is_archived.is_(False))
            .order_by(desc(PartnerComplaint.submitted_at))
            .limit(200)
        )
        query = apply_org_scope(query, PartnerComplaint, current_user)
        return [
            _model_dict(
                complaint,
                [
                    "complaint_id",
                    "complaint_code",
                    "product_or_batch",
                    "issue_category",
                    "severity",
                    "partner_visible_status",
                    "submitted_at",
                    "closed_at",
                ],
            )
            | {"route_path": f"/partner/complaint/{complaint.complaint_code}"}
            for complaint in db.execute(query).scalars().all()
        ]
    if route_key == "partner/documents":
        query = (
            select(SecureDocument)
            .join(PartnerDocument, PartnerDocument.document_id == SecureDocument.document_id, isouter=True)
            .where(SecureDocument.is_active.is_(True))
            .order_by(desc(SecureDocument.created_at))
            .limit(200)
        )
        query = apply_org_scope(query, SecureDocument, current_user)
        return [
            _model_dict(
                document,
                [
                    "document_id",
                    "record_type",
                    "record_id",
                    "document_name",
                    "document_type",
                    "access_classification",
                    "created_at",
                ],
            )
            | {"route_path": f"/partner/documents/{document.document_id}"}
            for document in db.execute(query).scalars().all()
        ]
    if route_key in {"admin/partners", "admin/suppliers"}:
        organizations = db.execute(
            select(Organization)
            .where(Organization.organization_type.in_(["Supplier", "supplier", "Partner", "partner", "Recovery Organization"]))
            .order_by(Organization.organization_name)
            .limit(250)
        ).scalars().all()
        return [
            _model_dict(
                org,
                [
                    "organization_id",
                    "organization_name",
                    "organization_type",
                    "approval_status",
                    "contact_email",
                    "mfa_required",
                    "is_active",
                    "created_at",
                ],
            )
            | {"route_path": f"/admin/partners/{org.organization_id}"}
            for org in organizations
        ]
    if route_key == "donor":
        donors = db.execute(select(Donor).order_by(desc(Donor.created_at)).limit(200)).scalars().all()
        return [
            _model_dict(donor, ["donor_pk", "donor_identifier", "donor_name", "age", "blood_type", "current_workflow_state", "eligibility_status", "final_disposition", "created_at"])
            | {"route_path": f"/donor/{donor.donor_pk}"}
            for donor in donors
        ]
    if route_key in {"referral", "screening"}:
        screenings = db.execute(select(DonorScreening).order_by(desc(DonorScreening.created_at)).limit(200)).scalars().all()
        return [
            _model_dict(screening, ["screening_id", "donor_pk", "referral_id", "administrative_outcome", "medical_social_outcome", "infectious_disease_outcome", "current_decision", "created_at"])
            | {"route_path": f"/{route_key}/{screening.screening_id}"}
            for screening in screenings
        ]
    if route_key == "medical-review":
        histories = db.execute(select(MedicalSocialHistory).order_by(desc(MedicalSocialHistory.created_at)).limit(200)).scalars().all()
        return [
            _model_dict(history, ["history_id", "donor_pk", "cancer_history", "transmissible_disease_history", "iv_drug_use", "travel_exposure", "high_risk_behavior", "unknown_history", "outcome", "created_at"])
            | {"route_path": f"/medical-review/{history.history_id}"}
            for history in histories
        ]
    if route_key == "recovery":
        recoveries = db.execute(select(RecoverySuitability).order_by(desc(RecoverySuitability.reviewed_at)).limit(200)).scalars().all()
        return [
            _model_dict(recovery, ["recovery_id", "donor_pk", "tissue_type_id", "body_cooling_status", "trauma_contamination", "hospital_release_status", "recovery_window_hours", "outcome", "reviewed_at"])
            | {"route_path": f"/recovery/{recovery.recovery_id}"}
            for recovery in recoveries
        ]
    if route_key in {"processing-release", "release"}:
        releases = db.execute(select(ProcessingRelease).order_by(desc(ProcessingRelease.created_at)).limit(200)).scalars().all()
        return [
            _model_dict(release, ["release_id", "release_identifier", "donor_pk", "tissue_type_id", "release_status", "final_disposition", "chain_of_custody_verified", "created_at", "released_at"])
            | {"route_path": f"/{route_key}/{release.release_id}"}
            for release in releases
        ]
    if route_key == "qa-review":
        releases = db.execute(
            select(ProcessingRelease)
            .where(ProcessingRelease.release_status.in_(["Pending QA Review", "QA Review Required", "Release Hold", "CAPA Required"]))
            .order_by(desc(ProcessingRelease.created_at))
            .limit(200)
        ).scalars().all()
        return [
            _model_dict(release, ["release_id", "release_identifier", "donor_pk", "release_status", "final_disposition", "deviation_id", "capa_id", "created_at"])
            | {"route_path": f"/processing-release/{release.release_id}"}
            for release in releases
        ]
    if route_key in {"deviation", "investigation"}:
        deviations = db.execute(select(Deviation).order_by(desc(Deviation.opened_at)).limit(200)).scalars().all()
        return [
            _model_dict(deviation, ["deviation_id", "deviation_code", "donor_pk", "release_id", "deviation_category", "severity", "status", "opened_at", "closed_at"])
            | {"route_path": f"/deviation/{deviation.deviation_id}"}
            for deviation in deviations
        ]
    if route_key == "capa":
        capas = db.execute(select(CAPA).order_by(desc(CAPA.created_at)).limit(200)).scalars().all()
        return [
            _model_dict(capa, ["capa_id", "capa_code", "donor_pk", "deviation_id", "release_id", "corrective_action_owner", "status", "due_date", "created_at"])
            | {"route_path": f"/capa/{capa.capa_id}"}
            for capa in capas
        ]
    if route_key == "eligibility-rule":
        rules = db.execute(select(EligibilityRule).order_by(EligibilityRule.rule_category, EligibilityRule.rule_name).limit(200)).scalars().all()
        return [
            _model_dict(rule, ["rule_id", "rule_name", "rule_category", "condition_field", "condition_operator", "condition_value", "outcome", "severity", "requires_review", "required_role", "sop_reference", "is_active", "version"])
            | {"route_path": f"/eligibility-rule/{rule.rule_id}"}
            for rule in rules
        ]
    if route_key == "infectious-disease-test":
        tests = db.execute(select(InfectiousDiseaseTest).order_by(InfectiousDiseaseTest.pathogen, InfectiousDiseaseTest.test_method).limit(200)).scalars().all()
        return [
            _model_dict(test, ["test_id", "test_name", "pathogen", "test_method", "valid_window_hours", "rejection_if_positive", "review_if_positive", "is_active"])
            | {"route_path": f"/infectious-disease-test/{test.test_id}"}
            for test in tests
        ]
    if route_key == "tissue-type":
        tissue_types = db.execute(select(TissueType).order_by(TissueType.tissue_name).limit(200)).scalars().all()
        return [
            _model_dict(tissue, ["tissue_type_id", "tissue_name", "tissue_category", "min_age", "max_age", "max_ischemic_hours", "preservation_window_hours", "sop_reference", "is_active"])
            | {"route_path": f"/tissue-type/{tissue.tissue_type_id}"}
            for tissue in tissue_types
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
            for task in _task_query_for_role(db, role, current_user)
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


def _get_donor(db: Session, record_id: str) -> Donor | None:
    if record_id.isdigit():
        donor = db.get(Donor, int(record_id))
        if donor:
            return donor
    return db.execute(select(Donor).where(Donor.donor_identifier == record_id)).scalar_one_or_none()


def _get_donor_review(db: Session, record_id: str) -> DonorReview | None:
    if record_id.isdigit():
        donor = db.get(DonorReview, int(record_id))
        if donor:
            return donor
    return db.execute(select(DonorReview).where(DonorReview.donor_id == record_id)).scalar_one_or_none()


def _load_entity(db: Session, route_key: str, record_id: str) -> tuple[Any | None, str | None, str | None]:
    if route_key == "donor":
        return _get_donor(db, record_id), "Donor", record_id
    if route_key == "review":
        return _get_donor_review(db, record_id), "DonorReview", record_id
    if route_key in {"referral", "screening"} and record_id.isdigit():
        return db.get(DonorScreening, int(record_id)), "DonorScreening", record_id
    if route_key == "medical-review" and record_id.isdigit():
        return db.get(MedicalSocialHistory, int(record_id)), "MedicalSocialHistory", record_id
    if route_key == "recovery" and record_id.isdigit():
        return db.get(RecoverySuitability, int(record_id)), "RecoverySuitability", record_id
    if route_key in {"processing-release", "release"} and record_id.isdigit():
        return db.get(ProcessingRelease, int(record_id)), "ProcessingRelease", record_id
    if route_key == "deviation" and record_id.isdigit():
        return db.get(Deviation, int(record_id)), "Deviation", record_id
    if route_key == "investigation" and record_id.isdigit():
        deviation = db.get(Deviation, int(record_id))
        if deviation:
            return deviation, "Deviation", record_id
        return db.get(ChangeControl, int(record_id)), "ChangeControl", record_id
    if route_key == "capa" and record_id.isdigit():
        return db.get(CAPA, int(record_id)), "CAPA", record_id
    if route_key == "eligibility-rule" and record_id.isdigit():
        return db.get(EligibilityRule, int(record_id)), "EligibilityRule", record_id
    if route_key == "infectious-disease-test" and record_id.isdigit():
        return db.get(InfectiousDiseaseTest, int(record_id)), "InfectiousDiseaseTest", record_id
    if route_key == "tissue-type" and record_id.isdigit():
        return db.get(TissueType, int(record_id)), "TissueType", record_id
    if route_key in {"workflow", "task"} and record_id.isdigit():
        return db.get(WorkflowTask, int(record_id)), "WorkflowTask", record_id
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
    if route_key == "partner/submission":
        if record_id.isdigit():
            return db.get(PartnerSubmission, int(record_id)), "PartnerSubmission", record_id
        return db.execute(
            select(PartnerSubmission).where(PartnerSubmission.submission_code == record_id)
        ).scalar_one_or_none(), "PartnerSubmission", record_id
    if route_key == "partner/complaint":
        if record_id.isdigit():
            return db.get(PartnerComplaint, int(record_id)), "PartnerComplaint", record_id
        return db.execute(
            select(PartnerComplaint).where(PartnerComplaint.complaint_code == record_id)
        ).scalar_one_or_none(), "PartnerComplaint", record_id
    if route_key == "partner/documents" and record_id.isdigit():
        return db.get(SecureDocument, int(record_id)), "SecureDocument", record_id
    if route_key == "supplier-documents" and record_id.isdigit():
        return db.get(SecureDocument, int(record_id)), "SecureDocument", record_id
    if route_key == "supplier-approvals" and record_id.isdigit():
        return db.get(SignatureEvent, int(record_id)), "SignatureEvent", record_id
    if route_key in {"admin/partners", "admin/suppliers"} and record_id.isdigit():
        return db.get(Organization, int(record_id)), "Organization", record_id
    return None, None, None


def _entity_payload(entity: Any, entity_type: str) -> dict[str, Any]:
    field_map = {
        "Donor": ["donor_pk", "donor_identifier", "donor_review_id", "donor_name", "age", "blood_type", "sex", "referral_source_id", "time_of_death", "source_organization", "donor_history", "current_workflow_state", "eligibility_status", "final_disposition", "created_at", "updated_at"],
        "DonorScreening": ["screening_id", "donor_pk", "referral_id", "administrative_outcome", "medical_social_outcome", "infectious_disease_outcome", "tissue_suitability_outcome", "recovery_suitability_outcome", "qa_outcome", "automated_rule_outcome", "current_decision", "created_at", "updated_at"],
        "EligibilityRule": ["rule_id", "rule_name", "rule_category", "condition_field", "condition_operator", "condition_value", "outcome", "severity", "requires_review", "required_role", "sop_reference", "is_active", "version", "created_by", "approved_by", "created_at"],
        "InfectiousDiseaseTest": ["test_id", "test_name", "pathogen", "test_method", "valid_window_hours", "rejection_if_positive", "review_if_positive", "is_active"],
        "TissueType": ["tissue_type_id", "tissue_name", "tissue_category", "min_age", "max_age", "max_ischemic_hours", "preservation_window_hours", "sop_reference", "is_active"],
        "MedicalSocialHistory": ["history_id", "donor_pk", "cancer_history", "neurological_disease", "autoimmune_disease", "transmissible_disease_history", "iv_drug_use", "incarceration_history", "travel_exposure", "high_risk_behavior", "unknown_history", "outcome", "review_notes", "created_at"],
        "RecoverySuitability": ["recovery_id", "donor_pk", "tissue_type_id", "refrigeration_timing_hours", "body_cooling_status", "trauma_contamination", "blood_draw_timing_hours", "hospital_release_status", "recovery_environment", "recovery_window_hours", "outcome", "reviewed_at"],
        "ProcessingRelease": ["release_id", "release_identifier", "donor_pk", "tissue_type_id", "sterility_testing", "bioburden_status", "environmental_monitoring", "packaging_qc", "labeling_verification", "traceability_verification", "chain_of_custody_verified", "deviation_id", "capa_id", "release_status", "final_disposition", "created_at", "released_at"],
        "Deviation": ["deviation_id", "deviation_code", "donor_pk", "release_id", "deviation_category", "severity", "description", "status", "opened_at", "closed_at"],
        "CAPA": ["capa_id", "capa_code", "donor_pk", "deviation_id", "release_id", "root_cause", "corrective_action_owner", "status", "due_date", "closed_at", "created_at"],
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
        "SecureDocument": ["document_id", "record_type", "record_id", "document_name", "document_type", "access_classification", "created_at", "organization_id"],
        "SignatureEvent": ["signature_id", "user_id", "organization_id", "record_type", "record_id", "signature_type", "reason", "meaning", "signed_at", "prior_state", "new_state"],
        "Organization": ["organization_id", "organization_name", "organization_type", "approval_status", "contact_email", "mfa_required", "is_active", "created_at"],
        "PartnerSubmission": ["submission_id", "submission_code", "organization_id", "submission_type", "title", "partner_visible_status", "priority", "description", "product_or_tissue", "batch_or_reference", "estimated_completion_at", "submitted_at", "closed_at"],
        "PartnerComplaint": ["complaint_id", "complaint_code", "organization_id", "product_or_batch", "issue_category", "severity", "description", "impact_assessment", "partner_visible_status", "submitted_at", "closed_at"],
    }
    return _model_dict(entity, field_map[entity_type])


def _workflow_target(entity: Any, entity_type: str) -> tuple[str | None, str | None, int | None, str | None]:
    if entity_type == "WorkflowTask":
        return entity.related_record_type, entity.related_record_id, entity.task_id, entity.workflow_state
    if entity_type == "PartnerSubmission":
        return "PartnerSubmission", str(entity.submission_id), None, entity.internal_state
    if entity_type == "PartnerComplaint":
        return "PartnerComplaint", str(entity.complaint_id), None, entity.internal_state
    if entity_type == "Donor":
        return "Donor", str(entity.donor_pk), None, entity.current_workflow_state
    if entity_type == "DonorScreening":
        return "Donor", str(entity.donor_pk), None, "Pending Administrative Screen"
    if entity_type == "MedicalSocialHistory":
        return "Donor", str(entity.donor_pk), None, "Pending Medical Social History Review"
    if entity_type == "RecoverySuitability":
        return "Donor", str(entity.donor_pk), None, "Pending Recovery Suitability Review"
    if entity_type == "ProcessingRelease":
        return "Donor", str(entity.donor_pk), None, entity.release_status
    if entity_type == "Deviation":
        return "Deviation", str(entity.deviation_id), None, "Pending QA Review"
    if entity_type == "CAPA":
        return "CAPA", str(entity.capa_id), None, "Pending QA Review"
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
    if entity_type == "SecureDocument":
        return entity.record_type, entity.record_id, None, "Document Submitted"
    if entity_type == "SignatureEvent":
        return entity.record_type, entity.record_id, None, entity.new_state or "Signed"
    if entity_type == "Organization":
        return "Organization", str(entity.organization_id), None, entity.approval_status
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


def _audit_events(db: Session, record_type: str | None, record_id: str | None) -> list[dict[str, Any]]:
    if not record_type or not record_id:
        return []
    events = db.execute(
        select(AuditLog)
        .where(
            or_(
                AuditLog.record_id == str(record_id),
                AuditLog.entity_id == str(record_id),
            )
        )
        .order_by(desc(AuditLog.timestamp))
        .limit(60)
    ).scalars().all()
    return [
        _model_dict(
            event,
            [
                "audit_id",
                "action_type",
                "table_name",
                "record_id",
                "entity_type",
                "entity_id",
                "ip_address",
                "timestamp",
            ],
        )
        for event in events
    ]


def _related_records(db: Session, entity: Any, entity_type: str) -> dict[str, Any]:
    record_type, record_id, _, _ = _workflow_target(entity, entity_type)
    related: dict[str, Any] = {
        "workflows": [],
        "investigations": [],
        "capas": [],
        "deviations": [],
        "processing_releases": [],
        "infectious_disease_results": [],
        "eligibility_decisions": [],
        "incidents": [],
        "ai_decisions": [],
        "escalations": [],
    }
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
    if entity_type == "Donor":
        related.update(eligibility_record_bundle(db, entity))
    if entity_type in {"DonorScreening", "MedicalSocialHistory", "RecoverySuitability", "ProcessingRelease"}:
        donor = db.get(Donor, entity.donor_pk)
        if donor:
            related["donor"] = [
                _model_dict(donor, ["donor_pk", "donor_identifier", "donor_name", "current_workflow_state", "eligibility_status", "final_disposition"])
                | {"route_path": f"/donor/{donor.donor_pk}"}
            ]
            related.update(eligibility_record_bundle(db, donor))
    if entity_type == "Deviation":
        related["capas"] = [
            _model_dict(capa, ["capa_id", "capa_code", "status", "due_date", "created_at"])
            | {"route_path": f"/capa/{capa.capa_id}"}
            for capa in db.execute(
                select(CAPA)
                .where(CAPA.deviation_id == entity.deviation_id)
                .order_by(desc(CAPA.created_at))
                .limit(25)
            ).scalars().all()
        ]
    if entity_type == "CAPA" and entity.deviation_id:
        deviation = db.get(Deviation, entity.deviation_id)
        if deviation:
            related["deviations"] = [
                _model_dict(deviation, ["deviation_id", "deviation_code", "deviation_category", "severity", "status", "opened_at"])
                | {"route_path": f"/deviation/{deviation.deviation_id}"}
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
        "Partner External User": "Bounded partner submissions, document exchange, response tasks, and status tracking.",
        "Supplier External User": "Legacy external supplier role routed through the Partner Portal.",
    }
    return {
        "role": role.role_name,
        "focus": focus_by_role.get(role.role_name, "Operational context for this enterprise function."),
        "default_queue": config.default_queue if config else "",
        "workspace": config.workspace_name if config else "",
        "route_key": route_key,
        "workflow_state": workflow_state,
    }


def _analytics_context(db: Session, route_key: str, role: Role, current_user: User) -> dict[str, Any]:
    tasks = _task_query_for_role(db, role, current_user)
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
    if is_external_user(current_user):
        return {
            "task_heatmap": task_rows,
            "workflow_sankey": [
                {"source": task.task_type, "target": task.workflow_state, "value": 1}
                for task in tasks[:120]
            ],
            "partner_queue": [{"status": task.status, "priority": task.priority, "volume": 1} for task in tasks],
            "route_key": route_key,
        }

    state_counts = db.execute(
        select(DonorReview.intake_status, func.count(DonorReview.review_id))
        .group_by(DonorReview.intake_status)
        .order_by(DonorReview.intake_status)
    ).all()
    incident_counts = db.execute(
        select(VendorIncident.severity, func.count(VendorIncident.incident_id))
        .group_by(VendorIncident.severity)
    ).all()
    analytics = {
        "task_heatmap": task_rows,
        "workflow_sankey": [
            {"source": task.task_type, "target": task.workflow_state, "value": 1}
            for task in tasks[:120]
        ],
        "donor_state_distribution": [{"state": row[0], "count": row[1]} for row in state_counts],
        "incident_severity": [{"severity": row[0], "count": row[1]} for row in incident_counts],
    }
    analytics.update(eligibility_analytics(db))
    return analytics


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
    visible_route_keys = {
        _route_parts(item["route_path"])[0]
        for group in nav["groups"]
        for item in group["items"]
    }
    if route_key not in visible_route_keys:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Route is not available for this role")
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
        if entity_type == "User":
            ensure_external_self_or_org(current_user, entity)
        else:
            ensure_org_access(current_user, entity, not_found_detail="Functional route record not found")
        entity_payload = _entity_payload(entity, entity_type)
        record_type, workflow_record_id, task_id, workflow_state = _workflow_target(entity, entity_type)
        if entity_type == "WorkflowTask":
            workflow_state = entity.workflow_state
        if record_type and workflow_record_id:
            tasks = _active_tasks_for_record(db, record_type, workflow_record_id)
            if tasks and not task_id:
                task_id = tasks[0].task_id
                workflow_state = workflow_state or tasks[0].workflow_state

    kind = "detail" if record_id else "analytics" if route_group == "Dashboard" else "collection"
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
        "audit_events": _audit_events(db, record_type, workflow_record_id),
        "related_records": _related_records(db, entity, entity_type) if entity and entity_type else {},
        "role_lens": _role_lens(db, role, route_key, workflow_state),
        "breadcrumbs": breadcrumbs,
        "analytics": _analytics_context(db, route_key, role, current_user),
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
        "partner": "partner_portal",
        "partner/submission": "partner_submissions",
        "partner/complaint": "partner_complaints",
        "partner/documents": "partner_documents",
        "supplier": "partner_portal",
        "supplier-documents": "partner_documents",
        "supplier-approvals": "partner_approvals",
        "admin/users": "admin_users",
        "admin/roles": "admin_roles",
        "admin/workflow-engine": "workflow_configuration",
        "admin/workspaces": "workspace_configuration",
        "admin/permissions": "admin_roles",
        "admin/audit-logs": "audit_administration",
        "admin/partners": "partner_admin",
        "admin/suppliers": "partner_admin",
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
            select(Donor)
            .where(or_(Donor.donor_identifier.ilike(like), Donor.donor_name.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                donor.donor_identifier,
                f"{donor.donor_name} | {donor.current_workflow_state} | {donor.eligibility_status}",
                f"/donor/{donor.donor_pk}",
                "Donor",
            )
            for donor in donors
        )
    if _has_any(permissions, ["qms.manage", "change_control.manage", "audit.review"]):
        deviations = db.execute(
            select(Deviation)
            .where(or_(Deviation.deviation_code.ilike(like), Deviation.description.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                deviation.deviation_code,
                f"{deviation.deviation_category} | {deviation.severity} | {deviation.status}",
                f"/deviation/{deviation.deviation_id}",
                "Deviation",
            )
            for deviation in deviations
        )
        capas = db.execute(
            select(CAPA)
            .where(or_(CAPA.capa_code.ilike(like), CAPA.root_cause.ilike(like)))
            .limit(8)
        ).scalars().all()
        results.extend(
            _search_result(
                capa.capa_code,
                f"{capa.status} | owner {capa.corrective_action_owner}",
                f"/capa/{capa.capa_id}",
                "CAPA",
            )
            for capa in capas
        )
        releases = db.execute(select(ProcessingRelease).where(ProcessingRelease.release_identifier.ilike(like)).limit(8)).scalars().all()
        results.extend(
            _search_result(
                release.release_identifier,
                f"{release.release_status} | {release.final_disposition or 'No disposition'}",
                f"/processing-release/{release.release_id}",
                "Processing Release",
            )
            for release in releases
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
        eligibility_rules = db.execute(select(EligibilityRule).where(EligibilityRule.rule_name.ilike(like)).limit(8)).scalars().all()
        results.extend(
            _search_result(
                rule.rule_name,
                f"{rule.rule_category} | {rule.condition_field} {rule.condition_operator} {rule.condition_value}",
                f"/eligibility-rule/{rule.rule_id}",
                "Eligibility Rule",
            )
            for rule in eligibility_rules
        )
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
        task_query = select(WorkflowTask).where(WorkflowTask.title.ilike(like)).limit(8)
        task_query = apply_org_scope(task_query, WorkflowTask, current_user)
        if is_external_user(current_user):
            task_query = task_query.where(
                or_(
                    WorkflowTask.assigned_to_user_id == current_user.user_id,
                    WorkflowTask.assigned_role_id == current_user.role_id,
                )
            )
        tasks = db.execute(task_query).scalars().all()
        results.extend(
            _search_result(task.title, f"{task.workflow_state} | {task.queue_name}", f"/task/{task.task_id}", "Task")
            for task in tasks
        )
    if _has_any(permissions, ["partner.portal", "partners.read", "supplier.portal", "suppliers.read"]):
        submission_query = (
            select(PartnerSubmission)
            .where(
                or_(
                    PartnerSubmission.submission_code.ilike(like),
                    PartnerSubmission.title.ilike(like),
                    PartnerSubmission.submission_type.ilike(like),
                    PartnerSubmission.batch_or_reference.ilike(like),
                )
            )
            .limit(8)
        )
        submission_query = apply_org_scope(submission_query, PartnerSubmission, current_user)
        submissions = db.execute(submission_query).scalars().all()
        results.extend(
            _search_result(
                submission.submission_code,
                f"{submission.title} | {submission.partner_visible_status}",
                f"/partner/submission/{submission.submission_code}",
                "Partner Submission",
            )
            for submission in submissions
        )
        complaint_query = (
            select(PartnerComplaint)
            .where(
                or_(
                    PartnerComplaint.complaint_code.ilike(like),
                    PartnerComplaint.product_or_batch.ilike(like),
                    PartnerComplaint.issue_category.ilike(like),
                )
            )
            .limit(8)
        )
        complaint_query = apply_org_scope(complaint_query, PartnerComplaint, current_user)
        complaints = db.execute(complaint_query).scalars().all()
        results.extend(
            _search_result(
                complaint.complaint_code,
                f"{complaint.issue_category} | {complaint.partner_visible_status}",
                f"/partner/complaint/{complaint.complaint_code}",
                "Quality Complaint",
            )
            for complaint in complaints
        )
        document_query = (
            select(SecureDocument)
            .where(
                or_(
                    SecureDocument.document_name.ilike(like),
                    SecureDocument.record_id.ilike(like),
                    SecureDocument.document_type.ilike(like),
                )
            )
            .limit(8)
        )
        document_query = apply_org_scope(document_query, SecureDocument, current_user)
        documents = db.execute(document_query).scalars().all()
        results.extend(
            _search_result(
                document.document_name,
                f"{document.document_type} | {document.record_type} {document.record_id}",
                f"/partner/documents/{document.document_id}",
                "Document",
            )
            for document in documents
        )
    return results[:25]
