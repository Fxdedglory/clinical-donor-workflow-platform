from __future__ import annotations

import json
import os
import subprocess
import sys

from app.services.clinical_audit_mirror import AuditMirrorConfig
from app.services.clinical_audit_signing import (
    ALGORITHM_LOCAL_HMAC_SHA256,
    SIGNING_MODE_LOCAL_HMAC_SHA256,
    AuditManifestSigningConfig,
)
from app.services.clinical_azure_worm_evidence import build_validation_evidence
from app.services.clinical_azure_worm_live_readiness import (
    LIVE_TEST_PREFIX_ENV,
    LIVE_TEST_PREFIX_OVERRIDE_ENV,
    LIVE_TESTS_ENV,
    azure_worm_live_tests_enabled,
    build_live_readiness_report,
    validate_live_test_prefix,
)


def _script_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "AUDIT_OBJECT_MIRROR_MODE": "object_storage",
            "AUDIT_OBJECT_MIRROR_PROVIDER": "azure_blob",
            "AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL": "",
            "AUDIT_OBJECT_MIRROR_AZURE_CONTAINER": "",
            "AUDIT_OBJECT_MIRROR_CONTAINER": "",
            "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE": "",
            "AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO": "false",
            "AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED": "false",
            "AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED": "false",
            "AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED": "false",
            "AUDIT_OBJECT_MIRROR_RETENTION_POLICY": "",
            "AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE": "",
            LIVE_TESTS_ENV: "false",
            LIVE_TEST_PREFIX_ENV: "",
            LIVE_TEST_PREFIX_OVERRIDE_ENV: "false",
        }
    )
    env.update(overrides)
    return env


def _azure_live_config(**overrides) -> AuditMirrorConfig:
    values = {
        "mode": "object_storage",
        "object_provider": "azure_blob",
        "azure_account_url": "https://clinicalaudit.blob.core.windows.net",
        "azure_container": "clinical-audit-worm",
        "azure_prefix": "workflow-audit",
        "azure_credential_mode": "managed_identity",
        "azure_enable_real_io": True,
        "azure_immutability_required": True,
        "azure_legal_hold_required": True,
        "azure_checksum_validation_required": True,
        "retention_policy": "RET-7Y-WORM",
        "legal_hold_reference": "LH-CLINICAL-AUDIT",
    }
    values.update(overrides)
    return AuditMirrorConfig(**values)


def test_azure_worm_live_tests_disabled_by_default() -> None:
    report = build_live_readiness_report(config=_azure_live_config(), env={})

    assert azure_worm_live_tests_enabled({}) is False
    assert report["live_tests_enabled"] is False
    assert report["ready_for_live_validation"] is False
    assert report["upload_attempted"] is False
    assert report["network_calls_performed"] is False


def test_azure_worm_live_tests_require_explicit_environment_flag() -> None:
    enabled_report = build_live_readiness_report(
        config=_azure_live_config(),
        env={LIVE_TESTS_ENV: "true", LIVE_TEST_PREFIX_ENV: "workflow-audit/live-validation-test"},
    )
    disabled_report = build_live_readiness_report(
        config=_azure_live_config(),
        env={LIVE_TESTS_ENV: "false", LIVE_TEST_PREFIX_ENV: "workflow-audit/live-validation-test"},
    )

    assert enabled_report["live_tests_enabled"] is True
    assert disabled_report["live_tests_enabled"] is False


def test_azure_worm_live_tests_fail_closed_when_required_settings_missing() -> None:
    report = build_live_readiness_report(
        config=AuditMirrorConfig(mode="object_storage", object_provider="azure_blob"),
        env={LIVE_TESTS_ENV: "true"},
    )
    codes = {issue["code"] for issue in report["blocking_issues"]}

    assert "azure_live_real_io_disabled" in codes
    assert "azure_live_account_url_missing" in codes
    assert "azure_live_container_missing" in codes
    assert "azure_live_test_prefix_missing" in codes


def test_azure_worm_live_tests_require_dedicated_nonproduction_prefix() -> None:
    missing = validate_live_test_prefix("")
    ambiguous = validate_live_test_prefix("workflow-audit")
    production_like = validate_live_test_prefix("workflow-audit/prod-check")
    safe = validate_live_test_prefix("workflow-audit/live-validation-test")

    assert {issue.code for issue in missing} == {"azure_live_test_prefix_missing"}
    assert {issue.code for issue in ambiguous} == {"azure_live_test_prefix_not_dedicated"}
    assert {issue.code for issue in production_like} == {"azure_live_test_prefix_not_dedicated"}
    assert safe == []


def test_azure_worm_live_prefix_override_is_explicit_warning() -> None:
    issues = validate_live_test_prefix("workflow-audit/prod-check", allow_unsafe_override=True)

    assert [(issue.code, issue.severity) for issue in issues] == [
        ("azure_live_test_prefix_override", "warning")
    ]


