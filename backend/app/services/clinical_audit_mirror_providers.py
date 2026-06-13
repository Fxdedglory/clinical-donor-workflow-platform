from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.clinical_audit_mirror import AuditMirrorConfig, audit_mirror_checksum

LOCAL_PROVIDER_ALIASES = {"local", "local_filesystem", "filesystem", "file"}
AZURE_BLOB_PROVIDER_ALIASES = {"azure", "azure_blob", "azure_blob_storage", "azure_blob_immutability"}
UNSAFE_CREDENTIAL_MODES = {
    "",
    "account_key",
    "account-key",
    "connection_string",
    "connection-string",
    "connection_string_in_code",
    "shared_key",
    "shared-key",
    "sas_token_inline",
    "plain_secret",
}


@dataclass(frozen=True)
class ProviderValidationIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ObjectStat:
    exists: bool
    uri: str
    checksum: str | None = None
    metadata: dict[str, Any] | None = None
    reason: str | None = None


class AuditMirrorProvider:
    name = "provider_placeholder"

    def __init__(self, config: AuditMirrorConfig) -> None:
        self.config = config
        self.sdk_imported = False

    def capabilities(self) -> dict[str, bool]:
        return {
            "put_object": False,
            "head_object": False,
            "read_object_metadata": False,
            "list_objects": False,
            "verify_object_checksum": False,
            "supports_immutability": False,
            "supports_legal_hold": False,
            "supports_retention_policy": False,
            "supports_etag_validation": False,
            "network_calls_required": False,
        }

    def expected_uri_prefix(self) -> str:
        prefix = self.config.uri_prefix.rstrip("/")
        object_prefix = self.config.object_prefix.strip("/")
        if prefix and object_prefix:
            return f"{prefix}/{object_prefix}"
        return prefix or object_prefix

    def validate_config(self) -> list[ProviderValidationIssue]:
        return []

    def readiness_summary(self) -> dict[str, Any]:
        issues = self.validate_config()
        errors = [issue for issue in issues if issue.severity == "error"]
        warnings = [issue for issue in issues if issue.severity != "error"]
        return {
            "provider": self.name,
            "provider_mode": self.config.normalized_mode,
            "expected_uri_prefix": self.expected_uri_prefix(),
            "capabilities": self.capabilities(),
            "ready": not errors,
            "validation_errors": [issue.__dict__ for issue in errors],
            "validation_warnings": [issue.__dict__ for issue in warnings],
            "network_calls_performed": False,
        }

    def put_object(self, key: str, payload: dict[str, Any], checksum: str) -> ObjectStat:
        raise NotImplementedError("Provider does not implement put_object.")

    def stat_object(self, uri: str) -> ObjectStat:
        raise NotImplementedError("Provider does not implement stat_object.")

    def read_object_metadata(self, uri: str) -> dict[str, Any]:
        raise NotImplementedError("Provider does not implement read_object_metadata.")

    def list_objects(self, prefix: str) -> list[ObjectStat]:
        raise NotImplementedError("Provider does not implement list_objects.")

    def verify_object_checksum(self, uri: str, expected_checksum: str) -> dict[str, Any]:
        raise NotImplementedError("Provider does not implement verify_object_checksum.")


