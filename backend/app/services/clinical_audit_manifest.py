from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ClinicalWorkflowAuditEvent,
    ClinicalWorkflowAuditMirrorEvent,
    ClinicalWorkflowAuditMirrorManifest,
)
from app.services.clinical_audit_mirror import (
    AUDIT_MIRROR_STATUS_MIRRORED,
    AuditMirrorConfig,
    audit_mirror_config_from_settings,
    read_db_mirror_events,
)
from app.services.clinical_audit_mirror_providers import (
    AuditMirrorProvider,
    get_audit_mirror_provider,
    provider_readiness_summary,
)
from app.services.clinical_audit_signing import (
    ALGORITHM_CHECKSUM_PLACEHOLDER,
    SIGNATURE_STATUS_CHECKSUM_PLACEHOLDER,
    SIGNATURE_STATUS_NOT_REQUIRED,
    SIGNING_MODE_CHECKSUM_PLACEHOLDER,
    SIGNING_MODE_DISABLED,
    AuditManifestSigningConfig,
    audit_manifest_signing_config_from_settings,
    azure_key_vault_key_reference,
    canonical_signing_payload,
    sign_manifest_checksum,
    signature_status_for_config,
    verify_manifest_signature,
)

AUDIT_MANIFEST_SCHEMA_VERSION = "clinical.workflow_audit.manifest.v1"
AUDIT_MANIFEST_STATUS_GENERATED = "generated"
AUDIT_MANIFEST_SIGNATURE_NOT_REQUIRED = SIGNATURE_STATUS_NOT_REQUIRED
AUDIT_MANIFEST_SIGNATURE_PLACEHOLDER = SIGNATURE_STATUS_CHECKSUM_PLACEHOLDER
AUDIT_MANIFEST_HASH_ALGORITHM = "sha256"
AUDIT_MANIFEST_DEFAULT_SIGNATURE_ALGORITHM = ALGORITHM_CHECKSUM_PLACEHOLDER
AUDIT_MANIFEST_CHECKSUM_EXCLUDED_FIELDS = {
    "manifest_checksum",
    "manifest_uri",
    "signature",
    "signature_reason",
    "signature_verification",
}


@dataclass(frozen=True)
class AuditManifestConfig:
    environment: str = "dev"
    generated_by: str = "system"
    mirror_mode: str = "disabled"
    provider: str = ""
    uri_prefix: str = "local-worm://clinical-audit"
    retention_policy: str = ""
    legal_hold: bool = False
    legal_hold_reference: str = ""
    manifest_required: bool = False
    signature_required: bool = False
    signing_mode: str = SIGNING_MODE_DISABLED
    signature_algorithm: str = AUDIT_MANIFEST_DEFAULT_SIGNATURE_ALGORITHM
    signature_key_ref: str = ""
    local_hmac_key: str = ""
    allow_local_signing_in_production: bool = False
    azure_key_vault_url: str = ""
    azure_key_name: str = ""
    azure_key_version: str = ""
    azure_key_vault_credential_mode: str = ""
    azure_key_vault_enable_real_io: bool = False
    azure_key_vault_require_hsm: bool = False

    @property
    def normalized_mirror_mode(self) -> str:
        return str(self.mirror_mode or "disabled").strip().lower()

    def signing_config(self) -> AuditManifestSigningConfig:
        signing_mode = str(self.signing_mode or "").strip().lower()
        if self.signature_required and signing_mode in {"", SIGNING_MODE_DISABLED}:
            signing_mode = SIGNING_MODE_CHECKSUM_PLACEHOLDER
        return AuditManifestSigningConfig(
            mode=signing_mode or SIGNING_MODE_DISABLED,
            required=self.signature_required,
            algorithm=self.signature_algorithm,
            key_ref=self.signature_key_ref,
            local_hmac_key=self.local_hmac_key,
            allow_local_signing_in_production=self.allow_local_signing_in_production,
            azure_key_vault_url=self.azure_key_vault_url,
            azure_key_name=self.azure_key_name,
            azure_key_version=self.azure_key_version,
            azure_key_vault_credential_mode=self.azure_key_vault_credential_mode,
            azure_key_vault_enable_real_io=self.azure_key_vault_enable_real_io,
            azure_key_vault_require_hsm=self.azure_key_vault_require_hsm,
            environment=self.environment,
        )


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y", "on", "enabled"}:
        return True
    if lowered in {"0", "false", "no", "n", "off", "disabled"}:
        return False
    return default


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _canonical_json(data: dict[str, Any]) -> str:
    return canonical_signing_payload(data)


