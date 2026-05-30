from __future__ import annotations

import csv
import hashlib
import json
import random
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from faker import Faker
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models import (
    CAPA,
    AuditLog,
    BackgroundJob,
    DataExportEvent,
    Deviation,
    DocumentVersion,
    Donor,
    DonorReview,
    DonorScreening,
    EligibilityDecision,
    EligibilityRule,
    InfectiousDiseaseResult,
    InfectiousDiseaseTest,
    MedicalSocialHistory,
    Notification,
    Organization,
    PartnerComplaint,
    PartnerDocument,
    PartnerMessage,
    PartnerSubmission,
    PartnerSubmissionStatus,
    PartnerTaskResponse,
    ProcessingRelease,
    RealtimeEvent,
    RecoverySuitability,
    ReferralSource,
    SecureDocument,
    SystemHealth,
    TissueType,
    TrainingRecord,
    User,
    Vendor,
    VendorIncident,
    WorkflowTask,
    WorkflowTimelineEvent,
    WorkflowTransitionEvent,
)
from app.services.data_scale_profiles import profile_as_dict, resolve_profile

SOURCE_SYSTEM = "clinical_donor_platform"
RUN_HISTORY_FILE = "generation_runs.json"
LATEST_VALIDATION_FILE = "latest_validation.json"
LATEST_EXPORT_FILE = "latest_export_manifest.json"
CONTINUOUS_STATE_FILE = "continuous_state.json"

EXPORT_MODELS: list[tuple[str, Any]] = [
    ("dim_organization", Organization),
    ("dim_user", User),
    ("dim_donor", Donor),
    ("fact_donor_review", DonorReview),
    ("fact_donor_screening", DonorScreening),
    ("fact_eligibility_decision", EligibilityDecision),
    ("fact_infectious_disease_result", InfectiousDiseaseResult),
    ("fact_medical_social_history", MedicalSocialHistory),
    ("fact_recovery_suitability", RecoverySuitability),
    ("fact_processing_release", ProcessingRelease),
    ("fact_deviation", Deviation),
    ("fact_capa", CAPA),
    ("dim_partner_submission", PartnerSubmission),
    ("fact_partner_submission_status", PartnerSubmissionStatus),
    ("fact_partner_message", PartnerMessage),
    ("fact_partner_complaint", PartnerComplaint),
    ("dim_partner_document", PartnerDocument),
    ("fact_partner_task_response", PartnerTaskResponse),
    ("dim_secure_document", SecureDocument),
    ("dim_document_version", DocumentVersion),
    ("fact_workflow_task", WorkflowTask),
    ("fact_notification", Notification),
    ("fact_vendor_incident", VendorIncident),
    ("fact_audit_log", AuditLog),
    ("fact_realtime_event", RealtimeEvent),
    ("fact_background_job", BackgroundJob),
    ("dim_training_record", TrainingRecord),
]

FRESHNESS_MODELS: list[tuple[str, Any, str]] = [
    ("donor_reviews", DonorReview, "updated_at"),
    ("donors", Donor, "updated_at"),
    ("partner_submissions", PartnerSubmission, "submitted_at"),
    ("partner_status_events", PartnerSubmissionStatus, "changed_at"),
    ("workflow_tasks", WorkflowTask, "created_at"),
    ("audit_events", AuditLog, "timestamp"),
    ("vendor_incidents", VendorIncident, "opened_at"),
    ("system_health", SystemHealth, "checked_at"),
]

DONOR_STATES = [
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
    "Quarantine",
    "Rejected",
]

PARTNER_STATUS_STEPS = [
    ("Submitted", "Pending Intake Validation"),
    ("In Review", "Clinical Review In Progress"),
    ("Additional Information Requested", "Pending Additional Information"),
    ("Quality Review", "QA Investigation"),
    ("Complete", "Closed"),
]

RISK_FACTORS = [
    "recent travel exposure",
    "incomplete authorization packet",
    "time-of-death window review",
    "reported fever within screening window",
    "conflicting social-history disclosure",
    "chain-of-custody document mismatch",
    "NAT result pending",
    "QA release hold",
]

CONFORMED_SITES = [
    {
        "site_id": "SITE-ALACHUA",
        "site_code": "ALACHUA",
        "site_name": "Alachua Regenerative Medicine Campus",
        "region": "North America",
        "country": "United States",
    },
    {
        "site_id": "SITE-WLAF",
        "site_code": "WLAF",
        "site_name": "West Lafayette Biologics Facility",
        "region": "North America",
        "country": "United States",
    },
    {
        "site_id": "SITE-EP",
        "site_code": "EP",
        "site_name": "Eden Prairie Distribution and QA",
        "region": "North America",
        "country": "United States",
    },
    {
        "site_id": "SITE-GLENCOE",
        "site_code": "GLENCOE",
        "site_name": "Glencoe Processing Annex",
        "region": "North America",
        "country": "United States",
    },
    {
        "site_id": "SITE-NEUNK",
        "site_code": "NEUNK",
        "site_name": "Neunkirchen Precision Manufacturing",
        "region": "EMEA",
        "country": "Germany",
    },
    {
        "site_id": "SITE-GLASGOW",
        "site_code": "GLASGOW",
        "site_name": "Glasgow Advanced Materials Site",
        "region": "EMEA",
        "country": "United Kingdom",
    },
    {
        "site_id": "SITE-MARTON",
        "site_code": "MARTON",
        "site_name": "Marton Tissue Processing Site",
        "region": "APAC",
        "country": "New Zealand",
    },
]

CLINICAL_PRODUCT_ALIGNMENT = {
    "bone": {"product_family": "Allograft", "erp_material_family": "Allograft"},
    "cornea": {"product_family": "Ocular Tissue", "erp_material_family": "Allograft"},
    "dermal matrix": {"product_family": "Dermal Matrix", "erp_material_family": "Allograft"},
    "heart valve": {"product_family": "Cardiovascular Tissue", "erp_material_family": "Allograft"},
    "organ": {"product_family": "Clinical Organ Referral", "erp_material_family": "Not ERP-managed"},
    "skin": {"product_family": "Dermal Tissue", "erp_material_family": "Allograft"},
    "tendon": {"product_family": "Musculoskeletal Tissue", "erp_material_family": "Allograft"},
}

EXPORT_METADATA_FIELDS = [
    "source_system",
    "source_table",
    "source_record_id",
    "source_created_at",
    "source_updated_at",
    "ingestion_batch_id",
    "extraction_batch_id",
    "generated_at",
    "extracted_at",
]


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat()


