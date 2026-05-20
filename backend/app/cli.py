import argparse
import random
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import delete, select

from app.auth.security import get_password_hash
from app.database import SessionLocal
from app.models import (
    SOP,
    AIDecision,
    AIModelVersion,
    AIOverrideEvent,
    AIRiskRule,
    AuditLog,
    ChangeControl,
    DonorReview,
    EscalationEvent,
    Notification,
    RiskCategory,
    Role,
    RoleDashboardWidget,
    RoleNavigationConfig,
    RolePermission,
    RoleResponsibility,
    RoleWorkspaceConfig,
    SOPTrainingAssignment,
    TrainingCompletion,
    User,
    Vendor,
    VendorIncident,
    WorkflowAssignmentRule,
    WorkflowEscalationRule,
    WorkflowNavigationRoute,
    WorkflowNotificationRule,
    WorkflowStateMachine,
    WorkflowTask,
    WorkflowTimelineEvent,
    WorkflowTransitionEvent,
    WorkflowTransitionRule,
)
from app.services.access_control import DEFAULT_PASSWORD, ROLE_DEFINITIONS
from app.services.ai_governance import (
    active_rules,
    ensure_ai_decisions_for_existing_donors,
    ensure_ai_governance_data,
)
from app.services.audit import log_audit, serialize_model
from app.services.escalations import evaluate_overdue_tasks
from app.services.functional_routes import route_path_for_record
from app.services.notifications import create_notification
from app.services.risk_engine import analyze_donor_risk
from app.services.workspace_config import ensure_workspace_definitions

fake = Faker()

BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Unknown"]
STATUSES = [
    "Pending Intake Validation",
    "Pending Clinical Review",
    "Clinical Review In Progress",
    "Pending Additional Information",
    "QA Investigation",
    "Approved",
    "Rejected",
]
NOTES = [
    "Routine intake packet reviewed. No abnormal disclosures.",
    "Recent travel documented; confirm exposure questionnaire during clinical review.",
    "Donor disclosed fever within prior screening window.",
    "Prior hospitalization requires supporting documentation.",
    "Self-reported hepatitis history requires medical director review.",
    "Missing consent attestation on imported intake packet.",
    "Clinical notes indicate unexplained weight loss; escalation recommended.",
    "Chain-of-custody missing for one imported lab attachment; QA review required.",
    "Conflicting documentation between donor questionnaire and lab validation packet.",
    "Failed lab validation documented by NorthStar Labs interface.",
]
CHANGE_REASONS = [
    "Revise donor intake checklist to include updated travel risk attestation.",
    "Update AI screening threshold after QMS review of false-positive escalations.",
    "Add CAPA workflow step for missing required clinical documentation.",
    "Document vendor downtime communication procedure for donor management system.",
    "Revise SOP owner approval matrix for medical director escalations.",
]
VENDOR_SYSTEMS = [
    ("Aster Clinical Exchange", "Donor Eligibility Interface", "Tier 1", 99.9),
    ("NorthStar Labs", "Infectious Disease Results Feed", "Tier 1", 99.8),
    ("Crescent QMS", "Document Control System", "Tier 2", 99.5),
    ("Helio Tickets", "Vendor Support Portal", "Tier 2", 99.0),
    ("Cobalt Archive", "Clinical Attachment Repository", "Tier 3", 98.5),
]

DEMO_USERS = [
    ("sysadmin", "Alex Rivera", "alex.rivera@example.org", "System Administrator", "Healthcare Technology"),
    ("intake", "Avery Chen", "avery.chen@example.org", "Donor Intake Coordinator", "Donor Services"),
    ("clinical", "Jordan Lee", "jordan.lee@example.org", "Clinical Reviewer", "Clinical Operations"),
    ("qa", "Morgan Shah", "morgan.shah@example.org", "Quality Assurance Specialist", "Quality Systems"),
    ("vendorops", "Riley Patel", "riley.patel@example.org", "Vendor Operations Analyst", "Healthcare Technology"),
    ("opsmanager", "Casey Morgan", "casey.morgan@example.org", "Operations Manager", "Enterprise Operations"),
    ("analyst", "Taylor Brooks", "taylor.brooks@example.org", "Business Technology Analyst", "Workflow Intelligence"),
]


