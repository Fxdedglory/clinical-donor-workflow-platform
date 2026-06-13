from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from app.models import ClinicalWorkflowAuditMirrorEvent
from app.services import clinical_audit_signing as signing
from app.services.clinical_audit_manifest import (
    AuditManifestConfig,
    generate_audit_mirror_manifest,
    verify_audit_mirror_manifest,
)
from app.services.clinical_audit_mirror import AUDIT_MIRROR_STATUS_MIRRORED
from app.services.clinical_audit_signing import (
    ALGORITHM_RSA_PSS_SHA256,
    SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE,
    SIGNATURE_STATUS_SIGNED,
    SIGNATURE_VERIFICATION_FAILED,
    SIGNATURE_VERIFICATION_VERIFIED,
    SIGNING_MODE_AZURE_KEY_VAULT,
    AuditManifestSigningConfig,
)
from app.services.clinical_azure_worm_evidence import build_validation_evidence
from app.services.production_security_gates import validate_production_security_gates


class _FakeKeyVaultSigningClient:
    def __init__(self, *, secret: bytes = b"fake-key-vault-signing-secret") -> None:
        self.secret = secret
        self.sign_calls: list[dict[str, Any]] = []
        self.verify_calls: list[dict[str, Any]] = []

    def _signature(self, digest: bytes) -> bytes:
        return hmac.new(self.secret, digest, hashlib.sha256).digest()

    def sign(self, algorithm: str, digest: bytes) -> bytes:
        self.sign_calls.append({"algorithm": algorithm, "digest": digest})
        return self._signature(digest)

    def verify(self, algorithm: str, digest: bytes, signature: bytes) -> bool:
        self.verify_calls.append({"algorithm": algorithm, "digest": digest, "signature": signature})
        return hmac.compare_digest(signature, self._signature(digest))


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
        "azure_key_vault_enable_real_io": True,
    }
    values.update(overrides)
    return AuditManifestSigningConfig(**values)


def _manifest_config(**overrides: Any) -> AuditManifestConfig:
    config = _kv_config(**overrides)
    return AuditManifestConfig(
        environment="test",
        mirror_mode="local_filesystem",
        signature_required=True,
        signing_mode=config.mode,
        signature_algorithm=config.algorithm,
        signature_key_ref=config.key_ref,
        azure_key_vault_url=config.azure_key_vault_url,
        azure_key_name=config.azure_key_name,
        azure_key_version=config.azure_key_version,
        azure_key_vault_credential_mode=config.azure_key_vault_credential_mode,
        azure_key_vault_enable_real_io=config.azure_key_vault_enable_real_io,
    )


def _mirror_event(**overrides: Any) -> ClinicalWorkflowAuditMirrorEvent:
    values = {
        "operation_id": "key-vault-manifest-op",
        "mirror_mode": "local_filesystem",
        "mirror_status": AUDIT_MIRROR_STATUS_MIRRORED,
        "payload_profile": "audit_metadata",
        "mirrored_at": datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
        "mirror_uri": "local-worm://clinical-audit/workflow-audit/key-vault-manifest-op.json",
        "mirror_checksum": "sha256-key-vault-manifest",
        "mirror_error": None,
        "dry_run": False,
    }
    values.update(overrides)
    return ClinicalWorkflowAuditMirrorEvent(**values)


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


def test_key_vault_signing_provider_constructs_without_sdk_when_real_io_disabled() -> None:
    config = _kv_config(azure_key_vault_enable_real_io=False)

    result = signing.sign_manifest_checksum("sha256-manifest-checksum", config)

    assert result.status == SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE
    assert result.reason == "Azure Key Vault signing real I/O is disabled."


def test_key_vault_readiness_reports_missing_sdk(monkeypatch) -> None:
    monkeypatch.setattr(signing, "_module_available", lambda _module_name: False)

    summary = signing.azure_key_vault_readiness_summary(_kv_config(azure_key_vault_enable_real_io=False))

    assert summary["sdk_available"] is False
    assert summary["sdk_modules"] == {
        "azure_keyvault_keys_crypto": False,
        "azure_identity": False,
    }
    assert "azure_key_vault_sdk_missing" in {
        issue["code"] for issue in summary["validation_warnings"]
    }


def test_fake_key_vault_client_signs_deterministic_canonical_payload() -> None:
    config = _kv_config()
    fake_client = _FakeKeyVaultSigningClient()
    payload = signing.signing_payload_for_manifest(
        manifest_checksum="sha256-manifest-checksum",
        mode=config.normalized_mode,
        algorithm=config.effective_algorithm,
        key_ref=signing.azure_key_vault_key_reference(config),
    )
    expected_digest = hashlib.sha256(signing.canonical_signing_payload(payload).encode("utf-8")).digest()

    result = signing.sign_manifest_payload(payload, config, signing_client=fake_client)
    repeat = signing.sign_manifest_payload(payload, config, signing_client=fake_client)

    assert result == repeat
    assert result.status == SIGNATURE_STATUS_SIGNED
    assert result.signature is not None
    assert result.signature.startswith(signing.AZURE_KEY_VAULT_SIGNATURE_PREFIX)
    assert fake_client.sign_calls[0] == {
        "algorithm": ALGORITHM_RSA_PSS_SHA256,
        "digest": expected_digest,
    }


