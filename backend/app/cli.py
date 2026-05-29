import argparse
import random
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import delete, or_, select

from app.auth.security import get_password_hash
from app.database import SessionLocal
from app.models import (
    CAPA,
    SOP,
    AccountType,
    AIDecision,
    AIModelVersion,
    AIOverrideEvent,
    AIRiskRule,
    AuditLog,
    AuthIdentity,
    BackgroundJob,
    ChangeControl,
    DataExportEvent,
    DeploymentEnvironment,
    Deviation,
    Disposition,
    DocumentAccess,
    DocumentVersion,
    Donor,
    DonorReview,
    DonorScreening,
    EligibilityDecision,
    EligibilityRule,
    EscalationEvent,
    ExternalInvitation,
    ExternalStatusMapping,
    InfectiousDiseaseResult,
    InfectiousDiseaseTest,
    MedicalSocialHistory,
    MFAConfiguration,
    Notification,
    Organization,
    PartnerComplaint,
    PartnerDocument,
    PartnerMessage,
    PartnerSubmission,
    PartnerSubmissionStatus,
    PasswordResetToken,
    ProcessingRelease,
    RealtimeEvent,
    RecoverySuitability,
    ReferralSource,
    RiskCategory,
    Role,
    RoleDashboardWidget,
    RoleNavigationConfig,
    RolePermission,
    RoleResponsibility,
    RoleWorkspaceConfig,
    SecureDocument,
    SecurityAudit,
    SecurityIncident,
    SidebarState,
    SignatureEvent,
    SOPTrainingAssignment,
    SupplierRelationship,
    SystemHealth,
    TissueType,
    TrainingCompletion,
    TrainingRecord,
    User,
    UserApprovalStatus,
    UserPreference,
    UserSessionRecord,
    ValidationEvidence,
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
from app.services.eligibility_engine import evaluate_donor_eligibility
from app.services.encryption import encrypt_text, protect_donor_master, protect_donor_review
from app.services.escalations import evaluate_overdue_tasks
from app.services.functional_routes import route_path_for_record
from app.services.notifications import create_notification
from app.services.risk_engine import analyze_donor_risk
from app.services.workspace_config import ensure_workspace_definitions

fake = Faker()

BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Unknown"]
STATUSES = [
    "Referral Received",
    "Intake In Progress",
    "Pending Administrative Screen",
    "Pending Medical Social History Review",
    "Pending Infectious Disease Review",
    "Pending Tissue Suitability Review",
    "Pending Recovery Suitability Review",
    "Pending Medical Director Review",
    "Awaiting Lab Results",
    "Awaiting Signatures",
    "Awaiting External Review",
    "Awaiting Medical Director Review",
    "Pending QA Review",
    "Recovery Authorized",
    "Processing Hold",
    "Pending Processing Release",
    "Released for Clinical Use",
    "Released for Research Use",
    "Quarantine",
    "Rejected",
    "Destroyed",
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

REFERRAL_SOURCES = [
    ("Memorial Donor Network", "OPO", "Great Lakes"),
    ("Aster Regional Hospital", "Hospital", "Northeast"),
    ("North Valley Recovery Partner", "Recovery Partner", "West"),
    ("Crescent Academic Medical Center", "Hospital", "South"),
    ("Helio Tissue Referral Line", "Referral Center", "Midwest"),
]

TISSUE_TYPES = [
    ("Cornea", "Ocular", 2, 75, 18, 168, "SOP-TS-101"),
    ("Skin", "Dermal", 15, 80, 24, 120, "SOP-TS-110"),
    ("Bone", "Musculoskeletal", 12, 70, 24, 120, "SOP-TS-120"),
    ("Tendon", "Musculoskeletal", 12, 65, 24, 120, "SOP-TS-121"),
    ("Heart Valve", "Cardiovascular", 0, 55, 24, 72, "SOP-TS-130"),
    ("Organ", "Organ", 0, 70, 12, 24, "SOP-TS-140"),
    ("Dermal Matrix", "Regenerative Medicine Material", 18, 75, 24, 168, "SOP-TS-150"),
]

INFECTIOUS_TESTS = [
    ("HIV NAT", "HIV", "NAT", 168, True, False),
    ("HIV Serology", "HIV", "Serology", 168, False, True),
    ("HBV NAT", "HBV", "NAT", 168, True, False),
    ("HCV NAT", "HCV", "NAT", 168, True, False),
    ("HTLV Serology", "HTLV", "Serology", 168, False, True),
    ("Syphilis Serology", "Syphilis", "Serology", 168, False, True),
    ("CMV Serology", "CMV", "Serology", 168, False, True),
    ("West Nile NAT", "West Nile", "NAT", 168, True, False),
]

DISPOSITIONS = [
    ("Clinical Transplant", "Released for transplantable clinical use."),
    ("Tissue Processing", "Accepted for downstream tissue processing."),
    ("Research Use", "Restricted to approved research use."),
    ("Quarantine", "Placed on quality hold pending additional review."),
    ("Destruction", "Rejected material requiring controlled destruction."),
    ("Rejected / Deferred", "Donor or material deferred from eligible recovery."),
]

ELIGIBILITY_RULES = [
    ("Identity Not Verified", "Administrative", "identity_verified", "is_false", "true", "Hold", "High", True, "Donor Intake Coordinator", "SOP-DS-001"),
    ("Legal Authorization Missing", "Administrative", "authorization_verified", "is_false", "true", "Reject", "Critical", True, "Donor Intake Coordinator", "SOP-DS-001"),
    ("Time Of Death Missing", "Administrative", "time_of_death_captured", "is_false", "true", "Hold", "High", True, "Donor Intake Coordinator", "SOP-DS-002"),
    ("Chain Of Custody Not Initiated", "Administrative", "chain_of_custody_initiated", "is_false", "true", "Hold", "High", True, "Quality Assurance Specialist", "SOP-QMS-012"),
    ("Recovery Window Invalid", "Administrative", "recovery_window_valid", "is_false", "true", "Reject", "Critical", True, "Operations Manager", "SOP-REC-005"),
    ("Cancer History", "Medical Social History", "cancer_history", "is_true", "true", "Medical Director Review", "High", True, "Clinical Reviewer", "SOP-CLN-210"),
    ("IV Drug Use", "Medical Social History", "iv_drug_use", "is_true", "true", "Medical Director Review", "High", True, "Clinical Reviewer", "SOP-CLN-211"),
    ("Unknown Donor History", "Medical Social History", "unknown_history", "is_true", "true", "Research Only", "Medium", True, "Clinical Reviewer", "SOP-CLN-212"),
    ("HIV NAT Positive", "Infectious Disease", "hiv_nat", "equals", "Positive", "Reject", "Critical", True, "Clinical Reviewer", "SOP-ID-300"),
    ("HIV Serology Positive", "Infectious Disease", "hiv_serology", "equals", "Positive", "Medical Director Review", "Critical", True, "Clinical Reviewer", "SOP-ID-301"),
    ("Specimen Window Invalid", "Infectious Disease", "specimen_window_invalid", "is_true", "true", "Hold", "High", True, "Quality Assurance Specialist", "SOP-ID-302"),
    ("Trauma Contamination", "Recovery Suitability", "trauma_contamination", "is_true", "true", "Recovery Rejected", "Critical", True, "Operations Manager", "SOP-REC-020"),
    ("Hospital Release Pending", "Recovery Suitability", "hospital_release_status", "not_equals", "Released", "Recovery Hold", "High", True, "Operations Manager", "SOP-REC-021"),
    ("Sterility Failure", "Processing Release", "sterility_testing", "equals", "Failed", "Reject / Destroy", "Critical", True, "Quality Assurance Specialist", "SOP-REL-400"),
    ("Traceability Not Verified", "Processing Release", "traceability_verification", "not_equals", "Verified", "QA Review Required", "High", True, "Quality Assurance Specialist", "SOP-REL-401"),
    ("Open CAPA Linked", "QMS Compliance", "open_capa_count", ">", "0", "CAPA Required", "High", True, "Quality Assurance Specialist", "SOP-QMS-022"),
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

MFA_REQUIRED_ROLES = {
    "System Administrator",
    "Business Technology Analyst",
    "Operations Manager",
    "Quality Assurance Specialist",
}


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
                display_name=full_name,
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
            user.display_name = user.display_name or full_name
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
        if not user.display_name:
            user.display_name = user.full_name
        if not user.role_id:
            role = fallback_roles[index % len(fallback_roles)]
            user.role_id = role.role_id
            user.role = role.role_name
    db.flush()
    return users_by_role


def _ensure_security_foundations(db, users_by_role: dict[str, User]) -> None:
    for account_type, description, is_internal, is_external, requires_approval in [
        ("internal", "Native platform account for internal operations.", True, False, False),
        ("supplier", "Legacy external supplier account type retained for compatibility.", False, True, True),
        ("partner", "Future partner account with organization-scoped access.", False, True, True),
        ("external", "Future external auditor or contractor account.", False, True, True),
    ]:
        row = db.execute(
            select(AccountType).where(AccountType.account_type_name == account_type)
        ).scalar_one_or_none()
        if not row:
            db.add(
                AccountType(
                    account_type_name=account_type,
                    description=description,
                    is_internal=is_internal,
                    is_external=is_external,
                    requires_approval=requires_approval,
                )
            )

    for status_name, description in [
        ("Pending Approval", "External or newly provisioned user awaiting approval."),
        ("Approved", "User is authorized for assigned operational access."),
        ("Rejected", "Access request was rejected."),
        ("Suspended", "Access is temporarily suspended."),
        ("Revoked", "Access was revoked and should not be restored without review."),
    ]:
        row = db.execute(
            select(UserApprovalStatus).where(UserApprovalStatus.status_name == status_name)
        ).scalar_one_or_none()
        if not row:
            db.add(UserApprovalStatus(status_name=status_name, description=description))

    internal_org = db.execute(
        select(Organization).where(Organization.organization_name == "Internal Operations")
    ).scalar_one_or_none()
    if not internal_org:
        internal_org = Organization(
            organization_name="Internal Operations",
            organization_type="internal",
            approval_status="Approved",
            contact_email="operations@teemails.com",
            mfa_required=True,
        )
        db.add(internal_org)
        db.flush()
    else:
        internal_org.contact_email = internal_org.contact_email or "operations@teemails.com"
        internal_org.mfa_required = True

    now = datetime.now(UTC)
    for role_name, user in users_by_role.items():
        user.account_type = "internal"
        user.user_type = "internal"
        user.organization_id = internal_org.organization_id
        user.is_internal = True
        user.is_external = False
        user.external_user_flag = False
        user.approval_status = "Approved"
        user.identity_provider = "Platform Native"
        user.mfa_enabled = role_name in MFA_REQUIRED_ROLES
        user.display_name = user.display_name or user.full_name
        user.password_changed_at = user.password_changed_at or now
        user.password_expires_at = user.password_expires_at or (now + timedelta(days=180))
        user.password_history = user.password_history or []

        identity = db.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.user_id,
                AuthIdentity.identity_provider == "Platform Native",
            )
        ).scalar_one_or_none()
        if not identity:
            db.add(
                AuthIdentity(
                    user_id=user.user_id,
                    identity_provider="Platform Native",
                    provider_subject=user.username or user.email,
                    user_type=user.user_type,
                    mfa_required=role_name in MFA_REQUIRED_ROLES,
                    external_user_flag=False,
                )
            )
        else:
            identity.provider_subject = user.username or user.email
            identity.mfa_required = role_name in MFA_REQUIRED_ROLES
            identity.user_type = user.user_type

        mfa = db.execute(select(MFAConfiguration).where(MFAConfiguration.user_id == user.user_id)).scalar_one_or_none()
        if not mfa:
            db.add(
                MFAConfiguration(
                    user_id=user.user_id,
                    method="TOTP",
                    is_enabled=role_name in MFA_REQUIRED_ROLES,
                    required_by_policy=role_name in MFA_REQUIRED_ROLES,
                    secret_encrypted=encrypt_text(f"demo-totp-secret-{user.username}"),
                    recovery_codes_encrypted=encrypt_text("demo-recovery-code"),
                    verified_at=now if role_name in MFA_REQUIRED_ROLES else None,
                )
            )
        else:
            mfa.required_by_policy = role_name in MFA_REQUIRED_ROLES
            mfa.is_enabled = mfa.is_enabled or role_name in MFA_REQUIRED_ROLES

    event_exists = db.execute(select(SecurityAudit.event_id).limit(1)).first()
    if not event_exists:
        db.add(
            SecurityAudit(
                user_id=users_by_role["System Administrator"].user_id,
                event_type="SECURITY_BASELINE_SEEDED",
                route="/admin/system-health",
                success=True,
                details={
                    "controls": [
                        "persistent_sessions",
                        "mfa_foundation",
                        "security_audit",
                        "secure_documents",
                        "external_ready_identity_foundation",
                    ]
                },
            )
        )

    for name, base_url, is_active in [
        ("DEV", "http://localhost:8501", True),
        ("TEST", "https://test.teemails.com", False),
        ("PROD", "https://teemails.com", False),
    ]:
        env = db.execute(
            select(DeploymentEnvironment).where(DeploymentEnvironment.environment_name == name)
        ).scalar_one_or_none()
        if not env:
            db.add(
                DeploymentEnvironment(
                    environment_name=name,
                    base_url=base_url,
                    database_url_masked="postgresql://***:***@db:5432/clinical_donor_workflow",
                    is_active=is_active,
                    deployed_version="0.1.0",
                )
            )

    for user in users_by_role.values():
        state = db.execute(select(SidebarState).where(SidebarState.user_id == user.user_id)).scalar_one_or_none()
        if not state:
            db.add(SidebarState(user_id=user.user_id, sidebar_collapsed=False, last_route="/dashboard"))
        pref = db.execute(
            select(UserPreference).where(
                UserPreference.user_id == user.user_id,
                UserPreference.preference_key == "notification_preferences",
            )
        ).scalar_one_or_none()
        if not pref:
            db.add(
                UserPreference(
                    user_id=user.user_id,
                    preference_key="notification_preferences",
                    preference_value={
                        "digest": True,
                        "sla_alerts": True,
                        "qms_alerts": True,
                        "ai_governance_alerts": True,
                    },
                )
            )

    incident_exists = db.execute(select(SecurityIncident.incident_id).limit(1)).first()
    if not incident_exists:
        db.add(
            SecurityIncident(
                incident_key="SEC-2026-0001",
                severity="Medium",
                status="Open",
                event_type="Suspicious Activity Review",
                summary="Repeated failed login monitoring enabled for production readiness.",
                assigned_to_user_id=users_by_role["System Administrator"].user_id,
                organization_id=internal_org.organization_id,
                details={"source": "seed", "control": "account_lockout_monitoring"},
            )
        )
    db.flush()


def _ensure_supplier_portal_data(db, roles: dict[str, Role]) -> None:
    supplier_role = roles.get("Partner External User") or roles.get("Supplier External User")
    admin_user = db.execute(select(User).where(User.username == "sysadmin")).scalar_one_or_none()
    internal_org = db.execute(
        select(Organization).where(Organization.organization_name == "Internal Operations")
    ).scalar_one_or_none()
    if not supplier_role or not internal_org or not admin_user:
        return

    password_hash = get_password_hash(DEFAULT_PASSWORD)
    now = datetime.now(UTC)
    for internal_state, external_status, description in [
        ("Referral Received", "Submitted", "Submission was received by the partner portal."),
        ("Pending Intake Validation", "Intake Review", "Submission is being checked for completeness."),
        ("Pending Administrative Screen", "Intake Review", "Submission is in intake review."),
        ("Pending Clinical Review", "Under Clinical Review", "Submission is under clinical review."),
        ("Pending Infectious Disease Review", "Under Clinical Review", "Clinical eligibility review is underway."),
        ("Pending QA Review", "Under QA Review", "Submission is under quality review."),
        ("QA Investigation", "Under QA Review", "Quality review is active."),
        ("CAPA Investigation", "Under QA Review", "Quality review is active."),
        ("Awaiting External Review", "Information Requested", "Additional information is requested from the partner."),
        ("Pending Additional Information", "Information Requested", "Additional information is requested from the partner."),
        ("Approved", "Approved", "Submission has been approved."),
        ("Rejected", "Rejected", "Submission has been rejected."),
        ("Closed", "Closed", "Submission lifecycle is closed."),
    ]:
        mapping = db.execute(
            select(ExternalStatusMapping).where(ExternalStatusMapping.internal_state == internal_state)
        ).scalar_one_or_none()
        if not mapping:
            db.add(
                ExternalStatusMapping(
                    internal_state=internal_state,
                    external_status=external_status,
                    external_description=description,
                )
            )
        else:
            mapping.external_status = external_status
            mapping.external_description = description
            mapping.is_active = True

    supplier_specs = [
        {
            "organization_name": "NorthStar Labs",
            "organization_type": "Partner",
            "contact_email": "partner@northstarlabs.example",
            "username": "partner",
            "full_name": "Riley Patel",
            "email": "riley.patel@northstarlabs.example",
            "risk_tier": "Medium",
        },
        {
            "organization_name": "NorthStar Labs",
            "organization_type": "Partner",
            "contact_email": "partner@northstarlabs.example",
            "username": "supplier",
            "full_name": "Sam Rivera",
            "email": "sam.rivera@northstarlabs.example",
            "risk_tier": "Medium",
        },
        {
            "organization_name": "Recovery Partners Southeast",
            "organization_type": "Recovery Organization",
            "contact_email": "coordination@recoverypartners.example",
            "username": "recoverypartner",
            "full_name": "Dana Ellis",
            "email": "dana.ellis@recoverypartners.example",
            "risk_tier": "High",
        },
        {
            "organization_name": "BioMatrix Packaging",
            "organization_type": "Supplier",
            "contact_email": "quality@biomatrixpackaging.example",
            "username": "biomatrix",
            "full_name": "Priya Nair",
            "email": "priya.nair@biomatrixpackaging.example",
            "risk_tier": "Low",
        },
    ]

    for spec in supplier_specs:
        org = db.execute(
            select(Organization).where(Organization.organization_name == spec["organization_name"])
        ).scalar_one_or_none()
        if not org:
            org = Organization(
                organization_name=spec["organization_name"],
                organization_type=spec["organization_type"],
                approval_status="Approved",
                contact_email=spec["contact_email"],
                mfa_required=True,
            )
            db.add(org)
            db.flush()
        else:
            org.organization_type = spec["organization_type"]
            org.approval_status = "Approved"
            org.contact_email = spec["contact_email"]
            org.mfa_required = True
            org.is_active = True

        relationship = db.execute(
            select(SupplierRelationship).where(
                SupplierRelationship.internal_organization_id == internal_org.organization_id,
                SupplierRelationship.external_organization_id == org.organization_id,
            )
        ).scalar_one_or_none()
        if not relationship:
            relationship = SupplierRelationship(
                internal_organization_id=internal_org.organization_id,
                external_organization_id=org.organization_id,
                relationship_type=spec["organization_type"],
                status="Approved",
                onboarding_status="Active",
                risk_tier=spec["risk_tier"],
                approved_by=admin_user.user_id,
                approved_at=now,
                details={
                    "scope": "bounded_partner_portal",
                    "access_model": "organization_scoped",
                },
            )
            db.add(relationship)
        else:
            relationship.status = "Approved"
            relationship.onboarding_status = "Active"
            relationship.risk_tier = spec["risk_tier"]
            relationship.approved_by = admin_user.user_id
            relationship.approved_at = relationship.approved_at or now

        user = db.execute(select(User).where(User.username == spec["username"])).scalar_one_or_none()
        if not user:
            user = db.execute(select(User).where(User.email == spec["email"])).scalar_one_or_none()
        if not user:
            user = User(
                username=spec["username"],
                full_name=spec["full_name"],
                display_name=spec["full_name"],
                email=spec["email"],
                hashed_password=password_hash,
                role_id=supplier_role.role_id,
                role=supplier_role.role_name,
                department="Partner Portal",
                is_active=True,
            )
            db.add(user)
            db.flush()
        user.username = spec["username"]
        user.full_name = spec["full_name"]
        user.display_name = user.display_name or spec["full_name"]
        user.email = spec["email"]
        user.hashed_password = user.hashed_password or password_hash
        user.role_id = supplier_role.role_id
        user.role = supplier_role.role_name
        user.department = "Partner Portal"
        user.account_type = "partner"
        user.user_type = "partner"
        user.organization_id = org.organization_id
        user.is_internal = False
        user.is_external = True
        user.external_user_flag = True
        user.approval_status = "Approved"
        user.identity_provider = "Platform Native"
        user.mfa_enabled = True
        user.is_active = True
        user.password_changed_at = user.password_changed_at or now
        user.password_expires_at = user.password_expires_at or (now + timedelta(days=180))
        relationship.primary_contact_user_id = user.user_id

        identity = db.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.user_id,
                AuthIdentity.identity_provider == "Platform Native",
            )
        ).scalar_one_or_none()
        if not identity:
            db.add(
                AuthIdentity(
                    user_id=user.user_id,
                    identity_provider="Platform Native",
                    provider_subject=user.username,
                    user_type="partner",
                    mfa_required=True,
                    external_user_flag=True,
                )
            )
        else:
            identity.provider_subject = user.username
            identity.user_type = "partner"
            identity.mfa_required = True
            identity.external_user_flag = True

        mfa = db.execute(select(MFAConfiguration).where(MFAConfiguration.user_id == user.user_id)).scalar_one_or_none()
        if not mfa:
            db.add(
                MFAConfiguration(
                    user_id=user.user_id,
                    method="TOTP",
                    is_enabled=True,
                    required_by_policy=True,
                    secret_encrypted=encrypt_text(f"demo-totp-secret-{user.username}"),
                    recovery_codes_encrypted=encrypt_text("demo-recovery-code"),
                    verified_at=now,
                )
            )
        else:
            mfa.is_enabled = True
            mfa.required_by_policy = True

        sidebar = db.execute(select(SidebarState).where(SidebarState.user_id == user.user_id)).scalar_one_or_none()
        if not sidebar:
            db.add(SidebarState(user_id=user.user_id, sidebar_collapsed=False, last_route="/partner"))
        else:
            sidebar.last_route = "/partner" if sidebar.last_route in {None, "", "/supplier"} else sidebar.last_route

        pref = db.execute(
            select(UserPreference).where(
                UserPreference.user_id == user.user_id,
                UserPreference.preference_key == "notification_preferences",
            )
        ).scalar_one_or_none()
        if not pref:
            db.add(
                UserPreference(
                    user_id=user.user_id,
                    preference_key="notification_preferences",
                    preference_value={
                        "partner_notifications": True,
                        "document_requests": True,
                        "approval_requests": True,
                    },
                )
            )

        task_specs = [
            ("Document Request", f"Upload NAT result packet for {org.organization_name}", "Requested Documents", "Awaiting External Review", "High"),
            ("External CAPA Response", f"Respond to CAPA evidence request for {org.organization_name}", "Partner CAPA Response", "Awaiting External Review", "Critical"),
            ("Partner Approval", f"Acknowledge qualification review for {org.organization_name}", "Partner Approvals", "Awaiting Signatures", "High"),
            ("Partner Review", f"Confirm annual certification status for {org.organization_name}", "Partner Collaboration Queue", "Submitted", "Standard"),
        ]
        existing_task_count = db.execute(
            select(WorkflowTask.task_id).where(WorkflowTask.organization_id == org.organization_id).limit(1)
        ).first()
        if not existing_task_count:
            for index, (task_type, title, queue_name, workflow_state, priority) in enumerate(task_specs, start=1):
                task = WorkflowTask(
                    task_type=task_type,
                    title=title,
                    description="Organization-scoped partner collaboration task.",
                    assigned_to_user_id=user.user_id,
                    assigned_role_id=supplier_role.role_id,
                    priority=priority,
                    status="Escalated" if priority == "Critical" else random.choice(["Assigned", "In Progress"]),
                    workflow_state=workflow_state,
                    queue_name=queue_name,
                    due_date=now + timedelta(hours=12 * index),
                    related_record_id=f"SUP-{org.organization_id:03d}-{index:03d}",
                    related_record_type=task_type.replace(" ", ""),
                    escalation_level=1 if priority == "Critical" else 0,
                    organization_id=org.organization_id,
                )
                db.add(task)
                db.flush()
                notification = Notification(
                    user_id=user.user_id,
                    title=f"[{priority}] {title}",
                    message=f"{queue_name} requires partner action for {org.organization_name}.",
                    notification_type=task_type,
                    priority=priority,
                    workflow_task_id=task.task_id,
                    related_record_type="WorkflowTask",
                    related_record_id=str(task.task_id),
                    action_route="/partner",
                    workflow_context={
                        "task_id": task.task_id,
                        "workflow_state": workflow_state,
                        "queue_name": queue_name,
                        "route_path": "/partner",
                    },
                    organization_id=org.organization_id,
                )
                db.add(notification)

        existing_docs = db.execute(
            select(SecureDocument.document_id).where(SecureDocument.organization_id == org.organization_id).limit(1)
        ).first()
        if not existing_docs:
            for version, document_type in enumerate(["Supplier Certification", "Qualification Doc"], start=1):
                doc = SecureDocument(
                    record_type="SupplierQualification",
                    record_id=f"SUP-QUAL-{org.organization_id:03d}",
                    document_name=f"{org.organization_name} {document_type}.pdf",
                    document_type=document_type,
                    storage_uri_encrypted=encrypt_text(f"partner://{org.organization_id}/{document_type.lower().replace(' ', '-')}.pdf"),
                    checksum_sha256=f"seed-checksum-{org.organization_id}-{version}",
                    uploaded_by=user.user_id,
                    access_classification="Partner Submitted",
                    organization_id=org.organization_id,
                )
                db.add(doc)
                db.flush()
                db.add(
                    DocumentVersion(
                        document_id=doc.document_id,
                        version_number=1,
                        document_status="Submitted",
                        uploaded_by=user.user_id,
                        storage_uri_encrypted=doc.storage_uri_encrypted,
                        checksum_sha256=doc.checksum_sha256,
                        approval_status="Pending Review",
                        extra_metadata={"source": "seed", "organization": org.organization_name},
                    )
                )
                db.add(
                    DocumentAccess(
                        document_id=doc.document_id,
                        user_id=user.user_id,
                        action_type="PARTNER_UPLOAD_SEEDED",
                        details={"document_type": document_type},
                    )
                )
                db.add(
                    PartnerDocument(
                        organization_id=org.organization_id,
                        document_id=doc.document_id,
                        document_category=document_type,
                        request_status="Submitted",
                    )
                )

        signature_exists = db.execute(
            select(SignatureEvent.signature_id).where(SignatureEvent.organization_id == org.organization_id).limit(1)
        ).first()
        if not signature_exists:
            db.add(
                SignatureEvent(
                    user_id=user.user_id,
                    organization_id=org.organization_id,
                    record_type="SupplierQualification",
                    record_id=f"SUP-QUAL-{org.organization_id:03d}",
                    signature_type="Partner Approval",
                    reason="Seeded partner qualification acknowledgement.",
                    meaning="Partner representative attests the qualification packet is accurate.",
                    signed_at=now,
                    signature_hash=f"seed-signature-{org.organization_id}-{user.user_id}",
                    prior_state="Pending Partner Approval",
                    new_state="Partner Approved",
                )
            )

        training = db.execute(
            select(TrainingRecord).where(TrainingRecord.user_id == user.user_id).limit(1)
        ).first()
        if not training:
            db.add(
                TrainingRecord(
                    user_id=user.user_id,
                    organization_id=org.organization_id,
                    status="Assigned",
                    expires_at=now + timedelta(days=365),
                    competency_status="Pending Validation",
                    validation_notes="Partner portal controlled-record handling training assigned.",
                )
            )

        event_exists = db.execute(
            select(RealtimeEvent.event_id).where(
                RealtimeEvent.organization_id == org.organization_id,
                RealtimeEvent.event_type == "Partner Portal Refreshed",
            )
        ).first()
        if not event_exists:
            db.add(
                RealtimeEvent(
                    event_type="Partner Portal Refreshed",
                    channel="partner-portal",
                    audience_user_id=user.user_id,
                    organization_id=org.organization_id,
                    record_type="Organization",
                    record_id=str(org.organization_id),
                    payload={"organization_name": org.organization_name, "relationship_status": relationship.status},
                )
            )
        job_exists = db.execute(
            select(BackgroundJob.job_id).where(
                BackgroundJob.organization_id == org.organization_id,
                BackgroundJob.job_type == "Partner SLA Monitor",
            )
        ).first()
        if not job_exists:
            db.add(
                BackgroundJob(
                    job_type="Partner SLA Monitor",
                    status="Queued",
                    priority="High" if spec["risk_tier"] == "High" else "Normal",
                    scheduled_for=now + timedelta(hours=1),
                    payload={"organization_id": org.organization_id, "monitor": "partner_response_sla"},
                    organization_id=org.organization_id,
                )
            )

        existing_partner_docs = db.execute(
            select(PartnerDocument.partner_document_id).where(PartnerDocument.organization_id == org.organization_id).limit(1)
        ).first()
        if not existing_partner_docs:
            for document in db.execute(
                select(SecureDocument).where(SecureDocument.organization_id == org.organization_id)
            ).scalars().all():
                db.add(
                    PartnerDocument(
                        organization_id=org.organization_id,
                        document_id=document.document_id,
                        document_category=document.document_type,
                        request_status=document.access_classification,
                    )
                )

        existing_submission = db.execute(
            select(PartnerSubmission.submission_id).where(PartnerSubmission.organization_id == org.organization_id).limit(1)
        ).first()
        if not existing_submission:
            submission_specs = [
                ("New Tissue Submission", "Tissue suitability packet", "Under Clinical Review", "Pending Clinical Review", "High"),
                ("New Recovery Submission", "Recovery coordination packet", "Intake Review", "Pending Intake Validation", "Standard"),
                ("New Qualification Request", "Annual qualification review", "Information Requested", "Awaiting External Review", "High"),
            ]
            for index, (submission_type, title, external_status, internal_state, priority) in enumerate(submission_specs, start=1):
                submission = PartnerSubmission(
                    submission_code=f"SUB-{now.year}-{org.organization_id:02d}{index:02d}",
                    organization_id=org.organization_id,
                    submitted_by_user_id=user.user_id,
                    submission_type=submission_type,
                    title=f"{org.organization_name} {title}",
                    partner_visible_status=external_status,
                    internal_state=internal_state,
                    priority=priority,
                    description="Seeded partner lifecycle submission for bounded external portal demonstration.",
                    product_or_tissue=random.choice(["Cornea", "Dermal Matrix", "Recovery Documentation", "Qualification File"]),
                    batch_or_reference=f"EXT-{org.organization_id:03d}-{index:03d}",
                    estimated_completion_at=now + timedelta(days=index + 1),
                    submitted_at=now - timedelta(days=index),
                    details={"source": "seed", "external_status_abstraction": True},
                )
                db.add(submission)
                db.flush()
                db.add(
                    PartnerSubmissionStatus(
                        submission_id=submission.submission_id,
                        from_status=None,
                        to_status=external_status,
                        internal_state=internal_state,
                        changed_by_user_id=user.user_id,
                        changed_at=submission.submitted_at,
                        note="Partner-visible lifecycle status seeded from internal workflow state.",
                    )
                )
                db.add(
                    WorkflowTask(
                        task_type="Partner Submission Review",
                        title=f"Review partner submission {submission.submission_code}",
                        description=submission.description,
                        assigned_to_user_id=None,
                        assigned_role_id=roles["Quality Assurance Specialist"].role_id if "Quality" in submission_type or "Qualification" in submission_type else roles["Donor Intake Coordinator"].role_id,
                        priority=priority,
                        status="Assigned",
                        workflow_state=internal_state,
                        queue_name="Partner Intake Review",
                        due_date=now + timedelta(hours=24 * index),
                        related_record_type="PartnerSubmission",
                        related_record_id=str(submission.submission_id),
                        organization_id=org.organization_id,
                    )
                )
            complaint = PartnerComplaint(
                complaint_code=f"QC-{now.year}-{org.organization_id:04d}",
                organization_id=org.organization_id,
                submitted_by_user_id=user.user_id,
                product_or_batch=f"Batch EXT-{org.organization_id:03d}",
                issue_category=random.choice(["Documentation discrepancy", "Packaging concern", "Temperature excursion"]),
                severity=random.choice(["Medium", "High"]),
                description="Partner-reported quality concern routed to QA review.",
                impact_assessment="Potential downstream review delay; no confirmed patient impact in demo data.",
                contact_email=spec["contact_email"],
                partner_visible_status="Under QA Review",
                internal_state="Pending QA Review",
                submitted_at=now - timedelta(days=2),
                details={"source": "seed", "complaint_intake": True},
            )
            db.add(complaint)
            db.flush()
            db.add(
                PartnerMessage(
                    organization_id=org.organization_id,
                    complaint_id=complaint.complaint_id,
                    sender_user_id=user.user_id,
                    audience="Internal",
                    subject=f"Initial complaint context for {complaint.complaint_code}",
                    body="Partner uploaded initial quality concern details and awaits QA review.",
                )
            )

    northstar = db.execute(select(Organization).where(Organization.organization_name == "NorthStar Labs")).scalar_one_or_none()
    pending_partner_token = f"seed-partner-invitation-{northstar.organization_id}" if northstar else ""
    invite_exists = db.execute(
        select(ExternalInvitation.invitation_id).where(
            or_(
                ExternalInvitation.email == "pending.partner@northstarlabs.example",
                ExternalInvitation.token_hash == pending_partner_token,
            )
        )
    ).first()
    if not invite_exists and northstar:
        db.add(
            ExternalInvitation(
                organization_id=northstar.organization_id,
                email="pending.partner@northstarlabs.example",
                invited_by=admin_user.user_id,
                role_id=supplier_role.role_id,
                token_hash=pending_partner_token,
                status="Pending Acceptance",
                expires_at=now + timedelta(days=7),
                extra_metadata={"source": "seed", "organization_name": northstar.organization_name},
            )
        )

    validation_exists = db.execute(select(ValidationEvidence.evidence_id).limit(1)).first()
    if not validation_exists:
        db.add(
            ValidationEvidence(
                evidence_type="Partner Portal Validation",
                title="Partner organization scoping validation evidence",
                status="Approved",
                owner_user_id=admin_user.user_id,
                approved_by=admin_user.user_id,
                approved_at=now,
                details={
                    "control": "organization_scoped_rbac",
                    "evidence": "partner users can only query records linked to their organization_id",
                },
            )
        )

    db.flush()