class LocalFilesystemAuditMirrorProvider(AuditMirrorProvider):
    name = "local_filesystem"

    def capabilities(self) -> dict[str, bool]:
        return {
            **super().capabilities(),
            "put_object": True,
            "head_object": True,
            "read_object_metadata": True,
            "list_objects": True,
            "verify_object_checksum": True,
        }

    def validate_config(self) -> list[ProviderValidationIssue]:
        issues: list[ProviderValidationIssue] = []
        if not str(self.config.local_root):
            issues.append(
                ProviderValidationIssue(
                    code="local_root_missing",
                    message="AUDIT_OBJECT_MIRROR_LOCAL_ROOT is required for local filesystem mirror simulation.",
                )
            )
        if not self.config.object_prefix:
            issues.append(
                ProviderValidationIssue(
                    code="object_prefix_missing",
                    message="AUDIT_OBJECT_MIRROR_PREFIX is required for mirror object keys.",
                )
            )
        return issues

    def _relative_from_uri(self, uri: str) -> Path:
        prefix = self.config.uri_prefix.rstrip("/")
        relative = uri
        if prefix and uri.startswith(f"{prefix}/"):
            relative = uri[len(prefix) + 1 :]
        return Path(*[part for part in relative.split("/") if part])

    def _uri_for_key(self, key: str) -> str:
        relative = key.strip("/").replace("\\", "/")
        prefix = self.config.uri_prefix.rstrip("/")
        if prefix:
            return f"{prefix}/{relative}"
        return relative

    def put_object(self, key: str, payload: dict[str, Any], checksum: str) -> ObjectStat:
        relative = Path(*[part for part in key.replace("\\", "/").split("/") if part])
        target = self.config.local_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing_payload = json.loads(target.read_text(encoding="utf-8"))
            existing_checksum = audit_mirror_checksum(existing_payload)
            if existing_checksum != checksum:
                return ObjectStat(
                    exists=True,
                    uri=self._uri_for_key(relative.as_posix()),
                    checksum=existing_checksum,
                    reason="existing object checksum differs",
                )
            return ObjectStat(exists=True, uri=self._uri_for_key(relative.as_posix()), checksum=existing_checksum)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return ObjectStat(exists=True, uri=self._uri_for_key(relative.as_posix()), checksum=checksum)

    def stat_object(self, uri: str) -> ObjectStat:
        target = self.config.local_root / self._relative_from_uri(uri)
        if not target.exists():
            return ObjectStat(exists=False, uri=uri, reason=f"local object not found: {target}")
        payload = json.loads(target.read_text(encoding="utf-8"))
        return ObjectStat(
            exists=True,
            uri=uri,
            checksum=audit_mirror_checksum(payload),
            metadata={"path": str(target), "size_bytes": target.stat().st_size},
        )

    def read_object_metadata(self, uri: str) -> dict[str, Any]:
        stat = self.stat_object(uri)
        return {
            "exists": stat.exists,
            "uri": stat.uri,
            "checksum": stat.checksum,
            **(stat.metadata or {}),
        }

    def list_objects(self, prefix: str) -> list[ObjectStat]:
        relative = self._relative_from_uri(prefix)
        root = self.config.local_root / relative
        if root.is_file():
            return [self.stat_object(prefix)]
        if not root.exists():
            return []
        return [
            self.stat_object(self._uri_for_key(path.relative_to(self.config.local_root).as_posix()))
            for path in sorted(root.rglob("*.json"))
        ]

    def verify_object_checksum(self, uri: str, expected_checksum: str) -> dict[str, Any]:
        stat = self.stat_object(uri)
        if not stat.exists:
            return {
                "status": "missing",
                "uri": uri,
                "expected_checksum": expected_checksum,
                "computed_checksum": None,
                "reason": stat.reason,
            }
        if stat.checksum != expected_checksum:
            return {
                "status": "checksum_mismatch",
                "uri": uri,
                "expected_checksum": expected_checksum,
                "computed_checksum": stat.checksum,
                "reason": "computed checksum differs from expected checksum",
            }
        return {
            "status": "verified",
            "uri": uri,
            "expected_checksum": expected_checksum,
            "computed_checksum": stat.checksum,
            "reason": None,
        }


