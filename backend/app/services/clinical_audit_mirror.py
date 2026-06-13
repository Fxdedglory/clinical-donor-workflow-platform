from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ClinicalWorkflowAuditEvent, ClinicalWorkflowAuditMirrorEvent
from app.schemas.clinical import WorkflowOperation
from app.services.clinical_phi import redact_audit_changes

AUDIT_MIRROR_PROFILE = "audit_metadata"
AUDIT_MIRROR_SCHEMA_VERSION = "clinical.workflow_audit.mirror.v1"
AUDIT_MIRROR_STATUS_DISABLED = "disabled"
AUDIT_MIRROR_STATUS_DRY_RUN = "dry_run"
AUDIT_MIRROR_STATUS_FAILED = "failed"
AUDIT_MIRROR_STATUS_MIRRORED = "mirrored"
AUDIT_MIRROR_STATUS_SKIPPED = "skipped"

DISABLED_MIRROR_MODES = {"", "disabled", "off", "none"}
LOCAL_MIRROR_MODES = {"local", "local_filesystem", "filesystem", "file"}
PLACEHOLDER_OBJECT_MODES = {"object_storage", "provider_placeholder", "worm_placeholder"}
AZURE_BLOB_PROVIDER_ALIASES = {"azure", "azure_blob", "azure_blob_storage", "azure_blob_immutability"}


class AuditMirrorError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuditMirrorConfig:
    mode: str = "disabled"
    required: bool = False
    local_root: Path = Path("metadata/audit_worm_mirror")
    uri_prefix: str = "local-worm://clinical-audit"
    object_provider: str = ""
    object_container: str = ""
    object_prefix: str = "workflow-audit"
    allow_local_production_simulation: bool = False
    retention_policy: str = ""
    legal_hold_reference: str = ""
    azure_account_url: str = ""
    azure_container: str = ""
    azure_prefix: str = ""
    azure_credential_mode: str = ""
    azure_enable_real_io: bool = False
    azure_immutability_required: bool = False
    azure_legal_hold_required: bool = False
    azure_checksum_validation_required: bool = False

    @property
    def normalized_mode(self) -> str:
        return str(self.mode or "disabled").strip().lower()

    @property
    def disabled(self) -> bool:
        return self.normalized_mode in DISABLED_MIRROR_MODES

    @property
    def local_filesystem(self) -> bool:
        return self.normalized_mode in LOCAL_MIRROR_MODES

    @property
    def object_placeholder(self) -> bool:
        return self.normalized_mode in PLACEHOLDER_OBJECT_MODES


@dataclass(frozen=True)
class AuditMirrorResult:
    operation_id: str
    mirror_mode: str
    mirror_status: str
    payload_profile: str = AUDIT_MIRROR_PROFILE
    mirrored_at: datetime | None = None
    mirror_uri: str | None = None
    mirror_checksum: str | None = None
    mirror_error: str | None = None
    dry_run: bool = False


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


def audit_mirror_config_from_settings(source: Any = settings) -> AuditMirrorConfig:
    object_container = str(getattr(source, "audit_object_mirror_container", "") or "")
    object_prefix = str(getattr(source, "audit_object_mirror_prefix", "workflow-audit") or "workflow-audit")
    return AuditMirrorConfig(
        mode=getattr(source, "audit_object_mirror_mode", "disabled"),
        required=_as_bool(getattr(source, "audit_object_mirror_required", False)),
        local_root=Path(getattr(source, "audit_object_mirror_local_root", "metadata/audit_worm_mirror")),
        uri_prefix=str(getattr(source, "audit_object_mirror_uri_prefix", "local-worm://clinical-audit") or ""),
        object_provider=str(getattr(source, "audit_object_mirror_provider", "") or ""),
        object_container=object_container,
        object_prefix=object_prefix,
        allow_local_production_simulation=_as_bool(
            getattr(source, "audit_object_mirror_allow_local_production_simulation", False)
        ),
        retention_policy=str(getattr(source, "audit_object_mirror_retention_policy", "") or ""),
        legal_hold_reference=str(getattr(source, "audit_object_mirror_legal_hold_reference", "") or ""),
        azure_account_url=str(getattr(source, "audit_object_mirror_azure_account_url", "") or ""),
        azure_container=str(getattr(source, "audit_object_mirror_azure_container", "") or object_container),
        azure_prefix=str(getattr(source, "audit_object_mirror_azure_prefix", "") or object_prefix),
        azure_credential_mode=str(getattr(source, "audit_object_mirror_azure_credential_mode", "") or ""),
        azure_enable_real_io=_as_bool(getattr(source, "audit_object_mirror_azure_enable_real_io", False)),
        azure_immutability_required=_as_bool(
            getattr(source, "audit_object_mirror_azure_immutability_required", False)
        ),
        azure_legal_hold_required=_as_bool(
            getattr(source, "audit_object_mirror_azure_legal_hold_required", False)
        ),
        azure_checksum_validation_required=_as_bool(
            getattr(source, "audit_object_mirror_azure_checksum_validation_required", False)
        ),
    )


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def audit_mirror_checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _redacted_operation(operation: WorkflowOperation) -> WorkflowOperation:
    return operation.model_copy(update={"changes": redact_audit_changes(operation.changes)})


