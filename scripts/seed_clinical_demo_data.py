from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.auth.security import get_password_hash  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Appointment,
    AppointmentResource,
    AppointmentStatusHistory,
    AppointmentType,
    ClinicalAdverseEvent,
    ClinicalAdminApprovalPath,
    ClinicalAdminApprovalStep,
    ClinicalAdminConfigVersion,
    ClinicalBillingAccount,
    ClinicalBillingCodeCatalog,
    ClinicalBillingStatusHistory,
    ClinicalCarePlan,
    ClinicalCarePlanGoal,
    ClinicalCarePlanIntervention,
    ClinicalCarePlanProgressNote,
    ClinicalCarePlanStatusHistory,
    ClinicalCarePlanTask,
    ClinicalCarePlanTeamMember,
    ClinicalCharge,
    ClinicalClaim,
    ClinicalClaimLine,
    ClinicalComplianceExport,
    ClinicalDeferral,
    ClinicalDeferralRuleVersion,
    ClinicalDenial,
    ClinicalEligibilityRuleVersion,
    ClinicalEncounter,
    ClinicalEncounterDiagnosis,
    ClinicalEncounterNote,
    ClinicalEncounterStatusHistory,
    ClinicalEquipment,
    ClinicalInsuranceVerification,
    ClinicalNoteTemplate,
    ClinicalNotificationTemplate,
    ClinicalOrder,
    ClinicalOrderCatalogItem,
    ClinicalOrderResult,
    ClinicalOrderStatusHistory,
    ClinicalPatientAllergy,
    ClinicalPatientMedication,
    ClinicalPayment,
    ClinicalProvider,
    ClinicalProviderScheduleTemplate,
    ClinicalQualityApproval,
    ClinicalQualityCategory,
    ClinicalQualityEvent,
    ClinicalQualityEventLink,
    ClinicalQualityInvestigation,
    ClinicalQualitySeverityMatrix,
    ClinicalQualityStatusHistory,
    ClinicalReportExport,
    ClinicalReportExportItem,
    ClinicalReportStatusHistory,
    ClinicalRoom,
    ClinicalScreeningAnswer,
    ClinicalScreeningOutcome,
    ClinicalScreeningSession,
    ClinicalScreeningStatusHistory,
    ClinicalScreeningTemplateVersion,
    ClinicalScreeningVitals,
    Donor,
    Patient,
    PatientConsent,
    PatientContact,
    PatientInsurance,
    Role,
    RolePermission,
    User,
)

T = TypeVar("T")

DEMO_ROLE = "Clinical Demo Operator"
DEMO_USERNAME = "clinical_demo"
DEMO_EMAIL = "clinical.demo@example.test"
DEFAULT_PASSWORD = "ClinicalDemo!2026"
DEMO_SOURCE = "clinical_local_demo"
BASE_TIME = datetime(2026, 6, 13, 14, 0, tzinfo=UTC)

DEMO_PERMISSIONS = sorted(
    {
        "audit.review",
        "billing.manage",
        "billing.payment_post",
        "billing.read",
        "care_plans.close",
        "care_plans.manage",
        "care_plans.read",
        "clinical_admin.manage",
        "clinical_admin.read",
        "dashboard.view",
        "documents.manage",
        "documents.read",
        "donors.create",
        "donors.read",
        "donors.review",
        "eligibility.manage",
        "eligibility.read",
        "eligibility.review",
        "encounters.manage",
        "encounters.read",
        "encounters.sign",
        "orders.acknowledge",
        "orders.manage",
        "orders.read",
        "patients.create",
        "patients.manage",
        "patients.read",
        "qms.manage",
        "quality.close",
        "quality.export",
        "quality.manage",
        "quality.read",
        "reports.export",
        "reports.read",
        "scheduling.manage",
        "scheduling.read",
        "screening.manage",
        "screening.override",
        "screening.read",
        "tasks.read",
        "tasks.update",
    }
)


def utc_at(hours: int) -> datetime:
    return BASE_TIME + timedelta(hours=hours)


def upsert_by(model: type[T], attr_name: str, value: Any, values: dict[str, Any], db: Session) -> tuple[T, bool]:
    attr = getattr(model, attr_name)
    row = db.execute(select(model).where(attr == value)).scalar_one_or_none()
    created = row is None
    if row is None:
        row = model(**{attr_name: value})
        db.add(row)
    for key, item in values.items():
        setattr(row, key, item)
    db.flush()
    return row, created


def first_or_create(model: type[T], filters: dict[str, Any], values: dict[str, Any], db: Session) -> tuple[T, bool]:
    query = select(model)
    for key, item in filters.items():
        query = query.where(getattr(model, key) == item)
    row = db.execute(query.limit(1)).scalar_one_or_none()
    created = row is None
    if row is None:
        row = model(**filters)
        db.add(row)
    for key, item in values.items():
        setattr(row, key, item)
    db.flush()
    return row, created