def _random_datetime(days_back: int = 30) -> datetime:
    return datetime.now(UTC) - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def _apply_analysis(db, donor: DonorReview) -> None:
    analysis = analyze_donor_risk(
        donor_name=donor.donor_name,
        age=donor.age,
        blood_type=donor.blood_type,
        infectious_history=donor.infectious_history,
        travel_risk=donor.travel_risk,
        missing_required_fields=donor.missing_required_fields,
        clinical_notes=donor.clinical_notes,
        rules=active_rules(db),
    )
    donor.risk_score = analysis.risk_score
    donor.risk_level = analysis.risk_level
    donor.risk_flags = analysis.flagged_conditions
    donor.recommended_action = analysis.recommended_action
    donor.review_priority = analysis.review_priority


def _ensure_roles(db) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for role_name, definition in ROLE_DEFINITIONS.items():
        role = db.execute(select(Role).where(Role.role_name == role_name)).scalar_one_or_none()
        if not role:
            role = Role(role_name=role_name, description=definition["description"])
            db.add(role)
            db.flush()
        else:
            role.description = definition["description"]
        roles[role_name] = role

        existing_permissions = {
            row[0]
            for row in db.execute(
                select(RolePermission.permission_name).where(RolePermission.role_id == role.role_id)
            ).all()
        }
        for permission in definition["permissions"]:
            if permission not in existing_permissions:
                db.add(RolePermission(role_id=role.role_id, permission_name=permission))

        responsibility = db.execute(
            select(RoleResponsibility).where(RoleResponsibility.role_id == role.role_id)
        ).scalar_one_or_none()
        payload = {
            "job_description": definition["job_description"],
            "responsibilities": definition["responsibilities"],
            "assigned_workflows": definition["workflows"],
            "operational_kpis": definition["kpis"],
        }
        if responsibility:
            for field, value in payload.items():
                setattr(responsibility, field, value)
        else:
            db.add(RoleResponsibility(role_id=role.role_id, **payload))
    db.flush()
    return roles


def _ensure_users(db, roles: dict[str, Role]) -> dict[str, User]:
    password_hash = get_password_hash(DEFAULT_PASSWORD)
    users_by_role: dict[str, User] = {}
    for username, full_name, email, role_name, department in DEMO_USERS:
        role = roles[role_name]
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not user:
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            user = User(
                username=username,
                full_name=full_name,
                email=email,
                hashed_password=password_hash,
                role_id=role.role_id,
                role=role.role_name,
                department=department,
                is_active=True,
            )
            db.add(user)
        else:
            user.username = username
            user.full_name = full_name
            user.email = email
            user.hashed_password = user.hashed_password or password_hash
            user.role_id = role.role_id
            user.role = role.role_name
            user.department = department
            user.is_active = True
        users_by_role[role_name] = user
    db.flush()

    fallback_roles = list(roles.values())
    for index, user in enumerate(db.execute(select(User)).scalars().all()):
        if not user.username:
            user.username = f"user{user.user_id}"
        if not user.hashed_password:
            user.hashed_password = password_hash
        if not user.role_id:
            role = fallback_roles[index % len(fallback_roles)]
            user.role_id = role.role_id
            user.role = role.role_name
    db.flush()
    return users_by_role