def audit_mirror_payload(operation: WorkflowOperation) -> dict[str, Any]:
    redacted = _redacted_operation(operation)
    return {
        "schema_version": AUDIT_MIRROR_SCHEMA_VERSION,
        "payload_profile": AUDIT_MIRROR_PROFILE,
        "redacted": True,
        "operation": redacted.model_dump(mode="json"),
    }


def workflow_operation_from_audit_event(event: ClinicalWorkflowAuditEvent) -> WorkflowOperation:
    return WorkflowOperation(
        operation_id=event.operation_id,
        workflow=event.workflow,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        actor=event.actor,
        timestamp=event.timestamp,
        preview_hash=event.preview_hash,
        commit_confirmed=event.commit_confirmed,
        status_before=event.status_before,
        status_after=event.status_after,
        reason=event.reason,
        changes=event.changes_json or {},
    )


def _safe_path_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return token.strip(".-") or "unknown"


def _is_azure_blob_provider(config: AuditMirrorConfig) -> bool:
    return (config.object_provider or "").strip().lower() in AZURE_BLOB_PROVIDER_ALIASES


def _mirror_relative_path(operation: WorkflowOperation, config: AuditMirrorConfig) -> Path:
    timestamp = operation.timestamp
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    workflow = _safe_path_token(operation.workflow)
    operation_id = _safe_path_token(operation.operation_id)
    object_prefix = config.azure_prefix if _is_azure_blob_provider(config) and config.azure_prefix else config.object_prefix
    return Path(object_prefix) / workflow / timestamp.strftime("%Y") / timestamp.strftime("%m") / f"{operation_id}.json"


def _mirror_uri(config: AuditMirrorConfig, relative_path: Path) -> str:
    relative = relative_path.as_posix()
    if _is_azure_blob_provider(config):
        account_url = config.azure_account_url.rstrip("/")
        container = (config.azure_container or config.object_container).strip("/")
        if account_url and container:
            return f"{account_url}/{container}/{relative}"
    if config.uri_prefix:
        return f"{config.uri_prefix.rstrip('/')}/{relative}"
    return relative


def _write_local_mirror(operation: WorkflowOperation, config: AuditMirrorConfig, payload: dict[str, Any], checksum: str) -> str:
    relative_path = _mirror_relative_path(operation, config)
    target = config.local_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if target.exists():
        existing_payload = json.loads(target.read_text(encoding="utf-8"))
        existing_checksum = audit_mirror_checksum(existing_payload)
        if existing_checksum != checksum:
            raise AuditMirrorError(f"Audit mirror target already exists with a different checksum: {target}")
        return _mirror_uri(config, relative_path)
    target.write_text(encoded, encoding="utf-8")
    return _mirror_uri(config, relative_path)