def ensure_demo_user(db: Session, password: str) -> tuple[User, dict[str, int]]:
    counts = {"created": 0, "updated": 0}
    role, created = upsert_by(
        Role,
        "role_name",
        DEMO_ROLE,
        {"description": "Local-only synthetic clinical demo operator for backend-connected screenshots."},
        db,
    )
    counts["created" if created else "updated"] += 1

    for permission in DEMO_PERMISSIONS:
        exists = db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role.role_id,
                RolePermission.permission_name == permission,
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(RolePermission(role_id=role.role_id, permission_name=permission))
            counts["created"] += 1

    user, created = upsert_by(
        User,
        "username",
        DEMO_USERNAME,
        {
            "full_name": "Clinical Demo Operator",
            "display_name": "Clinical Demo",
            "email": DEMO_EMAIL,
            "hashed_password": get_password_hash(password),
            "role_id": role.role_id,
            "role": DEMO_ROLE,
            "department": "Clinical Operations",
            "is_active": True,
            "account_type": "internal",
            "user_type": "internal",
            "is_internal": True,
            "is_external": False,
            "external_user_flag": False,
            "approval_status": "Approved",
            "identity_provider": "Platform Native",
            "mfa_enabled": False,
            "failed_login_count": 0,
            "locked_until": None,
            "password_changed_at": BASE_TIME,
            "password_expires_at": BASE_TIME + timedelta(days=180),
            "password_history": [],
            "is_archived": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return user, counts


def seed_patients(db: Session, user: User) -> tuple[list[Patient], Donor, dict[str, int]]:
    counts = {"created": 0, "updated": 0}
    donor, created = upsert_by(
        Donor,
        "donor_identifier",
        "DON-DEMO-001",
        {
            "donor_name": "Demo Donor Alpha",
            "age": 42,
            "blood_type": "O+",
            "sex": "Female",
            "source_organization": "Local Demo Referral Network",
            "donor_history": {"synthetic": True, "profile": "local demo"},
            "current_workflow_state": "Clinical Screening",
            "eligibility_status": "Requires Supervisor Review",
            "created_at": utc_at(-72),
            "updated_at": utc_at(-4),
            "is_archived": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    patient_specs = [
        {
            "patient_id": "PT-DEMO-001",
            "donor_reference": donor.donor_identifier,
            "first_name": "Ada",
            "middle_name": "Demo",
            "last_name": "Hart",
            "date_of_birth": date(1984, 4, 12),
            "sex_at_birth": "Female",
            "gender_identity": "Female",
            "preferred_language": "English",
            "phone": "555-0101",
            "email": "ada.hart@example.test",
            "address_line1": "100 Demo Clinic Way",
            "address_line2": "Suite 4",
            "city": "Rochester",
            "state": "NY",
            "postal_code": "14604",
            "status": "active",
            "created_at": utc_at(-70),
            "updated_at": utc_at(-3),
        },
        {
            "patient_id": "PT-DEMO-002",
            "donor_reference": "DON-DEMO-002",
            "first_name": "Milo",
            "middle_name": None,
            "last_name": "Rivera",
            "date_of_birth": date(1978, 9, 23),
            "sex_at_birth": "Male",
            "gender_identity": "Male",
            "preferred_language": "Spanish",
            "phone": "555-0102",
            "email": "milo.rivera@example.test",
            "address_line1": "200 Demo Review Ave",
            "address_line2": None,
            "city": "Buffalo",
            "state": "NY",
            "postal_code": "14202",
            "status": "active",
            "created_at": utc_at(-55),
            "updated_at": utc_at(-6),
        },
    ]
    patients: list[Patient] = []
    for spec in patient_specs:
        patient, created = upsert_by(
            Patient,
            "patient_id",
            spec["patient_id"],
            {
                **spec,
                "source": DEMO_SOURCE,
                "version": 1,
                "created_by": user.user_id,
                "updated_by": user.user_id,
                "is_deleted": False,
            },
            db,
        )
        counts["created" if created else "updated"] += 1
        patients.append(patient)

    first_patient = patients[0]
    contact, created = first_or_create(
        PatientContact,
        {"patient_pk": first_patient.patient_pk, "contact_type": "emergency", "full_name": "Jordan Demo"},
        {
            "contact_relationship": "Spouse",
            "phone": "555-0110",
            "email": "jordan.demo@example.test",
            "is_primary": True,
            "status": "active",
            "source": DEMO_SOURCE,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    insurance, created = first_or_create(
        PatientInsurance,
        {"patient_pk": first_patient.patient_pk, "priority": "primary", "payer_name": "DemoCare Health"},
        {
            "member_id": "DEMO-MEMBER-001",
            "group_number": "DEMO-GRP",
            "plan_type": "PPO",
            "eligibility_status": "verified",
            "status": "active",
            "source": DEMO_SOURCE,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    consent, created = first_or_create(
        PatientConsent,
        {"patient_pk": first_patient.patient_pk, "consent_type": "screening_authorization"},
        {
            "consent_status": "captured",
            "effective_at": utc_at(-60),
            "expires_at": utc_at(24 * 180),
            "captured_by_name": "Clinical Demo Operator",
            "notes": "Synthetic local demo consent record. No real PHI.",
            "source": DEMO_SOURCE,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return patients, donor, counts


def seed_scheduling(db: Session, user: User, patients: list[Patient]) -> tuple[dict[str, Any], dict[str, int]]:
    counts = {"created": 0, "updated": 0}
    provider, created = upsert_by(
        ClinicalProvider,
        "provider_code",
        "PROV-DEMO-001",
        {
            "full_name": "Dr. Casey Demo",
            "role": "Clinician",
            "specialty": "Donor Screening",
            "status": "active",
            "created_at": utc_at(-80),
            "updated_at": utc_at(-4),
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    room, created = upsert_by(
        ClinicalRoom,
        "room_code",
        "ROOM-DEMO-01",
        {
            "room_name": "Demo Screening Room 1",
            "location": "Local Demo Clinic",
            "status": "active",
            "created_at": utc_at(-80),
            "updated_at": utc_at(-4),
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    equipment, created = upsert_by(
        ClinicalEquipment,
        "equipment_code",
        "EQ-DEMO-VITALS",
        {
            "equipment_name": "Demo Vitals Station",
            "equipment_type": "vitals",
            "status": "active",
            "created_at": utc_at(-80),
            "updated_at": utc_at(-4),
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    appointment_type, created = upsert_by(
        AppointmentType,
        "type_code",
        "DEMO-SCREEN",
        {
            "name": "Demo Donor Screening",
            "default_duration_minutes": 60,
            "category": "screening",
            "description": "Local backend-connected demo appointment type.",
            "requires_room": True,
            "status": "active",
            "version": 1,
            "created_at": utc_at(-80),
            "updated_at": utc_at(-4),
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    appointments: list[Appointment] = []
    appointment_specs = [
        ("APT-DEMO-001", patients[0], utc_at(-2), utc_at(-1), "checked_in", "Backend-connected clinical screening demo."),
        ("APT-DEMO-002", patients[1], utc_at(26), utc_at(27), "scheduled", "Upcoming synthetic scheduling demo."),
    ]
    for number, patient, start, end, status, reason in appointment_specs:
        appointment, created = upsert_by(
            Appointment,
            "appointment_number",
            number,
            {
                "patient_pk": patient.patient_pk,
                "patient": patient,
                "provider_id": provider.provider_id,
                "provider": provider,
                "room_id": room.room_id,
                "room": room,
                "appointment_type_id": appointment_type.appointment_type_id,
                "appointment_type": appointment_type,
                "scheduled_start": start,
                "scheduled_end": end,
                "status": status,
                "reason": reason,
                "source": DEMO_SOURCE,
                "version": 1,
                "created_at": start - timedelta(hours=4),
                "created_by": user.user_id,
                "updated_at": start,
                "updated_by": user.user_id,
                "is_deleted": False,
                "check_in_time": start + timedelta(minutes=5) if status == "checked_in" else None,
                "cancellation_reason": None,
                "no_show_reason": None,
            },
            db,
        )
        counts["created" if created else "updated"] += 1
        appointments.append(appointment)

        resource, created = first_or_create(
            AppointmentResource,
            {"appointment_id": appointment.appointment_id, "equipment_id": equipment.equipment_id},
            {"created_by": user.user_id},
            db,
        )
        counts["created" if created else "updated"] += 1
        history, created = first_or_create(
            AppointmentStatusHistory,
            {"appointment_id": appointment.appointment_id, "to_status": status},
            {
                "from_status": None,
                "changed_at": start,
                "changed_by": user.user_id,
                "reason": reason,
                "notes": "Synthetic local demo status history.",
            },
            db,
        )
        counts["created" if created else "updated"] += 1

    schedule_template, created = first_or_create(
        ClinicalProviderScheduleTemplate,
        {"provider_id": provider.provider_id, "weekday": 1, "date_pattern": "weekly"},
        {
            "start_time": time(8, 0),
            "end_time": time(16, 0),
            "location": "Local Demo Clinic",
            "room_id": room.room_id,
            "active": True,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return {
        "provider": provider,
        "room": room,
        "equipment": equipment,
        "appointment_type": appointment_type,
        "appointments": appointments,
    }, counts


def seed_screening_and_encounter(
    db: Session,
    user: User,
    patients: list[Patient],
    donor: Donor,
    scheduling: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    counts = {"created": 0, "updated": 0}
    appointment = scheduling["appointments"][0]
    session, created = upsert_by(
        ClinicalScreeningSession,
        "session_number",
        "SCR-DEMO-001",
        {
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "donor_pk": donor.donor_pk,
            "donor": donor,
            "appointment_id": appointment.appointment_id,
            "appointment": appointment,
            "template_id": "minimal_donor_screening_v1",
            "status": "requires_supervisor_review",
            "current_outcome": "temporarily_deferred",
            "supervisor_review_required": True,
            "started_at": utc_at(-2),
            "completed_at": utc_at(-1),
            "reason": "Synthetic local demo screening with a supervisor review outcome.",
            "source": DEMO_SOURCE,
            "version": 1,
            "created_at": utc_at(-3),
            "created_by": user.user_id,
            "updated_at": utc_at(-1),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    for question_key, answer_value, notes in [
        ("authorization_verified", {"value": True}, "Authorization verified in synthetic demo packet."),
        ("high_risk_travel", {"value": False}, "No risk travel in synthetic demo answer."),
        ("recent_infection", {"value": True}, "Synthetic positive answer used to drive supervisor review."),
    ]:
        answer, created = first_or_create(
            ClinicalScreeningAnswer,
            {"session_id": session.session_id, "question_key": question_key},
            {
                "answer_value": answer_value,
                "notes": notes,
                "created_by": user.user_id,
                "updated_by": user.user_id,
            },
            db,
        )
        counts["created" if created else "updated"] += 1

    vitals, created = first_or_create(
        ClinicalScreeningVitals,
        {"session_id": session.session_id},
        {
            "height_cm": 168.0,
            "weight_kg": 72.5,
            "temperature_c": 37.8,
            "blood_pressure_systolic": 142,
            "blood_pressure_diastolic": 92,
            "pulse": 104,
            "respiration_rate": 18,
            "oxygen_saturation": 97.5,
            "captured_at": utc_at(-1),
            "captured_by": user.user_id,
            "notes": "Synthetic local demo vitals; elevated values drive review.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    outcome, created = first_or_create(
        ClinicalScreeningOutcome,
        {"session_id": session.session_id},
        {
            "proposed_outcome": "temporarily_deferred",
            "committed_outcome": "temporarily_deferred",
            "original_outcome": "requires_supervisor_review",
            "override_outcome": None,
            "deferral_type": "temporary",
            "supervisor_review_required": True,
            "blocking_issues": [],
            "warnings": [{"code": "elevated_vitals", "message": "Synthetic vitals require review."}],
            "rule_results": [{"rule": "recent_infection", "result": "review"}],
            "reason": "Local demo outcome with review and temporary deferral.",
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    deferral, created = upsert_by(
        ClinicalDeferral,
        "deferral_number",
        "DEF-DEMO-001",
        {
            "session_id": session.session_id,
            "session": session,
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "donor_pk": donor.donor_pk,
            "donor": donor,
            "deferral_type": "temporary",
            "reason": "Synthetic temporary deferral used for backend-connected visual verification.",
            "starts_at": utc_at(-1),
            "ends_at": utc_at(24 * 14),
            "status": "active",
            "created_at": utc_at(-1),
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    history, created = first_or_create(
        ClinicalScreeningStatusHistory,
        {"session_id": session.session_id, "to_status": "requires_supervisor_review"},
        {
            "from_status": "in_progress",
            "changed_at": utc_at(-1),
            "changed_by": user.user_id,
            "reason": "Synthetic local demo screening outcome.",
            "notes": "Backend-connected demo evidence.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    note_template, created = upsert_by(
        ClinicalNoteTemplate,
        "template_key",
        "clinical_demo_screening_note_v1",
        {
            "name": "Clinical Demo Screening Note",
            "note_type": "clinical_note",
            "body": "Synthetic clinical screening note template.",
            "sections": [{"key": "assessment", "label": "Assessment"}],
            "status": "active",
            "version": 1,
            "created_at": utc_at(-80),
            "updated_at": utc_at(-4),
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    encounter, created = upsert_by(
        ClinicalEncounter,
        "encounter_number",
        "ENC-DEMO-001",
        {
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "appointment_id": appointment.appointment_id,
            "appointment": appointment,
            "screening_session_id": session.session_id,
            "screening_session": session,
            "encounter_type": "donor_screening",
            "status": "signed",
            "chief_complaint": "Synthetic donor screening assessment.",
            "reason": "Backend-connected visual verification encounter.",
            "started_at": utc_at(-2),
            "ended_at": utc_at(-1),
            "signed_at": utc_at(-1),
            "signed_by": user.user_id,
            "source": DEMO_SOURCE,
            "version": 1,
            "created_at": utc_at(-2),
            "created_by": user.user_id,
            "updated_at": utc_at(-1),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    note, created = first_or_create(
        ClinicalEncounterNote,
        {"encounter_id": encounter.encounter_id, "title": "Demo screening assessment"},
        {
            "template_id": note_template.template_id,
            "template": note_template,
            "note_type": "clinical_note",
            "content": "Synthetic local demo note. No real PHI.",
            "status": "signed",
            "version": 1,
            "is_addendum": False,
            "amendment_reason": "",
            "signed_at": utc_at(-1),
            "signed_by": user.user_id,
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    diagnosis, created = first_or_create(
        ClinicalEncounterDiagnosis,
        {"encounter_id": encounter.encounter_id, "code": "Z02.89"},
        {
            "display": "Encounter for administrative examination",
            "diagnosis_type": "screening_context",
            "status": "active",
            "onset_date": date(2026, 6, 13),
            "notes": "Synthetic coding context for local demo.",
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    allergy, created = first_or_create(
        ClinicalPatientAllergy,
        {"patient_pk": patients[0].patient_pk, "allergen": "Demo contrast agent"},
        {
            "reaction": "Synthetic rash example.",
            "severity": "moderate",
            "status": "active",
            "onset_date": date(2025, 1, 15),
            "notes": "No real PHI.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    medication, created = first_or_create(
        ClinicalPatientMedication,
        {"patient_pk": patients[0].patient_pk, "medication_name": "Demo antihypertensive"},
        {
            "dose": "10 mg",
            "route": "oral",
            "frequency": "daily",
            "status": "active",
            "start_date": date(2025, 2, 1),
            "indication": "Synthetic medication context.",
            "notes": "No real PHI.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    encounter_history, created = first_or_create(
        ClinicalEncounterStatusHistory,
        {"encounter_id": encounter.encounter_id, "to_status": "signed"},
        {
            "from_status": "draft",
            "changed_at": utc_at(-1),
            "changed_by": user.user_id,
            "reason": "Synthetic demo signed encounter.",
            "notes": "Backend-connected visual verification.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return {"session": session, "encounter": encounter, "note_template": note_template, "deferral": deferral}, counts


def seed_orders_and_care(db: Session, user: User, patients: list[Patient], context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    counts = {"created": 0, "updated": 0}
    catalog, created = upsert_by(
        ClinicalOrderCatalogItem,
        "code",
        "LAB-DEMO-K",
        {
            "name": "Demo Potassium",
            "order_type": "laboratory",
            "description": "Synthetic potassium order for local demo.",
            "default_priority": "stat",
            "specimen_type": "blood",
            "active": True,
            "version": 1,
            "created_at": utc_at(-80),
            "updated_at": utc_at(-3),
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    order, created = upsert_by(
        ClinicalOrder,
        "order_number",
        "ORD-DEMO-001",
        {
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "encounter_id": context["encounter"].encounter_id,
            "encounter": context["encounter"],
            "screening_session_id": context["session"].session_id,
            "screening_session": context["session"],
            "appointment_id": context["encounter"].appointment_id,
            "appointment": context["encounter"].appointment,
            "catalog_item_id": catalog.catalog_item_id,
            "catalog_item": catalog,
            "order_type": "laboratory",
            "priority": "stat",
            "status": "resulted",
            "clinical_indication": "Synthetic abnormal result demonstration.",
            "ordering_provider": "Dr. Casey Demo",
            "ordered_at": utc_at(-1),
            "source": DEMO_SOURCE,
            "version": 1,
            "created_at": utc_at(-1),
            "created_by": user.user_id,
            "updated_at": utc_at(0),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    result, created = first_or_create(
        ClinicalOrderResult,
        {"order_id": order.order_id, "result_name": "Potassium"},
        {
            "result_value": "6.4",
            "result_unit": "mmol/L",
            "reference_range": "3.5-5.1",
            "result_status": "critical",
            "abnormal_flag": True,
            "critical_flag": True,
            "resulted_at": utc_at(0),
            "resulted_by": user.user_id,
            "notes": "Synthetic critical result for local backend-connected demo.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    order_history, created = first_or_create(
        ClinicalOrderStatusHistory,
        {"order_id": order.order_id, "to_status": "resulted"},
        {
            "from_status": "ordered",
            "changed_at": utc_at(0),
            "changed_by": user.user_id,
            "reason": "Synthetic critical result posted.",
            "notes": "Unacknowledged by design for work-queue visibility.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    care_plan, created = upsert_by(
        ClinicalCarePlan,
        "care_plan_number",
        "CP-DEMO-001",
        {
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "encounter_id": context["encounter"].encounter_id,
            "encounter": context["encounter"],
            "screening_session_id": context["session"].session_id,
            "screening_session": context["session"],
            "order_id": order.order_id,
            "order": order,
            "order_result_id": result.result_id,
            "order_result": result,
            "title": "Critical potassium follow-up",
            "plan_type": "result_follow_up",
            "priority": "critical",
            "status": "active",
            "reason": "Synthetic critical result requires follow-up.",
            "start_date": date(2026, 6, 13),
            "target_date": date(2026, 6, 14),
            "source": DEMO_SOURCE,
            "version": 1,
            "created_at": utc_at(0),
            "created_by": user.user_id,
            "updated_at": utc_at(1),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    goal, created = first_or_create(
        ClinicalCarePlanGoal,
        {"care_plan_id": care_plan.care_plan_id},
        {
            "goal": "Resolve synthetic critical potassium follow-up within 24 hours.",
            "target_date": date(2026, 6, 14),
            "status": "active",
            "priority": "critical",
            "notes": "Local demo goal.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    intervention, created = first_or_create(
        ClinicalCarePlanIntervention,
        {"care_plan_id": care_plan.care_plan_id, "intervention_type": "clinical_review"},
        {
            "intervention": "Notify clinician and repeat synthetic lab review.",
            "owner": "Clinical Demo Operator",
            "due_date": date(2026, 6, 14),
            "status": "planned",
            "notes": "Local demo intervention.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    task, created = first_or_create(
        ClinicalCarePlanTask,
        {"care_plan_id": care_plan.care_plan_id, "title": "Review critical potassium"},
        {
            "description": "Synthetic care-plan task for backend-connected visual verification.",
            "owner": "Clinical Demo Operator",
            "due_date": date(2026, 6, 14),
            "priority": "critical",
            "status": "open",
            "notes": "No real PHI.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    progress, created = first_or_create(
        ClinicalCarePlanProgressNote,
        {"care_plan_id": care_plan.care_plan_id},
        {
            "progress_note": "Synthetic follow-up plan opened for demo critical result.",
            "status_update": "active",
            "created_at": utc_at(1),
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    member, created = first_or_create(
        ClinicalCarePlanTeamMember,
        {"care_plan_id": care_plan.care_plan_id, "member_name": "Clinical Demo Operator"},
        {"role": "care_coordinator", "is_primary": True, "created_by": user.user_id},
        db,
    )
    counts["created" if created else "updated"] += 1

    care_history, created = first_or_create(
        ClinicalCarePlanStatusHistory,
        {"care_plan_id": care_plan.care_plan_id, "to_status": "active"},
        {
            "from_status": None,
            "changed_at": utc_at(1),
            "changed_by": user.user_id,
            "reason": "Synthetic critical care plan opened.",
            "notes": "Backend-connected visual verification.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return {"catalog": catalog, "order": order, "result": result, "care_plan": care_plan, "task": task}, counts


def seed_billing(db: Session, user: User, patients: list[Patient], clinical: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    counts = {"created": 0, "updated": 0}
    insurance = db.execute(
        select(PatientInsurance).where(PatientInsurance.patient_pk == patients[0].patient_pk)
    ).scalar_one()
    account, created = upsert_by(
        ClinicalBillingAccount,
        "account_number",
        "BA-DEMO-001",
        {
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "primary_insurance_id": insurance.insurance_id,
            "primary_insurance": insurance,
            "status": "open",
            "total_charges": 240.0,
            "total_payments": 40.0,
            "total_adjustments": 20.0,
            "balance": 180.0,
            "created_at": utc_at(1),
            "created_by": user.user_id,
            "updated_at": utc_at(2),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    verification, created = first_or_create(
        ClinicalInsuranceVerification,
        {"patient_pk": patients[0].patient_pk, "patient_insurance_id": insurance.insurance_id},
        {
            "verification_status": "verified",
            "verified_at": utc_at(-2),
            "verified_by": user.user_id,
            "payer_name": insurance.payer_name,
            "plan_name": "Demo PPO",
            "member_id": insurance.member_id,
            "group_number": insurance.group_number,
            "coverage_start": date(2026, 1, 1),
            "coverage_end": date(2026, 12, 31),
            "notes": "Synthetic eligibility verification.",
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    billing_code, created = upsert_by(
        ClinicalBillingCodeCatalog,
        "code",
        "DEMO-CLIN-001",
        {
            "code_type": "internal",
            "description": "Synthetic clinical screening service",
            "default_amount": 240.0,
            "active": True,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    charge, created = upsert_by(
        ClinicalCharge,
        "charge_number",
        "CHG-DEMO-001",
        {
            "billing_account_id": account.account_id,
            "billing_account": account,
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "encounter_id": clinical["care_plan"].encounter_id,
            "encounter": clinical["care_plan"].encounter,
            "order_id": clinical["order"].order_id,
            "order": clinical["order"],
            "order_result_id": clinical["result"].result_id,
            "order_result": clinical["result"],
            "care_plan_id": clinical["care_plan"].care_plan_id,
            "care_plan": clinical["care_plan"],
            "care_plan_task_id": clinical["task"].task_id,
            "care_plan_task": clinical["task"],
            "service_date": date(2026, 6, 13),
            "code": billing_code.code,
            "code_type": billing_code.code_type,
            "description": billing_code.description,
            "quantity": 1.0,
            "unit_amount": 240.0,
            "total_amount": 240.0,
            "status": "captured",
            "created_at": utc_at(2),
            "created_by": user.user_id,
            "updated_at": utc_at(2),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    claim, created = upsert_by(
        ClinicalClaim,
        "claim_number",
        "CLM-DEMO-001",
        {
            "billing_account_id": account.account_id,
            "billing_account": account,
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "patient_insurance_id": insurance.insurance_id,
            "patient_insurance": insurance,
            "status": "denied",
            "total_amount": 240.0,
            "paid_amount": 40.0,
            "adjustment_amount": 20.0,
            "balance": 180.0,
            "submitted_at": utc_at(3),
            "submitted_by": user.user_id,
            "created_at": utc_at(3),
            "created_by": user.user_id,
            "updated_at": utc_at(4),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    line, created = first_or_create(
        ClinicalClaimLine,
        {"claim_id": claim.claim_id, "line_number": 1},
        {
            "charge_id": charge.charge_id,
            "charge": charge,
            "code": charge.code,
            "code_type": charge.code_type,
            "description": charge.description,
            "quantity": 1.0,
            "unit_amount": 240.0,
            "line_amount": 240.0,
            "diagnosis_code": "Z02.89",
            "status": "denied",
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    payment, created = first_or_create(
        ClinicalPayment,
        {"claim_id": claim.claim_id, "reference_number": "PAY-DEMO-001"},
        {
            "billing_account_id": account.account_id,
            "billing_account": account,
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "payment_amount": 40.0,
            "adjustment_amount": 20.0,
            "payment_method": "eft",
            "payer_type": "insurance",
            "posted_at": utc_at(4),
            "posted_by": user.user_id,
            "notes": "Synthetic partial payment.",
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    denial, created = first_or_create(
        ClinicalDenial,
        {"claim_id": claim.claim_id, "denial_code": "DEMO-DENIAL"},
        {
            "claim_line_id": line.line_id,
            "claim_line": line,
            "denial_reason": "Synthetic documentation request for backend-connected billing demo.",
            "status": "open",
            "assigned_to": "Clinical Demo Operator",
            "due_date": date(2026, 6, 20),
            "resolution_notes": None,
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    billing_history, created = first_or_create(
        ClinicalBillingStatusHistory,
        {"billing_account_id": account.account_id, "to_status": "open"},
        {
            "claim_id": claim.claim_id,
            "charge_id": charge.charge_id,
            "from_status": None,
            "changed_at": utc_at(4),
            "changed_by": user.user_id,
            "reason": "Synthetic billing work-queue item created.",
            "notes": "Backend-connected visual verification.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return {"account": account, "charge": charge, "claim": claim, "payment": payment, "denial": denial}, counts


def seed_quality_admin_reports(
    db: Session,
    user: User,
    patients: list[Patient],
    context: dict[str, Any],
    clinical: dict[str, Any],
    billing: dict[str, Any],
) -> dict[str, int]:
    counts = {"created": 0, "updated": 0}
    category, created = upsert_by(
        ClinicalQualityCategory,
        "category_key",
        "demo_result_follow_up",
        {
            "category": "Demo Result Follow-up",
            "severity_mapping": {"critical_result": "high"},
            "closure_approval_required": True,
            "approval_required": True,
            "active": True,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    severity, created = upsert_by(
        ClinicalQualitySeverityMatrix,
        "severity",
        "high",
        {"response_sla_hours": 24, "investigation_required": True, "approval_required": True, "active": True, "version": 1},
        db,
    )
    counts["created" if created else "updated"] += 1

    event, created = upsert_by(
        ClinicalQualityEvent,
        "event_number",
        "QE-DEMO-001",
        {
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "appointment_id": context["encounter"].appointment_id,
            "appointment": context["encounter"].appointment,
            "screening_session_id": context["session"].session_id,
            "screening_session": context["session"],
            "encounter_id": context["encounter"].encounter_id,
            "encounter": context["encounter"],
            "order_id": clinical["order"].order_id,
            "order": clinical["order"],
            "order_result_id": clinical["result"].result_id,
            "order_result": clinical["result"],
            "care_plan_id": clinical["care_plan"].care_plan_id,
            "care_plan": clinical["care_plan"],
            "charge_id": billing["charge"].charge_id,
            "charge": billing["charge"],
            "claim_id": billing["claim"].claim_id,
            "claim": billing["claim"],
            "payment_id": billing["payment"].payment_id,
            "payment": billing["payment"],
            "denial_id": billing["denial"].denial_id,
            "denial": billing["denial"],
            "category": category.category,
            "severity": "high",
            "status": "investigation",
            "owner": "Clinical Demo Operator",
            "due_date": date(2026, 6, 14),
            "source_module": "clinical_quality",
            "description": "Synthetic quality event linked to a critical result and billing denial.",
            "created_at": utc_at(5),
            "created_by": user.user_id,
            "updated_at": utc_at(5),
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    investigation, created = first_or_create(
        ClinicalQualityInvestigation,
        {"event_id": event.event_id},
        {
            "note": "Synthetic investigation opened for local backend-connected demo.",
            "evidence_summary": "Critical result, care plan, and billing denial are linked.",
            "owner": "Clinical Demo Operator",
            "finding": "Demo evidence is complete.",
            "root_cause_category": "documentation",
            "corrective_action_recommendation": "Complete synthetic follow-up checklist.",
            "follow_up_due_date": date(2026, 6, 20),
            "created_at": utc_at(5),
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    approval, created = first_or_create(
        ClinicalQualityApproval,
        {"event_id": event.event_id, "approval_type": "closure"},
        {
            "status": "pending",
            "approved_at": None,
            "approved_by": None,
            "comments": "Synthetic pending closure approval.",
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    for entity_type, entity_id, label in [
        ("clinical_order", clinical["order"].order_number, "Critical result order"),
        ("clinical_care_plan", clinical["care_plan"].care_plan_number, "Follow-up care plan"),
        ("clinical_claim", billing["claim"].claim_number, "Denied claim"),
    ]:
        link, created = first_or_create(
            ClinicalQualityEventLink,
            {"event_id": event.event_id, "entity_type": entity_type, "entity_id": entity_id},
            {"label": label, "created_by": user.user_id},
            db,
        )
        counts["created" if created else "updated"] += 1

    status_history, created = first_or_create(
        ClinicalQualityStatusHistory,
        {"event_id": event.event_id, "to_status": "investigation"},
        {
            "from_status": "open",
            "changed_at": utc_at(5),
            "changed_by": user.user_id,
            "reason": "Synthetic quality investigation started.",
            "notes": "Backend-connected visual verification.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    adverse, created = upsert_by(
        ClinicalAdverseEvent,
        "adverse_event_number",
        "AE-DEMO-001",
        {
            "quality_event_id": event.event_id,
            "quality_event": event,
            "patient_pk": patients[0].patient_pk,
            "patient": patients[0],
            "screening_session_id": context["session"].session_id,
            "screening_session": context["session"],
            "encounter_id": context["encounter"].encounter_id,
            "encounter": context["encounter"],
            "order_id": clinical["order"].order_id,
            "order": clinical["order"],
            "order_result_id": clinical["result"].result_id,
            "order_result": clinical["result"],
            "care_plan_id": clinical["care_plan"].care_plan_id,
            "care_plan": clinical["care_plan"],
            "event_type": "clinical_result_follow_up",
            "severity": "moderate",
            "event_at": utc_at(4),
            "description": "Synthetic adverse event used for local visual verification.",
            "immediate_action_taken": "Care plan opened.",
            "reporter": "Clinical Demo Operator",
            "follow_up_required": True,
            "status": "open",
            "created_by": user.user_id,
            "updated_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    compliance_export, created = upsert_by(
        ClinicalComplianceExport,
        "export_number",
        "QEXP-DEMO-001",
        {
            "date_from": date(2026, 6, 1),
            "date_to": date(2026, 6, 30),
            "modules": ["quality", "orders", "billing"],
            "criteria": {"module": "quality", "synthetic": True},
            "evidence_summary": {"quality_events": 1, "adverse_events": 1, "phi": "none"},
            "status": "generated",
            "generated_at": utc_at(6),
            "generated_by": user.user_id,
            "created_at": utc_at(6),
            "created_by": user.user_id,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    screening_template, created = upsert_by(
        ClinicalScreeningTemplateVersion,
        "template_key",
        "demo_screening_template",
        {
            "template_name": "Demo Screening Template",
            "version": 1,
            "required_questions": [{"key": "authorization_verified"}, {"key": "recent_infection"}],
            "active": True,
            "created_by": user.user_id,
            "reason": "Local backend-connected demo readiness.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    eligibility_rule, created = upsert_by(
        ClinicalEligibilityRuleVersion,
        "rule_key",
        "demo_recent_infection_review",
        {
            "rule_name": "Demo Recent Infection Review",
            "rule_type": "eligibility",
            "severity": "high",
            "expression": "answers.recent_infection == true",
            "criteria": {"question": "recent_infection", "value": True},
            "explanation": "Synthetic rule for local demo.",
            "active": True,
            "version": 1,
            "created_by": user.user_id,
            "reason": "Local backend-connected demo readiness.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    deferral_rule, created = upsert_by(
        ClinicalDeferralRuleVersion,
        "rule_key",
        "demo_temp_deferral",
        {
            "rule_name": "Demo Temporary Deferral",
            "rule_type": "deferral",
            "severity": "medium",
            "expression": "outcome == temporarily_deferred",
            "criteria": {"duration_days": 14},
            "explanation": "Synthetic deferral rule for local demo.",
            "active": True,
            "version": 1,
            "created_by": user.user_id,
            "reason": "Local backend-connected demo readiness.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    approval_path, created = upsert_by(
        ClinicalAdminApprovalPath,
        "workflow",
        "quality.close_demo",
        {
            "path_name": "Demo Quality Closure Approval",
            "version": 1,
            "active": True,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    approval_step, created = first_or_create(
        ClinicalAdminApprovalStep,
        {"path_id": approval_path.path_id, "step_order": 1},
        {"role": DEMO_ROLE, "permission": "quality.close", "required": True, "active": True},
        db,
    )
    counts["created" if created else "updated"] += 1

    notification, created = first_or_create(
        ClinicalNotificationTemplate,
        {"workflow": "quality.close_demo", "channel": "in_app"},
        {
            "subject": "Demo quality closure requires review",
            "body": "Synthetic local demo notification template.",
            "active": True,
            "version": 1,
            "created_by": user.user_id,
            "updated_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    config, created = first_or_create(
        ClinicalAdminConfigVersion,
        {"config_type": "demo_readiness", "config_key": "clinical_local_demo"},
        {
            "version": 1,
            "status": "active",
            "entity_type": "clinical_demo_dataset",
            "entity_id": "clinical-local-demo",
            "snapshot": {"source": DEMO_SOURCE, "routes": "clinical"},
            "change_summary": {"seed": "scripts/seed_clinical_demo_data.py"},
            "effective_from": utc_at(6),
            "created_by": user.user_id,
            "reason": "Local backend-connected demo readiness.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    report_export, created = upsert_by(
        ClinicalReportExport,
        "export_number",
        "RPT-DEMO-001",
        {
            "modules": ["patients", "screening", "orders", "billing", "quality"],
            "filters": {"synthetic": True},
            "date_from": date(2026, 6, 1),
            "date_to": date(2026, 6, 30),
            "export_format": "json",
            "row_counts": {"patients": 2, "orders": 1, "quality": 1},
            "payload_metadata": {"source": DEMO_SOURCE, "small_cell_suppression": True},
            "status": "generated",
            "generated_at": utc_at(6),
            "generated_by": user.user_id,
            "created_at": utc_at(6),
            "created_by": user.user_id,
            "is_deleted": False,
        },
        db,
    )
    counts["created" if created else "updated"] += 1

    for module, report_name, row_count in [
        ("patients", "Patient throughput", 2),
        ("orders", "Orders and results", 1),
        ("quality", "Quality trends", 1),
    ]:
        item, created = first_or_create(
            ClinicalReportExportItem,
            {"export_id": report_export.export_id, "module": module, "report_name": report_name},
            {"row_count": row_count, "payload_metadata": {"source": DEMO_SOURCE}},
            db,
        )
        counts["created" if created else "updated"] += 1

    report_history, created = first_or_create(
        ClinicalReportStatusHistory,
        {"export_id": report_export.export_id, "to_status": "generated"},
        {
            "from_status": None,
            "changed_at": utc_at(6),
            "changed_by": user.user_id,
            "reason": "Synthetic report export generated.",
            "notes": "Backend-connected visual verification.",
        },
        db,
    )
    counts["created" if created else "updated"] += 1
    return counts


def merge_counts(*items: dict[str, int]) -> dict[str, int]:
    totals = {"created": 0, "updated": 0}
    for item in items:
        for key in totals:
            totals[key] += item.get(key, 0)
    return totals


def seed(password: str) -> dict[str, Any]:
    with SessionLocal() as db:
        user, auth_counts = ensure_demo_user(db, password)
        patients, donor, patient_counts = seed_patients(db, user)
        scheduling, scheduling_counts = seed_scheduling(db, user, patients)
        context, encounter_counts = seed_screening_and_encounter(db, user, patients, donor, scheduling)
        clinical, clinical_counts = seed_orders_and_care(db, user, patients, context)
        billing, billing_counts = seed_billing(db, user, patients, clinical)
        quality_counts = seed_quality_admin_reports(db, user, patients, context, clinical, billing)
        db.commit()
    counts = merge_counts(auth_counts, patient_counts, scheduling_counts, encounter_counts, clinical_counts, billing_counts, quality_counts)
    return {
        "status": "ok",
        "source": DEMO_SOURCE,
        "database_url_host_hint": os.getenv("DATABASE_URL", "").split("@")[-1].split("/")[0] if os.getenv("DATABASE_URL") else "",
        "demo_user": DEMO_USERNAME,
        "demo_patient_id": "PT-DEMO-001",
        "counts": counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic synthetic clinical demo data for local screenshots.")
    parser.add_argument(
        "--password",
        default=os.getenv("CLINICAL_DEMO_PASSWORD", DEFAULT_PASSWORD),
        help="Local demo password. Defaults to CLINICAL_DEMO_PASSWORD or a local-only demo value.",
    )
    args = parser.parse_args()
    result = seed(args.password)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
