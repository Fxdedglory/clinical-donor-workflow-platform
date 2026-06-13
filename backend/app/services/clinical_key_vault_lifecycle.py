from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.services.clinical_audit_signing import AuditManifestSigningConfig

LIFECYCLE_SCHEMA_VERSION = "clinical.azure_key_vault.lifecycle_readiness.v1"

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
class KeyVaultLifecycleConfig:
    rotation_required: bool = False
    rotation_interval_days: int | None = None
    next_key_name: str = ""
    next_key_version: str = ""
    retirement_policy_required: bool = False
    retirement_policy_ref: str = ""
    access_log_review_required: bool = False
    access_log_review_ref: str = ""
    incident_recovery_required: bool = False
    incident_recovery_ref: str = ""


@dataclass(frozen=True)
class KeyVaultLifecycleIssue:
    code: str
    message: str
    severity: str = "error"


def _candidate_names(*names: str) -> list[str]:
    candidates: list[str] = []
    for name in names:
        for candidate in {name, name.lower(), name.upper()}:
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _get(source: Mapping[str, Any] | object, *names: str, default: Any = None) -> Any:
    for candidate in _candidate_names(*names):
        if isinstance(source, Mapping) and candidate in source:
            return source[candidate]
        attr_name = candidate.lower()
        if not isinstance(source, Mapping) and hasattr(source, attr_name):
            return getattr(source, attr_name)
    return default


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalized(value: Any) -> str:
    return _text(value).lower()


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    lowered = _normalized(value)
    if lowered in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if lowered in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    stripped = _text(value)
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def key_vault_lifecycle_config_from_settings(
    source: Mapping[str, Any] | object = settings,
) -> KeyVaultLifecycleConfig:
    return KeyVaultLifecycleConfig(
        rotation_required=_as_bool(
            _get(
                source,
                "audit_manifest_azure_key_vault_key_rotation_required",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED",
                default=False,
            )
        ),
        rotation_interval_days=_as_int(
            _get(
                source,
                "audit_manifest_azure_key_vault_rotation_interval_days",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS",
                default=None,
            )
        ),
        next_key_name=_text(
            _get(
                source,
                "audit_manifest_azure_key_vault_next_key_name",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME",
                default="",
            )
        ),
        next_key_version=_text(
            _get(
                source,
                "audit_manifest_azure_key_vault_next_key_version",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION",
                default="",
            )
        ),
        retirement_policy_required=_as_bool(
            _get(
                source,
                "audit_manifest_azure_key_vault_retirement_policy_required",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REQUIRED",
                default=False,
            )
        ),
        retirement_policy_ref=_text(
            _get(
                source,
                "audit_manifest_azure_key_vault_retirement_policy_ref",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF",
                default="",
            )
        ),
        access_log_review_required=_as_bool(
            _get(
                source,
                "audit_manifest_azure_key_vault_access_log_review_required",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED",
                default=False,
            )
        ),
        access_log_review_ref=_text(
            _get(
                source,
                "audit_manifest_azure_key_vault_access_log_review_ref",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF",
                default="",
            )
        ),
        incident_recovery_required=_as_bool(
            _get(
                source,
                "audit_manifest_azure_key_vault_incident_recovery_required",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED",
                default=False,
            )
        ),
        incident_recovery_ref=_text(
            _get(
                source,
                "audit_manifest_azure_key_vault_incident_recovery_ref",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF",
                default="",
            )
        ),
    )


def _issue(code: str, message: str, *, severity: str = "error") -> KeyVaultLifecycleIssue:
    return KeyVaultLifecycleIssue(code=code, message=message, severity=severity)


def validate_key_vault_lifecycle_config(
    config: KeyVaultLifecycleConfig,
) -> list[KeyVaultLifecycleIssue]:
    issues: list[KeyVaultLifecycleIssue] = []
    if config.rotation_required:
        if config.rotation_interval_days is None or config.rotation_interval_days <= 0:
            issues.append(
                _issue(
                    "audit_manifest_azure_key_vault_rotation_interval_missing",
                    "AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS must be a positive integer when Key Vault key rotation is required.",
                )
            )
        if not config.next_key_name or not config.next_key_version:
            issues.append(
                _issue(
                    "audit_manifest_azure_key_vault_next_key_reference_missing",
                    "AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME and AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION are required when Key Vault key rotation is required.",
                )
            )
    else:
        if config.rotation_interval_days is not None and config.rotation_interval_days < 0:
            issues.append(
                _issue(
                    "audit_manifest_azure_key_vault_rotation_interval_invalid",
                    "AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS should be positive when configured.",
                    severity="warning",
                )
            )
        if bool(config.next_key_name) != bool(config.next_key_version):
            issues.append(
                _issue(
                    "audit_manifest_azure_key_vault_next_key_reference_incomplete",
                    "Both next Key Vault key name and version should be configured together.",
                    severity="warning",
                )
            )
    if config.retirement_policy_required and not config.retirement_policy_ref:
        issues.append(
            _issue(
                "audit_manifest_azure_key_vault_retirement_policy_missing",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF is required when Key Vault retirement policy readiness is required.",
            )
        )
    if config.access_log_review_required and not config.access_log_review_ref:
        issues.append(
            _issue(
                "audit_manifest_azure_key_vault_access_log_review_missing",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF is required when Key Vault access-log review readiness is required.",
            )
        )
    if config.incident_recovery_required and not config.incident_recovery_ref:
        issues.append(
            _issue(
                "audit_manifest_azure_key_vault_incident_recovery_missing",
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF is required when Key Vault incident recovery readiness is required.",
            )
        )
    return issues


