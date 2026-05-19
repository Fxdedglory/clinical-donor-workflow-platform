import argparse
import random
from datetime import UTC, datetime, timedelta

from faker import Faker
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import (
    SOP,
    AuditLog,
    ChangeControl,
    DonorReview,
    RiskCategory,
    User,
    Vendor,
    VendorIncident,
)
from app.services.audit import log_audit, serialize_model
from app.services.risk_engine import analyze_donor_risk

fake = Faker()

BLOOD_TYPES = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Unknown"]
STATUSES = ["Pending", "Under Review", "Approved", "Rejected", "Deferred"]
NOTES = [
    "Routine intake packet reviewed. No abnormal disclosures.",
    "Recent travel documented; confirm exposure questionnaire during clinical review.",
    "Donor disclosed fever within prior screening window.",
    "Prior hospitalization requires supporting documentation.",
    "Self-reported hepatitis history requires medical director review.",
    "Missing consent attestation on imported intake packet.",
    "Clinical notes indicate unexplained weight loss; escalation recommended.",
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


def _random_datetime(days_back: int = 30) -> datetime:
    return datetime.now(UTC) - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def _apply_analysis(donor: DonorReview) -> None:
    analysis = analyze_donor_risk(
        donor_name=donor.donor_name,
        age=donor.age,
        blood_type=donor.blood_type,
        infectious_history=donor.infectious_history,
        travel_risk=donor.travel_risk,
        missing_required_fields=donor.missing_required_fields,
        clinical_notes=donor.clinical_notes,
    )
    donor.risk_score = analysis.risk_score
    donor.risk_level = analysis.risk_level
    donor.risk_flags = analysis.flagged_conditions
    donor.recommended_action = analysis.recommended_action
    donor.review_priority = analysis.review_priority


def seed_database(records: int, force: bool = False) -> None:
    records = max(500, min(records, 5000))
    db = SessionLocal()
    try:
        existing = db.execute(select(DonorReview.review_id).limit(1)).first()
        if existing and not force:
            print("Seed skipped: donor data already exists. Use --force to reseed.")
            return

        if force:
            for model in [
                AuditLog,
                VendorIncident,
                ChangeControl,
                DonorReview,
                RiskCategory,
                SOP,
                Vendor,
                User,
            ]:
                db.execute(delete(model))
            db.commit()

        users = [
            User(
                full_name="Avery Chen",
                email="avery.chen@example.org",
                role="Clinical Reviewer",
                department="Clinical Operations",
            ),
            User(
                full_name="Morgan Shah",
                email="morgan.shah@example.org",
                role="Quality Manager",
                department="Quality Systems",
            ),
            User(
                full_name="Jordan Lee",
                email="jordan.lee@example.org",
                role="Medical Director",
                department="Clinical Governance",
            ),
            User(
                full_name="Riley Patel",
                email="riley.patel@example.org",
                role="Business Systems Analyst",
                department="Healthcare Technology",
            ),
        ]
        db.add_all(users)
        db.flush()

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
                weights=[32, 16, 34, 8, 10],
                k=1,
            )[0]
            created_at = _random_datetime(45)
            reviewer = random.choice(users) if status_choice != "Pending" else None
            reviewed_at = None
            if status_choice in {"Approved", "Rejected", "Deferred"}:
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
            _apply_analysis(donor)
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
        for idx in range(1, 26):
            status_choice = random.choice(["Draft", "Investigation", "Pending Approval", "Approved", "Rejected"])
            created_at = _random_datetime(120)
            changes.append(
                ChangeControl(
                    request_id=f"CCR-2026-{idx:04d}",
                    requested_by_id=random.choice(users).user_id,
                    sop_id=random.choice(sops).sop_id,
                    reason=random.choice(CHANGE_REASONS),
                    risk_level=random.choice(["Low", "Moderate", "High", "Critical"]),
                    approval_status=status_choice,
                    capa_required=random.random() < 0.35,
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

        db.commit()
        print(f"Seed complete: {records} donors, {len(changes)} change requests, {len(incidents)} vendor incidents.")
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

