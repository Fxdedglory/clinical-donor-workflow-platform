from __future__ import annotations

import importlib.util
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.services.clinical_audit_signing import (
    SAFE_SIGNING_ALGORITHMS,
    SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER,
    SIGNING_MODE_CHECKSUM_PLACEHOLDER,
    SIGNING_MODE_DISABLED,
    SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER,
    SIGNING_MODE_LOCAL_HMAC_SHA256,
    SIGNING_MODES,
    UNSAFE_SIGNING_ALGORITHMS,
)
from app.services.clinical_phi import (
    DEFAULT_AGGREGATE_EXPORT_PROFILE,
    DEFAULT_AUDIT_EXPORT_PROFILE,
    DEFAULT_COMPLIANCE_EXPORT_PROFILE,
    normalize_export_profile,
)

logger = logging.getLogger(__name__)

PRODUCTION_ENV_VALUES = {"prod", "production", "stage", "staging"}
DEVELOPMENT_ENV_VALUES = {"dev", "development", "local", "test", "testing", "demo"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
JSON_ONLY_AUDIT_MODES = {
    "disabled",
    "file",
    "filesystem",
    "json",
    "json_only",
    "json-only",
    "metadata_json",
    "metadata-json",
}
DISABLED_AUDIT_OBJECT_MIRROR_MODES = {"", "disabled", "off", "none"}
LOCAL_AUDIT_OBJECT_MIRROR_MODES = {"local", "local_filesystem", "filesystem", "file"}
PLACEHOLDER_AUDIT_OBJECT_MIRROR_MODES = {"object_storage", "provider_placeholder", "worm_placeholder"}
AZURE_BLOB_AUDIT_OBJECT_MIRROR_PROVIDERS = {"azure", "azure_blob", "azure_blob_storage", "azure_blob_immutability"}
UNSAFE_AZURE_CREDENTIAL_MODES = {
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
SAFE_ANALYTICS_EXPORT_PROFILES = {"aggregate_safe", "external_safe"}
SAFE_AUDIT_EXPORT_PROFILES = {"audit_metadata", "aggregate_safe", "external_safe"}
SAFE_COMPLIANCE_EXPORT_PROFILES = {"compliance_evidence", "audit_metadata"}
UNSAFE_MFA_BYPASS_CODES = {"000000", "111111", "123456", "654321", "999999"}

DEFAULT_CONFIG: dict[str, Any] = {
    "app_env": "dev",
    "environment": "",
    "clinical_env": "",
    "debug": False,
    "secret_key": "change-me-for-production-demo-only",
    "encryption_key": None,
    "cookie_secure": False,
    "cookie_samesite": "lax",
    "cors_origins": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://teemails.com",
        "https://www.teemails.com",
    ],
    "serve_frontend": True,
    "database_url": "postgresql+psycopg://clinical_admin@localhost:5432/clinical_donor_workflow",
    "startup_mode": "fastapi_react",
    "workflow_audit_storage": "db_with_json_mirror",
    "workflow_audit_db_required": True,
    "audit_object_mirror_mode": "disabled",
    "audit_object_mirror_required": False,
    "audit_object_mirror_local_root": "metadata/audit_worm_mirror",
    "audit_object_mirror_provider": "",
    "audit_object_mirror_container": "",
    "audit_object_mirror_prefix": "workflow-audit",
    "audit_object_mirror_allow_local_production_simulation": False,
    "audit_object_mirror_retention_policy": "",
    "audit_object_mirror_legal_hold_required": False,
    "audit_object_mirror_legal_hold_reference": "",
    "audit_object_mirror_manifest_required": False,
    "audit_object_mirror_signature_required": False,
    "audit_object_mirror_signature_algorithm": "sha256-placeholder",
    "audit_object_mirror_signature_key_ref": "",
    "audit_manifest_signing_mode": "",
    "audit_manifest_signing_required": False,
    "audit_manifest_signing_algorithm": "",
    "audit_manifest_signing_key_ref": "",
    "audit_manifest_local_hmac_key": "",
    "audit_manifest_allow_local_signing_in_production": False,
    "audit_manifest_azure_key_vault_url": "",
    "audit_manifest_azure_key_name": "",
    "audit_manifest_azure_key_version": "",
    "audit_object_mirror_azure_account_url": "",
    "audit_object_mirror_azure_container": "",
    "audit_object_mirror_azure_prefix": "",
    "audit_object_mirror_azure_credential_mode": "",
    "audit_object_mirror_azure_enable_real_io": False,
    "audit_object_mirror_azure_immutability_required": False,
    "audit_object_mirror_azure_legal_hold_required": False,
    "audit_object_mirror_azure_checksum_validation_required": False,
    "default_analytics_export_profile": DEFAULT_AGGREGATE_EXPORT_PROFILE,
    "default_compliance_export_profile": DEFAULT_COMPLIANCE_EXPORT_PROFILE,
    "default_audit_export_profile": DEFAULT_AUDIT_EXPORT_PROFILE,
    "phi_redaction_enabled": True,
    "allow_generic_foundation_commit": False,
    "generic_workflow_commit_admin_only": True,
    "authentication_enabled": True,
    "mfa_dev_bypass_code": "000000",
    "allow_demo_auth_bypass": False,
}


@dataclass(frozen=True)
class ProductionSecurityGateIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ProductionSecurityGateResult:
    environment: str
    production_like: bool
    failures: tuple[ProductionSecurityGateIssue, ...] = ()
    warnings: tuple[ProductionSecurityGateIssue, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failures

    def model_dump(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "production_like": self.production_like,
            "passed": self.passed,
            "failures": [issue.__dict__ for issue in self.failures],
            "warnings": [issue.__dict__ for issue in self.warnings],
        }


def _candidate_names(*names: str) -> list[str]:
    candidates: list[str] = []
    for name in names:
        for candidate in {name, name.lower(), name.upper()}:
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _get(config: Mapping[str, Any] | object, *names: str, default: Any = None) -> Any:
    for candidate in _candidate_names(*names):
        if isinstance(config, Mapping) and candidate in config:
            return config[candidate]
        attr_name = candidate.lower()
        if not isinstance(config, Mapping) and hasattr(config, attr_name):
            return getattr(config, attr_name)
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


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [_text(item) for item in parsed if _text(item)]
        return [item.strip() for item in stripped.split(",") if item.strip()]
    return [_text(value)] if _text(value) else []


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def _is_placeholder_secret(value: Any) -> bool:
    secret = _text(value)
    if not secret or len(secret) < 32:
        return True
    lowered = secret.lower()
    markers = {
        "change-me",
        "changeme",
        "demo-only",
        "demo-secret",
        "dev-secret",
        "test-secret",
        "placeholder",
        "default-secret",
        "secret-key",
        "not-a-secret",
    }
    return any(marker in lowered for marker in markers)


def _origin_is_local(origin: str) -> bool:
    if origin == "*":
        return False
    parsed = urlparse(origin)
    host = (parsed.hostname or origin).lower()
    return host in LOCAL_HOSTS or host.startswith("127.")


def _database_host_is_local(database_url: str) -> bool:
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    return host in LOCAL_HOSTS or host.startswith("127.")


def _production_like(config: Mapping[str, Any] | object, *, strict: bool | None) -> tuple[bool, str]:
    env_values = [
        _normalized(_get(config, "app_env", "APP_ENV", default=DEFAULT_CONFIG["app_env"])),
        _normalized(_get(config, "environment", "ENVIRONMENT", default="")),
        _normalized(_get(config, "clinical_env", "CLINICAL_ENV", default="")),
    ]
    selected = next((value for value in env_values if value), "dev")
    if strict is not None:
        return strict, selected
    if any(value in PRODUCTION_ENV_VALUES for value in env_values):
        return True, selected
    if selected in DEVELOPMENT_ENV_VALUES:
        return False, selected
    return False, selected


def _configured_profile(config: Mapping[str, Any] | object, *names: str, default: str) -> str:
    value = _get(config, *names, default=default)
    return normalize_export_profile(_text(value), default=default)


def validate_production_security_gates(
    config: Mapping[str, Any] | object | None = None,
    *,
    strict: bool | None = None,
) -> ProductionSecurityGateResult:
    source = config or DEFAULT_CONFIG
    production_like, environment = _production_like(source, strict=strict)
    issues: list[ProductionSecurityGateIssue] = []

    def add(code: str, message: str) -> None:
        issues.append(ProductionSecurityGateIssue(code=code, message=message))

    secret_key = _get(source, "secret_key", "SECRET_KEY", default=DEFAULT_CONFIG["secret_key"])
    if not _text(secret_key):
        add("secret_key_missing", "SECRET_KEY is required in production.")
    elif _is_placeholder_secret(secret_key):
        add("secret_key_unsafe", "SECRET_KEY must be a generated non-placeholder value of at least 32 characters.")

    encryption_key = _get(source, "encryption_key", "ENCRYPTION_KEY", default=DEFAULT_CONFIG["encryption_key"])
    if not _text(encryption_key):
        add("encryption_key_missing", "ENCRYPTION_KEY is required so sensitive-field encryption never falls back to SECRET_KEY.")
    elif _is_placeholder_secret(encryption_key):
        add("encryption_key_unsafe", "ENCRYPTION_KEY must be a generated non-placeholder value of at least 32 characters.")

    if not _as_bool(_get(source, "cookie_secure", "COOKIE_SECURE", default=DEFAULT_CONFIG["cookie_secure"])):
        add("cookie_secure_disabled", "COOKIE_SECURE must be true in production.")
    same_site = _normalized(_get(source, "cookie_samesite", "COOKIE_SAMESITE", default=DEFAULT_CONFIG["cookie_samesite"]))
    if same_site not in {"lax", "strict"}:
        add("cookie_samesite_unsafe", "COOKIE_SAMESITE must be lax or strict in production.")

    cors_origins = _as_list(_get(source, "cors_origins", "CORS_ORIGINS", default=DEFAULT_CONFIG["cors_origins"]))
    if "*" in cors_origins:
        add("cors_wildcard", "Wildcard CORS origins are not allowed in production.")
    local_origins = [origin for origin in cors_origins if _origin_is_local(origin)]
    if local_origins:
        add("cors_local_origin", "Production CORS origins must not include localhost, loopback, or local-only origins.")
    serve_frontend = _as_bool(_get(source, "serve_frontend", "SERVE_FRONTEND", default=DEFAULT_CONFIG["serve_frontend"]), default=True)
    if not cors_origins and not serve_frontend:
        add("cors_empty", "CORS_ORIGINS is required when the production frontend is hosted separately.")

    if _as_bool(_get(source, "debug", "DEBUG", default=DEFAULT_CONFIG["debug"])):
        add("debug_enabled", "DEBUG must be false in production.")
    if _as_bool(_get(source, "reload", "RELOAD", "UVICORN_RELOAD", default=False)):
        add("reload_enabled", "Reload/dev-server mode must be disabled in production.")
    startup_mode = _normalized(_get(source, "startup_mode", "STARTUP_MODE", default=DEFAULT_CONFIG["startup_mode"]))
    if "reload" in startup_mode or "dev" in startup_mode:
        add("startup_mode_dev", "STARTUP_MODE must not indicate reload or development server mode in production.")

    database_url = _text(_get(source, "database_url", "DATABASE_URL", default=DEFAULT_CONFIG["database_url"]))
    if not database_url:
        add("database_url_missing", "DATABASE_URL is required in production.")
    else:
        parsed_database = urlparse(database_url)
        scheme = parsed_database.scheme.lower()
        if scheme.startswith("sqlite"):
            add("database_url_sqlite", "SQLite/local file databases are not allowed in production.")
        elif not (scheme.startswith("postgresql") or scheme.startswith("postgres")):
            add("database_url_non_postgres", "Production DATABASE_URL must use PostgreSQL.")
        if _database_host_is_local(database_url):
            add("database_url_local", "Production DATABASE_URL must not point at localhost or loopback.")
        if not parsed_database.hostname and not scheme.startswith("sqlite"):
            add("database_url_missing_host", "Production DATABASE_URL must include a database host.")

    audit_mode = _normalized(_get(source, "workflow_audit_storage", "WORKFLOW_AUDIT_STORAGE", default=DEFAULT_CONFIG["workflow_audit_storage"]))
    if audit_mode in JSON_ONLY_AUDIT_MODES:
        add("workflow_audit_json_only", "Workflow audit storage must be DB-backed in production; JSON-only mode is not allowed.")
    if not _as_bool(_get(source, "workflow_audit_db_required", "WORKFLOW_AUDIT_DB_REQUIRED", default=DEFAULT_CONFIG["workflow_audit_db_required"]), default=True):
        add("workflow_audit_db_not_required", "WORKFLOW_AUDIT_DB_REQUIRED must remain true in production.")

    mirror_required = _as_bool(
        _get(source, "audit_object_mirror_required", "AUDIT_OBJECT_MIRROR_REQUIRED", default=DEFAULT_CONFIG["audit_object_mirror_required"]),
        default=False,
    )
    mirror_mode = _normalized(
        _get(source, "audit_object_mirror_mode", "AUDIT_OBJECT_MIRROR_MODE", default=DEFAULT_CONFIG["audit_object_mirror_mode"])
    )
    mirror_provider = _text(
        _get(source, "audit_object_mirror_provider", "AUDIT_OBJECT_MIRROR_PROVIDER", default=DEFAULT_CONFIG["audit_object_mirror_provider"])
    )
    mirror_container = _text(
        _get(source, "audit_object_mirror_container", "AUDIT_OBJECT_MIRROR_CONTAINER", default=DEFAULT_CONFIG["audit_object_mirror_container"])
    )
    mirror_prefix = _text(
        _get(source, "audit_object_mirror_prefix", "AUDIT_OBJECT_MIRROR_PREFIX", default=DEFAULT_CONFIG["audit_object_mirror_prefix"])
    )
    local_simulation_allowed = _as_bool(
        _get(
            source,
            "audit_object_mirror_allow_local_production_simulation",
            "AUDIT_OBJECT_MIRROR_ALLOW_LOCAL_PRODUCTION_SIMULATION",
            default=DEFAULT_CONFIG["audit_object_mirror_allow_local_production_simulation"],
        ),
        default=False,
    )
    mirror_retention_policy = _text(
        _get(
            source,
            "audit_object_mirror_retention_policy",
            "AUDIT_OBJECT_MIRROR_RETENTION_POLICY",
            default=DEFAULT_CONFIG["audit_object_mirror_retention_policy"],
        )
    )
    legal_hold_required = _as_bool(
        _get(
            source,
            "audit_object_mirror_legal_hold_required",
            "AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED",
            default=DEFAULT_CONFIG["audit_object_mirror_legal_hold_required"],
        ),
        default=False,
    )
    legal_hold_reference = _text(
        _get(
            source,
            "audit_object_mirror_legal_hold_reference",
            "AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE",
            default=DEFAULT_CONFIG["audit_object_mirror_legal_hold_reference"],
        )
    )
    manifest_required = _as_bool(
        _get(
            source,
            "audit_object_mirror_manifest_required",
            "AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED",
            default=DEFAULT_CONFIG["audit_object_mirror_manifest_required"],
        ),
        default=False,
    )
    signature_required = _as_bool(
        _get(
            source,
            "audit_object_mirror_signature_required",
            "AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED",
            default=DEFAULT_CONFIG["audit_object_mirror_signature_required"],
        ),
        default=False,
    )
    signature_algorithm = _text(
        _get(
            source,
            "audit_object_mirror_signature_algorithm",
            "AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM",
            default=DEFAULT_CONFIG["audit_object_mirror_signature_algorithm"],
        )
    )
    signature_key_ref = _text(
        _get(
            source,
            "audit_object_mirror_signature_key_ref",
            "AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF",
            default=DEFAULT_CONFIG["audit_object_mirror_signature_key_ref"],
        )
    )
    legacy_signature_required = signature_required
    manifest_signing_required = _as_bool(
        _get(
            source,
            "audit_manifest_signing_required",
            "AUDIT_MANIFEST_SIGNING_REQUIRED",
            default=DEFAULT_CONFIG["audit_manifest_signing_required"],
        ),
        default=False,
    ) or legacy_signature_required
    manifest_signing_mode = _normalized(
        _get(
            source,
            "audit_manifest_signing_mode",
            "AUDIT_MANIFEST_SIGNING_MODE",
            default=DEFAULT_CONFIG["audit_manifest_signing_mode"],
        )
    )
    if not manifest_signing_mode and legacy_signature_required:
        manifest_signing_mode = SIGNING_MODE_CHECKSUM_PLACEHOLDER
    manifest_signing_mode = manifest_signing_mode or SIGNING_MODE_DISABLED
    manifest_signing_algorithm = _text(
        _get(
            source,
            "audit_manifest_signing_algorithm",
            "AUDIT_MANIFEST_SIGNING_ALGORITHM",
            default=DEFAULT_CONFIG["audit_manifest_signing_algorithm"],
        )
    ) or signature_algorithm
    manifest_signing_key_ref = _text(
        _get(
            source,
            "audit_manifest_signing_key_ref",
            "AUDIT_MANIFEST_SIGNING_KEY_REF",
            default=DEFAULT_CONFIG["audit_manifest_signing_key_ref"],
        )
    ) or signature_key_ref
    manifest_local_hmac_key_configured = bool(
        _text(
            _get(
                source,
                "audit_manifest_local_hmac_key",
                "AUDIT_MANIFEST_LOCAL_HMAC_KEY",
                default=DEFAULT_CONFIG["audit_manifest_local_hmac_key"],
            )
        )
    )
    manifest_allow_local_signing = _as_bool(
        _get(
            source,
            "audit_manifest_allow_local_signing_in_production",
            "AUDIT_MANIFEST_ALLOW_LOCAL_SIGNING_IN_PRODUCTION",
            default=DEFAULT_CONFIG["audit_manifest_allow_local_signing_in_production"],
        ),
        default=False,
    )
    manifest_azure_key_vault_url = _text(
        _get(
            source,
            "audit_manifest_azure_key_vault_url",
            "AUDIT_MANIFEST_AZURE_KEY_VAULT_URL",
            default=DEFAULT_CONFIG["audit_manifest_azure_key_vault_url"],
        )
    )
    manifest_azure_key_name = _text(
        _get(
            source,
            "audit_manifest_azure_key_name",
            "AUDIT_MANIFEST_AZURE_KEY_NAME",
            default=DEFAULT_CONFIG["audit_manifest_azure_key_name"],
        )
    )
    azure_account_url = _text(
        _get(
            source,
            "audit_object_mirror_azure_account_url",
            "AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_account_url"],
        )
    )
    azure_container = _text(
        _get(
            source,
            "audit_object_mirror_azure_container",
            "AUDIT_OBJECT_MIRROR_AZURE_CONTAINER",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_container"],
        )
    ) or mirror_container
    azure_prefix = _text(
        _get(
            source,
            "audit_object_mirror_azure_prefix",
            "AUDIT_OBJECT_MIRROR_AZURE_PREFIX",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_prefix"],
        )
    ) or mirror_prefix
    azure_credential_mode = _normalized(
        _get(
            source,
            "audit_object_mirror_azure_credential_mode",
            "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_credential_mode"],
        )
    )
    azure_enable_real_io = _as_bool(
        _get(
            source,
            "audit_object_mirror_azure_enable_real_io",
            "AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_enable_real_io"],
        ),
        default=False,
    )
    azure_immutability_required = _as_bool(
        _get(
            source,
            "audit_object_mirror_azure_immutability_required",
            "AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_immutability_required"],
        ),
        default=False,
    )
    azure_legal_hold_required = _as_bool(
        _get(
            source,
            "audit_object_mirror_azure_legal_hold_required",
            "AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_legal_hold_required"],
        ),
        default=False,
    )
    azure_checksum_validation_required = _as_bool(
        _get(
            source,
            "audit_object_mirror_azure_checksum_validation_required",
            "AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED",
            default=DEFAULT_CONFIG["audit_object_mirror_azure_checksum_validation_required"],
        ),
        default=False,
    )
    azure_blob_provider = mirror_provider.lower() in AZURE_BLOB_AUDIT_OBJECT_MIRROR_PROVIDERS
    if mirror_required and mirror_mode in DISABLED_AUDIT_OBJECT_MIRROR_MODES:
        add("audit_object_mirror_required_but_disabled", "AUDIT_OBJECT_MIRROR_REQUIRED=true requires AUDIT_OBJECT_MIRROR_MODE to be configured.")
    if mirror_required and mirror_mode in PLACEHOLDER_AUDIT_OBJECT_MIRROR_MODES and not azure_blob_provider:
        if not mirror_provider:
            add("audit_object_mirror_provider_missing", "AUDIT_OBJECT_MIRROR_PROVIDER is required when the object/WORM mirror is required.")
        if not mirror_container:
            add("audit_object_mirror_container_missing", "AUDIT_OBJECT_MIRROR_CONTAINER is required when the object/WORM mirror is required.")
        if not mirror_prefix:
            add("audit_object_mirror_prefix_missing", "AUDIT_OBJECT_MIRROR_PREFIX is required when the object/WORM mirror is required.")
    if mirror_required and mirror_mode in LOCAL_AUDIT_OBJECT_MIRROR_MODES and not local_simulation_allowed:
        add(
            "audit_object_mirror_local_without_simulation_flag",
            "Local filesystem audit mirror cannot satisfy required production WORM storage unless explicitly marked as simulation.",
        )
    if mirror_required and azure_blob_provider:
        if not azure_account_url:
            add(
                "audit_object_mirror_azure_account_url_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL is required when azure_blob mirroring is required.",
            )
        if not azure_container:
            add(
                "audit_object_mirror_azure_container_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_CONTAINER or AUDIT_OBJECT_MIRROR_CONTAINER is required when azure_blob mirroring is required.",
            )
        if not azure_prefix:
            add(
                "audit_object_mirror_azure_prefix_missing",
                "AUDIT_OBJECT_MIRROR_AZURE_PREFIX or AUDIT_OBJECT_MIRROR_PREFIX is required when azure_blob mirroring is required.",
            )
        if azure_credential_mode in UNSAFE_AZURE_CREDENTIAL_MODES:
            add(
                "audit_object_mirror_azure_credential_mode_unsafe",
                "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE is required and must not use inline account keys, connection strings, or plain secrets.",
            )
        elif azure_credential_mode not in SAFE_AZURE_CREDENTIAL_MODES:
            add(
                "audit_object_mirror_azure_credential_mode_unsupported",
                "AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE must use an approved Azure identity mode.",
            )
        if azure_enable_real_io and not _module_available("azure.storage.blob"):
            add(
                "audit_object_mirror_azure_sdk_missing",
                "azure-storage-blob is required when AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true.",
            )
        if (
            azure_enable_real_io
            and azure_credential_mode in SAFE_AZURE_CREDENTIAL_MODES
            and not _module_available("azure.identity")
        ):
            add(
                "audit_object_mirror_azure_identity_sdk_missing",
                "azure-identity is required for Azure identity credential modes when real Azure Blob I/O is enabled.",
            )
        if azure_immutability_required and not mirror_retention_policy:
            add(
                "audit_object_mirror_azure_immutability_policy_missing",
                "AUDIT_OBJECT_MIRROR_RETENTION_POLICY is required when Azure immutability validation is required.",
            )
        if (azure_legal_hold_required or legal_hold_required) and not legal_hold_reference:
            add(
                "audit_object_mirror_azure_legal_hold_reference_missing",
                "AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE is required when Azure legal hold validation is required.",
            )
        if azure_checksum_validation_required and azure_credential_mode in UNSAFE_AZURE_CREDENTIAL_MODES:
            add(
                "audit_object_mirror_azure_checksum_validation_config_missing",
                "Safe Azure credential mode is required when Azure checksum validation is required.",
            )
    if mirror_required and manifest_required and not mirror_retention_policy:
        add(
            "audit_object_mirror_retention_policy_missing",
            "AUDIT_OBJECT_MIRROR_RETENTION_POLICY is required when mirror manifests are required.",
        )
    if mirror_required and legal_hold_required and not legal_hold_reference:
        add(
            "audit_object_mirror_legal_hold_reference_missing",
            "AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE is required when legal hold is required.",
        )
    if mirror_required and manifest_signing_required and not manifest_required:
        add(
            "audit_object_mirror_signature_requires_manifest",
            "AUDIT_MANIFEST_SIGNING_REQUIRED=true requires AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=true.",
        )
    if mirror_required and manifest_required and manifest_signing_required:
        normalized_signing_algorithm = _normalized(manifest_signing_algorithm)
        if manifest_signing_mode not in SIGNING_MODES:
            add(
                "audit_manifest_signing_mode_unsupported",
                "AUDIT_MANIFEST_SIGNING_MODE must use an approved signing mode.",
            )
        if manifest_signing_mode == SIGNING_MODE_DISABLED:
            add(
                "audit_manifest_signing_required_but_disabled",
                "AUDIT_MANIFEST_SIGNING_REQUIRED=true requires AUDIT_MANIFEST_SIGNING_MODE to be configured.",
            )
        if manifest_signing_mode == SIGNING_MODE_CHECKSUM_PLACEHOLDER:
            add(
                "audit_manifest_signing_checksum_placeholder_in_production",
                "checksum_placeholder is a non-production fallback and cannot satisfy required production manifest signing.",
            )
        if manifest_signing_mode == SIGNING_MODE_LOCAL_HMAC_SHA256 and not manifest_allow_local_signing:
            add(
                "audit_manifest_local_hmac_not_allowed_in_production",
                "local_hmac_sha256 requires AUDIT_MANIFEST_ALLOW_LOCAL_SIGNING_IN_PRODUCTION=true in production-like environments.",
            )
        if manifest_signing_mode == SIGNING_MODE_LOCAL_HMAC_SHA256 and not manifest_local_hmac_key_configured:
            add(
                "audit_manifest_local_hmac_key_missing",
                "AUDIT_MANIFEST_LOCAL_HMAC_KEY must be configured outside Git when local HMAC manifest signing is enabled.",
            )
        if (
            manifest_signing_mode
            in {SIGNING_MODE_EXTERNAL_KMS_PLACEHOLDER, SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER}
            and not manifest_signing_key_ref
        ):
            add(
                "audit_manifest_signing_key_ref_missing",
                "AUDIT_MANIFEST_SIGNING_KEY_REF is required when external/KMS manifest signing is configured.",
            )
        if manifest_signing_mode == SIGNING_MODE_AZURE_KEY_VAULT_PLACEHOLDER:
            if not manifest_azure_key_vault_url:
                add(
                    "audit_manifest_azure_key_vault_url_missing",
                    "AUDIT_MANIFEST_AZURE_KEY_VAULT_URL is required for Azure Key Vault placeholder signing.",
                )
            if not manifest_azure_key_name:
                add(
                    "audit_manifest_azure_key_name_missing",
                    "AUDIT_MANIFEST_AZURE_KEY_NAME is required for Azure Key Vault placeholder signing.",
                )
        if (
            not normalized_signing_algorithm
            or normalized_signing_algorithm in UNSAFE_SIGNING_ALGORITHMS
            or normalized_signing_algorithm not in SAFE_SIGNING_ALGORITHMS
        ):
            add(
                "audit_manifest_signing_algorithm_unsafe",
                "AUDIT_MANIFEST_SIGNING_ALGORITHM must be an approved non-deprecated signing algorithm.",
            )

    try:
        analytics_profile = _configured_profile(
            source,
            "default_analytics_export_profile",
            "DEFAULT_ANALYTICS_EXPORT_PROFILE",
            "DEFAULT_EXPORT_PROFILE",
            default=DEFAULT_CONFIG["default_analytics_export_profile"],
        )
        if analytics_profile not in SAFE_ANALYTICS_EXPORT_PROFILES:
            add("unsafe_analytics_export_profile", "Default analytics export profile must be aggregate_safe or external_safe.")
    except ValueError as exc:
        add("unsafe_analytics_export_profile", str(exc))

    try:
        compliance_profile = _configured_profile(
            source,
            "default_compliance_export_profile",
            "DEFAULT_COMPLIANCE_EXPORT_PROFILE",
            default=DEFAULT_CONFIG["default_compliance_export_profile"],
        )
        if compliance_profile not in SAFE_COMPLIANCE_EXPORT_PROFILES:
            add("unsafe_compliance_export_profile", "Default compliance export profile must be compliance_evidence or audit_metadata.")
    except ValueError as exc:
        add("unsafe_compliance_export_profile", str(exc))

    try:
        audit_profile = _configured_profile(
            source,
            "default_audit_export_profile",
            "DEFAULT_AUDIT_EXPORT_PROFILE",
            default=DEFAULT_CONFIG["default_audit_export_profile"],
        )
        if audit_profile not in SAFE_AUDIT_EXPORT_PROFILES:
            add("unsafe_audit_export_profile", "Default audit evidence profile must be audit_metadata, aggregate_safe, or external_safe.")
    except ValueError as exc:
        add("unsafe_audit_export_profile", str(exc))

    redaction_disabled = _as_bool(_get(source, "phi_redaction_disabled", "PHI_REDACTION_DISABLED", default=False))
    redaction_enabled = _as_bool(_get(source, "phi_redaction_enabled", "PHI_REDACTION_ENABLED", default=DEFAULT_CONFIG["phi_redaction_enabled"]), default=True)
    if redaction_disabled or not redaction_enabled:
        add("phi_redaction_disabled", "PHI/ePHI redaction must remain enabled in production.")

    if _as_bool(_get(source, "allow_generic_foundation_commit", "ALLOW_GENERIC_FOUNDATION_COMMIT", default=DEFAULT_CONFIG["allow_generic_foundation_commit"])):
        add("generic_workflow_commit_enabled", "Generic foundation workflow commit must not be broadly enabled in production.")
    if not _as_bool(_get(source, "generic_workflow_commit_admin_only", "GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY", default=DEFAULT_CONFIG["generic_workflow_commit_admin_only"]), default=True):
        add("generic_workflow_commit_not_admin_only", "Generic foundation workflow commit must remain admin-only in production.")

    auth_disabled = _as_bool(_get(source, "auth_disabled", "AUTH_DISABLED", default=False))
    auth_enabled = _as_bool(_get(source, "authentication_enabled", "AUTHENTICATION_ENABLED", default=DEFAULT_CONFIG["authentication_enabled"]), default=True)
    if auth_disabled or not auth_enabled:
        add("authentication_disabled", "Authentication must be enabled in production.")
    if _as_bool(_get(source, "allow_demo_auth_bypass", "ALLOW_DEMO_AUTH_BYPASS", "TEST_AUTH_BYPASS_ENABLED", default=DEFAULT_CONFIG["allow_demo_auth_bypass"])):
        add("demo_auth_bypass_enabled", "Demo/test authentication bypass flags must be disabled in production.")
    if _as_bool(_get(source, "demo_users_enabled", "DEMO_USERS_ENABLED", "ENABLE_DEMO_USERS", default=False)):
        add("demo_users_enabled", "Demo user creation or demo-user mode must not be enabled in production.")

    mfa_bypass = _text(_get(source, "mfa_dev_bypass_code", "MFA_DEV_BYPASS_CODE", default=DEFAULT_CONFIG["mfa_dev_bypass_code"]))
    if not mfa_bypass or mfa_bypass in UNSAFE_MFA_BYPASS_CODES or len(mfa_bypass) < 8 or len(set(mfa_bypass)) == 1:
        add("mfa_dev_bypass_unsafe", "MFA_DEV_BYPASS_CODE must not be missing, predictable, or the local demo default in production.")

    if production_like:
        return ProductionSecurityGateResult(
            environment=environment,
            production_like=True,
            failures=tuple(issues),
            warnings=(),
        )
    warnings = tuple(
        ProductionSecurityGateIssue(code=issue.code, message=issue.message, severity="warning")
        for issue in issues
    )
    return ProductionSecurityGateResult(
        environment=environment,
        production_like=False,
        failures=(),
        warnings=warnings,
    )


def format_gate_failure(result: ProductionSecurityGateResult) -> str:
    lines = [
        "Production security gate failed. Refusing to start with unsafe production configuration.",
        f"environment={result.environment}",
    ]
    for issue in result.failures:
        lines.append(f"- {issue.code}: {issue.message}")
    return "\n".join(lines)


def assert_production_security_gates(
    config: Mapping[str, Any] | object | None = None,
    *,
    strict: bool | None = None,
) -> ProductionSecurityGateResult:
    result = validate_production_security_gates(config, strict=strict)
    if result.failures:
        raise RuntimeError(format_gate_failure(result))
    for issue in result.warnings:
        logger.warning("production_security_gate_warning code=%s message=%s", issue.code, issue.message)
    return result
