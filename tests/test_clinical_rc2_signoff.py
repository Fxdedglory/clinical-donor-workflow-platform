import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CLINICAL_ROUTES = [
    "/clinical/dashboard",
    "/clinical/patients",
    "/clinical/patients/:id",
    "/clinical/scheduling",
    "/clinical/screening",
    "/clinical/encounters",
    "/clinical/orders",
    "/clinical/care-plans",
    "/clinical/billing",
    "/clinical/quality",
    "/clinical/admin",
    "/clinical/reports",
]

SPRINT_MIGRATIONS = [
    ("202606120001", "202606120001_clinical_patient_registration.py"),
    ("202606120002", "202606120002_clinical_scheduling.py"),
    ("202606120003", "202606120003_clinical_screening.py"),
    ("202606120004", "202606120004_clinical_encounters.py"),
    ("202606120005", "202606120005_clinical_orders.py"),
    ("202606120006", "202606120006_clinical_care_plans.py"),
    ("202606120007", "202606120007_clinical_billing.py"),
    ("202606120008", "202606120008_clinical_quality.py"),
    ("202606120009", "202606120009_clinical_admin.py"),
    ("202606120010", "202606120010_clinical_reports.py"),
]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rc2_release_docs_cover_signoff_and_exceptions() -> None:
    required_docs = {
        "docs/clinical-release-exceptions.md": [
            "No Vite/esbuild release exception is required for RC2",
            "vite` to `^8.0.16",
            "@vitejs/plugin-react` to `^6.0.2",
            "found 0 vulnerabilities",
            "Filesystem workflow audit storage",
        ],
        "docs/clinical-rc2-signoff.md": [
            "Manual QA Signoff Matrix",
            "Product Owner signoff",
            "Browser Route Smoke Inventory",
            "/clinical/patients/:id",
            "Migration readiness",
        ],
        "docs/clinical-release-notes-rc2.md": [
            "Accepted Commit Sequence",
            "9ad2b06",
            "Vite/esbuild",
            "Audit Durability Status",
            "Recommended Post-RC Backlog",
        ],
    }
    for doc_path, expected_tokens in required_docs.items():
        content = _read(doc_path)
        for token in expected_tokens:
            assert token in content


def test_rc2_frontend_dependency_advisory_is_remediated_in_manifest() -> None:
    package_json = json.loads(_read("frontend/package.json"))
    package_lock = json.loads(_read("frontend/package-lock.json"))
    packages = package_lock["packages"]

    assert package_json["dependencies"]["vite"] == "^8.0.16"
    assert package_json["dependencies"]["@vitejs/plugin-react"] == "^6.0.2"
    assert packages["node_modules/vite"]["version"] == "8.0.16"
    assert packages["node_modules/@vitejs/plugin-react"]["version"] == "6.0.2"
    assert "node_modules/esbuild" not in packages
    assert "node_modules/rolldown" in packages


def test_rc2_clinical_route_inventory_is_documented_and_present() -> None:
    route_module = _read("frontend/src/pages/clinical/clinicalRoutes.jsx")
    signoff = _read("docs/clinical-rc2-signoff.md")

    for route in REQUIRED_CLINICAL_ROUTES:
        assert route in route_module
        assert route in signoff

    assert "export const clinicalSections" in route_module
    assert "export const clinicalPatientDetailSection" in route_module
    assert "export function clinicalPatientId" in route_module


def test_rc2_clinical_migration_chain_is_documented_in_order() -> None:
    runbook = _read("docs/clinical-migration-runbook.md")
    last_position = -1
    previous_revision = None

    for revision, filename in SPRINT_MIGRATIONS:
        position = runbook.find(filename)
        assert position > last_position
        last_position = position

        migration = _read(f"database/migrations/versions/{filename}")
        assert re.search(rf'revision:\s*str\s*=\s*"{revision}"', migration)
        if previous_revision is not None:
            assert re.search(rf'down_revision:\s*str\s*\|\s*None\s*=\s*"{previous_revision}"', migration)
        previous_revision = revision
