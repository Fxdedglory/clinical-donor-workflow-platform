from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

SIGNING_MODE_DISABLED = "disabled"
SIGNING_MODE_CHECKSUM_PLACEHOLDER = "checksum_placeholder"
SIGNING_MODE_LOCAL_HMAC_SHA256 = "local_hmac_sha256"
SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER = "external_kms_placeholder"
SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER = "azure_key_vault_placeholder"

SIGNING_MODES = {
    SIGNING_MODE_DISABLED,
    SIGNING_MODE_CHECKSUM_PLACEHOLDER,
    SIGNING_MODE_LOCAL_HMAC_SHA256,
    SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER,
    SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER,
}
PROVIDER_PLACEHOLDER_SIGNING_MODES = {
    SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER,
    SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER,
}

SIGNATURE_STATUS_NOT_REQUIRED = "not_required"
SIGNATURE_STATUS_CHECKSUM_PLACEHOLDER = "checksum_placeholder"
SIGNATURE_STATUS_SIGNED = "signed"
SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE = "pending_provider_signature"
SIGNATURE_STATUS_FAILED = "signing_failed"
SIGNATURE_STATUS_UNSIGNED = "unsigned"

SIGNATURE_VERIFICATION_NOT_REQUIRED = "not_required"
SIGNATURE_VERIFICATION_VERIFIED = "verified"
SIGNATURE_VERIFICATION_FAILED = "failed"
SIGNATURE_VERIFICATION_MISSING = "missing_signature"
SIGNATURE_VERIFICATION_PENDING_PROVIDER = "pending_provider_verification"
SIGNATURE_VERIFICATION_NON_PRODUCTION_PLACEHOLDER = "non_production_placeholder"
SIGNATURE_VERIFICATION_UNSUPPORTED = "unsupported_signing_mode"

ALGORITHM_CHECKSUM_PLACEHOLDER = "sha256-placeholder"
ALGORITHM_LOCAL_HMAC_SHA256 = "hmac-sha256"
ALGORITHM_RSA_PSS_SHA256 = "rsa-pss-sha256"
ALGORITHM_ECDSA_P256_SHA256 = "ecdsa-p256-sha256"
SAFE_SIGNING_ALGORITHMS = {
    ALGORITHM_CHECKSUM_PLACEHOLDER,
    ALGORITHM_LOCAL_HMAC_SHA256,
    ALGORITHM_RSA_PSS_SHA256,
    ALGORITHM_ECDSA_P256_SHA256,
}
UNSAFE_SIGNING_ALGORITHMS = {"", "none", "disabled", "off", "md5", "sha1", "sha-1"}


@dataclass(frozen=True)
class AuditManifestSigningConfig:
    mode: str = SIGNING_MODE_DISABLED
    required: bool = False
    algorithm: str = ""
    key_ref: str = ""
    local_hmac_key: str = ""
    allow_local_signing_in_production: bool = False
    azure_key_vault_url: str = ""
    azure_key_name: str = ""
    azure_key_version: str = ""
    environment: str = "dev"

    @property
    def normalized_mode(self) -> str:
        value = _normalized(self.mode)
        return value if value else SIGNING_MODE_DISABLED

    @property
    def effective_algorithm(self) -> str:
        configured = _normalized(self.algorithm)
        if configured:
            return configured
        if self.normalized_mode == SIGNING_MODE_CHECKSUM_PLACEHOLDER:
            return ALGORITHM_CHECKSUM_PLACEHOLDER
        if self.normalized_mode == SIGNING_MODE_LOCAL_HMAC_SHA256:
            return ALGORITHM_LOCAL_HMAC_SHA256
        if self.normalized_mode in PROVIDER_PLACEHOLDER_SIGNING_MODES:
            return ALGORITHM_RSA_PSS_SHA256
        return ""


@dataclass(frozen=True)
class ManifestSignatureResult:
    status: str
    mode: str
    algorithm: str | None = None
    key_ref: str | None = None
    signature: str | None = None
    reason: str | None = None


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


def canonical_signing_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def signing_payload_for_manifest(
    *,
    manifest_checksum: str,
    mode: str,
    algorithm: str,
    key_ref: str,
) -> dict[str, str]:
    return {
        "manifest_checksum": manifest_checksum,
        "signing_mode": _normalized(mode),
        "signature_algorithm": _normalized(algorithm),
        "signature_key_ref": key_ref,
    }