def _protect_sensitive_demo_data(db, users_by_role: dict[str, User]) -> None:
    internal_org = db.execute(
        select(Organization).where(Organization.organization_name == "Internal Operations")
    ).scalar_one_or_none()
    org_id = internal_org.organization_id if internal_org else None
    for donor in db.execute(select(DonorReview)).scalars():
        donor.organization_id = donor.organization_id or org_id
        protect_donor_review(donor)
    for donor in db.execute(select(Donor)).scalars():
        donor.organization_id = donor.organization_id or org_id
        protect_donor_master(donor)
    for model in [ProcessingRelease, Deviation, CAPA, WorkflowTask, Notification, SecureDocument]:
        for row in db.execute(select(model)).scalars():
            if hasattr(row, "organization_id") and not row.organization_id:
                row.organization_id = org_id
    for result in db.execute(select(InfectiousDiseaseResult)).scalars():
        result.result_value_encrypted = encrypt_text(result.result_value)
    for history in db.execute(select(MedicalSocialHistory)).scalars():
        history.review_notes_encrypted = encrypt_text(history.review_notes)

    qa_user = users_by_role.get("Quality Assurance Specialist")
    if not qa_user:
        db.flush()
        return

    existing_docs = db.execute(select(SecureDocument.document_id).limit(1)).first()
    if existing_docs:
        db.flush()
        return
    donor_rows = db.execute(select(Donor).order_by(Donor.created_at.desc()).limit(24)).scalars().all()
    for index, donor in enumerate(donor_rows):
        document_type = ["Consent Form", "Lab Report", "Medical Social History", "Chain of Custody"][index % 4]
        db.add(
            SecureDocument(
                record_type="Donor",
                record_id=str(donor.donor_pk),
                document_name=f"{document_type} - {donor.donor_identifier}",
                document_type=document_type,
                storage_uri_encrypted=encrypt_text(f"s3://protected-demo/donors/{donor.donor_identifier}/{index}.pdf") or "",
                uploaded_by=qa_user.user_id,
                access_classification="Protected Health Information",
                organization_id=org_id,
            )
        )
    releases = db.execute(select(ProcessingRelease).limit(12)).scalars().all()
    for release in releases:
        db.add(
            SecureDocument(
                record_type="ProcessingRelease",
                record_id=str(release.release_id),
                document_name=f"Release packet {release.release_identifier}",
                document_type="Release Documentation",
                storage_uri_encrypted=encrypt_text(f"s3://protected-demo/releases/{release.release_identifier}.pdf") or "",
                uploaded_by=qa_user.user_id,
                access_classification="Controlled QMS Record",
                organization_id=org_id,
            )
        )
    db.flush()


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


