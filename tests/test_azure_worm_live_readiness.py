from __future__ import annotations

import json
import os
import subprocess
import sys

from app.services.clinical_audit_mirror import AuditMirrorConfig
from app.services.clinical_azure_worm_live_readiness import (
    LIVE_TEST_PREFIX_OVERRIDE_ENV,
    LIVE_TEST_PREFIX_ENV,
    LIVE_TESTS_ENV,
    azure_worm_live_tests_enabled,
    build_live_readiness_report,
    validate_live_test_prefix,
)


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