def audit_manifest_signing_config_from_settings(source: Any = settings) -> AuditManifestSigningConfig:
    legacy_required = _as_bool(getattr(source, "audit_object_mirror_signature_required", False))
    signing_required = _as_bool(getattr(source, "audit_manifest_signing_required", False)) or legacy_required
    configured_mode = _normalized(getattr(source, "audit_manifest_signing_mode", ""))
    legacy_algorithm = _text(
        getattr(source, "audit_object_mirror_signature_algorithm", ALGORITHM_CHECKSUM_PLACEHOLDER)
    )
    if not configured_mode and legacy_required:
        configured_mode = _mode_from_legacy_algorithm(legacy_algorithm)
    algorithm = _text(getattr(source, "audit_manifest_signing_algorithm", "")) or legacy_algorithm
    key_ref = _text(getattr(source, "audit_manifest_signing_key_ref", "")) or _text(
        getattr(source, "audit_object_mirror_signature_key_ref", "")
    )
    environment = _text(
        getattr(source, "app_env", "")
        or getattr(source, "environment", "")
        or getattr(source, "clinical_env", "")
        or "dev"
    )
    return AuditManifestSigningConfig(
        mode=configured_mode or SIGNING_MODE_DISABLED,
        required=signing_required,
        algorithm=algorithm,
        key_ref=key_ref,
        local_hmac_key=_text(getattr(source, "audit_manifest_local_hmac_key", "")),
        allow_local_signing_in_production=_as_bool(
            getattr(source, "audit_manifest_allow_local_signing_in_production", False)
        ),
        azure_key_vault_url=_text(getattr(source, "audit_manifest_azure_key_vault_url", "")),
        azure_key_name=_text(getattr(source, "audit_manifest_azure_key_name", "")),
        azure_key_version=_text(getattr(source, "audit_manifest_azure_key_version", "")),
        environment=environment,
    )


def _mode_from_legacy_algorithm(algorithm: str) -> str:
    normalized = _normalized(algorithm)
    if normalized in {"", ALGORITHM_CHECKSUM_PLACEHOLDER, SIGNING_MODE_CHECKSUM_PLACEHOLDER}:
        return SIGNING_MODE_CHECKSUM_PLACEHOLDER
    if normalized in {ALGORITHM_LOCAL_HMAC_SHA256, SIGNING_MODE_LOCAL_HMAC_SHA256}:
        return SIGNING_MODE_LOCAL_HMAC_SHA256
    return SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER


def _checksum_placeholder_signature(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_signing_payload(payload).encode("utf-8")).hexdigest()
    return f"placeholder:{digest}"


def _local_hmac_signature(payload: dict[str, Any], key: str) -> str:
    digest = hmac.new(
        key.encode("utf-8"),
        canonical_signing_payload(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"hmac-sha256:{digest}"


def sign_manifest_checksum(
    manifest_checksum: str,
    config: AuditManifestSigningConfig,
) -> ManifestSignatureResult:
    mode = config.normalized_mode
    algorithm = config.effective_algorithm
    key_ref = config.key_ref or None
    if not config.required and mode == SIGNING_MODE_DISABLED:
        return ManifestSignatureResult(status=SIGNATURE_STATUS_NOT_REQUIRED, mode=mode)
    if mode == SIGNING_MODE_DISABLED:
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_UNSIGNED,
            mode=mode,
            algorithm=algorithm or None,
            key_ref=key_ref,
            reason="Manifest signing is required but signing mode is disabled.",
        )
    payload = signing_payload_for_manifest(
        manifest_checksum=manifest_checksum,
        mode=mode,
        algorithm=algorithm,
        key_ref=config.key_ref,
    )
    if mode == SIGNING_MODE_CHECKSUM_PLACEHOLDER:
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_CHECKSUM_PLACEHOLDER,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref,
            signature=_checksum_placeholder_signature(payload),
            reason="Checksum placeholder is deterministic but not a cryptographic signature.",
        )
    if mode == SIGNING_MODE_LOCAL_HMAC_SHA256:
        if not config.local_hmac_key:
            return ManifestSignatureResult(
                status=SIGNATURE_STATUS_FAILED,
                mode=mode,
                algorithm=algorithm,
                key_ref=key_ref,
                reason="AUDIT_MANIFEST_LOCAL_HMAC_KEY is required for local HMAC signing.",
            )
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_SIGNED,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref,
            signature=_local_hmac_signature(payload, config.local_hmac_key),
        )
    if mode in PROVIDER_PLACEHOLDER_SIGNING_MODES:
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref,
            reason="External signing provider placeholder does not perform network calls.",
        )
    return ManifestSignatureResult(
        status=SIGNATURE_STATUS_FAILED,
        mode=mode,
        algorithm=algorithm or None,
        key_ref=key_ref,
        reason=f"Unsupported manifest signing mode: {mode}.",
    )


