from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.services.clinical_audit_mirror import AuditMirrorConfig, audit_mirror_config_from_settings
from app.services.clinical_audit_mirror_providers import provider_readiness_summary

LIVE_TESTS_ENV = "CLINICAL_RUN_AZURE_WORM_LIVE_TESTS"
LIVE_TEST_PREFIX_ENV = "AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX"
LIVE_TEST_PREFIX_OVERRIDE_ENV = "AUDIT_OBJECT_MIRROR_AZURE_LIVE_ALLOW_PRODUCTION_PREFIX"
LIVE_TEST_PROVIDER_VALUES = {"azure", "azure_blob", "azure_blob_storage", "azure_blob_immutability"}
LIVE_TEST_SAFE_PREFIX_TOKENS = ("test", "nonprod", "non-prod", "sandbox", "validation")
LIVE_TEST_UNSAFE_PREFIX_TOKENS = ("prod", "production", "customer", "patient", "donor")


@dataclass(frozen=True)
class LiveReadinessIssue:
    code: str
    message: str
    severity: str = "error"


def as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def azure_worm_live_tests_enabled(env: Mapping[str, str] | None = None) -> bool:
    source = env or os.environ
    return as_bool(source.get(LIVE_TESTS_ENV), default=False)


def live_test_prefix(env: Mapping[str, str] | None = None) -> str:
    source = env or os.environ
    return str(source.get(LIVE_TEST_PREFIX_ENV) or "").strip().strip("/")


def unsafe_prefix_override_enabled(env: Mapping[str, str] | None = None) -> bool:
    source = env or os.environ
    return as_bool(source.get(LIVE_TEST_PREFIX_OVERRIDE_ENV), default=False)


def validate_live_test_prefix(
    prefix: str,
    *,
    allow_unsafe_override: bool = False,
) -> list[LiveReadinessIssue]:
    normalized = prefix.strip().strip("/")
    issues: list[LiveReadinessIssue] = []
    if not normalized:
        return [
            LiveReadinessIssue(
                code="azure_live_test_prefix_missing",
                message=f"{LIVE_TEST_PREFIX_ENV} is required before Azure WORM live tests can run.",
            )
        ]
    lowered = normalized.lower()
    if "//" in normalized or "\\" in normalized:
        issues.append(
            LiveReadinessIssue(
                code="azure_live_test_prefix_invalid",
                message="Azure WORM live test prefix must be a simple blob prefix, not a URI or Windows path.",
            )
        )
    has_safe_token = any(token in lowered for token in LIVE_TEST_SAFE_PREFIX_TOKENS)
    has_unsafe_token = any(token in lowered for token in LIVE_TEST_UNSAFE_PREFIX_TOKENS)
    ambiguous = normalized in {"workflow-audit", "audit", "clinical-audit", "clinical-audit-worm"}
    if (not has_safe_token or has_unsafe_token or ambiguous) and not allow_unsafe_override:
        issues.append(
            LiveReadinessIssue(
                code="azure_live_test_prefix_not_dedicated",
                message=(
                    f"{LIVE_TEST_PREFIX_ENV} must clearly identify a dedicated non-production "
                    f"test prefix, such as workflow-audit/live-validation-test."
                ),
            )
        )
    elif allow_unsafe_override and (not has_safe_token or has_unsafe_token or ambiguous):
        issues.append(
            LiveReadinessIssue(
                code="azure_live_test_prefix_override",
                message=(
                    "Unsafe or ambiguous Azure WORM live test prefix accepted only because "
                    f"{LIVE_TEST_PREFIX_OVERRIDE_ENV}=true."
                ),
                severity="warning",
            )
        )
    return issues


def _config_issue(code: str, message: str) -> LiveReadinessIssue:
    return LiveReadinessIssue(code=code, message=message)


def validate_live_azure_config(
    config: AuditMirrorConfig,
    *,
    env: Mapping[str, str] | None = None,
) -> list[LiveReadinessIssue]:
    source = env or os.environ
    issues: list[LiveReadinessIssue] = []
    if (config.object_provider or "").strip().lower() not in LIVE_TEST_PROVIDER_VALUES:
        issues.append(
            _config_issue(
                "azure_live_provider_not_selected",
                "AUDIT_OBJECT_MIRROR_PROVIDER must be azure_blob or azure_blob_immutability for live validation.",
            )
        )
    if not config.azure_enable_real_io:
        issues.append(
            _config_issue(
                "azure_live_real_io_disabled",
                "AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true is required for Azure WORM live tests.",
            )
        )
    if not config.azure_account_url:
        issues.append(
            _config_issue(
                "azure_live_account_url_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL is required for Azure WORM live tests.",
            )
        )
    if not (config.azure_container or config.object_container):
        issues.append(
            _config_issue(
                "azure_live_container_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_CONTAINER or AUDIT_OBJECT_MIRROR_CONTAINER is required.",
            )
        )
    if not config.azure_credential_mode:
        issues.append(
            _config_issue(
                "azure_live_credential_mode_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE is required for Azure WORM live tests.",
            )
        )
    if not config.azure_immutability_required:
        issues.append(
            _config_issue(
                "azure_live_immutability_expectation_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=true is required before live WORM validation.",
            )
        )
    if not config.azure_legal_hold_required:
        issues.append(
            _config_issue(
                "azure_live_legal_hold_expectation_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=true is required before live WORM validation.",
            )
        )
    if not config.azure_checksum_validation_required:
        issues.append(
            _config_issue(
                "azure_live_checksum_expectation_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=true is required before live WORM validation.",
            )
        )
    issues.extend(
        validate_live_test_prefix(
            live_test_prefix(source),
            allow_unsafe_override=unsafe_prefix_override_enabled(source),
        )
    )
    return issues


def build_live_readiness_report(
    *,
    config: AuditMirrorConfig | None = None,
    env: Mapping[str, str] | None = None,
    live_write_requested: bool = False,
) -> dict[str, Any]:
    source = env or os.environ
    active_config = config or audit_mirror_config_from_settings()
    readiness = provider_readiness_summary(active_config)
    live_enabled = azure_worm_live_tests_enabled(source)
    issues: list[LiveReadinessIssue] = []
    if live_enabled or live_write_requested:
        issues.extend(validate_live_azure_config(active_config, env=source))
    elif live_test_prefix(source):
        issues.extend(
            validate_live_test_prefix(
                live_test_prefix(source),
                allow_unsafe_override=unsafe_prefix_override_enabled(source),
            )
        )
    warnings = [issue for issue in issues if issue.severity != "error"]
    errors = [issue for issue in issues if issue.severity == "error"]
    return {
        "provider_readiness": readiness,
        "live_tests_enabled": live_enabled,
        "live_write_requested": live_write_requested,
        "real_io_enabled": active_config.azure_enable_real_io,
        "live_test_env_var": LIVE_TESTS_ENV,
        "live_test_prefix_env_var": LIVE_TEST_PREFIX_ENV,
        "live_test_prefix": live_test_prefix(source),
        "live_test_prefix_override_enabled": unsafe_prefix_override_enabled(source),
        "upload_attempted": False,
        "network_calls_performed": False,
        "ready_for_live_validation": live_enabled and not errors and readiness.get("ready") is True,
        "blocking_issues": [issue.__dict__ for issue in errors],
        "warnings": [issue.__dict__ for issue in warnings],
    }
