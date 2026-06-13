from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import importlib
import importlib.util
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

SIGNING_MODE_DISABLED = "disabled"
SIGNING_MODE_CHECKSUM_PLACEHOLDER = "checksum_placeholder"
SIGNING_MODE_LOCAL_HMAC_SHA256 = "local_hmac_sha256"
SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER = "external_kms_placeholder"
SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER = "azure_key_vault_placeholder"
SIGNING_MODE_AZURE_KEY_VAULT = "azure_key_vault"

SIGNING_MODES = {
    SIGNING_MODE_DISABLED,
    SIGNING_MODE_CHECKSUM_PLACEHOLDER,
    SIGNING_MODE_LOCAL_HMAC_SHA256,
    SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER,
    SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER,
    SIGNING_MODE_AZURE_KEY_VAULT,
}
PROVIDER_PLACEHOLDER_SIGNING_MODES = {
    SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER,
    SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER,
}
AZURE_KEY_VAULT_SIGNING_MODES = {
    SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER,
    SIGNING_MODE_AZURE_KEY_VAULT,
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
AZURE_KEY_VAULT_SIGNATURE_PREFIX = "azure-key-vault:"
AZURE_KEY_VAULT_SDK_ALGORITHM_MAP = {
    ALGORITHM_RSA_PSS_SHA256: "PS256",
    ALGORITHM_ECDSA_P256_SHA256: "ES256",
}
SAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES = {
    "managed_identity",
    "workload_identity",
    "default_azure_credential",
    "entra_id",
    "azure_identity",
    "azure_cli",
}
UNSAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES = {
    "",
    "account_key",
    "account-key",
    "client_secret",
    "client-secret",
    "connection_string",
    "connection-string",
    "inline_secret",
    "plain_secret",
    "sas_token",
    "shared_key",
    "shared-key",
}

AzureKeyVaultClientFactory = Callable[["AuditManifestSigningConfig"], Any]


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
    azure_key_vault_credential_mode: str = ""
    azure_key_vault_enable_real_io: bool = False
    azure_key_vault_require_hsm: bool = False
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
        if self.normalized_mode in PROVIDER_PLACEHOLDER_SIGNING_MODES | {SIGNING_MODE_AZURE_KEY_VAULT}:
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
        azure_key_vault_credential_mode=_text(
            getattr(source, "audit_manifest_azure_key_vault_credential_mode", "")
        ),
        azure_key_vault_enable_real_io=_as_bool(
            getattr(source, "audit_manifest_azure_key_vault_enable_real_io", False)
        ),
        azure_key_vault_require_hsm=_as_bool(
            getattr(source, "audit_manifest_azure_key_vault_require_hsm", False)
        ),
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


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def azure_key_vault_sdk_availability() -> dict[str, bool]:
    crypto_available = _module_available("azure.keyvault.keys.crypto")
    identity_available = _module_available("azure.identity")
    return {
        "azure_keyvault_keys_crypto": crypto_available,
        "azure_identity": identity_available,
        "available": crypto_available and identity_available,
    }


def azure_key_vault_key_id(config: AuditManifestSigningConfig) -> str:
    vault_url = config.azure_key_vault_url.rstrip("/")
    key_name = config.azure_key_name.strip("/")
    if vault_url and key_name:
        key_id = f"{vault_url}/keys/{key_name}"
        if config.azure_key_version:
            key_id = f"{key_id}/{config.azure_key_version.strip('/')}"
        return key_id
    if config.key_ref.startswith("https://"):
        return config.key_ref
    return ""


def azure_key_vault_key_reference(config: AuditManifestSigningConfig) -> str:
    if config.key_ref:
        return config.key_ref
    return azure_key_vault_key_id(config)


def _azure_sdk_algorithm(algorithm: str) -> str:
    normalized = _normalized(algorithm)
    if normalized not in AZURE_KEY_VAULT_SDK_ALGORITHM_MAP:
        raise RuntimeError(
            "AUDIT_MANIFEST_SIGNING_ALGORITHM must be rsa-pss-sha256 or ecdsa-p256-sha256 "
            "for Azure Key Vault signing."
        )
    return AZURE_KEY_VAULT_SDK_ALGORITHM_MAP[normalized]


def _payload_digest(payload: dict[str, Any]) -> bytes:
    return hashlib.sha256(canonical_signing_payload(payload).encode("utf-8")).digest()


def _signature_bytes(raw: Any) -> bytes:
    value = raw
    if isinstance(raw, dict):
        value = raw.get("signature")
    elif hasattr(raw, "signature"):
        value = raw.signature
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        try:
            return base64.b64decode(value.encode("ascii"), validate=True)
        except (binascii.Error, UnicodeEncodeError) as exc:
            raise RuntimeError("Azure Key Vault signing client returned an invalid signature string.") from exc
    raise RuntimeError("Azure Key Vault signing client did not return signature bytes.")


def _verification_is_valid(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, dict):
        return bool(raw.get("is_valid", raw.get("valid", raw.get("verified", False))))
    if hasattr(raw, "is_valid"):
        return bool(raw.is_valid)
    if hasattr(raw, "valid"):
        return bool(raw.valid)
    if hasattr(raw, "verified"):
        return bool(raw.verified)
    return False


def _encode_azure_signature(signature: bytes) -> str:
    encoded = base64.b64encode(signature).decode("ascii")
    return f"{AZURE_KEY_VAULT_SIGNATURE_PREFIX}{encoded}"


def _decode_azure_signature(signature: str | None) -> bytes:
    if not signature:
        raise RuntimeError("Manifest signature is missing.")
    if not signature.startswith(AZURE_KEY_VAULT_SIGNATURE_PREFIX):
        raise RuntimeError("Manifest signature is not an Azure Key Vault signature.")
    encoded = signature[len(AZURE_KEY_VAULT_SIGNATURE_PREFIX) :]
    try:
        return base64.b64decode(encoded.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise RuntimeError("Manifest Azure Key Vault signature encoding is invalid.") from exc


def _azure_key_vault_config_errors(config: AuditManifestSigningConfig, *, require_real_io: bool) -> list[str]:
    errors: list[str] = []
    algorithm = config.effective_algorithm
    if algorithm not in AZURE_KEY_VAULT_SDK_ALGORITHM_MAP:
        errors.append(
            "AUDIT_MANIFEST_SIGNING_ALGORITHM must be rsa-pss-sha256 or ecdsa-p256-sha256 "
            "for Azure Key Vault signing."
        )
    if not config.azure_key_vault_url:
        errors.append("AUDIT_MANIFEST_AZURE_KEY_VAULT_URL is required for Azure Key Vault signing.")
    if not config.azure_key_name:
        errors.append("AUDIT_MANIFEST_AZURE_KEY_NAME is required for Azure Key Vault signing.")
    if not azure_key_vault_key_reference(config):
        errors.append("AUDIT_MANIFEST_SIGNING_KEY_REF is required for Azure Key Vault signing.")
    if require_real_io:
        credential_mode = _normalized(config.azure_key_vault_credential_mode)
        if credential_mode in UNSAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES:
            errors.append(
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE must use a non-secret Azure identity mode."
            )
        elif credential_mode not in SAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES:
            errors.append(
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE is not an approved Azure identity mode."
            )
    return errors


class AzureKeyVaultSigningClient:
    """Small Azure SDK wrapper kept behind the manifest signing boundary."""

    def __init__(self, *, key_id: str, credential_mode: str, crypto_client: Any | None = None) -> None:
        self.key_id = key_id
        self.credential_mode = credential_mode
        self._crypto_client = crypto_client or self._build_crypto_client(key_id, credential_mode)

    @classmethod
    def from_config(cls, config: AuditManifestSigningConfig) -> AzureKeyVaultSigningClient:
        key_id = azure_key_vault_key_id(config)
        if not key_id:
            raise RuntimeError(
                "AUDIT_MANIFEST_AZURE_KEY_VAULT_URL and AUDIT_MANIFEST_AZURE_KEY_NAME "
                "are required before Azure Key Vault real I/O can be enabled."
            )
        return cls(key_id=key_id, credential_mode=config.azure_key_vault_credential_mode)

    @staticmethod
    def _credential_for_mode(credential_mode: str) -> Any:
        normalized = _normalized(credential_mode)
        if normalized not in SAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES:
            raise RuntimeError(
                "Azure Key Vault real I/O requires AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE "
                "to be managed_identity, workload_identity, default_azure_credential, entra_id, "
                "azure_identity, or azure_cli."
            )
        try:
            identity = importlib.import_module("azure.identity")
        except ImportError as exc:
            raise RuntimeError(
                "azure-identity is required when AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true."
            ) from exc
        return identity.DefaultAzureCredential(exclude_interactive_browser_credential=True)

    @classmethod
    def _build_crypto_client(cls, key_id: str, credential_mode: str) -> Any:
        try:
            crypto = importlib.import_module("azure.keyvault.keys.crypto")
        except ImportError as exc:
            raise RuntimeError(
                "azure-keyvault-keys is required when AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true."
            ) from exc
        return crypto.CryptographyClient(
            key_id,
            credential=cls._credential_for_mode(credential_mode),
        )

    def sign(self, algorithm: str, digest: bytes) -> bytes:
        return _signature_bytes(self._crypto_client.sign(_azure_sdk_algorithm(algorithm), digest))

    def verify(self, algorithm: str, digest: bytes, signature: bytes) -> bool:
        return _verification_is_valid(
            self._crypto_client.verify(_azure_sdk_algorithm(algorithm), digest, signature)
        )


def _azure_key_vault_client(
    config: AuditManifestSigningConfig,
    *,
    signing_client: Any | None = None,
    signing_client_factory: AzureKeyVaultClientFactory | None = None,
) -> Any:
    if signing_client is not None:
        return signing_client
    if signing_client_factory is not None:
        return signing_client_factory(config)
    return AzureKeyVaultSigningClient.from_config(config)


def sign_manifest_payload(
    payload: dict[str, Any],
    config: AuditManifestSigningConfig,
    *,
    signing_client: Any | None = None,
    signing_client_factory: AzureKeyVaultClientFactory | None = None,
) -> ManifestSignatureResult:
    mode = config.normalized_mode
    algorithm = config.effective_algorithm
    key_ref = azure_key_vault_key_reference(config) if mode in AZURE_KEY_VAULT_SIGNING_MODES else config.key_ref
    key_ref_result = key_ref or None
    if not config.required and mode == SIGNING_MODE_DISABLED:
        return ManifestSignatureResult(status=SIGNATURE_STATUS_NOT_REQUIRED, mode=mode)
    if mode == SIGNING_MODE_DISABLED:
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_UNSIGNED,
            mode=mode,
            algorithm=algorithm or None,
            key_ref=key_ref_result,
            reason="Manifest signing is required but signing mode is disabled.",
        )
    if mode == SIGNING_MODE_CHECKSUM_PLACEHOLDER:
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_CHECKSUM_PLACEHOLDER,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref_result,
            signature=_checksum_placeholder_signature(payload),
            reason="Checksum placeholder is deterministic but not a cryptographic signature.",
        )
    if mode == SIGNING_MODE_LOCAL_HMAC_SHA256:
        if not config.local_hmac_key:
            return ManifestSignatureResult(
                status=SIGNATURE_STATUS_FAILED,
                mode=mode,
                algorithm=algorithm,
                key_ref=key_ref_result,
                reason="AUDIT_MANIFEST_LOCAL_HMAC_KEY is required for local HMAC signing.",
            )
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_SIGNED,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref_result,
            signature=_local_hmac_signature(payload, config.local_hmac_key),
        )
    if mode == SIGNING_MODE_AZURE_KEY_VAULT:
        if not config.azure_key_vault_enable_real_io:
            return ManifestSignatureResult(
                status=SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE,
                mode=mode,
                algorithm=algorithm,
                key_ref=key_ref_result,
                reason="Azure Key Vault signing real I/O is disabled.",
            )
        config_errors = _azure_key_vault_config_errors(config, require_real_io=True)
        if config_errors:
            return ManifestSignatureResult(
                status=SIGNATURE_STATUS_FAILED,
                mode=mode,
                algorithm=algorithm,
                key_ref=key_ref_result,
                reason=" ".join(config_errors),
            )
        try:
            client = _azure_key_vault_client(
                config,
                signing_client=signing_client,
                signing_client_factory=signing_client_factory,
            )
            signature = client.sign(algorithm, _payload_digest(payload))
        except Exception as exc:
            return ManifestSignatureResult(
                status=SIGNATURE_STATUS_FAILED,
                mode=mode,
                algorithm=algorithm,
                key_ref=key_ref_result,
                reason=str(exc),
            )
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_SIGNED,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref_result,
            signature=_encode_azure_signature(_signature_bytes(signature)),
        )
    if mode in PROVIDER_PLACEHOLDER_SIGNING_MODES:
        return ManifestSignatureResult(
            status=SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE,
            mode=mode,
            algorithm=algorithm,
            key_ref=key_ref_result,
            reason="External signing provider placeholder does not perform network calls.",
        )
    return ManifestSignatureResult(
        status=SIGNATURE_STATUS_FAILED,
        mode=mode,
        algorithm=algorithm or None,
        key_ref=key_ref_result,
        reason=f"Unsupported manifest signing mode: {mode}.",
    )


