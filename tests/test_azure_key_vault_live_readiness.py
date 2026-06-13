from __future__ import annotations

import json
import os
import subprocess
import sys

from app.services.clinical_audit_signing import (
    ALGORITHM_RSA_PSS_SHA256,
    SIGNING_MODE_AZURE_KEY_VAULT,
    AuditManifestSigningConfig,
)
from app.services.clinical_azure_key_vault_live_readiness import (
    LIVE_KEY_OVERRIDE_ENV,
    LIVE_TESTS_ENV,
    azure_key_vault_live_tests_enabled,
    build_key_vault_live_readiness_report,
    build_key_vault_signing_evidence,
    validate_live_key_identifier,
)


def _kv_config(**overrides) -> AuditManifestSigningConfig:
    values = {
        "mode": SIGNING_MODE_AZURE_KEY_VAULT,
        "required": True,
        "algorithm": ALGORITHM_RSA_PSS_SHA256,
        "key_ref": "keyvault://clinical-audit/manifest-validation-test/v1",
        "azure_key_vault_url": "https://clinical-audit.vault.azure.net",
        "azure_key_name": "manifest-validation-test",
        "azure_key_version": "v1",
        "azure_key_vault_credential_mode": "managed_identity",
        "azure_key_vault_enable_real_io": False,
    }
    values.update(overrides)
    return AuditManifestSigningConfig(**values)


def _script_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "AUDIT_MANIFEST_SIGNING_REQUIRED": "true",
            "AUDIT_MANIFEST_SIGNING_MODE": SIGNING_MODE_AZURE_KEY_VAULT,
            "AUDIT_MANIFEST_SIGNING_ALGORITHM": ALGORITHM_RSA_PSS_SHA256,
            "AUDIT_MANIFEST_SIGNING_KEY_REF": "keyvault://clinical-audit/manifest-validation-test/v1",
            "AUDIT_MANIFEST_AZURE_KEY_VAULT_URL": "https://clinical-audit.vault.azure.net",
            "AUDIT_MANIFEST_AZURE_KEY_NAME": "manifest-validation-test",
            "AUDIT_MANIFEST_AZURE_KEY_VERSION": "v1",
            "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE": "managed_identity",
            "AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO": "false",
            LIVE_TESTS_ENV: "false",
            LIVE_KEY_OVERRIDE_ENV: "false",
        }
    )
    env.update(overrides)
    return env


def test_key_vault_live_tests_disabled_by_default() -> None:
    report = build_key_vault_live_readiness_report(config=_kv_config(), env={})

    assert azure_key_vault_live_tests_enabled({}) is False
    assert report["live_tests_enabled"] is False
    assert report["signing_attempted"] is False
    assert report["verification_attempted"] is False
    assert report["network_calls_performed"] is False


def test_key_vault_live_tests_require_explicit_environment_flag() -> None:
    enabled = build_key_vault_live_readiness_report(
        config=_kv_config(azure_key_vault_enable_real_io=True),
        env={LIVE_TESTS_ENV: "true"},
        live_sign_requested=True,
    )
    disabled = build_key_vault_live_readiness_report(
        config=_kv_config(azure_key_vault_enable_real_io=True),
        env={LIVE_TESTS_ENV: "false"},
        live_sign_requested=True,
    )

    assert enabled["live_tests_enabled"] is True
    assert disabled["live_tests_enabled"] is False
    assert "azure_key_vault_live_tests_disabled" in {
        issue["code"] for issue in disabled["blocking_issues"]
    }


def test_key_vault_live_tests_require_dedicated_nonproduction_key_identifier() -> None:
    missing = validate_live_key_identifier("")
    ambiguous = validate_live_key_identifier("clinical-audit-manifest")
    production_like = validate_live_key_identifier("manifest-prod-signing-key")
    safe = validate_live_key_identifier("manifest-validation-test")

    assert {issue.code for issue in missing} == {"azure_key_vault_live_key_identifier_missing"}
    assert {issue.code for issue in ambiguous} == {
        "azure_key_vault_live_key_identifier_not_dedicated"
    }
    assert {issue.code for issue in production_like} == {
        "azure_key_vault_live_key_identifier_not_dedicated"
    }
    assert safe == []