def _ensure_notification_density(db, roles: dict[str, Role], users_by_role: dict[str, User]) -> None:
    role_notification_types = {
        "Donor Intake Coordinator": ["Missing Documentation", "Urgent Intake Assignment", "SLA Nearing Breach"],
        "Clinical Reviewer": ["New Donor Assigned", "SLA Nearing Breach", "Escalated Review"],
        "Quality Assurance Specialist": ["New Investigation", "Unresolved CAPA", "SOP Deviation"],
        "Vendor Operations Analyst": ["SLA Breach", "Outage Alert", "Critical Escalation"],
        "Operations Manager": ["Enterprise Bottleneck", "Staffing Overload", "Unresolved Escalation"],
        "Business Technology Analyst": ["AI Anomaly", "AI Override", "Workflow Bottleneck", "SLA Prediction"],
    }
    for role_name, notification_types in role_notification_types.items():
        role = roles.get(role_name)
        user = users_by_role.get(role_name)
        if not role or not user:
            continue
        existing_count = len(
            db.execute(select(Notification.notification_id).where(Notification.user_id == user.user_id)).all()
        )
        if existing_count >= 8:
            continue
        tasks = db.execute(
            select(WorkflowTask)
            .where(
                WorkflowTask.assigned_role_id == role.role_id,
                WorkflowTask.status.not_in(["Completed", "Rejected"]),
            )
            .order_by(WorkflowTask.due_date, WorkflowTask.created_at)
            .limit(12)
        ).scalars().all()
        if not tasks:
            continue
        for index, task in enumerate(tasks[: 8 - existing_count]):
            notification_type = notification_types[index % len(notification_types)]
            priority = "Critical" if task.priority in {"Critical", "STAT"} or task.escalation_level else task.priority
            create_notification(
                db,
                user_id=user.user_id,
                title=f"[{priority}] {task.title}",
                message=f"{task.related_record_type} {task.related_record_id} is in {task.workflow_state} for {task.queue_name}.",
                notification_type=notification_type,
                priority=priority,
                workflow_task_id=task.task_id,
                related_record_type=task.related_record_type,
                related_record_id=task.related_record_id,
                action_route=route_path_for_record(
                    task.related_record_type,
                    task.related_record_id,
                    role_name=role_name,
                    workflow_state=task.workflow_state,
                    task_id=task.task_id,
                ),
                workflow_context={
                    "task_id": task.task_id,
                    "workflow_state": task.workflow_state,
                    "queue_name": task.queue_name,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "escalation_level": task.escalation_level,
                    "route_path": route_path_for_record(
                        task.related_record_type,
                        task.related_record_id,
                        role_name=role_name,
                        workflow_state=task.workflow_state,
                        task_id=task.task_id,
                    ),
                },
            )


