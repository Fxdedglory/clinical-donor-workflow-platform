from __future__ import annotations

import json
from typing import Any

from app.services.clinical_audit_signing import (
    ALGORITHM_RSA_PSS_SHA256,
    SIGNING_MODE_AZURE_KEY_VAULT,
    AuditManifestSigningConfig,
)
from app.services.clinical_azure_key_vault_live_readiness import (
    build_key_vault_live_readiness_report,
    build_key_vault_signing_evidence,
)
from app.services.clinical_key_vault_lifecycle import (
    KeyVaultLifecycleConfig,
    key_vault_lifecycle_config_from_settings,
    key_vault_lifecycle_readiness_summary,
    sanitize_key_vault_lifecycle_payload,
    validate_key_vault_lifecycle_config,
)
from app.services.production_security_gates import validate_production_security_gates


def _kv_config(**overrides: Any) -> AuditManifestSigningConfig:
    values = {
        "mode": SIGNING_MODE_AZURE_KEY_VAULT,
        "required": True,
        "algorithm": ALGORITHM_RSA_PSS_SHA256,
        "key_ref": "keyvault://clinical-audit/manifest/v1",
        "azure_key_vault_url": "https://clinical-audit.vault.azure.net",
        "azure_key_name": "clinical-audit-manifest",
        "azure_key_version": "v1",
        "azure_key_vault_credential_mode": "managed_identity",
        "azure_key_vault_enable_real_io": False,
    }
    values.update(overrides)
    return AuditManifestSigningConfig(**values)


def _safe_production_config(**overrides: Any) -> dict[str, Any]:
    config = {
        "APP_ENV": "prod",
        "SECRET_KEY": "ProdAuthSigningValue1234567890abcdefXYZ",
        "ENCRYPTION_KEY": "ProdFieldCipherValue1234567890abcdefXYZ",
        "COOKIE_SECURE": True,
        "COOKIE_SAMESITE": "lax",
        "CORS_ORIGINS": ["https://clinical.example.com"],
        "DEBUG": False,
        "DATABASE_URL": "postgresql+psycopg://clinical_runtime:secret@db.example.com:5432/clinical?sslmode=require",
        "WORKFLOW_AUDIT_STORAGE": "db_with_json_mirror",
        "WORKFLOW_AUDIT_DB_REQUIRED": True,
        "AUDIT_OBJECT_MIRROR_REQUIRED": True,
        "AUDIT_OBJECT_MIRROR_MODE": "object_storage",
        "AUDIT_OBJECT_MIRROR_PROVIDER": "azure_blob_immutability",
        "AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL": "https://clinicalaudit.blob.core.windows.net",
        "AUDIT_OBJECT_MIRROR_AZURE_CONTAINER": "clinical-audit-worm",
        "AUDIT_OBJECT_MIRROR_AZURE_PREFIX": "workflow-audit",
        "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE": "managed_identity",
        "AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED": True,
        "AUDIT_OBJECT_MIRROR_RETENTION_POLICY": "RET-7Y-WORM",
        "AUDIT_MANIFEST_SIGNING_REQUIRED": True,
        "AUDIT_MANIFEST_SIGNING_MODE": SIGNING_MODE_AZURE_KEY_VAULT,
        "AUDIT_MANIFEST_SIGNING_ALGORITHM": ALGORITHM_RSA_PSS_SHA256,
        "AUDIT_MANIFEST_SIGNING_KEY_REF": "keyvault://clinical-audit/manifest/v1",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_URL": "https://clinical-audit.vault.azure.net",
        "AUDIT_MANIFEST_AZURE_KEY_NAME": "clinical-audit-manifest",
        "AUDIT_MANIFEST_AZURE_KEY_VERSION": "v1",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE": "managed_identity",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO": False,
        "DEFAULT_ANALYTICS_EXPORT_PROFILE": "aggregate_safe",
        "DEFAULT_COMPLIANCE_EXPORT_PROFILE": "compliance_evidence",
        "DEFAULT_AUDIT_EXPORT_PROFILE": "audit_metadata",
        "PHI_REDACTION_ENABLED": True,
        "ALLOW_GENERIC_FOUNDATION_COMMIT": False,
        "GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY": True,
        "AUTHENTICATION_ENABLED": True,
        "MFA_DEV_BYPASS_CODE": "839471652938",
    }
    config.update(overrides)
    return config


def _failure_codes(config: dict[str, Any]) -> set[str]:
    result = validate_production_security_gates(config)
    return {issue.code for issue in result.failures}


