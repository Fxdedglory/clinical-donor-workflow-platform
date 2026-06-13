from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.clinical_audit_signing import (
    AZURE_KEY_VAULT_SDK_ALGORITHM_MAP,
    SAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES,
    SIGNING_MODE_AZURE_KEY_VAULT,
    UNSAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES,
    AuditManifestSigningConfig,
    audit_manifest_signing_config_from_settings,
    azure_key_vault_readiness_summary,
)
from app.services.clinical_key_vault_lifecycle import (
    key_vault_lifecycle_config_from_settings,
    key_vault_lifecycle_readiness_summary,
)

LIVE_TESTS_ENV = "CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS"
LIVE_KEY_OVERRIDE_ENV = "AUDIT_MANIFEST_AZURE_KEY_VAULT_LIVE_ALLOW_PRODUCTION_KEY"
LIVE_SAFE_KEY_TOKENS = ("test", "nonprod", "non-prod", "sandbox", "validation", "dev")
LIVE_UNSAFE_KEY_TOKENS = ("prod", "production", "patient", "donor", "customer")
LIVE_AMBIGUOUS_KEY_NAMES = {
    "audit",
    "clinical-audit",
    "clinical-audit-manifest",
    "manifest",
    "signing",
}
EVIDENCE_SCHEMA_VERSION = "clinical.azure_key_vault.signing_evidence.v1"
SENSITIVE_FIELD_TOKENS = (
    "client_secret",
    "connection_string",
    "password",
    "private_key",
    "secret",
    "signature",
    "token",
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)("
    r"client_secret=|password=|secret=|token=|sig=|sharedaccesssignature|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r")"
)


@dataclass(frozen=True)
class KeyVaultLiveReadinessIssue:
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


def azure_key_vault_live_tests_enabled(env: Mapping[str, str] | None = None) -> bool:
    source = env or os.environ
    return as_bool(source.get(LIVE_TESTS_ENV), default=False)


def unsafe_key_override_enabled(env: Mapping[str, str] | None = None) -> bool:
    source = env or os.environ
    return as_bool(source.get(LIVE_KEY_OVERRIDE_ENV), default=False)


def utc_evidence_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _issue(code: str, message: str, *, severity: str = "error") -> KeyVaultLiveReadinessIssue:
    return KeyVaultLiveReadinessIssue(code=code, message=message, severity=severity)


def _key_identifier(config: AuditManifestSigningConfig) -> str:
    return config.key_ref or config.azure_key_name


def validate_live_key_identifier(
    key_identifier: str,
    *,
    allow_unsafe_override: bool = False,
) -> list[KeyVaultLiveReadinessIssue]:
    normalized = str(key_identifier or "").strip().strip("/")
    if not normalized:
        return [
            _issue(
                "azure_key_vault_live_key_identifier_missing",
                "A dedicated non-production Key Vault key name or key reference is required for live signing validation.",
            )
        ]
    lowered = normalized.lower()
    if "\\" in normalized:
        return [
            _issue(
                "azure_key_vault_live_key_identifier_invalid",
                "Key Vault live validation key identifier must be a key name, approved key reference, or HTTPS key id.",
            )
        ]
    if "://" in normalized and not (
        normalized.lower().startswith("https://") or normalized.lower().startswith("keyvault://")
    ):
        return [
            _issue(
                "azure_key_vault_live_key_identifier_invalid",
                "Key Vault live validation key identifier must be a key name, approved key reference, or HTTPS key id.",
            )
        ]
    last_part = lowered.rstrip("/").split("/")[-1]
    has_safe_token = any(token in lowered for token in LIVE_SAFE_KEY_TOKENS)
    has_unsafe_token = any(token in lowered for token in LIVE_UNSAFE_KEY_TOKENS)
    ambiguous = last_part in LIVE_AMBIGUOUS_KEY_NAMES or lowered in LIVE_AMBIGUOUS_KEY_NAMES
    if (not has_safe_token or has_unsafe_token or ambiguous) and not allow_unsafe_override:
        return [
            _issue(
                "azure_key_vault_live_key_identifier_not_dedicated",
                "Azure Key Vault live signing requires a dedicated non-production key name or reference.",
            )
        ]
    if allow_unsafe_override and (not has_safe_token or has_unsafe_token or ambiguous):
        return [
            _issue(
                "azure_key_vault_live_key_identifier_override",
                "Unsafe or ambiguous Key Vault live validation key identifier accepted only because override is enabled.",
                severity="warning",
            )
        ]
    return []