def test_key_vault_live_key_identifier_override_is_explicit_warning() -> None:
    issues = validate_live_key_identifier("manifest-prod-signing-key", allow_unsafe_override=True)

    assert [(issue.code, issue.severity) for issue in issues] == [
        ("azure_key_vault_live_key_identifier_override", "warning")
    ]


def test_key_vault_readiness_script_dry_run_does_not_require_credentials_or_signing() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_azure_key_vault_signing_readiness.py", "--json"],
        text=True,
        capture_output=True,
        check=False,
        env=_script_env(),
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry_run"
    assert payload["signing_attempted"] is False
    assert payload["verification_attempted"] is False
    assert payload["network_calls_performed"] is False
    assert payload["live_tests_enabled"] is False


def test_key_vault_readiness_script_live_sign_requires_explicit_flag() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_azure_key_vault_signing_readiness.py", "--json", "--live-sign"],
        text=True,
        capture_output=True,
        check=False,
        env=_script_env(),
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["signing_attempted"] is False
    assert payload["network_calls_performed"] is False
    assert "azure_key_vault_live_tests_disabled" in {
        issue["code"] for issue in payload["blocking_issues"]
    }


def test_key_vault_evidence_dry_run_writes_expected_json(tmp_path) -> None:
    evidence_path = tmp_path / "key-vault-signing-evidence.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_azure_key_vault_signing_readiness.py",
            "--json",
            "--evidence-out",
            str(evidence_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=_script_env(),
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert report["evidence_out"] == str(evidence_path)
    assert evidence["schema_version"] == "clinical.azure_key_vault.signing_evidence.v1"
    assert evidence["environment_mode"] == "test"
    assert evidence["signing_mode"] == SIGNING_MODE_AZURE_KEY_VAULT
    assert evidence["real_io_enabled"] is False
    assert evidence["live_tests_enabled"] is False
    assert evidence["live_sign_requested"] is False
    assert evidence["signing_attempted"] is False
    assert evidence["verification_attempted"] is False
    assert evidence["network_calls_performed"] is False
    assert evidence["vault_summary"]["vault_url_configured"] is True
    assert evidence["vault_summary"]["key_name"] == "manifest-validation-test"
    assert evidence["validation_result"] == "dry_run_complete"


def test_key_vault_evidence_includes_blocking_issues_with_incomplete_config(tmp_path) -> None:
    evidence_path = tmp_path / "key-vault-signing-evidence.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_azure_key_vault_signing_readiness.py",
            "--json",
            "--evidence-out",
            str(evidence_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=_script_env(
            AUDIT_MANIFEST_SIGNING_REQUIRED="false",
            AUDIT_MANIFEST_SIGNING_MODE="disabled",
            AUDIT_MANIFEST_SIGNING_KEY_REF="",
            AUDIT_MANIFEST_AZURE_KEY_VAULT_URL="",
            AUDIT_MANIFEST_AZURE_KEY_NAME="",
            AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE="",
        ),
    )

    assert result.returncode == 0
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    codes = {issue["code"] for issue in evidence["blocking_issues"]}
    assert "azure_key_vault_signing_mode_not_selected" in codes
    assert "azure_key_vault_url_missing" in codes
    assert "azure_key_name_missing" in codes
    assert "azure_key_vault_credential_mode_unsafe" in codes
    assert evidence["validation_result"] == "blocked"


def test_key_vault_evidence_excludes_secret_like_fields_and_values() -> None:
    report = build_key_vault_live_readiness_report(config=_kv_config(), env={})
    report["client_secret"] = "SHOULD_NOT_APPEAR"
    report["warnings"] = [{"code": "unsafe", "message": "token=SHOULD_NOT_APPEAR"}]

    evidence = build_key_vault_signing_evidence(
        report,
        environment_mode="test",
        generated_at="2026-06-13T00:00:00Z",
    )

    serialized = json.dumps(evidence, sort_keys=True)
    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "client_secret" not in serialized.lower()
    assert "token=" not in serialized.lower()
    assert "https://clinical-audit.vault.azure.net" not in serialized