def _safe_lifecycle_overrides() -> dict[str, Any]:
    return {
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED": True,
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS": 180,
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME": "clinical-audit-manifest-next",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION": "v2",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REQUIRED": True,
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF": "runbook://clinical-key-vault/key-retirement-v1",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED": True,
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF": "monitor://clinical-key-vault/access-log-review-monthly",
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED": True,
        "AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF": "runbook://clinical-key-vault/incident-recovery-v1",
    }


def test_lifecycle_helper_returns_sanitized_summary() -> None:
    summary = key_vault_lifecycle_readiness_summary(
        KeyVaultLifecycleConfig(
            rotation_required=True,
            rotation_interval_days=180,
            next_key_name="clinical-audit-manifest-next",
            next_key_version="v2",
            retirement_policy_required=True,
            retirement_policy_ref="runbook://clinical-key-vault/key-retirement-v1",
            access_log_review_required=True,
            access_log_review_ref="monitor://clinical-key-vault/access-log-review-monthly",
            incident_recovery_required=True,
            incident_recovery_ref="runbook://clinical-key-vault/incident-recovery-v1",
        ),
        signing_config=_kv_config(
            key_ref="https://clinical-audit.vault.azure.net/keys/clinical-audit-manifest/v1?token=SHOULD_NOT_APPEAR"
        ),
    )

    serialized = json.dumps(summary, sort_keys=True)
    assert summary["current_key_reference"] == "keyvault://clinical-audit-manifest/v1"
    assert summary["next_key_reference"] == "keyvault://clinical-audit-manifest-next/v2"
    assert summary["rotation_status"] == "ready"
    assert "token=" not in serialized.lower()
    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "https://clinical-audit.vault.azure.net" not in serialized


def test_lifecycle_sanitizer_excludes_secret_and_key_material_values() -> None:
    payload = sanitize_key_vault_lifecycle_payload(
        {
            "client_secret": "SHOULD_NOT_APPEAR",
            "note": "token=SHOULD_NOT_APPEAR",
            "nested": {"private_key": "-----BEGIN PRIVATE KEY-----SHOULD_NOT_APPEAR"},
        }
    )

    serialized = json.dumps(payload, sort_keys=True)
    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "client_secret" not in serialized.lower()
    assert "private_key" not in serialized.lower()
    assert "token=" not in serialized.lower()


def test_rotation_policy_validation_fails_when_required_fields_are_missing() -> None:
    issues = validate_key_vault_lifecycle_config(KeyVaultLifecycleConfig(rotation_required=True))
    codes = {issue.code for issue in issues}

    assert "audit_manifest_azure_key_vault_rotation_interval_missing" in codes
    assert "audit_manifest_azure_key_vault_next_key_reference_missing" in codes


def test_rotation_policy_validation_passes_safe_placeholder_metadata() -> None:
    config = key_vault_lifecycle_config_from_settings(_safe_lifecycle_overrides())

    assert validate_key_vault_lifecycle_config(config) == []


def test_key_vault_evidence_includes_lifecycle_metadata() -> None:
    report = build_key_vault_live_readiness_report(
        config=_kv_config(),
        env={key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in _safe_lifecycle_overrides().items()},
    )
    evidence = build_key_vault_signing_evidence(
        report,
        environment_mode="test",
        generated_at="2026-06-13T00:00:00Z",
    )

    lifecycle = evidence["lifecycle_summary"]
    serialized = json.dumps(evidence, sort_keys=True)
    assert lifecycle["rotation_required"] is True
    assert lifecycle["rotation_interval_days"] == 180
    assert lifecycle["current_key_reference"] == "keyvault://clinical-audit/manifest/v1"
    assert lifecycle["next_key_reference"] == "keyvault://clinical-audit-manifest-next/v2"
    assert lifecycle["retirement_policy_status"] == "documented"
    assert lifecycle["access_log_review_status"] == "documented"
    assert lifecycle["incident_recovery_status"] == "documented"
    assert lifecycle["blocking_issues"] == []
    assert "https://clinical-audit.vault.azure.net" not in serialized


def test_production_gate_fails_when_rotation_required_but_incomplete() -> None:
    codes = _failure_codes(
        _safe_production_config(
            AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED=True,
            AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS=0,
            AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME="",
            AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION="",
        )
    )

    assert "audit_manifest_azure_key_vault_rotation_interval_missing" in codes
    assert "audit_manifest_azure_key_vault_next_key_reference_missing" in codes


def test_production_gate_fails_when_incident_recovery_required_but_missing() -> None:
    codes = _failure_codes(
        _safe_production_config(
            AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED=True,
            AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF="",
        )
    )

    assert "audit_manifest_azure_key_vault_incident_recovery_missing" in codes


def test_production_gate_passes_safe_lifecycle_placeholder_config() -> None:
    result = validate_production_security_gates(
        _safe_production_config(**_safe_lifecycle_overrides())
    )

    assert result.passed is True