class AzureBlobAuditMirrorProvider(AuditMirrorProvider):
    name = "azure_blob"

    @property
    def container(self) -> str:
        return self.config.azure_container or self.config.object_container

    @property
    def object_prefix(self) -> str:
        return self.config.azure_prefix or self.config.object_prefix

    def capabilities(self) -> dict[str, bool]:
        return {
            **super().capabilities(),
            "put_object": False,
            "head_object": True,
            "read_object_metadata": True,
            "list_objects": True,
            "verify_object_checksum": True,
            "supports_immutability": True,
            "supports_legal_hold": True,
            "supports_retention_policy": True,
            "supports_etag_validation": True,
            "network_calls_required": True,
        }

    def expected_uri_prefix(self) -> str:
        account_url = self.config.azure_account_url.rstrip("/")
        container = self.container.strip("/")
        object_prefix = self.object_prefix.strip("/")
        parts = [part for part in (account_url, container, object_prefix) if part]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return "/".join(parts)

    def sdk_available(self) -> bool:
        try:
            return importlib.util.find_spec("azure.storage.blob") is not None
        except ModuleNotFoundError:
            return False

    def _require_sdk(self) -> Any:
        self.sdk_imported = True
        try:
            return importlib.import_module("azure.storage.blob")
        except ImportError as exc:
            raise RuntimeError(
                "Azure Blob SDK is not installed; provider readiness can be checked without it, "
                "but real object operations require azure-storage-blob."
            ) from exc

    def validate_config(self) -> list[ProviderValidationIssue]:
        issues: list[ProviderValidationIssue] = []
        if not self.config.azure_account_url:
            issues.append(
                ProviderValidationIssue(
                    code="azure_account_url_missing",
                    message="AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL is required for azure_blob readiness.",
                )
            )
        if not self.container:
            issues.append(
                ProviderValidationIssue(
                    code="azure_container_missing",
                    message="AUDIT_OBJECT_MIRROR_AZURE_CONTAINER or AUDIT_OBJECT_MIRROR_CONTAINER is required.",
                )
            )
        if not self.object_prefix:
            issues.append(
                ProviderValidationIssue(
                    code="azure_prefix_missing",
                    message="AUDIT_OBJECT_MIRROR_AZURE_PREFIX or AUDIT_OBJECT_MIRROR_PREFIX is required.",
                )
            )
        credential_mode = self.config.azure_credential_mode.strip().lower()
        if not credential_mode:
            issues.append(
                ProviderValidationIssue(
                    code="azure_credential_mode_missing",
                    message="AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE is required for azure_blob readiness.",
                )
            )
        elif credential_mode in UNSAFE_CREDENTIAL_MODES:
            issues.append(
                ProviderValidationIssue(
                    code="azure_credential_mode_unsafe",
                    message="AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE must not describe inline account keys, connection strings, or plain secrets.",
                )
            )
        if self.config.azure_immutability_required and not self.config.retention_policy:
            issues.append(
                ProviderValidationIssue(
                    code="azure_immutability_policy_missing",
                    message="AUDIT_OBJECT_MIRROR_RETENTION_POLICY is required when Azure immutability is required.",
                )
            )
        if self.config.azure_legal_hold_required and not self.config.legal_hold_reference:
            issues.append(
                ProviderValidationIssue(
                    code="azure_legal_hold_reference_missing",
                    message="AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE is required when Azure legal hold is required.",
                )
            )
        if self.config.azure_checksum_validation_required and not self.config.azure_credential_mode:
            issues.append(
                ProviderValidationIssue(
                    code="azure_checksum_validation_config_missing",
                    message="AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE is required when Azure checksum validation is required.",
                )
            )
        return issues

    def readiness_summary(self) -> dict[str, Any]:
        return {
            **super().readiness_summary(),
            "sdk_available": self.sdk_available(),
            "azure": {
                "account_url_configured": bool(self.config.azure_account_url),
                "container": self.container,
                "prefix": self.object_prefix,
                "credential_mode": self.config.azure_credential_mode,
                "immutability_required": self.config.azure_immutability_required,
                "legal_hold_required": self.config.azure_legal_hold_required,
                "checksum_validation_required": self.config.azure_checksum_validation_required,
            },
        }

    def put_object(self, key: str, payload: dict[str, Any], checksum: str) -> ObjectStat:
        self._require_sdk()
        raise NotImplementedError("Real Azure Blob object writes are reserved for a future provider integration sprint.")

    def stat_object(self, uri: str) -> ObjectStat:
        self._require_sdk()
        raise NotImplementedError("Real Azure Blob object stat calls are reserved for a future provider integration sprint.")

    def read_object_metadata(self, uri: str) -> dict[str, Any]:
        self._require_sdk()
        raise NotImplementedError("Real Azure Blob metadata reads are reserved for a future provider integration sprint.")

    def list_objects(self, prefix: str) -> list[ObjectStat]:
        self._require_sdk()
        raise NotImplementedError("Real Azure Blob object listing is reserved for a future provider integration sprint.")

    def verify_object_checksum(self, uri: str, expected_checksum: str) -> dict[str, Any]:
        return {
            "status": "not_checked",
            "uri": uri,
            "expected_checksum": expected_checksum,
            "computed_checksum": None,
            "reason": "Azure Blob checksum verification is readiness-only until real SDK integration is approved.",
        }


class PlaceholderAuditMirrorProvider(AuditMirrorProvider):
    name = "provider_placeholder"

    def validate_config(self) -> list[ProviderValidationIssue]:
        if not self.config.object_provider:
            return [
                ProviderValidationIssue(
                    code="provider_missing",
                    message="AUDIT_OBJECT_MIRROR_PROVIDER is required for object storage readiness.",
                )
            ]
        return [
            ProviderValidationIssue(
                code="provider_not_implemented",
                message=f"Provider {self.config.object_provider!r} has no readiness adapter yet.",
                severity="warning",
            )
        ]


def get_audit_mirror_provider(config: AuditMirrorConfig) -> AuditMirrorProvider:
    provider_name = (config.object_provider or "").strip().lower()
    if config.local_filesystem or provider_name in LOCAL_PROVIDER_ALIASES:
        return LocalFilesystemAuditMirrorProvider(config)
    if provider_name in AZURE_BLOB_PROVIDER_ALIASES:
        return AzureBlobAuditMirrorProvider(config)
    return PlaceholderAuditMirrorProvider(config)


def provider_readiness_summary(config: AuditMirrorConfig) -> dict[str, Any]:
    provider = get_audit_mirror_provider(config)
    return provider.readiness_summary()