def audit_manifest_checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def audit_manifest_config_from_settings(source: Any = settings) -> AuditManifestConfig:
    mirror_config = audit_mirror_config_from_settings(source)
    signing_config = audit_manifest_signing_config_from_settings(source)
    return AuditManifestConfig(
        environment=_text(
            getattr(source, "app_env", "")
            or getattr(source, "environment", "")
            or getattr(source, "clinical_env", "")
            or "dev"
        ),
        generated_by="system",
        mirror_mode=mirror_config.normalized_mode,
        provider=mirror_config.object_provider,
        uri_prefix=mirror_config.uri_prefix,
        retention_policy=_text(getattr(source, "audit_object_mirror_retention_policy", "")),
        legal_hold=_as_bool(getattr(source, "audit_object_mirror_legal_hold_required", False)),
        legal_hold_reference=_text(getattr(source, "audit_object_mirror_legal_hold_reference", "")),
        manifest_required=_as_bool(getattr(source, "audit_object_mirror_manifest_required", False)),
        signature_required=signing_config.required,
        signing_mode=signing_config.normalized_mode,
        signature_algorithm=signing_config.effective_algorithm or AUDIT_MANIFEST_DEFAULT_SIGNATURE_ALGORITHM,
        signature_key_ref=signing_config.key_ref,
        local_hmac_key=signing_config.local_hmac_key,
        allow_local_signing_in_production=signing_config.allow_local_signing_in_production,
        azure_key_vault_url=signing_config.azure_key_vault_url,
        azure_key_name=signing_config.azure_key_name,
        azure_key_version=signing_config.azure_key_version,
        azure_key_vault_credential_mode=signing_config.azure_key_vault_credential_mode,
        azure_key_vault_enable_real_io=signing_config.azure_key_vault_enable_real_io,
        azure_key_vault_require_hsm=signing_config.azure_key_vault_require_hsm,
    )


def _event_sort_key(event: ClinicalWorkflowAuditMirrorEvent) -> tuple[str, str, str]:
    return (
        str(event.operation_id or ""),
        str(event.mirror_uri or ""),
        str(event.mirror_checksum or ""),
    )


def successful_mirror_events(
    events: list[ClinicalWorkflowAuditMirrorEvent],
) -> list[ClinicalWorkflowAuditMirrorEvent]:
    latest_by_operation: dict[str, ClinicalWorkflowAuditMirrorEvent] = {}
    for event in sorted(events, key=_event_sort_key):
        if event.mirror_status != AUDIT_MIRROR_STATUS_MIRRORED or event.dry_run:
            continue
        if not event.operation_id or not event.mirror_uri or not event.mirror_checksum:
            continue
        latest_by_operation[str(event.operation_id)] = event
    return [latest_by_operation[key] for key in sorted(latest_by_operation)]