def metadata_root() -> Path:
    root = Path(settings.data_producer_metadata_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def export_root() -> Path:
    root = Path(settings.data_producer_export_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def stop_file_path() -> Path:
    return Path(settings.data_producer_stop_file)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _append_run(record: dict[str, Any]) -> dict[str, Any]:
    root = metadata_root()
    history_path = root / RUN_HISTORY_FILE
    history = _read_json(history_path, [])
    history.append(record)
    history = history[-500:]
    _write_json(history_path, history)
    _write_json(root / "latest_run.json", record)
    return record


def _new_batch_id(prefix: str) -> str:
    return f"{prefix}_{utc_now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"


def _record_run(
    *,
    run_type: str,
    status: str,
    started_at: datetime,
    row_counts: dict[str, int] | None = None,
    extraction_batch_id: str | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finished_at = utc_now()
    return _append_run(
        {
            "run_id": f"{run_type}_{finished_at.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
            "run_type": run_type,
            "status": status,
            "source_system": SOURCE_SYSTEM,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 2),
            "generated_at": finished_at.isoformat(),
            "extraction_batch_id": extraction_batch_id,
            "row_counts": row_counts or {},
            "warnings": warnings or [],
            "errors": errors or [],
            "details": details or {},
        }
    )


def generation_runs(limit: int = 50) -> list[dict[str, Any]]:
    history = _read_json(metadata_root() / RUN_HISTORY_FILE, [])
    return list(reversed(history[-limit:]))


def latest_validation_result() -> dict[str, Any]:
    return _read_json(metadata_root() / LATEST_VALIDATION_FILE, {})


def latest_export_manifest() -> dict[str, Any]:
    return _read_json(metadata_root() / LATEST_EXPORT_FILE, {})


def continuous_state() -> dict[str, Any]:
    return _read_json(metadata_root() / CONTINUOUS_STATE_FILE, {"running": False})


def row_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name, model in EXPORT_MODELS:
        counts[table_name] = int(db.execute(select(func.count()).select_from(model)).scalar() or 0)
    return counts


def source_freshness(db: Session) -> dict[str, Any]:
    rows = []
    for label, model, column_name in FRESHNESS_MODELS:
        column = getattr(model, column_name)
        value = db.execute(select(func.max(column))).scalar()
        rows.append(
            {
                "entity": label,
                "watermark_column": column_name,
                "latest_watermark": value.isoformat() if isinstance(value, datetime) else value,
            }
        )
    latest = max((row["latest_watermark"] for row in rows if row["latest_watermark"]), default=None)
    return {
        "source_system": SOURCE_SYSTEM,
        "generated_at": iso_now(),
        "latest_source_watermark": latest,
        "freshness": rows,
    }


def _choose(rng: random.Random, values: list[Any]) -> Any:
    if not values:
        raise ValueError("Cannot choose from an empty seed-data collection.")
    return values[rng.randrange(len(values))]


def _users_by_role(users: list[User]) -> dict[str, list[User]]:
    result: dict[str, list[User]] = {}
    for user in users:
        result.setdefault(user.role, []).append(user)
    return result


def _reviewer(users_by_role: dict[str, list[User]], rng: random.Random) -> User:
    for role in ["Clinical Reviewer", "Quality Assurance Specialist", "Operations Manager", "Donor Intake Coordinator"]:
        if users_by_role.get(role):
            return _choose(rng, users_by_role[role])
    return _choose(rng, [user for rows in users_by_role.values() for user in rows])


def _risk_profile(rng: random.Random) -> tuple[int, str, list[str], str, str]:
    flags = rng.sample(RISK_FACTORS, k=rng.randint(0, 3))
    score = min(100, rng.randint(4, 38) + len(flags) * rng.randint(8, 18))
    if score >= 75:
        return score, "Critical", flags, "Reject or Escalate", "Critical"
    if score >= 50:
        return score, "High", flags, "Defer Pending Clinical Review", "High"
    if score >= 25:
        return score, "Moderate", flags, "Manual Clinical Review", "Standard"
    return score, "Low", flags, "Approve", "Routine"


def _site_context_for_org(organization: Organization | None) -> dict[str, str]:
    if not organization:
        return CONFORMED_SITES[0]
    return CONFORMED_SITES[(organization.organization_id - 1) % len(CONFORMED_SITES)]


def _product_context(product_or_tissue: str | None) -> dict[str, str]:
    key = str(product_or_tissue or "").strip().lower()
    context = CLINICAL_PRODUCT_ALIGNMENT.get(
        key,
        {"product_family": product_or_tissue or "Unknown", "erp_material_family": "Unmapped"},
    )
    return {"product_or_tissue": product_or_tissue or "Unknown", **context}


def _create_donor_case(
    db: Session,
    *,
    rng: random.Random,
    fake: Faker,
    users: list[User],
    users_by_role: dict[str, list[User]],
    organizations: list[Organization],
    referral_sources: list[ReferralSource],
    tissue_types: list[TissueType],
    infectious_tests: list[InfectiousDiseaseTest],
    eligibility_rules: list[EligibilityRule],
    extraction_batch_id: str,
) -> dict[str, Any]:
    now = utc_now()
    created_at = now - timedelta(minutes=rng.randint(1, 240))
    reviewer = _reviewer(users_by_role, rng)
    organization = _choose(rng, organizations)
    referral_source = _choose(rng, referral_sources)
    tissue_type = _choose(rng, tissue_types)
    site_context = _site_context_for_org(organization)
    product_context = _product_context(tissue_type.tissue_name)
    risk_score, risk_level, flags, recommended_action, priority = _risk_profile(rng)
    donor_identifier = f"DON-{now.strftime('%y%m%d')}-{rng.randint(100000, 999999)}"
    donor_name = fake.name()
    state = _choose(rng, DONOR_STATES)
    eligibility_status = "Pending" if state not in {"Rejected", "Quarantine"} else state

    review = DonorReview(
        donor_id=donor_identifier,
        donor_name=donor_name,
        age=rng.randint(18, 78),
        blood_type=_choose(rng, ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Unknown"]),
        infectious_history="NAT result pending" in flags,
        travel_risk="recent travel exposure" in flags,
        missing_required_fields="incomplete authorization packet" in flags,
        risk_flags=flags,
        risk_score=risk_score,
        risk_level=risk_level,
        recommended_action=recommended_action,
        review_priority=priority,
        intake_status=state,
        reviewer_id=reviewer.user_id,
        clinical_notes=f"Generated intake packet: {', '.join(flags) if flags else 'routine referral'}",
        attachment_placeholder=f"clinical://attachments/{donor_identifier}/intake.pdf",
        created_at=created_at,
        updated_at=now,
        reviewed_at=None if state.startswith("Pending") else now,
        organization_id=organization.organization_id,
    )
    db.add(review)
    db.flush()

    donor = Donor(
        donor_identifier=donor_identifier,
        donor_review_id=review.review_id,
        donor_name=donor_name,
        age=review.age,
        blood_type=review.blood_type,
        sex=_choose(rng, ["Female", "Male", "Unknown"]),
        referral_source_id=referral_source.source_id,
        time_of_death=created_at - timedelta(hours=rng.randint(2, 30)),
        source_organization=referral_source.source_name,
        donor_history={
            "risk_factors": flags,
            "source": "continuous_data_producer",
            "source_system": SOURCE_SYSTEM,
            "extraction_batch_id": extraction_batch_id,
            "site_context": site_context,
            "product_context": product_context,
        },
        current_workflow_state=state,
        eligibility_status=eligibility_status,
        final_disposition=None if state not in {"Rejected", "Quarantine"} else state,
        created_at=created_at,
        updated_at=now,
        organization_id=organization.organization_id,
    )
    db.add(donor)
    db.flush()

    screening = DonorScreening(
        donor_pk=donor.donor_pk,
        referral_id=f"REF-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}",
        administrative_outcome=_choose(rng, ["Pending", "Complete", "Hold"]),
        medical_social_outcome=_choose(rng, ["Pending", "Acceptable", "Review Required"]),
        infectious_disease_outcome=_choose(rng, ["Pending", "Negative", "Review Required"]),
        tissue_suitability_outcome=_choose(rng, ["Pending", "Suitable", "Hold"]),
        recovery_suitability_outcome=_choose(rng, ["Pending", "Suitable", "Recovery Hold"]),
        qa_outcome=_choose(rng, ["Pending", "QA Review Required", "Released"]),
        automated_rule_outcome=recommended_action,
        current_decision=eligibility_status,
        created_at=created_at,
        updated_at=now,
    )
    db.add(screening)

    db.add(
        MedicalSocialHistory(
            donor_pk=donor.donor_pk,
            cancer_history=rng.random() < 0.08,
            neurological_disease=rng.random() < 0.05,
            autoimmune_disease=rng.random() < 0.06,
            transmissible_disease_history=rng.random() < 0.08,
            iv_drug_use=rng.random() < 0.05,
            incarceration_history=rng.random() < 0.04,
            travel_exposure=review.travel_risk,
            high_risk_behavior=rng.random() < 0.08,
            unknown_history=rng.random() < 0.06,
            outcome="Review Required" if risk_score >= 50 else "Acceptable",
            review_notes=f"Screening generated by {SOURCE_SYSTEM}; priority {priority}.",
            created_at=created_at + timedelta(minutes=20),
        )
    )

    for test in rng.sample(infectious_tests, k=min(len(infectious_tests), rng.randint(2, 4))):
        positive = rng.random() < (0.02 if test.rejection_if_positive else 0.05)
        db.add(
            InfectiousDiseaseResult(
                donor_pk=donor.donor_pk,
                test_id=test.test_id,
                result_value="Positive" if positive else "Negative",
                specimen_collected_at=created_at + timedelta(hours=rng.randint(1, 8)),
                specimen_window_valid=rng.random() > 0.04,
                reviewed_by=reviewer.user_id,
                review_status="Review Required" if positive else "Complete",
                created_at=created_at + timedelta(hours=rng.randint(2, 18)),
            )
        )

    db.add(
        RecoverySuitability(
            donor_pk=donor.donor_pk,
            tissue_type_id=tissue_type.tissue_type_id,
            refrigeration_timing_hours=round(rng.uniform(1.0, 18.0), 1),
            body_cooling_status=_choose(rng, ["Documented", "Pending Documentation", "Unknown"]),
            trauma_contamination=rng.random() < 0.08,
            blood_draw_timing_hours=round(rng.uniform(1.0, 12.0), 1),
            hospital_release_status=_choose(rng, ["Pending", "Released", "Hold"]),
            recovery_environment=_choose(rng, ["Hospital", "Medical Examiner", "Recovery Center"]),
            recovery_window_hours=round(rng.uniform(6.0, 36.0), 1),
            outcome="Suitable" if risk_score < 50 else "Review Required",
            reviewed_at=now,
        )
    )

    if eligibility_rules:
        rule = _choose(rng, eligibility_rules)
        db.add(
            EligibilityDecision(
                donor_pk=donor.donor_pk,
                rule_id=rule.rule_id,
                decision_stage=rule.rule_category,
                outcome=recommended_action,
                severity=risk_level,
                reason=f"Continuous producer evaluated {rule.rule_name}.",
                requires_review=risk_score >= 50,
                required_role=rule.required_role,
                triggered_rules=[{"rule_name": rule.rule_name, "severity": rule.severity}],
                final_disposition=donor.final_disposition,
                created_by=reviewer.user_id,
                created_at=now,
            )
        )

    if risk_score < 70 and rng.random() < 0.45:
        db.add(
            ProcessingRelease(
                release_identifier=f"REL-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}",
                donor_pk=donor.donor_pk,
                tissue_type_id=tissue_type.tissue_type_id,
                sterility_testing=_choose(rng, ["Pending", "Passed", "Review Required"]),
                bioburden_status=_choose(rng, ["Pending", "Passed", "Hold"]),
                environmental_monitoring=_choose(rng, ["Pending", "Clear", "Review Required"]),
                packaging_qc=_choose(rng, ["Pending", "Passed", "Hold"]),
                labeling_verification=_choose(rng, ["Pending", "Verified", "Correction Required"]),
                traceability_verification=_choose(rng, ["Pending", "Verified", "Review Required"]),
                chain_of_custody_verified=rng.random() > 0.12,
                release_status=_choose(rng, ["Pending QA Review", "Release Hold", "Released"]),
                final_disposition=None,
                created_at=now,
                organization_id=organization.organization_id,
            )
        )

    task = WorkflowTask(
        task_type="Clinical Donor Review",
        title=f"Review donor {donor_identifier}",
        description=f"{priority} review for generated donor referral.",
        assigned_to_user_id=reviewer.user_id,
        assigned_role_id=reviewer.role_id,
        priority=priority,
        status="Pending",
        workflow_state=state,
        queue_name="Clinical Review Queue" if risk_score >= 25 else "Donor Intake Queue",
        due_date=now + timedelta(hours=8 if priority in {"Critical", "High"} else 24),
        created_at=now,
        related_record_id=str(donor.donor_pk),
        related_record_type="Donor",
        escalation_level=1 if priority in {"Critical", "High"} else 0,
        organization_id=organization.organization_id,
    )
    db.add(task)
    db.flush()

    db.add(
        Notification(
            user_id=reviewer.user_id,
            title=f"{priority} donor review generated",
            message=f"Continuous producer created {donor_identifier} with {risk_level} risk.",
            notification_type="Data Producer",
            priority=priority,
            workflow_task_id=task.task_id,
            related_record_type="Donor",
            related_record_id=str(donor.donor_pk),
            action_route=f"/donor/{donor.donor_pk}",
            workflow_context={"workflow_state": state, "queue_name": task.queue_name},
            organization_id=organization.organization_id,
        )
    )
    db.add(
        WorkflowTimelineEvent(
            related_record_type="Donor",
            related_record_id=str(donor.donor_pk),
            event_type="DONOR_REFERRAL_GENERATED",
            event_summary=f"Generated donor referral {donor_identifier}",
            event_detail={
                "risk_score": risk_score,
                "risk_flags": flags,
                "extraction_batch_id": extraction_batch_id,
                "site_context": site_context,
                "product_context": product_context,
            },
            created_by=reviewer.user_id,
            created_at=now,
        )
    )
    db.add(
        WorkflowTransitionEvent(
            record_id=str(donor.donor_pk),
            record_type="Donor",
            from_state="None",
            to_state=state,
            action_taken="continuous_generation",
            performed_by=reviewer.user_id,
            timestamp=now,
            notes="Synthetic clinical workflow event.",
            decision_context={"source_system": SOURCE_SYSTEM, "extraction_batch_id": extraction_batch_id},
        )
    )
    db.add(
        AuditLog(
            user_id=reviewer.user_id,
            action_type="CONTINUOUS_DONOR_GENERATED",
            table_name="dim_donor",
            record_id=str(donor.donor_pk),
            entity_type="Donor",
            entity_id=str(donor.donor_pk),
            new_value={"donor_identifier": donor_identifier, "risk_level": risk_level},
            ip_address="127.0.0.1",
            timestamp=now,
        )
    )
    return {
        "donor_pk": donor.donor_pk,
        "task_id": task.task_id,
        "risk_level": risk_level,
        "site_id": site_context["site_id"],
        "product_family": product_context["product_family"],
    }


def _create_partner_activity(
    db: Session,
    *,
    rng: random.Random,
    fake: Faker,
    users: list[User],
    partner_orgs: list[Organization],
    extraction_batch_id: str,
) -> dict[str, Any] | None:
    if not partner_orgs:
        return None
    now = utc_now()
    org = _choose(rng, partner_orgs)
    site_context = _site_context_for_org(org)
    partner_users = [user for user in users if user.organization_id == org.organization_id and user.is_external]
    submitter = _choose(rng, partner_users) if partner_users else None
    status, internal_state = _choose(rng, PARTNER_STATUS_STEPS)
    submission_code = f"SUB-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}"
    product_or_tissue = _choose(rng, ["Cornea", "Skin", "Bone", "Dermal Matrix", "Heart Valve"])
    product_context = _product_context(product_or_tissue)
    submission = PartnerSubmission(
        submission_code=submission_code,
        organization_id=org.organization_id,
        submitted_by_user_id=submitter.user_id if submitter else None,
        submission_type=_choose(rng, ["Donor Referral", "Document Packet", "Recovery Update", "Quality Response"]),
        title=f"{org.organization_name} portal submission {submission_code}",
        partner_visible_status=status,
        internal_state=internal_state,
        priority=_choose(rng, ["Standard", "High", "Critical"]),
        description=fake.sentence(nb_words=14),
        product_or_tissue=product_or_tissue,
        batch_or_reference=f"REF-{rng.randint(100000, 999999)}",
        estimated_completion_at=now + timedelta(hours=rng.randint(12, 96)),
        submitted_at=now,
        details={
            "source_system": SOURCE_SYSTEM,
            "extraction_batch_id": extraction_batch_id,
            "site_context": site_context,
            "product_context": product_context,
        },
    )
    db.add(submission)
    db.flush()

    db.add(
        PartnerSubmissionStatus(
            submission_id=submission.submission_id,
            from_status=None,
            to_status=status,
            internal_state=internal_state,
            changed_by_user_id=submitter.user_id if submitter else None,
            changed_at=now,
            note="Synthetic partner portal status event.",
            partner_visible=True,
        )
    )
    document = SecureDocument(
        record_type="PartnerSubmission",
        record_id=str(submission.submission_id),
        document_name=f"{submission_code}_supporting_packet.pdf",
        document_type="Partner Submission Evidence",
        storage_uri_encrypted=f"encrypted://partner/{org.organization_id}/{submission_code}.pdf",
        checksum_sha256=hashlib.sha256(submission_code.encode("utf-8")).hexdigest(),
        uploaded_by=submitter.user_id if submitter else None,
        access_classification="Partner Protected",
        created_at=now,
        organization_id=org.organization_id,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=document.document_id,
            version_number=1,
            document_status="Submitted",
            uploaded_by=submitter.user_id if submitter else None,
            storage_uri_encrypted=document.storage_uri_encrypted,
            checksum_sha256=document.checksum_sha256,
            approval_status=_choose(rng, ["Pending Review", "Approved", "Correction Requested"]),
            created_at=now,
            extra_metadata={
                "source_system": SOURCE_SYSTEM,
                "extraction_batch_id": extraction_batch_id,
                "site_context": site_context,
                "product_context": product_context,
            },
        )
    )
    db.add(
        PartnerDocument(
            organization_id=org.organization_id,
            document_id=document.document_id,
            submission_id=submission.submission_id,
            document_category="Submission Evidence",
            request_status="Submitted",
            partner_visible=True,
            created_at=now,
        )
    )
    db.add(
        PartnerMessage(
            organization_id=org.organization_id,
            submission_id=submission.submission_id,
            sender_user_id=submitter.user_id if submitter else None,
            audience="Internal",
            subject=f"New partner submission {submission_code}",
            body="Synthetic OPO-like partner activity was generated for review.",
            created_at=now,
            is_read=False,
        )
    )
    db.add(
        RealtimeEvent(
            event_type="PARTNER_SUBMISSION_CREATED",
            channel="partner-portal",
            audience_user_id=submitter.user_id if submitter else None,
            organization_id=org.organization_id,
            record_type="PartnerSubmission",
            record_id=str(submission.submission_id),
            payload={
                "submission_code": submission_code,
                "status": status,
                "site_id": site_context["site_id"],
                "product_family": product_context["product_family"],
            },
            created_at=now,
        )
    )
    return {
        "submission_id": submission.submission_id,
        "document_id": document.document_id,
        "site_id": site_context["site_id"],
        "product_family": product_context["product_family"],
    }


def _create_qms_and_vendor_activity(
    db: Session,
    *,
    rng: random.Random,
    users: list[User],
    donors: list[Donor],
    vendors: list[Vendor],
    partner_orgs: list[Organization],
    extraction_batch_id: str,
) -> dict[str, Any]:
    now = utc_now()
    result: dict[str, Any] = {}
    donor = _choose(rng, donors) if donors else None
    owner = _choose(rng, users)
    if donor and rng.random() < 0.7:
        deviation = Deviation(
            deviation_code=f"DEV-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}",
            donor_pk=donor.donor_pk,
            deviation_category=_choose(rng, ["Documentation", "Chain of Custody", "Lab Interface", "Processing Hold"]),
            severity=_choose(rng, ["Low", "Medium", "High", "Critical"]),
            description="Continuous producer generated a regulated QMS deviation for portfolio review.",
            status=_choose(rng, ["Open", "Investigation", "CAPA Required"]),
            opened_at=now,
            organization_id=donor.organization_id,
        )
        db.add(deviation)
        db.flush()
        result["deviation_id"] = deviation.deviation_id
        if rng.random() < 0.65:
            capa = CAPA(
                capa_code=f"CAPA-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}",
                donor_pk=donor.donor_pk,
                deviation_id=deviation.deviation_id,
                root_cause=_choose(rng, ["Procedure gap", "Training gap", "Vendor data delay", "Document mismatch"]),
                corrective_action_owner=owner.full_name,
                status=_choose(rng, ["Open", "Containment", "Effectiveness Check"]),
                due_date=now + timedelta(days=rng.randint(7, 45)),
                created_at=now,
                organization_id=donor.organization_id,
            )
            db.add(capa)
            result["capa_code"] = capa.capa_code
    if vendors:
        vendor = _choose(rng, vendors)
        opened_at = now - timedelta(hours=rng.randint(1, 72))
        severity = _choose(rng, ["Low", "Medium", "High", "Critical"])
        sla_breached = severity == "Critical" or (now - opened_at).total_seconds() / 3600 > 48
        incident = VendorIncident(
            vendor_id=vendor.vendor_id,
            ticket_number=f"VND-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}",
            title=_choose(
                rng,
                [
                    "Lab result feed latency above threshold",
                    "Document portal response delay",
                    "Partner notification webhook retry backlog",
                    "Vendor support response outside SLA",
                ],
            ),
            severity=severity,
            status="Open" if rng.random() < 0.55 else "Resolved",
            uptime_percent=round(rng.uniform(97.5, 99.99), 2),
            sla_breached=sla_breached,
            opened_at=opened_at,
            resolved_at=None if sla_breached else now,
            ticket_age_hours=round((now - opened_at).total_seconds() / 3600, 1),
            resolution_minutes=None if sla_breached else int((now - opened_at).total_seconds() / 60),
            impact_summary="Synthetic vendor SLA event generated for monitoring and escalation review.",
        )
        db.add(incident)
        result["vendor_ticket"] = incident.ticket_number
    if partner_orgs and rng.random() < 0.35:
        org = _choose(rng, partner_orgs)
        site_context = _site_context_for_org(org)
        product_context = _product_context("Dermal Matrix")
        complaint = PartnerComplaint(
            complaint_code=f"CMP-{now.strftime('%y%m%d')}-{rng.randint(10000, 99999)}",
            organization_id=org.organization_id,
            product_or_batch=f"BATCH-{rng.randint(100000, 999999)}",
            issue_category=_choose(rng, ["Document Quality", "Packaging", "Communication", "Turnaround Time"]),
            severity=_choose(rng, ["Low", "Medium", "High"]),
            description="Synthetic partner quality complaint generated from continuous activity.",
            impact_assessment="Pending QA triage.",
            contact_email=org.contact_email,
            partner_visible_status="Submitted",
            internal_state="Pending QA Review",
            submitted_at=now,
            details={
                "source_system": SOURCE_SYSTEM,
                "extraction_batch_id": extraction_batch_id,
                "site_context": site_context,
                "product_context": product_context,
            },
        )
        db.add(complaint)
        result["complaint_code"] = complaint.complaint_code
        result["complaint_site_id"] = site_context["site_id"]
    db.add(
        AuditLog(
            user_id=owner.user_id,
            action_type="CONTINUOUS_QMS_VENDOR_ACTIVITY",
            table_name="producer_batch",
            record_id=extraction_batch_id,
            entity_type="DataProducerBatch",
            entity_id=extraction_batch_id,
            new_value=result,
            ip_address="127.0.0.1",
            timestamp=now,
        )
    )
    return result


def _mutate_existing_work(db: Session, *, rng: random.Random, users: list[User], extraction_batch_id: str) -> dict[str, int]:
    now = utc_now()
    changes = {"tasks_updated": 0, "documents_updated": 0, "training_updated": 0, "donors_updated": 0}
    open_tasks = list(
        db.execute(
            select(WorkflowTask)
            .where(WorkflowTask.status.in_(["Pending", "Assigned", "In Progress", "Blocked", "Escalated"]))
            .order_by(WorkflowTask.created_at)
            .limit(40)
        ).scalars().all()
    )
    for task in rng.sample(open_tasks, k=min(len(open_tasks), rng.randint(0, 5))):
        task.status = _choose(rng, ["In Progress", "Completed", "Blocked", "Escalated"])
        task.completed_at = now if task.status == "Completed" else None
        task.escalation_level = max(task.escalation_level, 1) if task.status == "Escalated" else task.escalation_level
        changes["tasks_updated"] += 1
        if task.organization_id and rng.random() < 0.25:
            db.add(
                PartnerTaskResponse(
                    task_id=task.task_id,
                    organization_id=task.organization_id,
                    responded_by_user_id=task.assigned_to_user_id,
                    response_status="Submitted",
                    response_note="Synthetic partner task response generated by data producer.",
                    submitted_at=now,
                )
            )

    documents = list(
        db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.approval_status.in_(["Pending Review", "Submitted"]))
            .order_by(DocumentVersion.created_at)
            .limit(30)
        ).scalars().all()
    )
    for document in rng.sample(documents, k=min(len(documents), rng.randint(0, 4))):
        approver = _choose(rng, users)
        document.approval_status = _choose(rng, ["Approved", "Correction Requested", "Rejected"])
        document.approved_by = approver.user_id if document.approval_status == "Approved" else None
        document.approved_at = now if document.approval_status == "Approved" else None
        changes["documents_updated"] += 1

    training_records = list(
        db.execute(
            select(TrainingRecord)
            .where(TrainingRecord.status.in_(["Assigned", "In Progress", "Pending Validation"]))
            .order_by(TrainingRecord.assigned_at)
            .limit(30)
        ).scalars().all()
    )
    for record in rng.sample(training_records, k=min(len(training_records), rng.randint(0, 3))):
        record.status = _choose(rng, ["Completed", "Expired", "Pending Validation"])
        record.completed_at = now if record.status == "Completed" else record.completed_at
        record.expires_at = now - timedelta(days=1) if record.status == "Expired" else now + timedelta(days=365)
        record.competency_status = "Validated" if record.status == "Completed" else "Pending Validation"
        changes["training_updated"] += 1

    donors = list(
        db.execute(
            select(Donor)
            .where(Donor.current_workflow_state.not_in(["Released for Clinical Use", "Rejected", "Destroyed"]))
            .order_by(Donor.updated_at)
            .limit(40)
        ).scalars().all()
    )
    for donor in rng.sample(donors, k=min(len(donors), rng.randint(0, 5))):
        old_state = donor.current_workflow_state
        donor.current_workflow_state = _choose(rng, DONOR_STATES)
        donor.eligibility_status = "Eligible" if donor.current_workflow_state == "Recovery Authorized" else donor.eligibility_status
        donor.final_disposition = donor.current_workflow_state if donor.current_workflow_state in {"Rejected", "Quarantine"} else donor.final_disposition
        donor.updated_at = now
        changes["donors_updated"] += 1
        db.add(
            WorkflowTransitionEvent(
                record_id=str(donor.donor_pk),
                record_type="Donor",
                from_state=old_state,
                to_state=donor.current_workflow_state,
                action_taken="continuous_status_mutation",
                performed_by=_choose(rng, users).user_id,
                timestamp=now,
                notes="Synthetic donor workflow status change.",
                decision_context={"source_system": SOURCE_SYSTEM, "extraction_batch_id": extraction_batch_id},
            )
        )
    return changes