def _ensure_eligibility_reference_data(db, users_by_role: dict[str, User]) -> dict[str, list]:
    analyst = users_by_role.get("Business Technology Analyst")
    sources = []
    for name, source_type, region in REFERRAL_SOURCES:
        source = db.execute(select(ReferralSource).where(ReferralSource.source_name == name)).scalar_one_or_none()
        if not source:
            source = ReferralSource(
                source_name=name,
                source_type=source_type,
                contact_name=fake.name(),
                region=region,
            )
            db.add(source)
        sources.append(source)

    tissues = []
    for name, category, min_age, max_age, ischemic, preservation, sop in TISSUE_TYPES:
        tissue = db.execute(select(TissueType).where(TissueType.tissue_name == name)).scalar_one_or_none()
        if not tissue:
            tissue = TissueType(
                tissue_name=name,
                tissue_category=category,
                min_age=min_age,
                max_age=max_age,
                max_ischemic_hours=ischemic,
                preservation_window_hours=preservation,
                sop_reference=sop,
            )
            db.add(tissue)
        tissues.append(tissue)

    tests = []
    for name, pathogen, method, valid_window, reject, review in INFECTIOUS_TESTS:
        test = db.execute(select(InfectiousDiseaseTest).where(InfectiousDiseaseTest.test_name == name)).scalar_one_or_none()
        if not test:
            test = InfectiousDiseaseTest(
                test_name=name,
                pathogen=pathogen,
                test_method=method,
                valid_window_hours=valid_window,
                rejection_if_positive=reject,
                review_if_positive=review,
            )
            db.add(test)
        tests.append(test)

    dispositions = []
    for name, description in DISPOSITIONS:
        disposition = db.execute(select(Disposition).where(Disposition.disposition_name == name)).scalar_one_or_none()
        if not disposition:
            disposition = Disposition(disposition_name=name, description=description)
            db.add(disposition)
        dispositions.append(disposition)

    for payload in ELIGIBILITY_RULES:
        (
            rule_name,
            rule_category,
            condition_field,
            condition_operator,
            condition_value,
            outcome,
            severity,
            requires_review,
            required_role,
            sop_reference,
        ) = payload
        rule = db.execute(select(EligibilityRule).where(EligibilityRule.rule_name == rule_name)).scalar_one_or_none()
        if not rule:
            db.add(
                EligibilityRule(
                    rule_name=rule_name,
                    rule_category=rule_category,
                    condition_field=condition_field,
                    condition_operator=condition_operator,
                    condition_value=condition_value,
                    outcome=outcome,
                    severity=severity,
                    requires_review=requires_review,
                    required_role=required_role,
                    sop_reference=sop_reference,
                    created_by=analyst.user_id if analyst else None,
                    approved_by=analyst.user_id if analyst else None,
                )
            )
    db.flush()
    return {"sources": sources, "tissues": tissues, "tests": tests, "dispositions": dispositions}


