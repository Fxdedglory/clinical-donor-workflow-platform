from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rc0_clinical_hardening_docs_exist_and_cover_core_topics() -> None:
    required_docs = {
        "docs/clinical-api-inventory.md": [
            "/api/clinical/patients",
            "/api/clinical/scheduling",
            "/api/clinical/screening",
            "/api/clinical/encounters",
            "/api/clinical/orders",
            "/api/clinical/care-plans",
            "/api/clinical/billing",
            "/api/clinical/quality",
            "/api/clinical/reports",
            "/api/clinical/admin",
            "X-Confirm-Generation: true",
            "reports.analytics_export",
        ],
        "docs/clinical-rbac-matrix.md": [
            "System Administrator",
            "Clinical Reviewer",
            "Quality Assurance Specialist",
            "Business Technology Analyst",
            "Partner External User",
            "reports.export",
        ],
        "docs/clinical-migration-runbook.md": [
            "202606120001_clinical_patient_registration.py",
            "202606120010_clinical_reports.py",
            "alembic upgrade head",
            "Rollback Notes",
        ],
        "docs/clinical-audit-durability-decision.md": [
            "metadata/workflow_operations.json",
            "database-backed audit storage",
            "object-storage mirroring",
            "Do not implement production audit storage in RC0",
        ],
        "docs/clinical-rc-qa-checklist.md": [
            "Patient / Donor Registration",
            "Scheduling",
            "Screening / Eligibility",
            "Reports / Analytics",
            "Migration Readiness",
        ],
    }
    for doc_path, expected_tokens in required_docs.items():
        content = _read(doc_path)
        for token in expected_tokens:
            assert token in content


def test_clinical_frontend_route_metadata_is_extracted() -> None:
    app = _read("frontend/src/App.jsx")
    route_module = _read("frontend/src/pages/clinical/clinicalRoutes.jsx")
    shell_module = _read("frontend/src/pages/clinical/ClinicalShellPlaceholder.jsx")

    assert "from \"./pages/clinical/clinicalRoutes\"" in app
    assert "from \"./pages/clinical/ClinicalShellPlaceholder\"" in app
    assert "export const clinicalSections" in route_module
    assert "export function clinicalPatientId" in route_module
    assert "export function ClinicalShellPlaceholder" in shell_module