def run_seed_generation(
    records: int | None = 1200,
    seed: int | None = None,
    force: bool = False,
    profile: str = "demo",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    started = utc_now()
    extraction_batch_id = _new_batch_id("clinical_seed")
    resolved = resolve_profile(profile, records_override=records, start_date_override=start_date, end_date_override=end_date)
    try:
        from app import cli as seed_cli

        seed_cli.seed_database(
            records=resolved.records,
            force=force,
            seed=seed,
            start_date=resolved.start_date.isoformat(),
            end_date=resolved.end_date.isoformat(),
        )
        with SessionLocal() as db:
            counts = row_counts(db)
        return _record_run(
            run_type="seed",
            status="succeeded",
            started_at=started,
            row_counts=counts,
            extraction_batch_id=extraction_batch_id,
            details={
                "records_requested": resolved.records,
                "seed": seed,
                "force": force,
                "profile": profile_as_dict(resolved),
            },
        )
    except Exception as exc:
        return _record_run(
            run_type="seed",
            status="failed",
            started_at=started,
            extraction_batch_id=extraction_batch_id,
            errors=[str(exc)],
            details={"records_requested": resolved.records, "seed": seed, "force": force, "profile": profile_as_dict(resolved)},
        )


def run_incremental_generation(
    db: Session,
    *,
    seed: int | None = None,
    scale: int = 1,
    extraction_batch_id: str | None = None,
) -> dict[str, Any]:
    started = utc_now()
    extraction_batch_id = extraction_batch_id or _new_batch_id("clinical_incremental")
    scale = max(1, min(scale, 25))
    rng = random.Random(seed if seed is not None else int(started.timestamp()))
    fake = Faker()
    if seed is not None:
        Faker.seed(seed)
        fake.seed_instance(seed)
    try:
        users = list(db.execute(select(User).where(User.is_active.is_(True))).scalars().all())
        organizations = list(db.execute(select(Organization).where(Organization.is_active.is_(True))).scalars().all())
        partner_orgs = [
            org
            for org in organizations
            if str(org.organization_type).lower() in {"partner", "supplier", "recovery organization", "opo"}
        ]
        referral_sources = list(db.execute(select(ReferralSource).where(ReferralSource.is_active.is_(True))).scalars().all())
        tissue_types = list(db.execute(select(TissueType).where(TissueType.is_active.is_(True))).scalars().all())
        infectious_tests = list(db.execute(select(InfectiousDiseaseTest).where(InfectiousDiseaseTest.is_active.is_(True))).scalars().all())
        eligibility_rules = list(db.execute(select(EligibilityRule).where(EligibilityRule.is_active.is_(True))).scalars().all())
        vendors = list(db.execute(select(Vendor).where(Vendor.status == "Active")).scalars().all())
        donors = list(db.execute(select(Donor).order_by(Donor.created_at.desc()).limit(200)).scalars().all())
        users_by_role = _users_by_role(users)
        if not all([users, organizations, referral_sources, tissue_types, infectious_tests]):
            raise ValueError("Seed data is required before incremental generation. Run seed generation first.")

        details: dict[str, Any] = {"created_donors": [], "partner_activity": [], "qms_vendor_activity": [], "mutations": []}
        for _ in range(scale):
            details["created_donors"].append(
                _create_donor_case(
                    db,
                    rng=rng,
                    fake=fake,
                    users=users,
                    users_by_role=users_by_role,
                    organizations=organizations,
                    referral_sources=referral_sources,
                    tissue_types=tissue_types,
                    infectious_tests=infectious_tests,
                    eligibility_rules=eligibility_rules,
                    extraction_batch_id=extraction_batch_id,
                )
            )
            partner_activity = _create_partner_activity(
                db,
                rng=rng,
                fake=fake,
                users=users,
                partner_orgs=partner_orgs,
                extraction_batch_id=extraction_batch_id,
            )
            if partner_activity:
                details["partner_activity"].append(partner_activity)
            current_donors = donors + list(db.execute(select(Donor).order_by(Donor.created_at.desc()).limit(scale + 5)).scalars().all())
            details["qms_vendor_activity"].append(
                _create_qms_and_vendor_activity(
                    db,
                    rng=rng,
                    users=users,
                    donors=current_donors,
                    vendors=vendors,
                    partner_orgs=partner_orgs,
                    extraction_batch_id=extraction_batch_id,
                )
            )
            details["mutations"].append(_mutate_existing_work(db, rng=rng, users=users, extraction_batch_id=extraction_batch_id))

        db.add(
            SystemHealth(
                component_name="Clinical Data Producer",
                status="Healthy",
                latency_ms=None,
                checked_at=utc_now(),
                details={"scale": scale, "extraction_batch_id": extraction_batch_id},
            )
        )
        db.add(
            BackgroundJob(
                job_type="continuous_data_producer",
                status="Completed",
                priority="Normal",
                scheduled_for=started,
                attempts=1,
                max_attempts=1,
                payload={"scale": scale, "source_system": SOURCE_SYSTEM},
                created_at=started,
                started_at=started,
                completed_at=utc_now(),
            )
        )
        db.commit()
        counts = row_counts(db)
        return _record_run(
            run_type="incremental",
            status="succeeded",
            started_at=started,
            row_counts=counts,
            extraction_batch_id=extraction_batch_id,
            details=details,
        )
    except Exception as exc:
        db.rollback()
        return _record_run(
            run_type="incremental",
            status="failed",
            started_at=started,
            extraction_batch_id=extraction_batch_id,
            errors=[str(exc)],
            details={"seed": seed, "scale": scale},
        )


def _count_orphans(db: Session, source: Any, target: Any, source_column: Any, target_column: Any) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(source)
            .outerjoin(target, source_column == target_column)
            .where(source_column.is_not(None), target_column.is_(None))
        ).scalar()
        or 0
    )


