import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_deploy02_checklist_docs_exist_and_cover_required_topics() -> None:
    required_docs = {
        "docs/clinical-azure-provisioning-checklist.md": [
            "Resource group",
            "App Service Plan",
            "Web App / App Service",
            "PostgreSQL Flexible Server",
            "Application Insights",
            "Key Vault",
            "DNS/custom domain",
            "TLS certificate",
            "Azure Blob WORM storage",
            "No Docker or Kubernetes",
        ],
        "docs/clinical-production-postgres-checklist.md": [
            "PostgreSQL is mandatory",
            "DATABASE_URL=postgresql+psycopg://<db_user>:<db_password>@<postgres_host>:5432/clinical_donor_workflow?sslmode=require",
            "sslmode=require",
            "alembic upgrade head",
            "202606130003 (head)",
            "scripts/seed_clinical_demo_data.py",
        ],
        "docs/clinical-app-service-settings-checklist.md": [
            "docs/clinical-production-env-template.md",
            "docs/clinical-deployment-env-vars.md",
            "docs/clinical-production-security-gates.md",
            "APP_ENV",
            "CLINICAL_ENV",
            "SERVE_FRONTEND",
            "DATABASE_URL",
            "SECRET_KEY",
            "CORS_ORIGINS",
            "COOKIE_SECURE",
            "PHI_REDACTION_ENABLED",
            "WORKFLOW_AUDIT_STORAGE",
            "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE",
            "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE",
        ],
        "docs/clinical-dns-custom-domain-checklist.md": [
            "clinical.teemails.com",
            "teemails.com/clinical",
            "CNAME",
            "TLS",
            "CORS",
            "cookies",
            "SPA asset URLs",
            "API routes",
            "site-wide app launcher",
        ],
        "docs/clinical-deployment-execution-runbook.md": [
            "Phase 1: Preflight",
            "Phase 5: Apply Migrations",
            "Phase 12: Verify Production Security Gates",
            "Phase 18: Rollback",
            "npm run build",
            "python scripts/start_app_service.py",
            "/api/monitoring/health",
            "/clinical/dashboard",
            "scripts/seed_clinical_demo_data.py",
        ],
    }
    for doc_path, expected_tokens in required_docs.items():
        content = _read(doc_path)
        for token in expected_tokens:
            assert token in content


def test_deploy02_site_integration_manifest_is_valid_and_references_package_docs() -> None:
    manifest = json.loads(_read("docs/clinical-site-integration-manifest.json"))

    assert manifest["deployment_phase"] == "environment_provisioning_ready"
    assert manifest["deployment_status"] == "environment_provisioning_ready_no_resources_created"
    assert manifest["recommended_hosting_option"] == "single_azure_app_service_fastapi_react"
    assert manifest["recommended_public_url"] == "https://clinical.teemails.com"
    assert manifest["deployment_package_commit"] == "48d804b"

    docs = manifest["deployment_docs"]
    for key in [
        "deployment_runbook",
        "environment_variables",
        "production_env_template",
        "azure_provisioning_checklist",
        "postgres_checklist",
        "app_service_settings_checklist",
        "dns_checklist",
        "package_manifest",
        "dry_run_results",
    ]:
        assert docs[key].startswith("docs/")
        assert (ROOT / docs[key]).exists()


def test_go_live_signoff_references_deploy02_readiness_package() -> None:
    content = _read("docs/clinical-production-go-live-signoff.md")

    for token in [
        "Deployment Provisioning Checklist",
        "docs/clinical-azure-provisioning-checklist.md",
        "docs/clinical-production-postgres-checklist.md",
        "docs/clinical-app-service-settings-checklist.md",
        "docs/clinical-dns-custom-domain-checklist.md",
        "docs/clinical-deployment-execution-runbook.md",
        "docs/clinical-site-integration-manifest.json",
        "https://clinical.teemails.com",
        "single App Service-style FastAPI plus built React frontend",
    ]:
        assert token in content


def test_deployment_execution_runbook_contains_all_required_phases_in_order() -> None:
    content = _read("docs/clinical-deployment-execution-runbook.md")
    phases = [
        "Phase 1: Preflight",
        "Phase 2: Build Frontend",
        "Phase 3: Package App",
        "Phase 4: Provision Database",
        "Phase 5: Apply Migrations",
        "Phase 6: Configure App Settings",
        "Phase 7: Deploy App",
        "Phase 8: Run Startup Check",
        "Phase 9: Verify Health Endpoints",
        "Phase 10: Verify SPA Routes",
        "Phase 11: Verify Clinical Route Smoke",
        "Phase 12: Verify Production Security Gates",
        "Phase 13: Verify Audit DB Table Availability",
        "Phase 14: Verify Reports/Exports Are Gated",
        "Phase 15: Verify No Demo Seed In Production",
        "Phase 16: DNS Cutover",
        "Phase 17: Post-Deploy Monitoring",
        "Phase 18: Rollback",
    ]

    positions = [content.index(phase) for phase in phases]
    assert positions == sorted(positions)
