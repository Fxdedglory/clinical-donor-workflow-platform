from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import Callable
from dataclasses import dataclass, field
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
SAFE_AZURE_CREDENTIAL_MODES = {
    "managed_identity",
    "workload_identity",
    "default_azure_credential",
    "entra_id",
    "azure_identity",
    "azure_cli",
}
AZURE_CHECKSUM_METADATA_KEY = "audit_checksum"
AZURE_CHECKSUM_METADATA_KEYS = (
    AZURE_CHECKSUM_METADATA_KEY,
    "clinical_audit_checksum",
    "checksum",
    "sha256",
)


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


@dataclass(frozen=True)
class AzureBlobObjectProperties:
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    size_bytes: int | None = None
    etag: str | None = None
    last_modified: Any | None = None


AzureBlobClientFactory = Callable[[AuditMirrorConfig], Any]


def _is_resource_not_found(exc: Exception) -> bool:
    return exc.__class__.__name__ in {"ResourceNotFoundError", "BlobNotFoundError"}


def _raw_property_value(raw: Any, *names: str, default: Any = None) -> Any:
    if isinstance(raw, dict):
        for name in names:
            if name in raw:
                return raw[name]
    for name in names:
        if hasattr(raw, name):
            return getattr(raw, name)
    return default


def _normalize_blob_properties(raw: Any, *, fallback_name: str = "") -> AzureBlobObjectProperties:
    if isinstance(raw, AzureBlobObjectProperties):
        if raw.name or not fallback_name:
            return raw
        return AzureBlobObjectProperties(
            name=fallback_name,
            metadata=dict(raw.metadata or {}),
            size_bytes=raw.size_bytes,
            etag=raw.etag,
            last_modified=raw.last_modified,
        )
    metadata = _raw_property_value(raw, "metadata", default={}) or {}
    size_bytes = _raw_property_value(raw, "size_bytes", "size", "content_length", default=None)
    return AzureBlobObjectProperties(
        name=str(_raw_property_value(raw, "name", "blob_name", default=fallback_name) or fallback_name),
        metadata=dict(metadata),
        size_bytes=int(size_bytes) if size_bytes is not None else None,
        etag=_raw_property_value(raw, "etag", default=None),
        last_modified=_raw_property_value(raw, "last_modified", default=None),
    )