def mirror_workflow_operation(
    operation: WorkflowOperation,
    *,
    config: AuditMirrorConfig | None = None,
    dry_run: bool = False,
) -> AuditMirrorResult:
    active_config = config or audit_mirror_config_from_settings()
    payload = audit_mirror_payload(operation)
    checksum = audit_mirror_checksum(payload)
    mode = active_config.normalized_mode

    if active_config.disabled:
        if active_config.required:
            raise AuditMirrorError("Audit object mirror is required but disabled.")
        return AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=mode,
            mirror_status=AUDIT_MIRROR_STATUS_DISABLED,
            mirror_checksum=checksum,
        )

    if dry_run:
        return AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=mode,
            mirror_status=AUDIT_MIRROR_STATUS_DRY_RUN,
            mirror_uri=_mirror_uri(active_config, _mirror_relative_path(operation, active_config)),
            mirror_checksum=checksum,
            dry_run=True,
        )

    if active_config.local_filesystem:
        uri = _write_local_mirror(operation, active_config, payload, checksum)
        return AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=mode,
            mirror_status=AUDIT_MIRROR_STATUS_MIRRORED,
            mirrored_at=datetime.now(UTC),
            mirror_uri=uri,
            mirror_checksum=checksum,
        )

    if _is_azure_blob_provider(active_config):
        if not active_config.azure_enable_real_io:
            message = "Azure Blob real I/O is disabled; AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true is required for object writes."
            if active_config.required:
                raise AuditMirrorError(message)
            return AuditMirrorResult(
                operation_id=operation.operation_id,
                mirror_mode=mode,
                mirror_status=AUDIT_MIRROR_STATUS_SKIPPED,
                mirror_checksum=checksum,
                mirror_error=message,
            )
        from app.services.clinical_audit_mirror_providers import get_audit_mirror_provider

        relative_path = _mirror_relative_path(operation, active_config)
        provider = get_audit_mirror_provider(active_config)
        stat = provider.put_object(relative_path.as_posix(), payload, checksum)
        if stat.reason and stat.checksum != checksum:
            raise AuditMirrorError(f"Audit mirror target was not written: {stat.reason}")
        if not stat.exists:
            raise AuditMirrorError("Azure Blob provider did not confirm mirrored object existence.")
        return AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=mode,
            mirror_status=AUDIT_MIRROR_STATUS_MIRRORED,
            mirrored_at=datetime.now(UTC),
            mirror_uri=stat.uri,
            mirror_checksum=stat.checksum or checksum,
        )

    if active_config.object_placeholder:
        message = "Object-storage/WORM provider integration is configured as a placeholder only."
        if active_config.required:
            raise AuditMirrorError(message)
        return AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=mode,
            mirror_status=AUDIT_MIRROR_STATUS_SKIPPED,
            mirror_checksum=checksum,
            mirror_error=message,
        )

    raise AuditMirrorError(f"Unsupported audit object mirror mode: {active_config.mode}")


def mirror_result_to_event(result: AuditMirrorResult) -> ClinicalWorkflowAuditMirrorEvent:
    return ClinicalWorkflowAuditMirrorEvent(
        operation_id=result.operation_id,
        mirror_mode=result.mirror_mode,
        mirror_status=result.mirror_status,
        payload_profile=result.payload_profile,
        mirrored_at=result.mirrored_at,
        mirror_uri=result.mirror_uri,
        mirror_checksum=result.mirror_checksum,
        mirror_error=result.mirror_error,
        dry_run=result.dry_run,
    )


def record_mirror_result(db: Session, result: AuditMirrorResult, *, commit: bool = True) -> ClinicalWorkflowAuditMirrorEvent:
    event = mirror_result_to_event(result)
    db.add(event)
    db.flush()
    if commit:
        db.commit()
    return event


def mirror_and_record_workflow_operation(
    db: Session,
    operation: WorkflowOperation,
    *,
    config: AuditMirrorConfig | None = None,
    commit: bool = True,
) -> AuditMirrorResult:
    active_config = config or audit_mirror_config_from_settings()
    if active_config.disabled and not active_config.required:
        return AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=active_config.normalized_mode,
            mirror_status=AUDIT_MIRROR_STATUS_DISABLED,
            mirror_checksum=audit_mirror_checksum(audit_mirror_payload(operation)),
        )
    try:
        result = mirror_workflow_operation(operation, config=active_config)
    except Exception as exc:
        result = AuditMirrorResult(
            operation_id=operation.operation_id,
            mirror_mode=active_config.normalized_mode,
            mirror_status=AUDIT_MIRROR_STATUS_FAILED,
            mirror_checksum=audit_mirror_checksum(audit_mirror_payload(operation)),
            mirror_error=str(exc),
        )
        record_mirror_result(db, result, commit=commit)
        if active_config.required:
            raise AuditMirrorError(str(exc)) from exc
        return result
    if result.mirror_status != AUDIT_MIRROR_STATUS_DISABLED:
        record_mirror_result(db, result, commit=commit)
    return result