def signature_status_for_config(config: AuditManifestSigningConfig) -> str:
    mode = config.normalized_mode
    if not config.required and mode == SIGNING_MODE_DISABLED:
        return SIGNATURE_STATUS_NOT_REQUIRED
    if mode == SIGNING_MODE_DISABLED:
        return SIGNATURE_STATUS_UNSIGNED
    if mode == SIGNING_MODE_CHECKSUM_PLACEHOLDER:
        return SIGNATURE_STATUS_CHECKSUM_PLACEHOLDER
    if mode == SIGNING_MODE_LOCAL_HMAC_SHA256:
        if not config.local_hmac_key:
            return SIGNATURE_STATUS_FAILED
        return SIGNATURE_STATUS_SIGNED
    if mode in PROVIDER_PLACEHOLDER_SIGNING_MODES:
        return SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE
    return SIGNATURE_STATUS_FAILED


def verify_manifest_signature(
    *,
    manifest_checksum: str,
    signature: str | None,
    config: AuditManifestSigningConfig,
) -> dict[str, Any]:
    mode = config.normalized_mode
    algorithm = config.effective_algorithm
    if not config.required and mode == SIGNING_MODE_DISABLED:
        return {
            "signature_verification_status": SIGNATURE_VERIFICATION_NOT_REQUIRED,
            "signing_mode": mode,
            "signature_algorithm": None,
            "signature_key_ref": None,
            "verified": True,
            "reason": None,
        }
    if mode == SIGNING_MODE_DISABLED:
        return _verification_result(
            SIGNATURE_VERIFICATION_MISSING,
            config=config,
            verified=False,
            reason="Manifest signing is required but signing mode is disabled.",
        )
    if mode == SIGNING_MODE_CHECKSUM_PLACEHOLDER:
        payload = signing_payload_for_manifest(
            manifest_checksum=manifest_checksum,
            mode=mode,
            algorithm=algorithm,
            key_ref=config.key_ref,
        )
        expected = _checksum_placeholder_signature(payload)
        return _verification_result(
            SIGNATURE_VERIFICATION_NON_PRODUCTION_PLACEHOLDER
            if signature == expected
            else SIGNATURE_VERIFICATION_FAILED,
            config=config,
            verified=signature == expected,
            reason="Checksum placeholder is non-production evidence, not cryptographic signing.",
        )
    if mode == SIGNING_MODE_LOCAL_HMAC_SHA256:
        if not signature:
            return _verification_result(
                SIGNATURE_VERIFICATION_MISSING,
                config=config,
                verified=False,
                reason="Manifest signature is missing.",
            )
        if not config.local_hmac_key:
            return _verification_result(
                SIGNATURE_VERIFICATION_FAILED,
                config=config,
                verified=False,
                reason="Local HMAC verification requires AUDIT_MANIFEST_LOCAL_HMAC_KEY.",
            )
        payload = signing_payload_for_manifest(
            manifest_checksum=manifest_checksum,
            mode=mode,
            algorithm=algorithm,
            key_ref=config.key_ref,
        )
        expected = _local_hmac_signature(payload, config.local_hmac_key)
        return _verification_result(
            SIGNATURE_VERIFICATION_VERIFIED if hmac.compare_digest(signature, expected) else SIGNATURE_VERIFICATION_FAILED,
            config=config,
            verified=hmac.compare_digest(signature, expected),
            reason=None if hmac.compare_digest(signature, expected) else "Manifest HMAC signature mismatch.",
        )
    if mode in PROVIDER_PLACEHOLDER_SIGNING_MODES:
        return _verification_result(
            SIGNATURE_VERIFICATION_PENDING_PROVIDER,
            config=config,
            verified=False,
            reason="Provider placeholder verification must be completed outside this repository.",
        )
    return _verification_result(
        SIGNATURE_VERIFICATION_UNSUPPORTED,
        config=config,
        verified=False,
        reason=f"Unsupported manifest signing mode: {mode}.",
    )


def _verification_result(
    status: str,
    *,
    config: AuditManifestSigningConfig,
    verified: bool,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "signature_verification_status": status,
        "signing_mode": config.normalized_mode,
        "signature_algorithm": config.effective_algorithm or None,
        "signature_key_ref": config.key_ref or None,
        "verified": verified,
        "reason": reason,
    }


def signing_evidence_summary(
    config: AuditManifestSigningConfig,
    *,
    signature_verification_status: str | None = None,
) -> dict[str, Any]:
    return {
        "manifest_signing_mode": config.normalized_mode,
        "signing_required": config.required,
        "signature_algorithm": config.effective_algorithm or None,
        "signature_key_ref": config.key_ref or None,
        "signature_verification_status": signature_verification_status or "not_checked_no_manifest",
        "local_signing_material_configured": bool(config.local_hmac_key),
        "azure_key_vault_url_configured": bool(config.azure_key_vault_url),
        "azure_signing_key_name_configured": bool(config.azure_key_name),
        "azure_signing_key_version_configured": bool(config.azure_key_version),
    }