def ensure_enterprise_data(db) -> None:
    roles = _ensure_roles(db)
    users_by_role = _ensure_users(db, roles)
    ensure_ai_governance_data(db, users_by_role)
    ensure_workspace_definitions(db, roles)
    ensure_ai_decisions_for_existing_donors(db)

    existing_task = db.execute(select(WorkflowTask.task_id).limit(1)).first()
    if not existing_task:
        clinical_user = users_by_role["Clinical Reviewer"]
        vendor_user = users_by_role["Vendor Operations Analyst"]
        qa_user = users_by_role["Quality Assurance Specialist"]
        intake_user = users_by_role["Donor Intake Coordinator"]

        active_donors = db.execute(
            select(DonorReview)
            .where(
                DonorReview.intake_status.in_(
                    [
                        "Pending Intake Validation",
                        "Pending Clinical Review",
                        "Clinical Review In Progress",
                        "Pending Additional Information",
                        "QA Investigation",
                    ]
                )
            )
            .order_by(DonorReview.risk_score.desc(), DonorReview.created_at)
            .limit(160)
        ).scalars().all()
        for donor in active_donors:
            due_hours = 12 if donor.risk_level in {"Critical", "High"} else 36
            db.add(
                WorkflowTask(
                    task_type="Donor Review Task",
                    title=f"Review donor eligibility for {donor.donor_id}",
                    description=donor.recommended_action,
                    assigned_to_user_id=clinical_user.user_id if donor.risk_score >= 50 else intake_user.user_id,
                    assigned_role_id=roles["Clinical Reviewer"].role_id,
                    priority=donor.review_priority,
                    status=random.choice(["Assigned", "In Progress", "Pending", "Blocked"]),
                    workflow_state="Pending Clinical Review",
                    queue_name="Clinical Review Workbench",
                    due_date=donor.created_at + timedelta(hours=due_hours),
                    related_record_id=str(donor.review_id),
                    related_record_type="DonorReview",
                )
            )

        breached_incidents = db.execute(
            select(VendorIncident)
            .where(VendorIncident.sla_breached.is_(True))
            .order_by(VendorIncident.opened_at.desc())
            .limit(45)
        ).scalars().all()
        for incident in breached_incidents:
            db.add(
                WorkflowTask(
                    task_type="SLA Investigation Task",
                    title=f"Investigate SLA breach {incident.ticket_number}",
                    description=incident.impact_summary,
                    assigned_to_user_id=vendor_user.user_id,
                    assigned_role_id=roles["Vendor Operations Analyst"].role_id,
                    priority="Critical" if incident.severity == "Critical" else "High",
                    status=random.choice(["Assigned", "In Progress", "Escalated"]),
                    workflow_state="Vendor SLA Investigation",
                    queue_name="Vendor Operations Workbench",
                    due_date=incident.opened_at + timedelta(hours=24),
                    related_record_id=str(incident.incident_id),
                    related_record_type="VendorIncident",
                )
            )

        open_changes = db.execute(
            select(ChangeControl)
            .where(ChangeControl.approval_status.in_(["Draft", "Investigation", "Pending Approval"]))
            .limit(25)
        ).scalars().all()
        for change in open_changes:
            db.add(
                WorkflowTask(
                    task_type="SOP Deviation Investigation",
                    title=f"QMS investigation for {change.request_id}",
                    description=change.reason,
                    assigned_to_user_id=qa_user.user_id,
                    assigned_role_id=roles["Quality Assurance Specialist"].role_id,
                    priority=change.risk_level,
                    status=random.choice(["Assigned", "In Progress", "Blocked"]),
                    workflow_state="CAPA Investigation",
                    queue_name="QA Investigation Workbench",
                    due_date=change.created_at + timedelta(days=14),
                    related_record_id=str(change.change_id),
                    related_record_type="ChangeControl",
                )
            )
        db.flush()

    intake_task_exists = db.execute(
        select(WorkflowTask.task_id)
        .where(WorkflowTask.assigned_role_id == roles["Donor Intake Coordinator"].role_id)
        .limit(1)
    ).first()
    if not intake_task_exists:
        intake_user = users_by_role["Donor Intake Coordinator"]
        intake_donors = db.execute(
            select(DonorReview)
            .where(DonorReview.intake_status.in_(["Pending Intake Validation", "Pending Additional Information"]))
            .order_by(DonorReview.created_at.desc())
            .limit(65)
        ).scalars().all()
        for donor in intake_donors:
            db.add(
                WorkflowTask(
                    task_type="Intake Packet Validation",
                    title=f"Validate donor intake packet for {donor.donor_id}",
                    description="Resolve required fields, documentation, and readiness before clinical routing.",
                    assigned_to_user_id=intake_user.user_id,
                    assigned_role_id=roles["Donor Intake Coordinator"].role_id,
                    priority="High" if donor.missing_required_fields or donor.risk_score >= 50 else "Standard",
                    status=random.choice(["Assigned", "In Progress", "Blocked"]),
                    workflow_state="Pending Intake Validation",
                    queue_name="My Intake Workbench",
                    due_date=donor.created_at + timedelta(hours=18),
                    related_record_id=str(donor.review_id),
                    related_record_type="DonorReview",
                )
            )
        db.flush()

    manager_task_exists = db.execute(
        select(WorkflowTask.task_id)
        .where(WorkflowTask.assigned_role_id == roles["Operations Manager"].role_id)
        .limit(1)
    ).first()
    if not manager_task_exists:
        manager_user = users_by_role["Operations Manager"]
        escalated_source_tasks = db.execute(
            select(WorkflowTask)
            .where(WorkflowTask.status.in_(["Escalated", "Blocked"]))
            .order_by(WorkflowTask.due_date)
            .limit(18)
        ).scalars().all()
        for task in escalated_source_tasks:
            db.add(
                WorkflowTask(
                    task_type="Operational Escalation Review",
                    title=f"Resolve bottleneck for {task.title}",
                    description="Manager review of cross-functional queue pressure, priority, or reassignment need.",
                    assigned_to_user_id=manager_user.user_id,
                    assigned_role_id=roles["Operations Manager"].role_id,
                    priority="Critical",
                    status="Escalated",
                    workflow_state="Operations Escalation",
                    queue_name="Enterprise Queue Management",
                    due_date=datetime.now(UTC) + timedelta(hours=8),
                    related_record_id=str(task.task_id),
                    related_record_type="WorkflowTask",
                    escalation_level=max(task.escalation_level, 1),
                )
            )
        db.flush()

    existing_training = db.execute(select(SOPTrainingAssignment.assignment_id).limit(1)).first()
    if not existing_training:
        sops = db.execute(select(SOP).limit(4)).scalars().all()
        training_roles = [
            "Clinical Reviewer",
            "Donor Intake Coordinator",
            "Quality Assurance Specialist",
        ]
        for sop in sops:
            for role_name in training_roles:
                assigned_date = _random_datetime(45)
                status_choice = random.choice(["Assigned", "In Progress", "Completed", "Overdue"])
                due_date = assigned_date + timedelta(days=random.choice([14, 21, 30]))
                if status_choice == "Overdue":
                    due_date = datetime.now(UTC) - timedelta(days=random.randint(1, 18))
                assignment = SOPTrainingAssignment(
                    sop_id=sop.sop_id,
                    assigned_role_id=roles[role_name].role_id,
                    assigned_date=assigned_date,
                    due_date=due_date,
                    acknowledgment_status=status_choice,
                )
                db.add(assignment)
                db.flush()
                if status_choice == "Completed":
                    user = users_by_role[role_name]
                    db.add(
                        TrainingCompletion(
                            assignment_id=assignment.assignment_id,
                            completed_by_user_id=user.user_id,
                            completion_date=assigned_date + timedelta(days=random.randint(1, 10)),
                            acknowledgment_status="Acknowledged",
                            attestation_text="I acknowledge the SOP revision and workflow responsibilities.",
                        )
                    )

    for role_name, user in users_by_role.items():
        notice_exists = db.execute(
            select(Notification.notification_id)
            .where(Notification.user_id == user.user_id, Notification.notification_type == "System")
            .limit(1)
        ).first()
        if not notice_exists:
            create_notification(
                db,
                user_id=user.user_id,
                title=f"{role_name} workspace ready",
                message="Enterprise workflow tasks and regulated operations dashboards are available for review.",
                notification_type="System",
                priority="Normal",
                action_route="/dashboard",
            )

    existing_escalation_notice = db.execute(
        select(Notification.notification_id)
        .where(
            Notification.user_id == users_by_role["Operations Manager"].user_id,
            Notification.title == "Escalation review required",
        )
        .limit(1)
    ).first()
    if not existing_escalation_notice:
        create_notification(
            db,
            user_id=users_by_role["Operations Manager"].user_id,
            title="Escalation review required",
            message="Overdue donor review and vendor SLA tasks require operations manager review.",
            notification_type="Escalation",
            priority="Critical",
            action_route="/escalation",
        )

    _ensure_notification_density(db, roles, users_by_role)
    evaluate_overdue_tasks(db)
    db.commit()