def _ensure_eligibility_workflow_config(db, roles: dict[str, Role]) -> None:
    state_rows = [
        ("Referral Received", "Referral Intake", "Donor Intake Coordinator", ["Create Referral", "Validate Intake"], ["Intake In Progress"], 8, False),
        ("Intake In Progress", "Referral Intake", "Donor Intake Coordinator", ["Validate Intake", "Request Missing Info", "Cancel Referral"], ["Pending Administrative Screen", "Rejected"], 12, False),
        ("Pending Administrative Screen", "Administrative Screening", "Donor Intake Coordinator", ["Submit to Admin Screen", "Place Hold", "Reject Donor"], ["Pending Medical Social History Review", "Processing Hold", "Rejected"], 12, False),
        ("Pending Medical Social History Review", "Clinical Eligibility", "Clinical Reviewer", ["Continue Review", "Request Medical Director Review", "Reject Donor"], ["Pending Infectious Disease Review", "Pending Medical Director Review", "Rejected"], 24, False),
        ("Pending Infectious Disease Review", "Clinical Eligibility", "Clinical Reviewer", ["Continue Review", "Request Medical Director Review", "Reject Donor"], ["Pending Tissue Suitability Review", "Pending Medical Director Review", "Rejected"], 24, False),
        ("Pending Tissue Suitability Review", "Clinical Eligibility", "Clinical Reviewer", ["Approve for Recovery Review", "Request Medical Director Review", "Reject Donor"], ["Pending Recovery Suitability Review", "Pending Medical Director Review", "Rejected"], 24, False),
        ("Pending Recovery Suitability Review", "Recovery Suitability", "Clinical Reviewer", ["Authorize Recovery", "Recovery Hold", "Reject Donor"], ["Recovery Authorized", "Processing Hold", "Rejected"], 18, False),
        ("Pending Medical Director Review", "Medical Director Escalation", "Clinical Reviewer", ["Approve for Recovery Review", "Reject Donor"], ["Pending Recovery Suitability Review", "Rejected"], 12, False),
        ("Awaiting Lab Results", "Waiting", "Clinical Reviewer", ["Continue Review", "Request Medical Director Review", "Place Hold"], ["Pending Infectious Disease Review", "Pending Medical Director Review", "Processing Hold"], 36, False),
        ("Awaiting Signatures", "Waiting", "Quality Assurance Specialist", ["Approve QA Release", "Place Hold"], ["Pending Processing Release", "Processing Hold"], 24, False),
        ("Awaiting External Review", "Waiting", "Operations Manager", ["Reassign Task", "Escalate Priority", "Override SLA"], ["Pending QA Review", "Operations Escalation", "Processing Hold"], 48, False),
        ("Awaiting Medical Director Review", "Medical Director Escalation", "Clinical Reviewer", ["Approve for Recovery Review", "Reject Donor"], ["Pending Recovery Suitability Review", "Rejected"], 12, False),
        ("Recovery Authorized", "Recovery Authorization", "Clinical Reviewer", ["Submit to QA Review"], ["Pending QA Review"], 12, False),
        ("Pending QA Review", "QMS Review", "Quality Assurance Specialist", ["Approve QA Release", "Place Hold", "Open Deviation", "Open CAPA", "Reject Release"], ["Pending Processing Release", "Processing Hold", "Rejected", "Destroyed"], 24, False),
        ("Processing Hold", "QMS Review", "Quality Assurance Specialist", ["Open CAPA", "Request Rework", "Reject Release"], ["Pending QA Review", "Destroyed"], 72, False),
        ("Pending Processing Release", "Processing Release", "Quality Assurance Specialist", ["Approve Release", "Place Processing Hold", "Reject Release"], ["Released for Clinical Use", "Released for Research Use", "Processing Hold", "Destroyed"], 24, False),
        ("Released for Clinical Use", "Final Disposition", "Quality Assurance Specialist", [], ["Closed"], 0, True),
        ("Released for Research Use", "Final Disposition", "Quality Assurance Specialist", [], ["Closed"], 0, True),
        ("Quarantine", "Final Disposition", "Quality Assurance Specialist", [], ["Closed"], 0, True),
        ("Rejected", "Final Disposition", "Clinical Reviewer", [], ["Closed"], 0, True),
        ("Destroyed", "Final Disposition", "Quality Assurance Specialist", [], ["Closed"], 0, True),
        ("Closed", "Final Disposition", "Operations Manager", [], [], 0, True),
    ]
    for index, (state, category, role_name, actions, next_states, sla, terminal) in enumerate(state_rows, start=1):
        row = db.execute(select(WorkflowStateMachine).where(WorkflowStateMachine.state_name == state)).scalar_one_or_none()
        payload = {
            "state_category": category,
            "owning_role_id": roles[role_name].role_id if role_name in roles else None,
            "allowed_roles": [role_name],
            "allowed_actions": actions,
            "next_possible_states": next_states,
            "sla_hours": sla,
            "is_terminal": terminal,
            "is_terminal_state": terminal,
            "sort_order": index,
        }
        if row:
            for field, value in payload.items():
                setattr(row, field, value)
        else:
            db.add(WorkflowStateMachine(state_name=state, **payload))

    transition_rows = [
        ("validate_intake", "Validate Intake", "Intake In Progress", "Pending Administrative Screen", "Donor Intake Coordinator", "Donor Intake Coordinator", "Administrative Exclusion Screen", "Intake Validated", 12),
        ("submit_admin_screen", "Submit to Admin Screen", "Pending Administrative Screen", "Pending Medical Social History Review", "Donor Intake Coordinator", "Clinical Reviewer", "Medical Social History Review", "Referral Routed", 24),
        ("continue_infectious_review", "Continue Infectious Disease Review", "Pending Medical Social History Review", "Pending Infectious Disease Review", "Clinical Reviewer", "Clinical Reviewer", "Infectious Disease Eligibility Review", "Medical Review Complete", 24),
        ("continue_tissue_review", "Continue Tissue Suitability Review", "Pending Infectious Disease Review", "Pending Tissue Suitability Review", "Clinical Reviewer", "Clinical Reviewer", "Tissue-Specific Eligibility Review", "Infectious Review Complete", 24),
        ("approve_for_recovery_review", "Approve for Recovery Review", "Pending Tissue Suitability Review", "Pending Recovery Suitability Review", "Clinical Reviewer", "Clinical Reviewer", "Recovery Suitability Review", "Tissue Suitability Complete", 18),
        ("request_medical_director_review", "Request Medical Director Review", "Pending Infectious Disease Review", "Pending Medical Director Review", "Clinical Reviewer", "Clinical Reviewer", "Medical Director Review", "Medical Director Review", 12),
        ("authorize_recovery", "Authorize Recovery", "Pending Recovery Suitability Review", "Recovery Authorized", "Clinical Reviewer", "Quality Assurance Specialist", "QA Recovery Authorization Review", "Recovery Authorized", 12),
        ("submit_to_qa_release", "Submit to QA Review", "Recovery Authorized", "Pending QA Review", "Clinical Reviewer", "Quality Assurance Specialist", "QA Release Review", "QA Review Requested", 24),
        ("approve_qa_release", "Approve QA Release", "Pending QA Review", "Pending Processing Release", "Quality Assurance Specialist", "Quality Assurance Specialist", "Processing Release Review", "QA Release Approved", 24),
        ("place_processing_hold", "Place Processing Hold", "Pending QA Review", "Processing Hold", "Quality Assurance Specialist", "Quality Assurance Specialist", "Processing Hold Review", "Processing Hold", 72),
        ("open_deviation", "Open Deviation", "Pending QA Review", "Pending QA Review", "Quality Assurance Specialist", "Quality Assurance Specialist", "Deviation Investigation", "Deviation Opened", 72),
        ("open_capa", "Open CAPA", "Processing Hold", "Pending QA Review", "Quality Assurance Specialist", "Quality Assurance Specialist", "CAPA Review", "CAPA Opened", 168),
        ("approve_release", "Approve Release", "Pending Processing Release", "Released for Clinical Use", "Quality Assurance Specialist", "Operations Manager", "Final Disposition Review", "Released", 0),
        ("reject_release", "Reject Release", "Pending Processing Release", "Destroyed", "Quality Assurance Specialist", "Operations Manager", "Final Disposition Review", "Destroyed", 0),
        ("reject_donor_eligibility", "Reject Donor", "Pending Medical Social History Review", "Rejected", "Clinical Reviewer", "Operations Manager", "Final Disposition Review", "Rejected", 0),
    ]
    for action_name, label, from_state, to_state, source_role, target_role, task_type, notification_type, sla in transition_rows:
        rule = db.execute(
            select(WorkflowTransitionRule).where(WorkflowTransitionRule.action_name == action_name)
        ).scalar_one_or_none()
        payload = {
            "action_label": label,
            "from_state": from_state,
            "to_state": to_state,
            "source_role_id": roles[source_role].role_id,
            "target_role_id": roles[target_role].role_id,
            "task_type": task_type,
            "notification_type": notification_type,
            "audit_action": action_name.upper(),
            "sla_hours": sla,
            "is_active": True,
        }
        if rule:
            for field, value in payload.items():
                setattr(rule, field, value)
        else:
            db.add(WorkflowTransitionRule(action_name=action_name, **payload))
    db.flush()


