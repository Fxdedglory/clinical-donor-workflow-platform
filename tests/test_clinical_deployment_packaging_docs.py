import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_site_integration_manifest_remains_parseable_and_points_to_single_host_startup() -> None:
    manifest = json.loads(_read("docs/clinical-site-integration-manifest.json"))

    assert manifest["recommended_url"] == "https://clinical.teemails.com"
    assert manifest["backend_start_command"] == "python scripts/start_app_service.py"
    assert manifest["startup_check_command"] == "python scripts/start_app_service.py --check"
    assert manifest["health_endpoint"] == "/api/health"
    assert "/clinical/dashboard" in manifest["clinical_routes"]
    assert "PostgreSQL 16-compatible production database" in manifest["production_dependencies"]


def test_production_env_template_is_placeholder_only_and_documents_security_gates() -> None:
    content = _read("docs/clinical-production-env-template.md")

    for token in [
        "APP_ENV=prod",
        "CLINICAL_ENV=prod",
        "DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<postgres_host>:5432/clinical_donor_workflow?sslmode=require",
        "SECRET_KEY=<generated-secret-at-least-32-chars>",
        "ENCRYPTION_KEY=<generated-encryption-key-at-least-32-chars>",
        "COOKIE_SECURE=true",
        "CORS_ORIGINS=[\"https://clinical.teemails.com\",\"https://teemails.com\",\"https://www.teemails.com\"]",
        "SERVE_FRONTEND=true",
        "FRONTEND_DIST_DIR=frontend/dist",
        "WORKFLOW_AUDIT_STORAGE=db_with_json_mirror",
        "PHI_REDACTION_ENABLED=true",
        "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE=managed_identity",
        "SQLite and local file databases are blocked",
    ]:
        assert token in content

    forbidden_values = [
        "Clinical" + "Demo!2026",
        "change-me-for-production-" + "demo-only",
        "0" * 6,
        "AZURE_CLIENT_" + "SECRET=",
        "DefaultEndpoints" + "Protocol=",
    ]
    for forbidden in forbidden_values:
        assert forbidden not in content


def test_package_manifest_documents_runtime_artifacts_and_exclusions() -> None:
    content = _read("docs/clinical-deployment-package-manifest.md")

    for token in [
        "scripts/start_app_service.py",
        "frontend/dist/index.html",
        "frontend/dist/assets/",
        "SERVE_FRONTEND=true",
        "/api/health",
        "/clinical/dashboard",
        "202606130003 (head)",
        "backend/app/cli.py",
        "metadata/visual_audit/",
        "metadata/production_evidence/",
        "data/generated/",
        "data/exports/",
        "logs/",
        "scripts/seed_clinical_demo_data.py",
    ]:
        assert token in content


def test_dry_run_results_record_static_serving_gate_and_migration_checks() -> None:
    content = _read("docs/clinical-deployment-dry-run-results.md")

    for token in [
        "npm run build",
        "scripts\\start_app_service.py --check",
        "SERVE_FRONTEND=true",
        "/api/health",
        "/clinical/dashboard",
        "safe placeholder shape",
        "unsafe local shape",
        "database_url_sqlite",
        "202606130003 (head)",
        "DEPLOY-02 environment provisioning",
    ]:
        assert token in content


def test_start_app_service_check_succeeds_without_live_credentials() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/start_app_service.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "serve_frontend=True" in result.stdout
    assert "frontend_dist_dir=frontend/dist" in result.stdout
    assert "production_security_gate=passed" in result.stdout
    assert "status=ok" in result.stdout
