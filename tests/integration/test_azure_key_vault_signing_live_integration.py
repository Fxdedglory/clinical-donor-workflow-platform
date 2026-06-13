from __future__ import annotations

import pytest
from app.core.config import settings
from app.services.clinical_audit_signing import (
    AzureKeyVaultSigningClient,
    audit_manifest_signing_config_from_settings,
    sign_manifest_checksum,
    verify_manifest_signature,
)
from app.services.clinical_azure_key_vault_live_readiness import (
    LIVE_TESTS_ENV,
    build_key_vault_live_readiness_report,
    validate_live_key_identifier,
)

pytestmark = [
    pytest.mark.azure_key_vault_live,
    pytest.mark.skipif(
        not build_key_vault_live_readiness_report()["live_tests_enabled"],
        reason=f"Azure Key Vault live tests require {LIVE_TESTS_ENV}=true.",
    ),
]

LIVE_VALIDATION_MANIFEST_CHECKSUM = "sha256-azure-key-vault-live-integration"


def _live_config():
    return audit_manifest_signing_config_from_settings(settings)


def test_live_key_vault_readiness_requires_explicit_safe_configuration() -> None:
    config = _live_config()
    report = build_key_vault_live_readiness_report(config=config)

    assert report["live_tests_enabled"] is True
    assert report["real_io_enabled"] is True
    assert report["ready_for_live_validation"] is True
    assert not report["blocking_issues"]
    assert report["signing_readiness"]["provider"] == "azure_key_vault"


def test_live_key_vault_client_constructs_only_when_real_io_enabled() -> None:
    config = _live_config()
    report = build_key_vault_live_readiness_report(config=config)

    assert report["ready_for_live_validation"] is True, report
    assert config.azure_key_vault_enable_real_io is True

    client = AzureKeyVaultSigningClient.from_config(config)

    assert client is not None


def test_live_key_vault_key_identifier_is_dedicated_or_explicitly_overridden() -> None:
    config = _live_config()

    assert validate_live_key_identifier(config.key_ref or config.azure_key_name) == []


def test_live_key_vault_sign_and_verify_non_phi_manifest_checksum() -> None:
    config = _live_config()
    report = build_key_vault_live_readiness_report(config=config, live_sign_requested=True)

    assert report["ready_for_live_validation"] is True, report

    signature = sign_manifest_checksum(LIVE_VALIDATION_MANIFEST_CHECKSUM, config)
    verification = verify_manifest_signature(
        manifest_checksum=LIVE_VALIDATION_MANIFEST_CHECKSUM,
        signature=signature.signature,
        config=config,
    )

    assert signature.status == "signed"
    assert verification["signature_verification_status"] == "verified"