def read_db_mirror_events(db: Session) -> list[ClinicalWorkflowAuditMirrorEvent]:
    try:
        return list(
            db.execute(
                select(ClinicalWorkflowAuditMirrorEvent).order_by(
                    ClinicalWorkflowAuditMirrorEvent.created_at.asc(),
                    ClinicalWorkflowAuditMirrorEvent.mirror_event_id.asc(),
                )
            )
            .scalars()
            .all()
        )
    except (SQLAlchemyError, AttributeError, TypeError):
        return []


def successful_mirror_operation_ids(db: Session) -> set[str]:
    return {
        event.operation_id
        for event in read_db_mirror_events(db)
        if event.mirror_status == AUDIT_MIRROR_STATUS_MIRRORED and not event.dry_run
    }


def mirror_unmirrored_workflow_audit_events(
    db: Session,
    *,
    config: AuditMirrorConfig | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    active_config = config or audit_mirror_config_from_settings()
    mirrored_ids = successful_mirror_operation_ids(db)
    rows = list(
        db.execute(
            select(ClinicalWorkflowAuditEvent).order_by(
                ClinicalWorkflowAuditEvent.timestamp.asc(),
                ClinicalWorkflowAuditEvent.id.asc(),
            )
        )
        .scalars()
        .all()
    )

    mirrored = 0
    skipped = 0
    failed = 0
    dry_run_count = 0
    results: list[dict[str, Any]] = []
    for event in rows:
        if event.operation_id in mirrored_ids:
            skipped += 1
            continue
        if limit is not None and mirrored + failed + dry_run_count >= limit:
            break
        operation = workflow_operation_from_audit_event(event)
        try:
            result = mirror_workflow_operation(operation, config=active_config, dry_run=dry_run)
        except Exception as exc:
            result = AuditMirrorResult(
                operation_id=operation.operation_id,
                mirror_mode=active_config.normalized_mode,
                mirror_status=AUDIT_MIRROR_STATUS_FAILED,
                mirror_checksum=audit_mirror_checksum(audit_mirror_payload(operation)),
                mirror_error=str(exc),
            )
            failed += 1
            if not dry_run:
                record_mirror_result(db, result, commit=False)
            if active_config.required:
                if commit and not dry_run:
                    db.commit()
                raise AuditMirrorError(str(exc)) from exc
        else:
            if result.mirror_status == AUDIT_MIRROR_STATUS_DRY_RUN:
                dry_run_count += 1
            elif result.mirror_status == AUDIT_MIRROR_STATUS_MIRRORED:
                mirrored += 1
            elif result.mirror_status == AUDIT_MIRROR_STATUS_DISABLED:
                skipped += 1
            elif result.mirror_status == AUDIT_MIRROR_STATUS_SKIPPED:
                skipped += 1
            if not dry_run and result.mirror_status not in {AUDIT_MIRROR_STATUS_DISABLED}:
                record_mirror_result(db, result, commit=False)
                if result.mirror_status == AUDIT_MIRROR_STATUS_MIRRORED:
                    mirrored_ids.add(result.operation_id)
        results.append(
            {
                "operation_id": result.operation_id,
                "mirror_status": result.mirror_status,
                "mirror_uri": result.mirror_uri,
                "mirror_checksum": result.mirror_checksum,
                "mirror_error": result.mirror_error,
            }
        )
    if commit and not dry_run:
        db.commit()
    return {
        "mirrored": mirrored,
        "skipped": skipped,
        "failed": failed,
        "dry_run": dry_run_count,
        "source_deleted": False,
        "results": results,
    }