def test_fake_key_vault_client_verifies_signature_successfully() -> None:
    config = _kv_config()
    fake_client = _FakeKeyVaultSigningClient()

    signature = signing.sign_manifest_checksum(
        "sha256-manifest-checksum",
        config,
        signing_client=fake_client,
    )
    verification = signing.verify_manifest_signature(
        manifest_checksum="sha256-manifest-checksum",
        signature=signature.signature,
        config=config,
        signing_client=fake_client,
    )

    assert signature.status == SIGNATURE_STATUS_SIGNED
    assert verification["signature_verification_status"] == SIGNATURE_VERIFICATION_VERIFIED
    assert verification["verified"] is True


def test_key_vault_manifest_signature_fails_after_tampering() -> None:
    fake_client = _FakeKeyVaultSigningClient()
    config = _manifest_config()
    manifest = generate_audit_mirror_manifest(
        [_mirror_event()],
        config=config,
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
        signing_client=fake_client,
    )
    ok = verify_audit_mirror_manifest(
        manifest,
        signing_config=config.signing_config(),
        signing_client=fake_client,
    )

    manifest["objects"][0]["checksum"] = "sha256-tampered"
    tampered = verify_audit_mirror_manifest(
        manifest,
        signing_config=config.signing_config(),
        signing_client=fake_client,
    )

    assert ok["signature_verification_status"] == SIGNATURE_VERIFICATION_VERIFIED
    assert tampered["checksum_status"] == "checksum_mismatch"
    assert tampered["signature_verification_status"] == SIGNATURE_VERIFICATION_FAILED
    assert tampered["blocking"] is True


def test_key_vault_signature_includes_key_reference_without_key_material() -> None:
    fake_client = _FakeKeyVaultSigningClient(secret=b"SHOULD_NOT_APPEAR")
    config = _kv_config()

    result = signing.sign_manifest_checksum(
        "sha256-manifest-checksum",
        config,
        signing_client=fake_client,
    )

    serialized = json.dumps(result.__dict__, sort_keys=True)
    assert result.key_ref == "keyvault://clinical-audit/manifest/v1"
    assert "SHOULD_NOT_APPEAR" not in serialized


def test_key_vault_real_io_path_fails_clearly_when_sdk_missing(monkeypatch) -> None:
    original_import_module = signing.importlib.import_module

    def fake_import_module(module_name: str, *args: Any, **kwargs: Any) -> Any:
        if module_name == "azure.keyvault.keys.crypto":
            raise ImportError("missing azure key vault sdk")
        return original_import_module(module_name, *args, **kwargs)

    monkeypatch.setattr(signing.importlib, "import_module", fake_import_module)

    result = signing.sign_manifest_checksum("sha256-manifest-checksum", _kv_config())

    assert result.status == "signing_failed"
    assert "azure-keyvault-keys is required" in str(result.reason)


def test_key_vault_evidence_metadata_excludes_secrets() -> None:
    report = {
        "provider_readiness": {
            "provider": "azure_blob",
            "provider_mode": "object_storage",
            "ready": True,
            "capabilities": {"verify_object_checksum": True},
            "validation_errors": [],
            "validation_warnings": [],
            "azure": {
                "account_url_configured": True,
                "container": "clinical-audit-worm",
                "prefix": "workflow-audit",
                "credential_mode": "managed_identity",
            },
        },
        "real_io_enabled": False,
        "live_tests_enabled": False,
        "live_write_requested": False,
        "upload_attempted": False,
        "network_calls_performed": False,
        "live_test_prefix": "",
        "live_test_prefix_override_enabled": False,
        "blocking_issues": [],
        "warnings": [],
    }
    config = _kv_config(local_hmac_key="SHOULD_NOT_APPEAR")

    evidence = build_validation_evidence(
        report,
        environment_mode="test",
        signing_config=config,
        generated_at="2026-06-13T00:00:00Z",
    )

    summary = evidence["manifest_signing_summary"]
    serialized = json.dumps(evidence, sort_keys=True)
    assert summary["manifest_signing_mode"] == SIGNING_MODE_AZURE_KEY_VAULT
    assert summary["azure_key_vault_url_configured"] is True
    assert summary["azure_key_vault_key_name"] == "clinical-audit-manifest"
    assert summary["azure_key_vault_key_version"] == "v1"
    assert summary["azure_key_vault_credential_mode"] == "managed_identity"
    assert summary["azure_key_vault_real_io_enabled"] is True
    assert summary["azure_key_vault_readiness"]["vault_url_configured"] is True
    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "https://clinical-audit.vault.azure.net" not in serialized


def test_production_gate_fails_when_required_key_vault_signing_config_is_incomplete() -> None:
    result = validate_production_security_gates(
        _safe_production_config(
            AUDIT_MANIFEST_SIGNING_KEY_REF="",
            AUDIT_MANIFEST_AZURE_KEY_VAULT_URL="",
            AUDIT_MANIFEST_AZURE_KEY_NAME="",
            AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE="",
        )
    )
    codes = {issue.code for issue in result.failures}

    assert "audit_manifest_signing_key_ref_missing" in codes
    assert "audit_manifest_azure_key_vault_url_missing" in codes
    assert "audit_manifest_azure_key_name_missing" in codes
    assert "audit_manifest_azure_key_vault_credential_mode_unsafe" in codes


def test_production_gate_passes_with_safe_key_vault_readiness_config() -> None:
    result = validate_production_security_gates(_safe_production_config())

    assert result.passed is True