def validate_database(db: Session, *, record_run: bool = True) -> dict[str, Any]:
    started = utc_now()
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    def add_check(name: str, passed: bool, detail: str, severity: str = "error") -> None:
        checks.append({"name": name, "passed": passed, "severity": severity, "detail": detail})
        if not passed and severity == "warning":
            warnings.append(detail)
        elif not passed:
            errors.append(detail)

    try:
        counts = row_counts(db)
        required = [
            "dim_organization",
            "dim_user",
            "dim_donor",
            "fact_donor_screening",
            "dim_partner_submission",
            "fact_workflow_task",
            "fact_audit_log",
        ]
        for table in required:
            add_check(f"required table {table}", counts.get(table, 0) > 0, f"{table} row count: {counts.get(table, 0)}")

        add_check(
            "donor screenings reference valid donors",
            _count_orphans(db, DonorScreening, Donor, DonorScreening.donor_pk, Donor.donor_pk) == 0,
            "DonorScreening rows must reference dim_donor.",
        )
        add_check(
            "eligibility decisions reference valid donors",
            _count_orphans(db, EligibilityDecision, Donor, EligibilityDecision.donor_pk, Donor.donor_pk) == 0,
            "EligibilityDecision rows must reference dim_donor.",
        )
        add_check(
            "infectious results reference valid donors",
            _count_orphans(db, InfectiousDiseaseResult, Donor, InfectiousDiseaseResult.donor_pk, Donor.donor_pk) == 0,
            "InfectiousDiseaseResult rows must reference dim_donor.",
        )
        add_check(
            "infectious results reference valid tests",
            _count_orphans(db, InfectiousDiseaseResult, InfectiousDiseaseTest, InfectiousDiseaseResult.test_id, InfectiousDiseaseTest.test_id) == 0,
            "InfectiousDiseaseResult rows must reference dim_infectious_disease_test.",
        )
        add_check(
            "recovery suitability references valid tissue types",
            _count_orphans(db, RecoverySuitability, TissueType, RecoverySuitability.tissue_type_id, TissueType.tissue_type_id) == 0,
            "RecoverySuitability rows must reference dim_tissue_type.",
        )
        add_check(
            "CAPA records reference valid deviations",
            _count_orphans(db, CAPA, Deviation, CAPA.deviation_id, Deviation.deviation_id) == 0,
            "CAPA deviation_id values must resolve to fact_deviation.",
        )
        add_check(
            "partner submissions reference valid organizations",
            _count_orphans(db, PartnerSubmission, Organization, PartnerSubmission.organization_id, Organization.organization_id) == 0,
            "PartnerSubmission rows must reference dim_organization.",
        )
        add_check(
            "partner status rows reference valid submissions",
            _count_orphans(db, PartnerSubmissionStatus, PartnerSubmission, PartnerSubmissionStatus.submission_id, PartnerSubmission.submission_id) == 0,
            "PartnerSubmissionStatus rows must reference dim_partner_submission.",
        )
        add_check(
            "partner documents reference valid secure documents",
            _count_orphans(db, PartnerDocument, SecureDocument, PartnerDocument.document_id, SecureDocument.document_id) == 0,
            "PartnerDocument rows must reference dim_secure_document.",
        )
        add_check(
            "document versions reference valid documents",
            _count_orphans(db, DocumentVersion, SecureDocument, DocumentVersion.document_id, SecureDocument.document_id) == 0,
            "DocumentVersion rows must reference dim_secure_document.",
        )

        donor_timestamp_issues = int(
            db.execute(select(func.count()).select_from(Donor).where(Donor.updated_at < Donor.created_at)).scalar()
            or 0
        )
        add_check("donor timestamps are consistent", donor_timestamp_issues == 0, f"{donor_timestamp_issues} donors have updated_at before created_at.")

        closed_before_open = int(
            db.execute(
                select(func.count())
                .select_from(VendorIncident)
                .where(VendorIncident.resolved_at.is_not(None), VendorIncident.resolved_at < VendorIncident.opened_at)
            ).scalar()
            or 0
        )
        add_check("vendor incident timestamps are consistent", closed_before_open == 0, f"{closed_before_open} vendor incidents close before opening.")

        audit_integrity = int(
            db.execute(
                select(func.count())
                .select_from(AuditLog)
                .where(or_(AuditLog.action_type == "", AuditLog.table_name == "", AuditLog.record_id == ""))
            ).scalar()
            or 0
        )
        add_check("audit events have core attributes", audit_integrity == 0, f"{audit_integrity} audit events are missing action/table/record.")

        conformed_site_ids = {site["site_id"] for site in CONFORMED_SITES}
        add_check(
            "conformed site references are defined",
            conformed_site_ids
            == {
                "SITE-ALACHUA",
                "SITE-WLAF",
                "SITE-EP",
                "SITE-GLENCOE",
                "SITE-NEUNK",
                "SITE-GLASGOW",
                "SITE-MARTON",
            },
            "Clinical producer must retain the shared enterprise site ids.",
        )
        tissue_names = [row[0] for row in db.execute(select(TissueType.tissue_name)).all()]
        unmapped_tissues = [
            tissue_name
            for tissue_name in tissue_names
            if _product_context(tissue_name).get("erp_material_family") == "Unmapped"
        ]
        add_check(
            "clinical tissue types have product-family mappings",
            not unmapped_tissues,
            f"Unmapped tissue types: {unmapped_tissues}",
        )

        overdue_capa = int(
            db.execute(
                select(func.count())
                .select_from(CAPA)
                .where(CAPA.status.not_in(["Closed", "Complete"]), CAPA.due_date.is_not(None), CAPA.due_date < utc_now())
            ).scalar()
            or 0
        )
        add_check("CAPA aging is visible", overdue_capa == 0, f"{overdue_capa} open CAPAs are overdue.", severity="warning")

        breached_sla = int(
            db.execute(select(func.count()).select_from(VendorIncident).where(VendorIncident.sla_breached.is_(True))).scalar()
            or 0
        )
        add_check("vendor SLA breach count is tracked", True, f"{breached_sla} vendor incidents are marked SLA breached.", severity="warning")

        status = "passed" if not errors else "failed"
        payload = {
            "status": status,
            "source_system": SOURCE_SYSTEM,
            "validated_at": iso_now(),
            "checks": checks,
            "warnings": warnings,
            "errors": errors,
            "row_counts": counts,
        }
    except Exception as exc:
        payload = {
            "status": "failed",
            "source_system": SOURCE_SYSTEM,
            "validated_at": iso_now(),
            "checks": checks,
            "warnings": warnings,
            "errors": [str(exc)],
            "row_counts": {},
        }

    _write_json(metadata_root() / LATEST_VALIDATION_FILE, payload)
    if record_run:
        _record_run(
            run_type="validation",
            status="succeeded" if payload["status"] == "passed" else "failed",
            started_at=started,
            row_counts=payload.get("row_counts", {}),
            warnings=payload.get("warnings", []),
            errors=payload.get("errors", []),
            details={"check_count": len(payload.get("checks", []))},
        )
    return payload