def seed_database(records: int, force: bool = False) -> None:
    records = max(500, min(records, 5000))
    db = SessionLocal()
    try:
        existing = db.execute(select(DonorReview.review_id).limit(1)).first()
        if existing and not force:
            ensure_enterprise_data(db)
            print("Seed skipped donor reload: enterprise demo data verified.")
            return

        if force:
            for model in [
                AuditLog,
                WorkflowTimelineEvent,
                WorkflowTransitionEvent,
                AIOverrideEvent,
                AIDecision,
                TrainingCompletion,
                SOPTrainingAssignment,
                EscalationEvent,
                Notification,
                WorkflowTask,
                WorkflowNotificationRule,
                WorkflowEscalationRule,
                WorkflowNavigationRoute,
                WorkflowAssignmentRule,
                WorkflowTransitionRule,
                WorkflowStateMachine,
                RoleDashboardWidget,
                RoleNavigationConfig,
                RoleWorkspaceConfig,
                VendorIncident,
                ChangeControl,
                DonorReview,
                AIRiskRule,
                AIModelVersion,
                RiskCategory,
                RoleResponsibility,
                RolePermission,
                SOP,
                Vendor,
                User,
                Role,
            ]:
                db.execute(delete(model))
            db.commit()

        roles = _ensure_roles(db)
        users_by_role = _ensure_users(db, roles)
        ensure_ai_governance_data(db, users_by_role)
        users = list(users_by_role.values())

        vendors = [
            Vendor(
                vendor_name=name,
                system_name=system,
                criticality=criticality,
                sla_target_percent=sla,
                business_owner=random.choice(users).full_name,
            )
            for name, system, criticality, sla in VENDOR_SYSTEMS
        ]
        db.add_all(vendors)
        db.flush()

        risk_categories = [
            RiskCategory(label="Low", min_score=0, max_score=24, default_action="Approve"),
            RiskCategory(label="Moderate", min_score=25, max_score=49, default_action="Manual Clinical Review"),
            RiskCategory(label="High", min_score=50, max_score=74, default_action="Defer Pending Clinical Review"),
            RiskCategory(label="Critical", min_score=75, max_score=100, default_action="Reject or Escalate"),
        ]
        db.add_all(risk_categories)

        sop_templates = [
            ("SOP-DS-001", "Donor Intake Review"),
            ("SOP-DS-014", "AI-Assisted Screening Review"),
            ("SOP-QMS-022", "Change Control and CAPA"),
            ("SOP-VND-008", "Vendor SLA Escalation"),
        ]
        sops = [
            SOP(
                sop_code=code,
                title=title,
                version=f"{random.randint(1, 4)}.{random.randint(0, 9)}",
                effective_date=_random_datetime(180),
                approved_by_id=random.choice(users).user_id,
                revision_notes=random.choice(CHANGE_REASONS),
            )
            for code, title in sop_templates
        ]
        db.add_all(sops)
        db.flush()

        donors: list[DonorReview] = []
        for idx in range(1, records + 1):
            infectious = random.random() < 0.08
            travel = random.random() < 0.18
            missing = random.random() < 0.07
            status_choice = random.choices(
                STATUSES,
                weights=[22, 24, 12, 10, 9, 17, 6],
                k=1,
            )[0]
            created_at = _random_datetime(45)
            reviewer = random.choice(users) if status_choice != "Pending Intake Validation" else None
            reviewed_at = None
            if status_choice in {"Approved", "Rejected"}:
                reviewed_at = created_at + timedelta(hours=random.randint(2, 96))

            donor = DonorReview(
                donor_id=f"DNR-2026-{idx:05d}",
                donor_name=fake.name(),
                age=random.choices(
                    [random.randint(18, 69), random.randint(70, 88), random.randint(14, 17)],
                    weights=[82, 14, 4],
                    k=1,
                )[0],
                blood_type=random.choice(BLOOD_TYPES),
                infectious_history=infectious,
                travel_risk=travel,
                missing_required_fields=missing,
                intake_status=status_choice,
                reviewer_id=reviewer.user_id if reviewer else None,
                clinical_notes=random.choice(NOTES),
                attachment_placeholder="clinical_packet_placeholder.pdf",
                rejection_reason="Risk profile exceeds acceptance criteria"
                if status_choice == "Rejected"
                else None,
                created_at=created_at,
                updated_at=reviewed_at or created_at,
                reviewed_at=reviewed_at,
            )
            _apply_analysis(db, donor)
            donors.append(donor)
        db.add_all(donors)
        db.flush()

        for donor in random.sample(donors, k=min(len(donors), 180)):
            log_audit(
                db,
                user_id=donor.reviewer_id or random.choice(users).user_id,
                action_type=random.choice(
                    [
                        "CREATE_DONOR_INTAKE",
                        "UPDATE_DONOR_REVIEW",
                        f"DONOR_{donor.intake_status.upper()}",
                    ]
                ),
                table_name="fact_donor_review",
                record_id=str(donor.review_id),
                old_value=None,
                new_value=serialize_model(
                    donor,
                    [
                        "donor_id",
                        "intake_status",
                        "risk_score",
                        "risk_level",
                        "recommended_action",
                        "review_priority",
                    ],
                ),
            )

        changes = []
        for idx in range(1, 76):
            status_choice = random.choice(["Draft", "Investigation", "Pending Approval", "Approved", "Rejected"])
            created_at = _random_datetime(120)
            capa_required = idx <= 45 or random.random() < 0.35
            changes.append(
                ChangeControl(
                    request_id=f"CCR-2026-{idx:04d}",
                    requested_by_id=random.choice(users).user_id,
                    sop_id=random.choice(sops).sop_id,
                    reason=random.choice(CHANGE_REASONS),
                    risk_level=random.choice(["Low", "Moderate", "High", "Critical"]),
                    approval_status=status_choice,
                    capa_required=capa_required,
                    investigation_notes=fake.paragraph(nb_sentences=2),
                    implementation_due_date=created_at + timedelta(days=random.randint(7, 45)),
                    created_at=created_at,
                    approved_at=created_at + timedelta(days=random.randint(2, 20))
                    if status_choice == "Approved"
                    else None,
                )
            )
        db.add_all(changes)

        incidents = []
        for idx in range(1, 91):
            opened_at = _random_datetime(60)
            is_open = random.random() < 0.28
            resolved_at = None if is_open else opened_at + timedelta(hours=random.randint(1, 80))
            age_hours = (
                (datetime.now(UTC) - opened_at).total_seconds() / 3600
                if is_open
                else (resolved_at - opened_at).total_seconds() / 3600
            )
            severity = random.choice(["Low", "Medium", "High", "Critical"])
            breached = age_hours > 48 or severity == "Critical" and age_hours > 8
            incidents.append(
                VendorIncident(
                    vendor_id=random.choice(vendors).vendor_id,
                    ticket_number=f"VND-2026-{idx:05d}",
                    title=random.choice(
                        [
                            "Interface latency above threshold",
                            "Queued lab result feed delay",
                            "Document repository intermittent error",
                            "Support ticket response overdue",
                            "Scheduled maintenance exceeded approved window",
                        ]
                    ),
                    severity=severity,
                    status="Open" if is_open else "Resolved",
                    uptime_percent=round(random.uniform(97.9, 99.99), 2),
                    sla_breached=breached,
                    opened_at=opened_at,
                    resolved_at=resolved_at,
                    ticket_age_hours=round(age_hours, 1),
                    resolution_minutes=int(age_hours * 60) if resolved_at else None,
                    impact_summary=random.choice(
                        [
                            "No donor safety impact; operations monitored backlog.",
                            "Potential review delay; clinical queue prioritized manually.",
                            "QMS notification sent and vendor escalation opened.",
                            "Temporary workaround used by intake coordinators.",
                        ]
                    ),
                )
            )
        db.add_all(incidents)

        db.flush()
        ensure_enterprise_data(db)
        print(f"Seed complete: {records} donors, {len(changes)} change requests, {len(incidents)} vendor incidents.")
        print(f"Demo login: sysadmin / {DEFAULT_PASSWORD}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinical donor workflow utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Seed realistic demo data")
    seed_parser.add_argument("--records", type=int, default=1200, help="Donor records, clamped to 500-5000")
    seed_parser.add_argument("--force", action="store_true", help="Clear and reseed existing demo data")

    args = parser.parse_args()
    if args.command == "seed":
        seed_database(records=args.records, force=args.force)


if __name__ == "__main__":
    main()