class AzureBlobSdkClient:
    """Small Azure SDK wrapper kept behind the provider boundary."""

    def __init__(self, *, account_url: str, credential_mode: str, sdk_module: Any | None = None) -> None:
        self._sdk_module = sdk_module or importlib.import_module("azure.storage.blob")
        credential = self._credential_for_mode(credential_mode)
        self._service_client = self._sdk_module.BlobServiceClient(
            account_url=account_url,
            credential=credential,
        )

    @staticmethod
    def _credential_for_mode(credential_mode: str) -> Any:
        normalized = credential_mode.strip().lower()
        if normalized not in SAFE_AZURE_CREDENTIAL_MODES:
            raise RuntimeError(
                "Azure Blob real I/O requires AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE "
                "to be a non-secret Azure identity mode."
            )
        try:
            identity = importlib.import_module("azure.identity")
        except ImportError as exc:
            raise RuntimeError(
                "Azure identity dependency is not installed; real Azure Blob I/O with identity credentials "
                "requires azure-identity."
            ) from exc
        return identity.DefaultAzureCredential(exclude_interactive_browser_credential=True)

    def _blob_client(self, container: str, name: str) -> Any:
        return self._service_client.get_blob_client(container=container, blob=name)

    def upload_object(
        self,
        *,
        container: str,
        name: str,
        data: bytes,
        metadata: dict[str, str],
        overwrite: bool = False,
    ) -> AzureBlobObjectProperties:
        blob_client = self._blob_client(container, name)
        kwargs: dict[str, Any] = {
            "overwrite": overwrite,
            "metadata": metadata,
        }
        content_settings = getattr(self._sdk_module, "ContentSettings", None)
        if content_settings is not None:
            kwargs["content_settings"] = content_settings(content_type="application/json")
        blob_client.upload_blob(data, **kwargs)
        return self.get_object_properties(container=container, name=name) or AzureBlobObjectProperties(
            name=name,
            metadata=metadata,
            size_bytes=len(data),
        )

    def get_object_properties(self, *, container: str, name: str) -> AzureBlobObjectProperties | None:
        try:
            raw = self._blob_client(container, name).get_blob_properties()
        except Exception as exc:
            if _is_resource_not_found(exc):
                return None
            raise
        return _normalize_blob_properties(raw, fallback_name=name)

    def list_objects(self, *, container: str, prefix: str) -> list[AzureBlobObjectProperties]:
        container_client = self._service_client.get_container_client(container)
        return [
            _normalize_blob_properties(raw)
            for raw in container_client.list_blobs(name_starts_with=prefix)
        ]

    def download_object(self, *, container: str, name: str) -> bytes | None:
        try:
            stream = self._blob_client(container, name).download_blob()
            return stream.readall()
        except Exception as exc:
            if _is_resource_not_found(exc):
                return None
            raise


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

    def __init__(
        self,
        config: AuditMirrorConfig,
        *,
        client: Any | None = None,
        client_factory: AzureBlobClientFactory | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._client_factory = client_factory

    @property
    def container(self) -> str:
        return self.config.azure_container or self.config.object_container

    @property
    def object_prefix(self) -> str:
        return self.config.azure_prefix or self.config.object_prefix

    def capabilities(self) -> dict[str, bool]:
        return {
            **super().capabilities(),
            "put_object": True,
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

    def identity_sdk_available(self) -> bool:
        try:
            return importlib.util.find_spec("azure.identity") is not None
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

    def _operation_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self._client_factory is not None:
            self._client = self._client_factory(self.config)
            return self._client
        if not self.config.azure_enable_real_io:
            raise RuntimeError(
                "Azure Blob real I/O is disabled; set AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true "
                "or inject a test client before calling provider operations."
            )
        sdk_module = self._require_sdk()
        self._client = AzureBlobSdkClient(
            account_url=self.config.azure_account_url,
            credential_mode=self.config.azure_credential_mode,
            sdk_module=sdk_module,
        )
        return self._client

    def _blob_name_for_key(self, key: str) -> str:
        return "/".join(part for part in key.strip().replace("\\", "/").split("/") if part)

    def _blob_name_from_uri(self, uri: str) -> str:
        without_query = uri.split("?", 1)[0].strip()
        account_url = self.config.azure_account_url.rstrip("/")
        container = self.container.strip("/")
        candidates = []
        if account_url and container:
            candidates.append(f"{account_url}/{container}/")
        if container:
            candidates.append(f"{container}/")
        for candidate in candidates:
            if without_query.startswith(candidate):
                return self._blob_name_for_key(without_query[len(candidate) :])
        return self._blob_name_for_key(without_query)

    def _uri_for_blob_name(self, name: str) -> str:
        account_url = self.config.azure_account_url.rstrip("/")
        container = self.container.strip("/")
        blob_name = self._blob_name_for_key(name)
        if account_url and container:
            return f"{account_url}/{container}/{blob_name}"
        prefix = self.expected_uri_prefix().rstrip("/")
        if prefix:
            return f"{prefix}/{blob_name}"
        return blob_name

    def _payload_bytes(self, payload: dict[str, Any]) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")

    def _metadata_for_payload(self, payload: dict[str, Any], checksum: str) -> dict[str, str]:
        return {
            AZURE_CHECKSUM_METADATA_KEY: checksum,
            "schema_version": str(payload.get("schema_version") or ""),
            "payload_profile": str(payload.get("payload_profile") or ""),
            "redacted": str(bool(payload.get("redacted"))).lower(),
        }

    def _checksum_from_metadata(self, metadata: dict[str, Any] | None) -> str | None:
        normalized = {str(key).lower(): value for key, value in (metadata or {}).items()}
        for key in AZURE_CHECKSUM_METADATA_KEYS:
            value = normalized.get(key.lower())
            if value:
                return str(value)
        return None

    def _stat_from_properties(self, properties: Any, *, uri: str) -> ObjectStat:
        normalized = _normalize_blob_properties(properties, fallback_name=self._blob_name_from_uri(uri))
        metadata = dict(normalized.metadata or {})
        metadata.update(
            {
                "blob_name": normalized.name,
                "size_bytes": normalized.size_bytes,
                "etag": normalized.etag,
                "last_modified": normalized.last_modified,
            }
        )
        return ObjectStat(
            exists=True,
            uri=self._uri_for_blob_name(normalized.name),
            checksum=self._checksum_from_metadata(normalized.metadata),
            metadata=metadata,
        )

    def _download_payload(self, blob_name: str) -> dict[str, Any] | None:
        client = self._operation_client()
        data = client.download_object(container=self.container, name=blob_name)
        if data is None:
            return None
        if isinstance(data, bytes):
            return json.loads(data.decode("utf-8"))
        if isinstance(data, str):
            return json.loads(data)
        if isinstance(data, dict):
            return data
        raise RuntimeError("Azure Blob client returned an unsupported payload type.")

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
        elif credential_mode not in SAFE_AZURE_CREDENTIAL_MODES:
            issues.append(
                ProviderValidationIssue(
                    code="azure_credential_mode_unsupported",
                    message="AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE must use an approved Azure identity mode.",
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
        if self.config.azure_enable_real_io and not self.sdk_available():
            issues.append(
                ProviderValidationIssue(
                    code="azure_sdk_missing",
                    message="azure-storage-blob is required when AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true.",
                )
            )
        if (
            self.config.azure_enable_real_io
            and credential_mode in SAFE_AZURE_CREDENTIAL_MODES
            and not self.identity_sdk_available()
        ):
            issues.append(
                ProviderValidationIssue(
                    code="azure_identity_sdk_missing",
                    message="azure-identity is required for Azure identity credential modes when real I/O is enabled.",
                )
            )
        return issues

    def readiness_summary(self) -> dict[str, Any]:
        sdk_available = self.sdk_available()
        identity_sdk_available = self.identity_sdk_available()
        return {
            **super().readiness_summary(),
            "sdk_available": sdk_available,
            "identity_sdk_available": identity_sdk_available,
            "real_io_enabled": self.config.azure_enable_real_io,
            "client_injected": self._client is not None or self._client_factory is not None,
            "supported_operations": {
                "put_object": True,
                "stat_object": True,
                "read_object_metadata": True,
                "list_objects": True,
                "verify_object_checksum": True,
            },
            "no_network_dry_run": {
                "status": "completed",
                "network_calls_performed": False,
            },
            "azure": {
                "account_url_configured": bool(self.config.azure_account_url),
                "container": self.container,
                "prefix": self.object_prefix,
                "credential_mode": self.config.azure_credential_mode,
                "real_io_enabled": self.config.azure_enable_real_io,
                "immutability_required": self.config.azure_immutability_required,
                "legal_hold_required": self.config.azure_legal_hold_required,
                "checksum_validation_required": self.config.azure_checksum_validation_required,
            },
        }

    def put_object(self, key: str, payload: dict[str, Any], checksum: str) -> ObjectStat:
        client = self._operation_client()
        blob_name = self._blob_name_for_key(key)
        uri = self._uri_for_blob_name(blob_name)
        existing = client.get_object_properties(container=self.container, name=blob_name)
        if existing is not None:
            stat = self._stat_from_properties(existing, uri=uri)
            if stat.checksum and stat.checksum != checksum:
                return ObjectStat(
                    exists=True,
                    uri=stat.uri,
                    checksum=stat.checksum,
                    metadata=stat.metadata,
                    reason="existing object checksum differs",
                )
            if stat.checksum is None and self.config.azure_checksum_validation_required:
                return ObjectStat(
                    exists=True,
                    uri=stat.uri,
                    checksum=None,
                    metadata=stat.metadata,
                    reason="existing object checksum metadata missing",
                )
            return ObjectStat(
                exists=True,
                uri=stat.uri,
                checksum=stat.checksum or checksum,
                metadata=stat.metadata,
            )
        metadata = self._metadata_for_payload(payload, checksum)
        uploaded = client.upload_object(
            container=self.container,
            name=blob_name,
            data=self._payload_bytes(payload),
            metadata=metadata,
            overwrite=False,
        )
        return self._stat_from_properties(uploaded, uri=uri)

    def stat_object(self, uri: str) -> ObjectStat:
        client = self._operation_client()
        blob_name = self._blob_name_from_uri(uri)
        properties = client.get_object_properties(container=self.container, name=blob_name)
        if properties is None:
            return ObjectStat(exists=False, uri=uri, reason=f"Azure Blob object not found: {blob_name}")
        return self._stat_from_properties(properties, uri=uri)

    def read_object_metadata(self, uri: str) -> dict[str, Any]:
        stat = self.stat_object(uri)
        return {
            "exists": stat.exists,
            "uri": stat.uri,
            "checksum": stat.checksum,
            "reason": stat.reason,
            **(stat.metadata or {}),
        }

    def list_objects(self, prefix: str) -> list[ObjectStat]:
        client = self._operation_client()
        blob_prefix = self._blob_name_from_uri(prefix) if prefix else self.object_prefix.strip("/")
        return [
            self._stat_from_properties(properties, uri=self._uri_for_blob_name(properties.name))
            for properties in (
                _normalize_blob_properties(raw)
                for raw in client.list_objects(container=self.container, prefix=blob_prefix)
            )
        ]

    def verify_object_checksum(self, uri: str, expected_checksum: str) -> dict[str, Any]:
        if not (self._client is not None or self._client_factory is not None or self.config.azure_enable_real_io):
            return {
                "status": "not_checked",
                "uri": uri,
                "expected_checksum": expected_checksum,
                "computed_checksum": None,
                "reason": "Azure Blob real I/O is disabled and no test client was injected.",
            }
        stat = self.stat_object(uri)
        if not stat.exists:
            return {
                "status": "missing",
                "uri": uri,
                "expected_checksum": expected_checksum,
                "computed_checksum": None,
                "reason": stat.reason,
            }
        computed_checksum = stat.checksum
        if computed_checksum is None:
            payload = self._download_payload(self._blob_name_from_uri(uri))
            computed_checksum = audit_mirror_checksum(payload) if payload is not None else None
        if computed_checksum is None:
            return {
                "status": "not_checked",
                "uri": uri,
                "expected_checksum": expected_checksum,
                "computed_checksum": None,
                "reason": "Azure Blob checksum metadata and downloadable payload were unavailable.",
            }
        if computed_checksum != expected_checksum:
            return {
                "status": "checksum_mismatch",
                "uri": uri,
                "expected_checksum": expected_checksum,
                "computed_checksum": computed_checksum,
                "reason": "computed checksum differs from expected checksum",
            }
        return {
            "status": "verified",
            "uri": uri,
            "expected_checksum": expected_checksum,
            "computed_checksum": computed_checksum,
            "reason": None,
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


def get_audit_mirror_provider(
    config: AuditMirrorConfig,
    *,
    client: Any | None = None,
    client_factory: AzureBlobClientFactory | None = None,
) -> AuditMirrorProvider:
    provider_name = (config.object_provider or "").strip().lower()
    if config.local_filesystem or provider_name in LOCAL_PROVIDER_ALIASES:
        return LocalFilesystemAuditMirrorProvider(config)
    if provider_name in AZURE_BLOB_PROVIDER_ALIASES:
        return AzureBlobAuditMirrorProvider(config, client=client, client_factory=client_factory)
    return PlaceholderAuditMirrorProvider(config)


def provider_readiness_summary(config: AuditMirrorConfig) -> dict[str, Any]:
    provider = get_audit_mirror_provider(config)
    return provider.readiness_summary()