def _generated_at_from_events(
    events: list[ClinicalWorkflowAuditMirrorEvent],
    generated_at: datetime | None,
) -> datetime:
    if generated_at is not None:
        return generated_at
    candidates = [
        value
        for event in events
        for value in (getattr(event, "mirrored_at", None), getattr(event, "created_at", None))
        if isinstance(value, datetime)
    ]
    if candidates:
        latest = max(candidates)
        if latest.tzinfo is None:
            return latest.replace(tzinfo=UTC)
        return latest
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _manifest_objects(events: list[ClinicalWorkflowAuditMirrorEvent]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for event in successful_mirror_events(events):
        mirrored_at = getattr(event, "mirrored_at", None)
        objects.append(
            {
                "operation_id": event.operation_id,
                "mirror_uri": event.mirror_uri,
                "checksum": event.mirror_checksum,
                "mirrored_at": _iso(mirrored_at) if isinstance(mirrored_at, datetime) else None,
            }
        )
    return objects


def _manifest_fingerprint(base: dict[str, Any]) -> str:
    fingerprint_source = {
        "schema_version": base["schema_version"],
        "generated_at": base["generated_at"],
        "generated_by": base["generated_by"],
        "environment": base["environment"],
        "mirror": base["mirror"],
        "retention": base["retention"],
        "audit_event_count": base["audit_event_count"],
        "operation_ids": base["operation_ids"],
        "objects": base["objects"],
    }
    return audit_manifest_checksum(fingerprint_source)


def generate_audit_mirror_manifest(
    mirror_events: list[ClinicalWorkflowAuditMirrorEvent],
    *,
    config: AuditManifestConfig | None = None,
    generated_at: datetime | None = None,
    generated_by: str | None = None,
    signing_client: Any | None = None,
    signing_client_factory: Any | None = None,
) -> dict[str, Any]:
    active_config = config or audit_manifest_config_from_settings()
    objects = _manifest_objects(mirror_events)
    generated_at_value = _generated_at_from_events(successful_mirror_events(mirror_events), generated_at)
    operation_ids = [item["operation_id"] for item in objects]
    signing_config = active_config.signing_config()
    signature_status = signature_status_for_config(signing_config)
    signature_algorithm = signing_config.effective_algorithm or None
    signature_key_ref = azure_key_vault_key_reference(signing_config) or signing_config.key_ref or None
    base = {
        "schema_version": AUDIT_MANIFEST_SCHEMA_VERSION,
        "generated_at": _iso(generated_at_value),
        "generated_by": generated_by or active_config.generated_by,
        "environment": active_config.environment,
        "mirror": {
            "mode": active_config.normalized_mirror_mode,
            "provider": active_config.provider,
            "uri_prefix": active_config.uri_prefix,
        },
        "retention": {
            "policy_reference": active_config.retention_policy,
            "legal_hold": active_config.legal_hold,
            "legal_hold_reference": active_config.legal_hold_reference,
        },
        "audit_event_count": len(objects),
        "operation_ids": operation_ids,
        "objects": objects,
        "hash_algorithm": AUDIT_MANIFEST_HASH_ALGORITHM,
        "signing_mode": signing_config.normalized_mode,
        "signature_status": signature_status,
        "signature_algorithm": signature_algorithm,
        "signature_key_ref": signature_key_ref,
    }
    manifest_id = f"audit-manifest-{_manifest_fingerprint(base)[:24]}"
    unsigned_manifest = {"manifest_id": manifest_id, **base}
    manifest_checksum = audit_manifest_checksum(unsigned_manifest)
    signature_result = sign_manifest_checksum(
        manifest_checksum,
        signing_config,
        signing_client=signing_client,
        signing_client_factory=signing_client_factory,
    )
    return {
        **unsigned_manifest,
        "manifest_checksum": manifest_checksum,
        "signature": signature_result.signature,
        "signature_status": signature_result.status,
        "signature_algorithm": signature_result.algorithm,
        "signature_key_ref": signature_result.key_ref,
        "signing_mode": signature_result.mode,
        "signature_reason": signature_result.reason,
    }


def manifest_to_event(manifest: dict[str, Any]) -> ClinicalWorkflowAuditMirrorManifest:
    mirror = manifest.get("mirror") or {}
    retention = manifest.get("retention") or {}
    generated_at = manifest.get("generated_at")
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if not isinstance(generated_at, datetime):
        generated_at = datetime.now(UTC)
    return ClinicalWorkflowAuditMirrorManifest(
        manifest_id=str(manifest["manifest_id"]),
        manifest_status=AUDIT_MANIFEST_STATUS_GENERATED,
        mirror_mode=str(mirror.get("mode") or ""),
        provider=str(mirror.get("provider") or ""),
        uri_prefix=str(mirror.get("uri_prefix") or ""),
        audit_event_count=int(manifest.get("audit_event_count") or 0),
        manifest_checksum=str(manifest.get("manifest_checksum") or ""),
        signature_status=str(manifest.get("signature_status") or AUDIT_MANIFEST_SIGNATURE_NOT_REQUIRED),
        signature_algorithm=manifest.get("signature_algorithm"),
        signature_key_ref=manifest.get("signature_key_ref"),
        retention_policy=str(retention.get("policy_reference") or ""),
        legal_hold=bool(retention.get("legal_hold")),
        legal_hold_reference=retention.get("legal_hold_reference"),
        manifest_uri=manifest.get("manifest_uri"),
        generated_at=generated_at,
        generated_by=str(manifest.get("generated_by") or "system"),
    )


def _manifest_without_checksum_fields(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in AUDIT_MANIFEST_CHECKSUM_EXCLUDED_FIELDS
    }


def _signing_config_for_manifest(
    manifest: dict[str, Any],
    config: AuditManifestSigningConfig | None,
) -> AuditManifestSigningConfig:
    source = config or audit_manifest_signing_config_from_settings()
    signature_status = str(manifest.get("signature_status") or "")
    mode = str(manifest.get("signing_mode") or source.normalized_mode or "").strip().lower()
    if not mode and signature_status == AUDIT_MANIFEST_SIGNATURE_PLACEHOLDER:
        mode = SIGNING_MODE_CHECKSUM_PLACEHOLDER
    required = source.required or signature_status not in {"", AUDIT_MANIFEST_SIGNATURE_NOT_REQUIRED}
    return AuditManifestSigningConfig(
        mode=mode or SIGNING_MODE_DISABLED,
        required=required,
        algorithm=str(manifest.get("signature_algorithm") or source.effective_algorithm or ""),
        key_ref=str(manifest.get("signature_key_ref") or source.key_ref or ""),
        local_hmac_key=source.local_hmac_key,
        allow_local_signing_in_production=source.allow_local_signing_in_production,
        azure_key_vault_url=source.azure_key_vault_url,
        azure_key_name=source.azure_key_name,
        azure_key_version=source.azure_key_version,
        azure_key_vault_credential_mode=source.azure_key_vault_credential_mode,
        azure_key_vault_enable_real_io=source.azure_key_vault_enable_real_io,
        azure_key_vault_require_hsm=source.azure_key_vault_require_hsm,
        environment=source.environment,
    )


def verify_audit_mirror_manifest(
    manifest: dict[str, Any],
    *,
    signing_config: AuditManifestSigningConfig | None = None,
    signing_client: Any | None = None,
    signing_client_factory: Any | None = None,
) -> dict[str, Any]:
    expected_checksum = audit_manifest_checksum(_manifest_without_checksum_fields(manifest))
    recorded_checksum = str(manifest.get("manifest_checksum") or "")
    checksum_verified = bool(recorded_checksum) and expected_checksum == recorded_checksum
    active_signing_config = _signing_config_for_manifest(manifest, signing_config)
    signature_verification = verify_manifest_signature(
        manifest_checksum=expected_checksum,
        signature=manifest.get("signature"),
        config=active_signing_config,
        signing_client=signing_client,
        signing_client_factory=signing_client_factory,
    )
    signature_status = signature_verification["signature_verification_status"]
    blocking_signature_statuses = {
        "failed",
        "missing_signature",
        "unsupported_signing_mode",
    }
    blocking = (not checksum_verified) or signature_status in blocking_signature_statuses
    return {
        "manifest_id": manifest.get("manifest_id"),
        "checksum_status": "verified" if checksum_verified else "checksum_mismatch",
        "recorded_checksum": recorded_checksum,
        "computed_checksum": expected_checksum,
        "signature_verification": signature_verification,
        "signature_verification_status": signature_status,
        "blocking": blocking,
        "verified": not blocking,
    }


def record_audit_mirror_manifest(
    db: Session,
    manifest: dict[str, Any],
    *,
    commit: bool = True,
) -> ClinicalWorkflowAuditMirrorManifest:
    event = manifest_to_event(manifest)
    db.add(event)
    db.flush()
    if commit:
        db.commit()
    return event


def read_db_mirror_manifests(db: Session) -> list[ClinicalWorkflowAuditMirrorManifest]:
    try:
        return list(
            db.execute(
                select(ClinicalWorkflowAuditMirrorManifest).order_by(
                    ClinicalWorkflowAuditMirrorManifest.generated_at.asc(),
                    ClinicalWorkflowAuditMirrorManifest.id.asc(),
                )
            )
            .scalars()
            .all()
        )
    except (SQLAlchemyError, AttributeError, TypeError):
        return []


def _manifest_object_map(manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    return {
        str(item.get("operation_id")): item
        for item in manifest.get("objects", [])
        if item.get("operation_id")
    }


def verify_mirror_inventory(
    mirror_events: list[ClinicalWorkflowAuditMirrorEvent],
    *,
    config: AuditMirrorConfig | None = None,
    manifest: dict[str, Any] | None = None,
    dry_run: bool = False,
    provider: AuditMirrorProvider | None = None,
) -> dict[str, Any]:
    active_config = config or audit_mirror_config_from_settings()
    active_provider = provider or get_audit_mirror_provider(active_config)
    events = successful_mirror_events(mirror_events)
    manifest_objects = _manifest_object_map(manifest)
    seen_operation_ids: set[str] = set()
    results: list[dict[str, Any]] = []
    verified = 0
    missing = 0
    mismatched = 0
    manifest_mismatched = 0
    skipped = 0

    for event in events:
        operation_id = str(event.operation_id)
        seen_operation_ids.add(operation_id)
        result = {
            "operation_id": operation_id,
            "mirror_uri": event.mirror_uri,
            "recorded_checksum": event.mirror_checksum,
            "computed_checksum": None,
            "status": "planned" if dry_run else "verified",
            "reason": None,
        }

        manifest_object = manifest_objects.get(operation_id)
        if manifest is not None:
            if manifest_object is None:
                result["status"] = "manifest_mismatch"
                result["reason"] = "mirror event missing from manifest"
                manifest_mismatched += 1
            elif (
                manifest_object.get("mirror_uri") != event.mirror_uri
                or manifest_object.get("checksum") != event.mirror_checksum
            ):
                result["status"] = "manifest_mismatch"
                result["reason"] = "manifest URI or checksum differs from mirror event"
                manifest_mismatched += 1

        if dry_run:
            skipped += 1
            results.append(result)
            continue

        if not event.mirror_uri or not event.mirror_checksum:
            result["status"] = "missing"
            result["reason"] = "mirror URI or checksum missing"
            missing += 1
            results.append(result)
            continue

        try:
            provider_result = active_provider.verify_object_checksum(
                str(event.mirror_uri),
                str(event.mirror_checksum),
            )
        except Exception as exc:
            if result["status"] == "verified":
                result["status"] = "skipped"
                result["reason"] = f"provider verification unavailable: {exc}"
            skipped += 1
            results.append(result)
            continue

        result["computed_checksum"] = provider_result.get("computed_checksum")
        provider_status = str(provider_result.get("status") or "")
        if provider_status == "verified":
            if result["status"] == "verified":
                verified += 1
        elif provider_status == "missing":
            result["status"] = "missing"
            result["reason"] = provider_result.get("reason")
            missing += 1
        elif provider_status == "checksum_mismatch":
            result["status"] = "checksum_mismatch"
            result["reason"] = provider_result.get("reason")
            mismatched += 1
        else:
            if result["status"] == "verified":
                result["status"] = "skipped"
                result["reason"] = provider_result.get("reason") or "provider verification did not check checksum"
            skipped += 1
        results.append(result)

    manifest_only_operation_ids = sorted(set(manifest_objects) - seen_operation_ids)
    manifest_mismatched += len(manifest_only_operation_ids)
    return {
        "checked": len(events),
        "verified": verified,
        "missing": missing,
        "mismatched": mismatched,
        "manifest_mismatched": manifest_mismatched,
        "skipped": skipped,
        "dry_run": dry_run,
        "manifest_only_operation_ids": manifest_only_operation_ids,
        "provider": active_provider.name,
        "results": results,
    }


def _read_db_audit_events(db: Session) -> list[ClinicalWorkflowAuditEvent]:
    try:
        return list(
            db.execute(
                select(ClinicalWorkflowAuditEvent).order_by(
                    ClinicalWorkflowAuditEvent.timestamp.asc(),
                    ClinicalWorkflowAuditEvent.id.asc(),
                )
            )
            .scalars()
            .all()
        )
    except (SQLAlchemyError, AttributeError, TypeError):
        return []


def _in_range(
    event: ClinicalWorkflowAuditEvent,
    *,
    start_at: datetime | None,
    end_at: datetime | None,
) -> bool:
    timestamp = event.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    if start_at is not None:
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=UTC)
        if timestamp < start_at:
            return False
    if end_at is not None:
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=UTC)
        if timestamp > end_at:
            return False
    return True


