from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rc1_security_readiness_docs_cover_required_topics() -> None:
    required_docs = {
        "docs/clinical-security-readiness.md": [
            "Secret/config scan",
            "npm audit --audit-level=high",
            "Vite/esbuild",
            "APP_ENV=prod",
            "COOKIE_SECURE",
            "metadata/workflow_operations.json",
        ],
        "docs/clinical-export-permission-review.md": [
            "/api/clinical/reports/analytics-exports",
            "/api/clinical/quality/compliance-exports",
            "/api/clinical/quality/audit-evidence",
            "/api/clinical/reports/audit-activity",
            "require_reports_export",
            "require_quality_export",
        ],
        "docs/clinical-phi-field-inventory.md": [
            "Patients / Donors",
            "Insurance",
            "Screening / Vitals",
            "Encounters / Notes / Diagnoses / Allergies / Medications",
            "Billing / Claims / Payments / Denials",
            "Audit Evidence",
            "Masking And Redaction Future Needs",
        ],
        "docs/clinical-audit-durability-implementation-plan.md": [
            "operational.clinical_workflow_operations",
            "Append-Only Controls",
            "Object-Storage Mirror",
            "Backfill Plan",
            "database-first reads",
        ],
        "docs/clinical-production-readiness-runbook.md": [
            "Environment Variables",
            "alembic upgrade head",
            "Manual QA Checklist Reference",
            "Smoke Test Checklist",
            "Rollback Notes",
        ],
        "docs/clinical-release-notes-rc1.md": [
            "ee40f42 Hardening pass for clinical release candidate",
            "RC1 Additions",
            "Known Limitations",
            "Next-Phase Recommendations",
        ],
        "docs/clinical-demo-script.md": [
            "Patient Registration",
            "Scheduling",
            "Screening / Eligibility",
            "Encounter Documentation",
            "Orders / Results",
            "Care Plans",
            "Billing / Insurance",
            "Quality / Compliance",
            "Reports / Analytics",
            "Audit Evidence",
        ],
    }
    for doc_path, expected_tokens in required_docs.items():
        content = _read(doc_path)
        for token in expected_tokens:
            assert token in content


def test_rc1_updates_existing_rbac_and_audit_decision_docs() -> None:
    rbac = _read("docs/clinical-rbac-matrix.md")
    audit_decision = _read("docs/clinical-audit-durability-decision.md")

    for token in [
        "RC1 Route-Level Enforcement Review",
        "/api/clinical/workflows/commit",
        "RC1 Mutation / Export / Admin Endpoint Review",
        "RC2 Remediation Items",
    ]:
        assert token in rbac

    for token in [
        "RC1 implementation plan documented",
        "docs/clinical-audit-durability-implementation-plan.md",
        "RC2 Follow-Up",
    ]:
        assert token in audit_decision