def validate_key_vault_signing_config(
    config: AuditManifestSigningConfig,
    *,
    env: Mapping[str, str] | None = None,
    require_live: bool = False,
) -> list[KeyVaultLiveReadinessIssue]:
    source = env or os.environ
    issues: list[KeyVaultLiveReadinessIssue] = []
    if config.normalized_mode != SIGNING_MODE_AZURE_KEY_VAULT:
        issues.append(
            _issue(
                "azure_key_vault_signing_mode_not_selected",
                "AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault is required for Key Vault signing validation.",
            )
        )
    if not config.required:
        issues.append(
            _issue(
                "azure_key_vault_signing_required_disabled",
                "AUDIT_MANIFEST_SIGNING_REQUIRED=true is required for Key Vault signing validation.",
            )
        )
    if config.effective_algorithm not in AZURE_KEY_VAULT_SDK_ALGORITHM_MAP:
        issues.append(
            _issue(
                "azure_key_vault_signing_algorithm_unsupported",
                "AUDIT_MANIFEST_SIGNING_ALGORITHM must be rsa-pss-sha256 or ecdsa-p256-sha256.",
            )
        )
    if not config.azure_key_vault_url:
        issues.append(
            _issue(
                "azure_key_vault_url_missing",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_URL is required for Key Vault signing validation.",
            )
        )
    if not config.azure_key_name:
        issues.append(
            _issue(
                "azure_key_name_missing",
                "AUDIT_MANIFEST_AZURE_KEY_NAME is required for Key Vault signing validation.",
            )
        )
    if not (config.key_ref or config.azure_key_version):
        issues.append(
            _issue(
                "azure_key_reference_missing",
                "AUDIT_MANIFEST_SIGNING_KEY_REF or AUDIT_MANIFEST_AZURE_KEY_VERSION is required for traceable validation.",
            )
        )
    credential_mode = _normalized(config.azure_key_vault_credential_mode)
    if credential_mode in UNSAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES:
        issues.append(
            _issue(
                "azure_key_vault_credential_mode_unsafe",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE must use a non-secret Azure identity mode.",
            )
        )
    elif credential_mode not in SAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES:
        issues.append(
            _issue(
                "azure_key_vault_credential_mode_unsupported",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE is not an approved Azure identity mode.",
            )
        )
    if require_live:
        if not config.azure_key_vault_enable_real_io:
            issues.append(
                _issue(
                    "azure_key_vault_real_io_disabled",
                    "AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true is required for live signing validation.",
                )
            )
        readiness = azure_key_vault_readiness_summary(config)
        if readiness["sdk_available"] is not True:
            issues.append(
                _issue(
                    "azure_key_vault_sdk_missing",
                    "azure-keyvault-keys and azure-identity are required for live signing validation.",
                )
            )
        issues.extend(
            validate_live_key_identifier(
                _key_identifier(config),
                allow_unsafe_override=unsafe_key_override_enabled(source),
            )
        )
    return issues


def build_key_vault_live_readiness_report(
    *,
    config: AuditManifestSigningConfig | None = None,
    env: Mapping[str, str] | None = None,
    live_sign_requested: bool = False,
) -> dict[str, Any]:
    source = env or os.environ
    active_config = config or audit_manifest_signing_config_from_settings()
    live_enabled = azure_key_vault_live_tests_enabled(source)
    require_live = live_enabled or live_sign_requested
    readiness = azure_key_vault_readiness_summary(active_config)
    issues = validate_key_vault_signing_config(active_config, env=source, require_live=require_live)
    lifecycle_config = (
        key_vault_lifecycle_config_from_settings(source)
        if env is not None
        else key_vault_lifecycle_config_from_settings()
    )
    lifecycle_summary = key_vault_lifecycle_readiness_summary(
        lifecycle_config,
        signing_config=active_config,
    )
    issues.extend(
        _issue(
            str(issue.get("code") or "azure_key_vault_lifecycle_incomplete"),
            str(issue.get("message") or "Azure Key Vault lifecycle readiness is incomplete."),
            severity=str(issue.get("severity") or "error"),
        )
        for issue in lifecycle_summary.get("blocking_issues", [])
        if isinstance(issue, Mapping)
    )
    issues.extend(
        _issue(
            str(issue.get("code") or "azure_key_vault_lifecycle_warning"),
            str(issue.get("message") or "Azure Key Vault lifecycle readiness warning."),
            severity="warning",
        )
        for issue in lifecycle_summary.get("warnings", [])
        if isinstance(issue, Mapping)
    )
    if live_sign_requested and not live_enabled:
        issues.append(
            _issue(
                "azure_key_vault_live_tests_disabled",
                f"{LIVE_TESTS_ENV}=true is required before live Key Vault signing can run.",
            )
        )
    warnings = [issue for issue in issues if issue.severity != "error"]
    errors = [issue for issue in issues if issue.severity == "error"]
    return {
        "mode": "live_sign" if live_sign_requested else "dry_run",
        "signing_readiness": readiness,
        "lifecycle_readiness": lifecycle_summary,
        "signing_mode": active_config.normalized_mode,
        "signing_required": active_config.required,
        "signature_algorithm": active_config.effective_algorithm or None,
        "signature_key_ref": active_config.key_ref or None,
        "real_io_enabled": bool(active_config.azure_key_vault_enable_real_io),
        "live_tests_enabled": live_enabled,
        "live_sign_requested": live_sign_requested,
        "live_test_env_var": LIVE_TESTS_ENV,
        "live_key_override_env_var": LIVE_KEY_OVERRIDE_ENV,
        "live_key_override_enabled": unsafe_key_override_enabled(source),
        "signing_attempted": False,
        "verification_attempted": False,
        "network_calls_performed": False,
        "ready_for_live_validation": live_enabled and not errors and readiness.get("real_io_ready") is True,
        "lifecycle_blocking_issues": lifecycle_summary.get("blocking_issues") or [],
        "lifecycle_warnings": lifecycle_summary.get("warnings") or [],
        "blocking_issues": [issue.__dict__ for issue in errors],
        "warnings": [issue.__dict__ for issue in warnings],
    }


