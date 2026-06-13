from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.clinical_audit_mirror_providers import SAFE_AZURE_CREDENTIAL_MODES
from app.services.clinical_audit_signing import (
    AuditManifestSigningConfig,
    audit_manifest_signing_config_from_settings,
    signing_evidence_summary,
)
from app.services.clinical_azure_worm_live_readiness import (
    LIVE_TEST_PREFIX_ENV,
    LIVE_TEST_PREFIX_OVERRIDE_ENV,
    LIVE_TESTS_ENV,
)

EVIDENCE_SCHEMA_VERSION = "clinical.azure_worm.validation_evidence.v1"

SENSITIVE_FIELD_TOKENS = (
    "account_key",
    "api_key",
    "client_secret",
    "connection_string",
    "password",
    "private_key",
    "sas_token",
    "secret",
    "shared_key",
    "signature_key_material",
    "token",
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)("
    r"accountkey=|sharedaccesssignature|sig=|password=|secret=|token=|client_secret=|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r")"
)


def utc_evidence_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _configured(value: Any) -> bool:
    return bool(str(value or "").strip())


def _safe_issue(issue: Mapping[str, Any]) -> dict[str, str]:
    return {
        "code": str(issue.get("code") or "unknown"),
        "severity": str(issue.get("severity") or "error"),
        "message": _sanitize_scalar(str(issue.get("message") or "")),
    }


def _sensitive_field_name(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_FIELD_TOKENS)


def _sanitize_scalar(value: str) -> str:
    if SENSITIVE_VALUE_PATTERN.search(value):
        return "[redacted]"
    return value


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            if _sensitive_field_name(str(key)):
                continue
            sanitized[str(key)] = _sanitize_payload(child)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_payload(child) for child in value]
    if isinstance(value, str):
        return _sanitize_scalar(value)
    return value


def _issue_list(*groups: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        for issue in group:
            if isinstance(issue, Mapping):
                issues.append(_safe_issue(issue))
    return issues


def _validation_result(report: Mapping[str, Any], blocking_issues: list[dict[str, str]]) -> str:
    readiness = report.get("provider_readiness") or {}
    if blocking_issues:
        return "blocked"
    if report.get("live_write_requested") and not report.get("upload_attempted"):
        return "blocked"
    live_write = report.get("live_write") or {}
    if isinstance(live_write, Mapping) and live_write.get("verification_status") == "verified":
        return "live_write_verified"
    if readiness.get("ready") is True and report.get("live_tests_enabled") is True:
        return "ready_for_live_validation"
    if readiness.get("ready") is True:
        return "dry_run_complete"
    return "blocked"


def _prefix_safety(
    report: Mapping[str, Any],
    blocking_issues: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    prefix = str(report.get("live_test_prefix") or "").strip()
    prefix_codes = {
        issue["code"]
        for issue in [*blocking_issues, *warnings]
        if issue["code"].startswith("azure_live_test_prefix")
    }
    if "azure_live_test_prefix_missing" in prefix_codes:
        status = "not_configured"
    elif "azure_live_test_prefix_not_dedicated" in prefix_codes or "azure_live_test_prefix_invalid" in prefix_codes:
        status = "blocked"
    elif "azure_live_test_prefix_override" in prefix_codes:
        status = "override_warning"
    elif prefix:
        status = "dedicated_prefix_configured"
    else:
        status = "not_configured"
    return {
        "environment_variable": LIVE_TEST_PREFIX_ENV,
        "configured": bool(prefix),
        "prefix": prefix,
        "override_environment_variable": LIVE_TEST_PREFIX_OVERRIDE_ENV,
        "override_enabled": bool(report.get("live_test_prefix_override_enabled")),
        "status": status,
        "issue_codes": sorted(prefix_codes),
    }


def build_validation_evidence(
    report: Mapping[str, Any],
    *,
    environment_mode: str = "unknown",
    signing_config: AuditManifestSigningConfig | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    readiness = report.get("provider_readiness") or {}
    if not isinstance(readiness, Mapping):
        readiness = {}
    azure = readiness.get("azure") or {}
    if not isinstance(azure, Mapping):
        azure = {}
    capabilities = readiness.get("capabilities") or {}
    if not isinstance(capabilities, Mapping):
        capabilities = {}

    blocking_issues = _issue_list(report.get("blocking_issues"), readiness.get("validation_errors"))
    warnings = _issue_list(report.get("warnings"), readiness.get("validation_warnings"))
    provider = str(readiness.get("provider") or "unknown")
    auth_mode = str(azure.get("credential_mode") or "").strip()
    immutability_policy_missing = any(
        issue["code"] == "azure_immutability_policy_missing" for issue in blocking_issues
    )
    legal_hold_reference_missing = any(
        issue["code"] == "azure_legal_hold_reference_missing" for issue in blocking_issues
    )

    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "generated_at": generated_at or utc_evidence_timestamp(),
        "environment_mode": str(environment_mode or "unknown"),
        "provider": provider,
        "provider_mode": str(readiness.get("provider_mode") or "unknown"),
        "real_io_enabled": bool(report.get("real_io_enabled")),
        "live_tests_enabled": bool(report.get("live_tests_enabled")),
        "live_tests_environment_variable": LIVE_TESTS_ENV,
        "live_write_requested": bool(report.get("live_write_requested")),
        "upload_attempted": bool(report.get("upload_attempted")),
        "network_calls_performed": bool(report.get("network_calls_performed")),
        "storage_readiness_summary": {
            "account_url_configured": bool(azure.get("account_url_configured")),
            "container_configured": _configured(azure.get("container")),
            "container": str(azure.get("container") or ""),
            "prefix_configured": _configured(azure.get("prefix")),
            "prefix": str(azure.get("prefix") or ""),
            "expected_uri_prefix_available": _configured(readiness.get("expected_uri_prefix")),
        },
        "prefix_safety_status": _prefix_safety(report, blocking_issues, warnings),
        "credential_mode_summary": {
            "configured": bool(auth_mode),
            "mode": auth_mode,
            "approved_identity_mode": auth_mode.lower() in SAFE_AZURE_CREDENTIAL_MODES,
        },
        "immutability_requirement_summary": {
            "required": bool(azure.get("immutability_required")),
            "retention_policy_reference_configured": bool(azure.get("immutability_required"))
            and not immutability_policy_missing,
            "provider_claims_support": bool(capabilities.get("supports_immutability")),
        },
        "legal_hold_requirement_summary": {
            "required": bool(azure.get("legal_hold_required")),
            "legal_hold_reference_configured": bool(azure.get("legal_hold_required"))
            and not legal_hold_reference_missing,
            "provider_claims_support": bool(capabilities.get("supports_legal_hold")),
        },
        "checksum_validation_summary": {
            "required": bool(azure.get("checksum_validation_required")),
            "operation_supported": bool(capabilities.get("verify_object_checksum")),
            "validated_in_live_write": (
                isinstance(report.get("live_write"), Mapping)
                and report["live_write"].get("verification_status") == "verified"
            ),
        },
        "manifest_signing_summary": signing_evidence_summary(
            signing_config or audit_manifest_signing_config_from_settings()
        ),
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "validation_result": _validation_result(report, blocking_issues),
        "data_safety_summary": {
            "contains_raw_credentials": False,
            "contains_phi_ephi": False,
            "sanitization": "whitelisted operational readiness fields only",
        },
    }
    return _sanitize_payload(evidence)


def write_validation_evidence(path: str | Path, evidence: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return target