def _serialize_cell(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=_json_default, sort_keys=True)
    return value


def _source_record_id(record: Any, model: Any) -> str:
    key_values = []
    for column in model.__mapper__.primary_key:
        key_values.append(str(getattr(record, column.name)))
    return "|".join(key_values)


def _record_timestamp(record: Any, *names: str) -> str:
    for name in names:
        if hasattr(record, name):
            value = getattr(record, name)
            if isinstance(value, datetime):
                return value.isoformat()
            if value is not None:
                return str(value)
    return ""


def export_database_batch(
    db: Session,
    *,
    batch_id: str | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    started = utc_now()
    batch_id = batch_id or _new_batch_id("clinical_export")
    target_root = Path(root) if root else export_root()
    batch_dir = target_root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    row_count_payload: dict[str, int] = {}
    checksums: dict[str, str] = {}
    files: list[dict[str, Any]] = []

    try:
        for table_name, model in EXPORT_MODELS:
            columns = [column.name for column in model.__table__.columns]
            output_path = batch_dir / f"{table_name}.csv"
            digest = hashlib.sha256()
            count = 0
            with output_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[*columns, *EXPORT_METADATA_FIELDS],
                )
                writer.writeheader()
                for record in db.execute(select(model)).scalars().all():
                    row = {column: _serialize_cell(getattr(record, column)) for column in columns}
                    row["source_system"] = SOURCE_SYSTEM
                    row["source_table"] = table_name
                    row["source_record_id"] = _source_record_id(record, model)
                    row["source_created_at"] = _record_timestamp(record, "created_at", "submitted_at", "opened_at")
                    row["source_updated_at"] = _record_timestamp(
                        record,
                        "updated_at",
                        "changed_at",
                        "submitted_at",
                        "created_at",
                        "opened_at",
                    )
                    row["ingestion_batch_id"] = batch_id
                    row["extraction_batch_id"] = batch_id
                    row["generated_at"] = started.isoformat()
                    row["extracted_at"] = started.isoformat()
                    writer.writerow(row)
                    digest.update(json.dumps(row, default=_json_default, sort_keys=True).encode("utf-8"))
                    count += 1
            row_count_payload[table_name] = count
            checksums[f"{table_name}.csv"] = digest.hexdigest()
            files.append({"file": f"{table_name}.csv", "table": table_name, "row_count": count})

        manifest = {
            "batch_id": batch_id,
            "source_system": SOURCE_SYSTEM,
            "generated_at": iso_now(),
            "extraction_batch_id": batch_id,
            "row_counts": row_count_payload,
            "checksums": checksums,
            "files": files,
            "export_path": str(batch_dir),
        }
        _write_json(batch_dir / "manifest.json", manifest)
        _write_json(metadata_root() / LATEST_EXPORT_FILE, manifest)
        db.add(
            DataExportEvent(
                export_type="source_batch",
                entity_type="clinical_source_tables",
                record_count=sum(row_count_payload.values()),
                route="/api/generation/export",
                status="Completed",
                created_at=utc_now(),
                details={"batch_id": batch_id, "export_path": str(batch_dir)},
            )
        )
        db.commit()
        _record_run(
            run_type="export",
            status="succeeded",
            started_at=started,
            row_counts=row_count_payload,
            extraction_batch_id=batch_id,
            details={"export_path": str(batch_dir)},
        )
        return manifest
    except Exception as exc:
        db.rollback()
        _record_run(
            run_type="export",
            status="failed",
            started_at=started,
            extraction_batch_id=batch_id,
            errors=[str(exc)],
            details={"export_path": str(batch_dir)},
        )
        raise