def _random_donor_history(status: str) -> dict:
    return {
        "identity_verified": random.random() > 0.06,
        "authorization_verified": random.random() > 0.05,
        "chain_of_custody_initiated": random.random() > 0.08,
        "specimen_available": random.random() > 0.07,
        "recovery_window_valid": status not in {"Rejected", "Destroyed"} and random.random() > 0.08,
        "jurisdiction_cleared": random.random() > 0.04,
        "documentation_complete": random.random() > 0.18,
        "source_validated": random.random() > 0.03,
    }


def _ensure_donor_eligibility_data(db, roles: dict[str, Role], users_by_role: dict[str, User]) -> None:
    reference = _ensure_eligibility_reference_data(db, users_by_role)
    _ensure_eligibility_workflow_config(db, roles)
    sources = reference["sources"]
    tissues = reference["tissues"]
    tests = reference["tests"]

    existing_donors = db.execute(select(Donor.donor_pk).limit(1)).first()
    if not existing_donors:
        review_rows = db.execute(select(DonorReview).order_by(DonorReview.review_id).limit(1200)).scalars().all()
        for index, review in enumerate(review_rows, start=1):
            status = random.choices(
                STATUSES,
                weights=[8, 12, 15, 14, 12, 10, 7, 5, 6, 4, 4, 5, 3, 2, 2, 1, 1],
                k=1,
            )[0]
            created_at = review.created_at or _random_datetime(90)
            donor = Donor(
                donor_identifier=f"D-{index:04d}",
                donor_review_id=review.review_id,
                donor_name=review.donor_name,
                age=review.age,
                blood_type=review.blood_type,
                sex=random.choice(["Female", "Male", "Unknown"]),
                referral_source_id=random.choice(sources).source_id,
                time_of_death=created_at - timedelta(hours=random.randint(4, 48)),
                source_organization=random.choice(sources).source_name,
                donor_history=_random_donor_history(status),
                current_workflow_state=status,
                eligibility_status=random.choice(["Pending", "Eligible", "Conditional", "Hold", "Medical Director Review", "Rejected"]),
                final_disposition=random.choice(["Clinical Transplant", "Tissue Processing", "Research Use", "Quarantine", None])
                if status in {"Released for Clinical Use", "Released for Research Use", "Quarantine", "Rejected", "Destroyed"}
                else None,
                created_at=created_at,
                updated_at=review.updated_at or created_at,
            )
            db.add(donor)
        db.flush()

    donors = db.execute(select(Donor).order_by(Donor.donor_pk)).scalars().all()
    existing_screening = db.execute(select(DonorScreening.screening_id).limit(1)).first()
    if not existing_screening:
        for donor in donors:
            db.add(
                DonorScreening(
                    donor_pk=donor.donor_pk,
                    referral_id=f"REF-2026-{donor.donor_pk:05d}",
                    administrative_outcome=random.choice(["Continue", "Continue", "Hold", "Escalate", "Reject"]),
                    medical_social_outcome=random.choice(["Eligible", "Conditional", "Medical Director Review", "Research Only", "Reject"]),
                    infectious_disease_outcome=random.choice(["Continue", "Continue", "Hold", "Medical Director Review", "Reject"]),
                    tissue_suitability_outcome=random.choice(["Eligible", "Conditional", "Research Only", "Reject"]),
                    recovery_suitability_outcome=random.choice(["Recovery Approved", "Recovery Hold", "Recovery Escalation", "Recovery Rejected"]),
                    qa_outcome=random.choice(["Pending", "QA Review Required", "Release Approved", "Release Hold", "CAPA Required"]),
                    automated_rule_outcome=random.choice(["Continue", "Conditional", "Hold", "Medical Director Review"]),
                    current_decision=donor.eligibility_status,
                    created_at=donor.created_at,
                    updated_at=donor.updated_at,
                )
            )
        db.flush()

    if not db.execute(select(MedicalSocialHistory.history_id).limit(1)).first():
        for donor in random.sample(donors, k=min(180, len(donors))):
            history = MedicalSocialHistory(
                donor_pk=donor.donor_pk,
                cancer_history=random.random() < 0.08,
                neurological_disease=random.random() < 0.04,
                autoimmune_disease=random.random() < 0.06,
                transmissible_disease_history=random.random() < 0.05,
                iv_drug_use=random.random() < 0.07,
                incarceration_history=random.random() < 0.04,
                travel_exposure=random.random() < 0.12,
                high_risk_behavior=random.random() < 0.05,
                unknown_history=random.random() < 0.08,
                outcome=random.choice(["Eligible", "Conditional", "Medical Director Review", "Research Only", "Reject"]),
                review_notes=random.choice(NOTES),
            )
            db.add(history)
        db.flush()

    if not db.execute(select(InfectiousDiseaseResult.result_id).limit(1)).first():
        for donor in random.sample(donors, k=min(220, len(donors))):
            for test in tests:
                positive_rate = 0.015 if test.rejection_if_positive else 0.04
                result = random.choices(["Negative", "Positive", "Indeterminate"], weights=[1 - positive_rate - 0.02, positive_rate, 0.02], k=1)[0]
                db.add(
                    InfectiousDiseaseResult(
                        donor_pk=donor.donor_pk,
                        test_id=test.test_id,
                        result_value=result,
                        specimen_collected_at=donor.time_of_death + timedelta(hours=random.randint(1, 24)) if donor.time_of_death else _random_datetime(30),
                        specimen_window_valid=random.random() > 0.06,
                        reviewed_by=users_by_role["Clinical Reviewer"].user_id,
                        review_status="Review Required" if result != "Negative" else "Reviewed",
                    )
                )
        db.flush()

    if not db.execute(select(RecoverySuitability.recovery_id).limit(1)).first():
        for donor in random.sample(donors, k=min(110, len(donors))):
            tissue = random.choice(tissues)
            db.add(
                RecoverySuitability(
                    donor_pk=donor.donor_pk,
                    tissue_type_id=tissue.tissue_type_id,
                    refrigeration_timing_hours=round(random.uniform(1, 18), 1),
                    body_cooling_status=random.choice(["Cooling Complete", "Cooling Delayed", "Unknown"]),
                    trauma_contamination=random.random() < 0.08,
                    blood_draw_timing_hours=round(random.uniform(1, 36), 1),
                    hospital_release_status=random.choice(["Released", "Pending", "Delayed"]),
                    recovery_environment=random.choice(["Hospital OR", "Recovery Suite", "Morgue", "Transport"]),
                    recovery_window_hours=round(random.uniform(6, 48), 1),
                    outcome=random.choice(["Recovery Approved", "Recovery Hold", "Recovery Escalation", "Recovery Rejected"]),
                    reviewed_at=_random_datetime(20),
                )
            )
        db.flush()

    releases: list[ProcessingRelease] = []
    if not db.execute(select(ProcessingRelease.release_id).limit(1)).first():
        for index, donor in enumerate(random.sample(donors, k=min(60, len(donors))), start=1):
            status = random.choice(["Pending QA Review", "Release Approved", "Release Hold", "QA Review Required", "CAPA Required", "Reject / Destroy"])
            release = ProcessingRelease(
                release_identifier=f"REL-2026-{index:04d}",
                donor_pk=donor.donor_pk,
                tissue_type_id=random.choice(tissues).tissue_type_id,
                sterility_testing=random.choice(["Passed", "Passed", "Pending", "Failed"]),
                bioburden_status=random.choice(["Acceptable", "Acceptable", "Pending", "Failed"]),
                environmental_monitoring=random.choice(["Acceptable", "Pending", "Exception"]),
                packaging_qc=random.choice(["Verified", "Pending", "Exception"]),
                labeling_verification=random.choice(["Verified", "Pending", "Exception"]),
                traceability_verification=random.choice(["Verified", "Pending", "Exception"]),
                chain_of_custody_verified=random.random() > 0.08,
                release_status=status,
                final_disposition=random.choice(["Clinical Transplant", "Tissue Processing", "Research Use", "Quarantine", "Destruction"]),
                created_at=_random_datetime(45),
                released_at=_random_datetime(10) if status == "Release Approved" else None,
            )
            db.add(release)
            releases.append(release)
        db.flush()
    else:
        releases = list(db.execute(select(ProcessingRelease).limit(100)).scalars().all())

    deviations: list[Deviation] = []
    if not db.execute(select(Deviation.deviation_id).limit(1)).first():
        for index, donor in enumerate(random.sample(donors, k=min(45, len(donors))), start=1):
            release = random.choice(releases) if releases else None
            deviation = Deviation(
                deviation_code=f"DEV-2026-{index:04d}",
                donor_pk=donor.donor_pk,
                release_id=release.release_id if release else None,
                deviation_category=random.choice(["Documentation", "Chain of Custody", "Environmental Monitoring", "Labeling", "Processing Hold"]),
                severity=random.choice(["Low", "Medium", "High", "Critical"]),
                description=fake.paragraph(nb_sentences=2),
                status=random.choice(["Open", "Investigation", "Pending QA Review", "Closed"]),
                opened_at=_random_datetime(60),
                closed_at=_random_datetime(20) if random.random() < 0.25 else None,
            )
            db.add(deviation)
            deviations.append(deviation)
        db.flush()
    else:
        deviations = list(db.execute(select(Deviation).limit(100)).scalars().all())

    if not db.execute(select(CAPA.capa_id).limit(1)).first():
        for index, deviation in enumerate(random.sample(deviations, k=min(30, len(deviations))), start=1):
            capa = CAPA(
                capa_code=f"CAPA-2026-{index:04d}",
                donor_pk=deviation.donor_pk,
                deviation_id=deviation.deviation_id,
                release_id=deviation.release_id,
                root_cause=random.choice(["Procedure gap", "Training gap", "System interface delay", "Documentation mismatch"]),
                corrective_action_owner=random.choice([users_by_role["Quality Assurance Specialist"].full_name, users_by_role["Operations Manager"].full_name]),
                status=random.choice(["Open", "Investigation", "Effectiveness Check", "Closed"]),
                due_date=datetime.now(UTC) + timedelta(days=random.randint(7, 45)),
                closed_at=_random_datetime(15) if random.random() < 0.2 else None,
            )
            db.add(capa)
        db.flush()

    decision_count = len(db.execute(select(EligibilityDecision.decision_id).limit(1)).all())
    if decision_count == 0:
        clinical_user = users_by_role["Clinical Reviewer"]
        categories = ["Administrative", "Medical Social History", "Infectious Disease", "Recovery Suitability", "Processing Release", "QMS Compliance"]
        for donor in random.sample(donors, k=min(650, len(donors))):
            evaluate_donor_eligibility(db, donor, category=random.choice(categories), user_id=clinical_user.user_id)
        db.flush()

    _ensure_eligibility_tasks_notifications_audits(db, donors, roles, users_by_role)