def _safe_reference_from_https_key_id(value: str) -> str:
    parsed = urlparse(value)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0].lower() == "keys":
        key_name = parts[1]
        key_version = parts[2] if len(parts) >= 3 else ""
        return _logical_key_reference(key_name, key_version)
    return ""


def _logical_key_reference(key_name: str, key_version: str = "") -> str:
    name = _text(key_name).strip("/")
    version = _text(key_version).strip("/")
    if not name:
        return ""
    if version:
        return f"keyvault://{name}/{version}"
    return f"keyvault://{name}"


def _safe_key_reference(value: str) -> str:
    reference = _text(value).split("?", 1)[0].split("#", 1)[0].strip("/")
    if not reference or SENSITIVE_VALUE_PATTERN.search(reference):
        return ""
    lowered = reference.lower()
    if lowered.startswith("https://"):
        return _safe_reference_from_https_key_id(reference)
    if lowered.startswith("keyvault://"):
        return reference
    return reference


def current_key_reference(signing_config: AuditManifestSigningConfig | None) -> str:
    if signing_config is None:
        return ""
    if signing_config.key_ref:
        key_ref = _safe_key_reference(signing_config.key_ref)
        if key_ref:
            return key_ref
    return _logical_key_reference(signing_config.azure_key_name, signing_config.azure_key_version)


def next_key_reference(config: KeyVaultLifecycleConfig) -> str:
    return _logical_key_reference(config.next_key_name, config.next_key_version)


def _requirement_status(required: bool, reference: str) -> str:
    if not required:
        return "not_required"
    if reference:
        return "documented"
    return "missing"


def key_vault_lifecycle_readiness_summary(
    config: KeyVaultLifecycleConfig,
    *,
    signing_config: AuditManifestSigningConfig | None = None,
) -> dict[str, Any]:
    issues = validate_key_vault_lifecycle_config(config)
    blocking_issues = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity != "error"]
    rotation_blocking_issues = [
        issue
        for issue in blocking_issues
        if issue.code in {
            "audit_manifest_azure_key_vault_rotation_interval_missing",
            "audit_manifest_azure_key_vault_next_key_reference_missing",
        }
    ]
    current_reference = current_key_reference(signing_config)
    next_reference = next_key_reference(config)
    if not config.rotation_required:
        rotation_status = "not_required"
    elif rotation_blocking_issues:
        rotation_status = "incomplete"
    else:
        rotation_status = "ready"
    summary = {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "rotation_required": bool(config.rotation_required),
        "rotation_interval_days": config.rotation_interval_days,
        "current_key_reference": current_reference or None,
        "next_key_reference": next_reference or None,
        "next_key_name_configured": bool(config.next_key_name),
        "next_key_version_configured": bool(config.next_key_version),
        "rotation_status": rotation_status,
        "retirement_policy_required": bool(config.retirement_policy_required),
        "retirement_policy_status": _requirement_status(
            config.retirement_policy_required,
            config.retirement_policy_ref,
        ),
        "retirement_policy_ref": config.retirement_policy_ref or None,
        "access_log_review_required": bool(config.access_log_review_required),
        "access_log_review_status": _requirement_status(
            config.access_log_review_required,
            config.access_log_review_ref,
        ),
        "access_log_review_ref": config.access_log_review_ref or None,
        "incident_recovery_required": bool(config.incident_recovery_required),
        "incident_recovery_status": _requirement_status(
            config.incident_recovery_required,
            config.incident_recovery_ref,
        ),
        "incident_recovery_ref": config.incident_recovery_ref or None,
        "blocking_issues": [issue.__dict__ for issue in blocking_issues],
        "warnings": [issue.__dict__ for issue in warnings],
        "data_safety_summary": {
            "contains_raw_credentials": False,
            "contains_key_material": False,
            "contains_phi_ephi": False,
            "sanitization": "Key Vault lifecycle metadata, logical key references, and runbook references only",
        },
    }
    return sanitize_key_vault_lifecycle_payload(summary)


def _sensitive_field_name(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_FIELD_TOKENS)


def _sanitize_scalar(value: str) -> str:
    if SENSITIVE_VALUE_PATTERN.search(value):
        return "[redacted]"
    return value


def sanitize_key_vault_lifecycle_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            if _sensitive_field_name(str(key)):
                continue
            sanitized[str(key)] = sanitize_key_vault_lifecycle_payload(child)
        return sanitized
    if isinstance(value, list):
        return [sanitize_key_vault_lifecycle_payload(child) for child in value]
    if isinstance(value, str):
        return _sanitize_scalar(value)
    return value