def generation_status(db: Session | None = None) -> dict[str, Any]:
    status: dict[str, Any] = {
        "source_system": SOURCE_SYSTEM,
        "generated_at": iso_now(),
        "latest_run": _read_json(metadata_root() / "latest_run.json", {}),
        "latest_validation": latest_validation_result(),
        "latest_export_manifest": latest_export_manifest(),
        "continuous": continuous_state(),
        "metadata_root": str(metadata_root()),
        "export_root": str(export_root()),
        "stop_file": str(stop_file_path()),
    }
    if db is not None:
        try:
            status["row_counts"] = row_counts(db)
            status["source_freshness"] = source_freshness(db)
        except Exception as exc:
            status["database_error"] = str(exc)
    return status


class ContinuousProducer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(
        self,
        *,
        interval_seconds: int,
        cycles: int | None,
        seed: int | None,
        scale: int,
        export_each_cycle: bool = False,
        allow_infinite: bool = False,
    ) -> dict[str, Any]:
        minimum = max(1, settings.data_producer_min_interval_seconds)
        if interval_seconds < minimum:
            raise ValueError(f"interval_seconds must be at least {minimum}.")
        if cycles is None:
            if not allow_infinite or not settings.data_producer_allow_infinite:
                raise ValueError("Infinite continuous generation requires allow_infinite=true and DATA_PRODUCER_ALLOW_INFINITE=true.")
        elif cycles < 1:
            raise ValueError("cycles must be greater than zero.")
        elif cycles > settings.data_producer_max_cycles:
            raise ValueError(f"cycles must be <= {settings.data_producer_max_cycles}.")

        with self._lock:
            if self._thread and self._thread.is_alive():
                raise ValueError("Continuous producer is already running.")
            self._stop_event.clear()
            stop_path = stop_file_path()
            if stop_path.exists():
                stop_path.unlink()
            state = {
                "running": True,
                "started_at": iso_now(),
                "interval_seconds": interval_seconds,
                "cycles_requested": cycles,
                "cycles_completed": 0,
                "seed": seed,
                "scale": scale,
                "export_each_cycle": export_each_cycle,
                "allow_infinite": allow_infinite,
                "stop_file": str(stop_path),
                "last_error": None,
            }
            _write_json(metadata_root() / CONTINUOUS_STATE_FILE, state)
            self._thread = threading.Thread(
                target=self._run_loop,
                kwargs={
                    "interval_seconds": interval_seconds,
                    "cycles": cycles,
                    "seed": seed,
                    "scale": scale,
                    "export_each_cycle": export_each_cycle,
                },
                daemon=True,
            )
            self._thread.start()
            return state

    def stop(self) -> dict[str, Any]:
        self._stop_event.set()
        stop_path = stop_file_path()
        stop_path.parent.mkdir(parents=True, exist_ok=True)
        stop_path.write_text(f"stop requested at {iso_now()}\n", encoding="utf-8")
        state = continuous_state()
        state["stop_requested_at"] = iso_now()
        state["running"] = bool(self._thread and self._thread.is_alive())
        _write_json(metadata_root() / CONTINUOUS_STATE_FILE, state)
        return state

    def _run_loop(
        self,
        *,
        interval_seconds: int,
        cycles: int | None,
        seed: int | None,
        scale: int,
        export_each_cycle: bool,
    ) -> None:
        completed = 0
        last_error = None
        try:
            while cycles is None or completed < cycles:
                if self._stop_event.is_set() or stop_file_path().exists():
                    break
                cycle_seed = None if seed is None else seed + completed
                with SessionLocal() as db:
                    run_incremental_generation(db, seed=cycle_seed, scale=scale)
                    validate_database(db, record_run=True)
                    if export_each_cycle:
                        export_database_batch(db)
                completed += 1
                state = continuous_state()
                state.update(
                    {
                        "running": True,
                        "cycles_completed": completed,
                        "last_cycle_finished_at": iso_now(),
                        "last_error": None,
                    }
                )
                _write_json(metadata_root() / CONTINUOUS_STATE_FILE, state)
                slept = 0.0
                while slept < interval_seconds:
                    if self._stop_event.is_set() or stop_file_path().exists():
                        break
                    time.sleep(min(1.0, interval_seconds - slept))
                    slept += min(1.0, interval_seconds - slept)
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            last_error = str(exc)
        finally:
            state = continuous_state()
            state.update(
                {
                    "running": False,
                    "cycles_completed": completed,
                    "stopped_at": iso_now(),
                    "last_error": last_error,
                }
            )
            _write_json(metadata_root() / CONTINUOUS_STATE_FILE, state)


DATA_PRODUCER = ContinuousProducer()