def _ensure_eligibility_tasks_notifications_audits(db, donors: list[Donor], roles: dict[str, Role], users_by_role: dict[str, User]) -> None:
    existing_tasks = len(db.execute(select(WorkflowTask.task_id)).all())
    task_targets = [
        ("Referral Intake", "Donor Intake Coordinator", "Referral Intake Workbench", "Intake In Progress"),
        ("Administrative Exclusion Screen", "Donor Intake Coordinator", "Administrative Screening Queue", "Pending Administrative Screen"),
        ("Medical Social History Review", "Clinical Reviewer", "Medical Review Queue", "Pending Medical Social History Review"),
        ("Infectious Disease Eligibility Review", "Clinical Reviewer", "Infectious Disease Review Queue", "Pending Infectious Disease Review"),
        ("Tissue-Specific Eligibility Review", "Clinical Reviewer", "Tissue Suitability Queue", "Pending Tissue Suitability Review"),
        ("Recovery Suitability Review", "Clinical Reviewer", "Recovery Suitability Queue", "Pending Recovery Suitability Review"),
        ("Medical Director Escalation", "Clinical Reviewer", "Medical Director Review Queue", "Pending Medical Director Review"),
        ("QA Processing Release Review", "Quality Assurance Specialist", "QA Release Queue", "Pending QA Review"),
        ("Processing Hold Review", "Quality Assurance Specialist", "Processing Hold Queue", "Processing Hold"),
    ]
    if existing_tasks < 500:
        needed = 500 - existing_tasks
        for donor in random.sample(donors, k=min(needed, len(donors))):
            task_type, role_name, queue_name, workflow_state = random.choice(task_targets)
            role = roles[role_name]
            user = users_by_role[role_name]
            priority = random.choice(["Routine", "Standard", "High", "Critical"])
            db.add(
                WorkflowTask(
                    task_type=task_type,
                    title=f"{task_type} for {donor.donor_identifier}",
                    description=f"Donor eligibility workflow is in {workflow_state}.",
                    assigned_to_user_id=user.user_id,
                    assigned_role_id=role.role_id,
                    priority=priority,
                    status=random.choice(["Assigned", "In Progress", "Pending", "Blocked", "Escalated"]),
                    workflow_state=workflow_state,
                    queue_name=queue_name,
                    due_date=datetime.now(UTC) + timedelta(hours=random.randint(4, 72)),
                    related_record_id=str(donor.donor_pk),
                    related_record_type="Donor",
                    escalation_level=1 if priority == "Critical" else 0,
                )
            )
        db.flush()

    existing_notifications = len(db.execute(select(Notification.notification_id)).all())
    if existing_notifications < 500:
        tasks = db.execute(
            select(WorkflowTask)
            .where(WorkflowTask.status.in_(["Assigned", "In Progress", "Pending", "Blocked", "Escalated"]))
            .order_by(WorkflowTask.due_date)
            .limit(500 - existing_notifications)
        ).scalars().all()
        for task in tasks:
            role = db.get(Role, task.assigned_role_id) if task.assigned_role_id else None
            if not role:
                continue
            user = users_by_role.get(role.role_name)
            if not user:
                continue
            create_notification(
                db,
                user_id=user.user_id,
                title=f"[{task.priority}] {task.title}",
                message=f"{task.workflow_state} requires action in {task.queue_name}.",
                notification_type=random.choice(["Eligibility", "SLA", "QMS", "Recovery", "Release"]),
                priority=task.priority,
                workflow_task_id=task.task_id,
                related_record_type=task.related_record_type,
                related_record_id=task.related_record_id,
                action_route=route_path_for_record(task.related_record_type, task.related_record_id),
                workflow_context={
                    "task_id": task.task_id,
                    "workflow_state": task.workflow_state,
                    "queue_name": task.queue_name,
                    "route_path": route_path_for_record(task.related_record_type, task.related_record_id),
                },
            )

    audit_count = len(db.execute(select(AuditLog.audit_id)).all())
    if audit_count < 2000:
        needed = 2000 - audit_count
        users = list(users_by_role.values())
        for donor in random.choices(donors, k=min(needed, 2000)):
            log_audit(
                db,
                user_id=random.choice(users).user_id,
                action_type=random.choice(["ELIGIBILITY_RULE_EVALUATED", "DONOR_STATE_UPDATED", "QMS_RELEASE_CHECK", "SCREENING_MATRIX_REVIEWED"]),
                table_name="dim_donor",
                record_id=str(donor.donor_pk),
                entity_type="Donor",
                entity_id=str(donor.donor_pk),
                old_value=None,
                new_value={
                    "donor_identifier": donor.donor_identifier,
                    "workflow_state": donor.current_workflow_state,
                    "eligibility_status": donor.eligibility_status,
                    "final_disposition": donor.final_disposition,
                },
            )

    existing_timeline = db.execute(
        select(WorkflowTimelineEvent.timeline_event_id)
        .where(WorkflowTimelineEvent.related_record_type == "Donor")
        .limit(1)
    ).first()
    if not existing_timeline:
        for donor in random.sample(donors, k=min(350, len(donors))):
            events = [
                ("Referral Received", "Referral intake created"),
                ("Eligibility Matrix", f"Automated rule outcome: {donor.eligibility_status}"),
                ("Workflow State", f"Current state: {donor.current_workflow_state}"),
            ]
            for event_type, summary in events:
                db.add(
                    WorkflowTimelineEvent(
                        related_record_type="Donor",
                        related_record_id=str(donor.donor_pk),
                        event_type=event_type,
                        event_summary=summary,
                        event_detail={
                            "donor_identifier": donor.donor_identifier,
                            "final_disposition": donor.final_disposition,
                        },
                        created_by=random.choice(list(users_by_role.values())).user_id,
                        created_at=donor.created_at + timedelta(hours=random.randint(1, 48)),
                    )
                )
    db.flush()