def sign_manifest_checksum(
    manifest_checksum: str,
    config: AuditManifestSigningConfig,
    *,
    signing_client: Any | None = None,
    signing_client_factory: AzureKeyVaultClientFactory | None = None,
) -> ManifestSignatureResult:
    payload = signing_payload_for_manifest(
        manifest_checksum=manifest_checksum,
        mode=config.normalized_mode,
        algorithm=config.effective_algorithm,
        key_ref=azure_key_vault_key_reference(config)
        if config.normalized_mode in AZURE_KEY_VAULT_SIGNING_MODES
        else config.key_ref,
    )
    return sign_manifest_payload(
        payload,
        config,
        signing_client=signing_client,
        signing_client_factory=signing_client_factory,
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
    if mode == SIGNING_MODE_AZURE_KEY_VAULT:
        if not config.azure_key_vault_enable_real_io:
            return SIGNATURE_STATUS_PENDING_PROVIDER_SIGNATURE
        if _azure_key_vault_config_errors(config, require_real_io=True):
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
    signing_client: Any | None = None,
    signing_client_factory: AzureKeyVaultClientFactory | None = None,
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
    if mode == SIGNING_MODE_AZURE_KEY_VAULT:
        if not signature:
            return _verification_result(
                SIGNATURE_VERIFICATION_MISSING,
                config=config,
                verified=False,
                reason="Manifest signature is missing.",
            )
        if not config.azure_key_vault_enable_real_io:
            return _verification_result(
                SIGNATURE_VERIFICATION_PENDING_PROVIDER,
                config=config,
                verified=False,
                reason="Azure Key Vault signature verification real I/O is disabled.",
            )
        config_errors = _azure_key_vault_config_errors(config, require_real_io=True)
        if config_errors:
            return _verification_result(
                SIGNATURE_VERIFICATION_FAILED,
                config=config,
                verified=False,
                reason=" ".join(config_errors),
            )
        payload = signing_payload_for_manifest(
            manifest_checksum=manifest_checksum,
            mode=mode,
            algorithm=algorithm,
            key_ref=azure_key_vault_key_reference(config),
        )
        try:
            signature_bytes = _decode_azure_signature(signature)
            client = _azure_key_vault_client(
                config,
                signing_client=signing_client,
                signing_client_factory=signing_client_factory,
            )
            verified = bool(client.verify(algorithm, _payload_digest(payload), signature_bytes))
        except Exception as exc:
            return _verification_result(
                SIGNATURE_VERIFICATION_FAILED,
                config=config,
                verified=False,
                reason=str(exc),
            )
        return _verification_result(
            SIGNATURE_VERIFICATION_VERIFIED if verified else SIGNATURE_VERIFICATION_FAILED,
            config=config,
            verified=verified,
            reason=None if verified else "Azure Key Vault signature verification failed.",
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
    key_ref = (
        azure_key_vault_key_reference(config)
        if config.normalized_mode in AZURE_KEY_VAULT_SIGNING_MODES
        else config.key_ref
    )
    return {
        "signature_verification_status": status,
        "signing_mode": config.normalized_mode,
        "signature_algorithm": config.effective_algorithm or None,
        "signature_key_ref": key_ref or None,
        "verified": verified,
        "reason": reason,
    }


def azure_key_vault_readiness_summary(
    config: AuditManifestSigningConfig,
    *,
    signing_client: Any | None = None,
) -> dict[str, Any]:
    azure_selected = config.normalized_mode in AZURE_KEY_VAULT_SIGNING_MODES or any(
        (
            config.azure_key_vault_url,
            config.azure_key_name,
            config.azure_key_version,
            config.azure_key_vault_credential_mode,
            config.azure_key_vault_enable_real_io,
            config.azure_key_vault_require_hsm,
        )
    )
    sdk = azure_key_vault_sdk_availability()
    credential_mode = _normalized(config.azure_key_vault_credential_mode)
    metadata_errors = _azure_key_vault_config_errors(config, require_real_io=False) if azure_selected else []
    credential_safe = credential_mode in SAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES
    algorithm_supported = config.effective_algorithm in AZURE_KEY_VAULT_SDK_ALGORITHM_MAP
    sdk_available = bool(sdk["available"])
    sdk_or_fake_available = sdk_available or signing_client is not None
    real_io_ready = (
        config.azure_key_vault_enable_real_io
        and not metadata_errors
        and credential_safe
        and algorithm_supported
        and sdk_or_fake_available
    )
    errors: list[dict[str, str]] = [
        {"code": "azure_key_vault_metadata_incomplete", "message": message}
        for message in metadata_errors
    ]
    if azure_selected and config.azure_key_vault_enable_real_io:
        if credential_mode in UNSAFE_AZURE_KEY_VAULT_CREDENTIAL_MODES:
            errors.append(
                {
                    "code": "azure_key_vault_credential_mode_unsafe",
                    "message": "Azure Key Vault signing requires a non-secret Azure identity credential mode.",
                }
            )
        elif not credential_safe:
            errors.append(
                {
                    "code": "azure_key_vault_credential_mode_unsupported",
                    "message": "Azure Key Vault signing credential mode is not approved.",
                }
            )
        if signing_client is None and not sdk_available:
            errors.append(
                {
                    "code": "azure_key_vault_sdk_missing",
                    "message": "azure-keyvault-keys and azure-identity are required for real Azure Key Vault signing I/O.",
                }
            )
    warnings: list[dict[str, str]] = []
    if azure_selected and not sdk_available:
        warnings.append(
            {
                "code": "azure_key_vault_sdk_missing",
                "message": "Azure Key Vault SDK packages are not installed; fake-client and metadata-only paths remain available.",
            }
        )
    if azure_selected and not config.azure_key_vault_enable_real_io:
        warnings.append(
            {
                "code": "azure_key_vault_real_io_disabled",
                "message": "Azure Key Vault signing real I/O is disabled.",
            }
        )
    return {
        "provider": "azure_key_vault",
        "selected": azure_selected,
        "signing_mode": config.normalized_mode,
        "signature_algorithm": config.effective_algorithm or None,
        "signature_key_ref": azure_key_vault_key_reference(config) or None,
        "vault_url_configured": bool(config.azure_key_vault_url),
        "key_name_configured": bool(config.azure_key_name),
        "key_name": config.azure_key_name or None,
        "key_version_configured": bool(config.azure_key_version),
        "key_version": config.azure_key_version or None,
        "credential_mode": credential_mode,
        "credential_mode_safe": credential_safe,
        "real_io_enabled": bool(config.azure_key_vault_enable_real_io),
        "hsm_required": bool(config.azure_key_vault_require_hsm),
        "sdk_available": sdk_available,
        "sdk_modules": {
            "azure_keyvault_keys_crypto": bool(sdk["azure_keyvault_keys_crypto"]),
            "azure_identity": bool(sdk["azure_identity"]),
        },
        "fake_client_injected": signing_client is not None,
        "metadata_ready": not metadata_errors,
        "real_io_ready": real_io_ready,
        "validation_errors": errors,
        "validation_warnings": warnings,
    }


def signing_evidence_summary(
    config: AuditManifestSigningConfig,
    *,
    signature_verification_status: str | None = None,
) -> dict[str, Any]:
    key_vault_summary = azure_key_vault_readiness_summary(config)
    return {
        "manifest_signing_mode": config.normalized_mode,
        "signing_required": config.required,
        "signature_algorithm": config.effective_algorithm or None,
        "signature_key_ref": (
            azure_key_vault_key_reference(config)
            if config.normalized_mode in AZURE_KEY_VAULT_SIGNING_MODES
            else config.key_ref
        )
        or None,
        "signature_verification_status": signature_verification_status or "not_checked_no_manifest",
        "local_signing_material_configured": bool(config.local_hmac_key),
        "azure_key_vault_url_configured": bool(config.azure_key_vault_url),
        "azure_signing_key_name_configured": bool(config.azure_key_name),
        "azure_signing_key_version_configured": bool(config.azure_key_version),
        "azure_key_vault_key_name": config.azure_key_name or None,
        "azure_key_vault_key_version": config.azure_key_version or None,
        "azure_key_vault_credential_mode": key_vault_summary["credential_mode"],
        "azure_key_vault_real_io_enabled": key_vault_summary["real_io_enabled"],
        "azure_key_vault_hsm_required": key_vault_summary["hsm_required"],
        "azure_key_vault_sdk_available": key_vault_summary["sdk_available"],
        "azure_key_vault_metadata_ready": key_vault_summary["metadata_ready"],
        "azure_key_vault_real_io_ready": key_vault_summary["real_io_ready"],
        "azure_key_vault_readiness": key_vault_summary,
    }
