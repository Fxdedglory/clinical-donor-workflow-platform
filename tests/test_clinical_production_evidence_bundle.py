from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_bundle(tmp_path: Path) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "SECRET_KEY": "SHOULD_NOT_APPEAR_SECRET_VALUE_1234567890",
            "ENCRYPTION_KEY": "SHOULD_NOT_APPEAR_ENCRYPTION_VALUE_1234567890",
            "DATABASE_URL": "postgresql+psycopg://clinical:SHOULD_NOT_APPEAR_DB_PASSWORD@db.example.com:5432/clinical",
            "PATIENT_NAME": "Jane Example",
            "PATIENT_DOB": "1970-01-01",
            "PATIENT_SSN": "123-45-6789",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_clinical_production_evidence_bundle.py",
            "--out",
            str(tmp_path),
            "--generated-at",
            "2026-06-13T00:00:00Z",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "clinical-production-evidence-bundle.json").read_text(encoding="utf-8"))
    assert (tmp_path / "clinical-production-evidence-summary.md").exists()
    return payload


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_evidence_bundle_generator_dry_run_creates_sanitized_json(tmp_path: Path) -> None:
    payload = _run_bundle(tmp_path)

    assert payload["schema_version"] == "clinical.production_evidence_bundle.v1"
    assert payload["generated_at"] == "2026-06-13T00:00:00Z"
    assert payload["dry_run"] is True
    assert payload["network_calls_performed"] is False
    assert payload["live_cloud_tests_performed"] is False
    assert payload["data_safety_summary"]["contains_raw_credentials"] is False
    assert payload["data_safety_summary"]["contains_secret_values"] is False
    assert payload["data_safety_summary"]["contains_phi_ephi"] is False


def test_evidence_bundle_output_excludes_secret_like_values(tmp_path: Path) -> None:
    payload = _run_bundle(tmp_path)
    serialized = json.dumps(payload, sort_keys=True)

    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "DB_PASSWORD" not in serialized
    assert "postgresql+psycopg://clinical" not in serialized


def test_evidence_bundle_output_excludes_phi_ephi_values(tmp_path: Path) -> None:
    payload = _run_bundle(tmp_path)
    serialized = json.dumps(payload, sort_keys=True)

    assert "Jane Example" not in serialized
    assert "1970-01-01" not in serialized
    assert "123-45-6789" not in serialized
    assert "patient_name" not in serialized.lower()


def test_evidence_bundle_includes_expected_readiness_sections(tmp_path: Path) -> None:
    payload = _run_bundle(tmp_path)

    for key in [
        "validation_command_checklist",
        "clinical_module_inventory",
        "api_inventory_reference",
        "rbac_matrix_reference",
        "migration_runbook_reference",
        "security_gate_summary",
        "audit_durability_summary",
        "worm_mirror_readiness_summary",
        "azure_worm_readiness_dry_run_summary",
        "key_vault_signing_readiness_dry_run_summary",
        "key_lifecycle_readiness_summary",
        "known_limitations",
        "external_approval_checklist",
    ]:
        assert key in payload

    module_ids = {module["module_id"] for module in payload["clinical_module_inventory"]}
    assert {"patients", "scheduling", "screening", "encounters", "orders", "billing", "quality", "reports"}.issubset(module_ids)
    assert payload["alembic"]["heads"] == ["202606130003"]


def test_go_live_signoff_doc_exists_and_includes_required_sections() -> None:
    content = _read("docs/clinical-production-go-live-signoff.md")

    for token in [
        "release baseline",
        "Validation Evidence Checklist",
        "Migration Readiness Checklist",
        "RBAC / Export Readiness Checklist",
        "PHI/ePHI Readiness Checklist",
        "Audit / WORM Readiness Checklist",
        "Azure WORM External Approval Checklist",
        "Key Vault External Approval Checklist",
        "Product Owner Signoff",
        "Security/Compliance Signoff",
        "Operations Signoff",
    ]:
        assert token.lower() in content.lower()


def test_live_validation_decision_log_documents_skipped_by_default_policy() -> None:
    content = _read("docs/clinical-live-validation-decision-log.md")

    for token in [
        "Skipped by default",
        "CLINICAL_RUN_AZURE_WORM_LIVE_TESTS",
        "CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS",
        "Decision Template For Enabling Live Tests",
        "Rollback / Disable Plan",
    ]:
        assert token in content


def test_post_rc_backlog_exists_and_includes_external_azure_validation_items() -> None:
    content = _read("docs/clinical-post-rc-backlog.md")

    for token in [
        "real Azure WORM validation",
        "real Azure Key Vault validation",
        "provider-side immutable retention",
        "legal hold",
        "key rotation live exercise",
        "Azure Monitor access-log evidence review",
        "incident recovery tabletop",
        "Snowflake",
        "Power BI",
        "FHIR/HL7",
        "Clearinghouse/EDI",
        "notification delivery",
        "approval execution",
        "frontend component decomposition",
    ]:
        assert token.lower() in content.lower()