def test_azure_worm_readiness_script_dry_run_does_not_require_credentials_or_uploads() -> None:
    env = os.environ.copy()
    env[LIVE_TESTS_ENV] = "false"
    env.pop(LIVE_TEST_PREFIX_ENV, None)
    env.pop(LIVE_TEST_PREFIX_OVERRIDE_ENV, None)

    result = subprocess.run(
        [sys.executable, "scripts/check_azure_worm_readiness.py", "--json"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry_run"
    assert payload["upload_attempted"] is False
    assert payload["network_calls_performed"] is False
    assert payload["live_tests_enabled"] is False


def test_azure_worm_readiness_script_live_write_requires_safe_live_settings() -> None:
    env = os.environ.copy()
    env[LIVE_TESTS_ENV] = "false"
    env.pop(LIVE_TEST_PREFIX_ENV, None)
    env.pop(LIVE_TEST_PREFIX_OVERRIDE_ENV, None)

    result = subprocess.run(
        [sys.executable, "scripts/check_azure_worm_readiness.py", "--json", "--live-write"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["upload_attempted"] is False
    assert payload["network_calls_performed"] is False
    assert payload["blocking_issues"]


def test_azure_worm_evidence_dry_run_writes_expected_json(tmp_path) -> None:
    evidence_path = tmp_path / "azure-worm-evidence.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_azure_worm_readiness.py",
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
    assert evidence["schema_version"] == "clinical.azure_worm.validation_evidence.v1"
    assert evidence["environment_mode"] == "test"
    assert evidence["provider"] == "azure_blob"
    assert evidence["real_io_enabled"] is False
    assert evidence["live_tests_enabled"] is False
    assert evidence["live_write_requested"] is False
    assert evidence["credential_mode_summary"]["approved_identity_mode"] is False
    assert evidence["manifest_signing_summary"]["manifest_signing_mode"] == "disabled"
    assert evidence["manifest_signing_summary"]["signing_required"] is False
    assert evidence["validation_result"] == "blocked"
    assert evidence["data_safety_summary"] == {
        "contains_phi_ephi": False,
        "contains_raw_credentials": False,
        "sanitization": "whitelisted operational readiness fields only",
    }


def test_azure_worm_evidence_dry_run_records_no_uploads_or_network(tmp_path) -> None:
    evidence_path = tmp_path / "azure-worm-evidence.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_azure_worm_readiness.py",
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
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["upload_attempted"] is False
    assert evidence["network_calls_performed"] is False


def test_azure_worm_evidence_includes_blocking_issues_with_incomplete_config(tmp_path) -> None:
    evidence_path = tmp_path / "azure-worm-evidence.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_azure_worm_readiness.py",
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
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    codes = {issue["code"] for issue in evidence["blocking_issues"]}
    assert "azure_account_url_missing" in codes
    assert "azure_container_missing" in codes
    assert "azure_credential_mode_missing" in codes


def test_azure_worm_evidence_includes_prefix_safety_status() -> None:
    report = build_live_readiness_report(
        config=_azure_live_config(),
        env={LIVE_TEST_PREFIX_ENV: "workflow-audit/prod-check"},
    )
    evidence = build_validation_evidence(
        report,
        environment_mode="test",
        generated_at="2026-06-13T00:00:00Z",
    )

    assert evidence["prefix_safety_status"]["configured"] is True
    assert evidence["prefix_safety_status"]["status"] == "blocked"
    assert "azure_live_test_prefix_not_dedicated" in evidence["prefix_safety_status"]["issue_codes"]


def test_azure_worm_evidence_excludes_secret_like_fields_and_values() -> None:
    report = {
        "provider_readiness": {
            "provider": "azure_blob",
            "provider_mode": "object_storage",
            "expected_uri_prefix": "https://example.blob.core.windows.net/clinical-audit-worm/workflow-audit",
            "ready": False,
            "capabilities": {"verify_object_checksum": True},
            "validation_errors": [{"code": "unsafe_value", "message": "password=SHOULD_NOT_APPEAR"}],
            "validation_warnings": [],
            "azure": {
                "account_url_configured": True,
                "container": "clinical-audit-worm",
                "prefix": "workflow-audit",
                "credential_mode": "managed_identity",
                "account_key": "SHOULD_NOT_APPEAR",
                "connection_string": "SHOULD_NOT_APPEAR",
            },
            "secret_token": "SHOULD_NOT_APPEAR",
        },
        "real_io_enabled": False,
        "live_tests_enabled": False,
        "live_write_requested": False,
        "upload_attempted": False,
        "network_calls_performed": False,
        "live_test_prefix": "",
        "live_test_prefix_override_enabled": False,
        "blocking_issues": [{"code": "leaked_token", "message": "token=SHOULD_NOT_APPEAR"}],
        "warnings": [],
    }

    signing_config = AuditManifestSigningConfig(
        mode=SIGNING_MODE_LOCAL_HMAC_SHA256,
        required=True,
        algorithm=ALGORITHM_LOCAL_HMAC_SHA256,
        key_ref="local-dev-hmac-key-v1",
        local_hmac_key="SHOULD_NOT_APPEAR",
    )
    evidence = build_validation_evidence(
        report,
        environment_mode="test",
        signing_config=signing_config,
        generated_at="2026-06-13T00:00:00Z",
    )

    serialized = json.dumps(evidence, sort_keys=True)
    assert evidence["manifest_signing_summary"]["manifest_signing_mode"] == "local_hmac_sha256"
    assert evidence["manifest_signing_summary"]["signing_required"] is True
    assert evidence["manifest_signing_summary"]["signature_algorithm"] == "hmac-sha256"
    assert evidence["manifest_signing_summary"]["signature_key_ref"] == "local-dev-hmac-key-v1"
    assert evidence["manifest_signing_summary"]["signature_verification_status"] == "not_checked_no_manifest"
    assert "SHOULD_NOT_APPEAR" not in serialized
    assert "account_key" not in serialized.lower()
    assert "connection_string" not in serialized.lower()
    assert "password=" not in serialized.lower()
    assert "token=" not in serialized.lower()