def ensure_enterprise_data(db) -> None:
    roles = _ensure_roles(db)
    users_by_role = _ensure_users(db, roles)
    _ensure_security_foundations(db, users_by_role)
    ensure_ai_governance_data(db, users_by_role)
    ensure_workspace_definitions(db, roles)
    _ensure_donor_eligibility_data(db, roles, users_by_role)
    _protect_sensitive_demo_data(db, users_by_role)
    _ensure_supplier_portal_data(db, roles)
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


def seed_database(records: int, force: bool = False, seed: int | None = None) -> None:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)
        fake.seed_instance(seed)
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
                DataExportEvent,
                ExternalInvitation,
                ValidationEvidence,
                TrainingRecord,
                SignatureEvent,
                RealtimeEvent,
                BackgroundJob,
                SupplierRelationship,
                PasswordResetToken,
                DocumentAccess,
                DocumentVersion,
                SecureDocument,
                SecurityIncident,
                SecurityAudit,
                SystemHealth,
                MFAConfiguration,
                UserSessionRecord,
                AuthIdentity,
                SidebarState,
                UserPreference,
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
                EligibilityDecision,
                CAPA,
                Deviation,
                ProcessingRelease,
                RecoverySuitability,
                MedicalSocialHistory,
                InfectiousDiseaseResult,
                DonorScreening,
                Donor,
                EligibilityRule,
                InfectiousDiseaseTest,
                TissueType,
                Disposition,
                ReferralSource,
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
                UserApprovalStatus,
                AccountType,
                DeploymentEnvironment,
                Organization,
                Role,
            ]:
                db.execute(delete(model))
            db.commit()

        roles = _ensure_roles(db)
        users_by_role = _ensure_users(db, roles)
        _ensure_security_foundations(db, users_by_role)
        ensure_ai_governance_data(db, users_by_role)
        _ensure_supplier_portal_data(db, roles)
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
                weights=[
                    28,
                    24,
                    20,
                    18,
                    18,
                    16,
                    14,
                    12,
                    10,
                    8,
                    8,
                    8,
                    8,
                    10,
                    8,
                    10,
                    8,
                    8,
                    7,
                    12,
                    4,
                ],
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
    seed_parser.add_argument("--seed", type=int, default=None, help="Optional deterministic random seed")

    args = parser.parse_args()
    if args.command == "seed":
        seed_database(records=args.records, force=args.force, seed=args.seed)


if __name__ == "__main__":
    main()