def audit_mirror_recovery_drill_summary(
    db: Session,
    *,
    config: AuditMirrorConfig | None = None,
    manifest: dict[str, Any] | None = None,
    manifest_signing_config: AuditManifestSigningConfig | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    dry_run: bool = False,
    provider: AuditMirrorProvider | None = None,
) -> dict[str, Any]:
    active_config = config or audit_mirror_config_from_settings()
    active_provider = provider or get_audit_mirror_provider(active_config)
    audit_events = [
        event
        for event in _read_db_audit_events(db)
        if _in_range(event, start_at=start_at, end_at=end_at)
    ]
    audit_ids = {event.operation_id for event in audit_events}
    mirror_events = [
        event
        for event in read_db_mirror_events(db)
        if event.operation_id in audit_ids
        and event.mirror_status == AUDIT_MIRROR_STATUS_MIRRORED
        and not event.dry_run
    ]
    mirrored_ids = {event.operation_id for event in mirror_events}
    verification = verify_mirror_inventory(
        mirror_events,
        config=active_config,
        manifest=manifest,
        dry_run=dry_run,
        provider=active_provider,
    )
    manifest_signature_verification = (
        verify_audit_mirror_manifest(manifest, signing_config=manifest_signing_config)
        if manifest is not None
        else {
            "checksum_status": "not_checked",
            "signature_verification_status": "not_checked_no_manifest",
            "blocking": False,
            "verified": False,
        }
    )
    provider_readiness = active_provider.readiness_summary() if provider is not None else provider_readiness_summary(active_config)
    manifest_count = len(read_db_mirror_manifests(db))
    missing_mirror_operation_ids = sorted(audit_ids - mirrored_ids)
    orphan_mirror_operation_ids = sorted(
        {
            event.operation_id
            for event in read_db_mirror_events(db)
            if event.mirror_status == AUDIT_MIRROR_STATUS_MIRRORED
            and not event.dry_run
            and event.operation_id not in audit_ids
        }
    )
    blocking_findings = (
        len(missing_mirror_operation_ids)
        + verification["missing"]
        + verification["mismatched"]
        + verification["manifest_mismatched"]
        + (1 if manifest_signature_verification["blocking"] else 0)
    )
    return {
        "source_deleted": False,
        "dry_run": dry_run,
        "provider_readiness": provider_readiness,
        "selected_audit_event_count": len(audit_events),
        "successful_mirror_event_count": len(mirror_events),
        "mirrored_object_count": len(mirror_events),
        "manifest_count": manifest_count,
        "missing_mirror_count": len(missing_mirror_operation_ids),
        "missing_mirror_operation_ids": missing_mirror_operation_ids,
        "orphan_mirror_count": len(orphan_mirror_operation_ids),
        "orphan_mirror_operation_ids": orphan_mirror_operation_ids,
        "verification": verification,
        "manifest_signature_verification": manifest_signature_verification,
        "recovery_ready": blocking_findings == 0,
    }