def validation_result(report: Mapping[str, Any]) -> str:
    if report.get("blocking_issues"):
        return "blocked"
    if report.get("live_sign_requested") and not report.get("signing_attempted"):
        return "blocked"
    if report.get("verification_status") == "verified":
        return "live_sign_verified"
    if report.get("ready_for_live_validation") is True:
        return "ready_for_live_validation"
    return "dry_run_complete"


def _sensitive_field_name(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_FIELD_TOKENS)


def _sanitize_scalar(value: str) -> str:
    if SENSITIVE_VALUE_PATTERN.search(value):
        return "[redacted]"
    return value


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            if _sensitive_field_name(str(key)):
                continue
            sanitized[str(key)] = sanitize_payload(child)
        return sanitized
    if isinstance(value, list):
        return [sanitize_payload(child) for child in value]
    if isinstance(value, str):
        return _sanitize_scalar(value)
    return value


def build_key_vault_signing_evidence(
    report: Mapping[str, Any],
    *,
    environment_mode: str = "unknown",
    generated_at: str | None = None,
) -> dict[str, Any]:
    readiness = report.get("signing_readiness") or {}
    if not isinstance(readiness, Mapping):
        readiness = {}
    lifecycle_readiness = report.get("lifecycle_readiness") or {}
    if not isinstance(lifecycle_readiness, Mapping):
        lifecycle_readiness = {}
    blocking_issues = report.get("blocking_issues") or []
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "generated_at": generated_at or utc_evidence_timestamp(),
        "environment_mode": str(environment_mode or "unknown"),
        "signing_mode": report.get("signing_mode"),
        "signing_required": bool(report.get("signing_required")),
        "real_io_enabled": bool(report.get("real_io_enabled")),
        "live_tests_enabled": bool(report.get("live_tests_enabled")),
        "live_test_environment_variable": LIVE_TESTS_ENV,
        "live_sign_requested": bool(report.get("live_sign_requested")),
        "network_calls_performed": bool(report.get("network_calls_performed")),
        "signing_attempted": bool(report.get("signing_attempted")),
        "verification_attempted": bool(report.get("verification_attempted")),
        "vault_summary": {
            "vault_url_configured": bool(readiness.get("vault_url_configured")),
            "key_name_configured": bool(readiness.get("key_name_configured")),
            "key_name": readiness.get("key_name"),
            "key_version_configured": bool(readiness.get("key_version_configured")),
            "key_version": readiness.get("key_version"),
            "key_reference": readiness.get("signature_key_ref"),
        },
        "credential_mode_summary": {
            "configured": bool(readiness.get("credential_mode")),
            "mode": readiness.get("credential_mode"),
            "approved_identity_mode": bool(readiness.get("credential_mode_safe")),
        },
        "sdk_availability": {
            "sdk_available": bool(readiness.get("sdk_available")),
            "modules": readiness.get("sdk_modules") or {},
        },
        "lifecycle_summary": lifecycle_readiness,
        "algorithm": report.get("signature_algorithm"),
        "signing_readiness_status": (
            "ready" if not blocking_issues and readiness.get("metadata_ready") is True else "blocked"
        ),
        "verification_readiness_status": (
            "ready" if not blocking_issues and readiness.get("real_io_ready") is True else "pending_or_blocked"
        ),
        "blocking_issues": blocking_issues,
        "warnings": report.get("warnings") or [],
        "validation_result": validation_result(report),
        "data_safety_summary": {
            "contains_raw_credentials": False,
            "contains_key_material": False,
            "contains_phi_ephi": False,
            "sanitization": "whitelisted Key Vault signing readiness metadata only",
        },
    }
    return sanitize_payload(evidence)


def write_key_vault_signing_evidence(path: str | Path, evidence: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return target
