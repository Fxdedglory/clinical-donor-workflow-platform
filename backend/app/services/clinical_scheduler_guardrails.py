"""Guardrails for the future Clinical external scheduler.

This module is intentionally not imported by app startup. It gives the future
Azure Container Apps Job a reusable, testable path with dry-run and destructive
operation gates before any PostgreSQL refresh/export work is executed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.database import SessionLocal
from app.services.data_producer import (
    export_database_batch,
    run_incremental_generation,
    run_seed_generation,
    validate_database,
)

SOURCE_SYSTEM = "clinical"
ACCEPTED_REFRESH_CONTRACT_VERSION = "1.0"
DESTRUCTIVE_CONFIRMATION_PHRASE = "CONFIRM_CLINICAL_DESTRUCTIVE_REFRESH"
ALLOWED_REFRESH_MODES = {"export_only", "incremental_demo_refresh", "full_reseed"}
DESTRUCTIVE_REFRESH_MODES = {"full_reseed"}

RunFn = Callable[..., dict[str, Any]]
PublisherFn = Callable[..., None]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sum_row_counts(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    row_counts = payload.get("row_counts")
    if isinstance(row_counts, dict):
        return sum(int(value or 0) for value in row_counts.values())
    files = payload.get("files")
    if isinstance(files, list):
        return sum(int(row.get("row_count") or 0) for row in files if isinstance(row, dict))
    return int(payload.get("row_count") or payload.get("rows_affected") or 0)


def _file_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    files = payload.get("files")
    return len(files) if isinstance(files, list) else int(payload.get("file_count") or 0)


def sanitize_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    blocked = ("password", "secret", "token", "key", "credential", "connection", "mfa", "session")
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_text = str(key).lower()
        value_text = str(value).lower()
        if any(marker in key_text for marker in blocked):
            continue
        if any(marker in value_text for marker in ("begin rsa", "private key", "password=", "accountkey=")):
            continue
        sanitized[str(key)] = value
    return sanitized


def validate_backup_evidence(evidence: dict[str, Any] | None) -> list[str]:
    if not isinstance(evidence, dict):
        return ["backup_evidence is required for destructive Clinical refresh modes."]
    required = [
        "server_name",
        "database_name",
        "observed_at",
        "backup_retention_days",
        "earliest_restore_time",
        "restore_scope",
    ]
    missing = [field for field in required if not evidence.get(field)]
    issues = [f"backup_evidence.{field} is required." for field in missing]
    try:
        retention = int(evidence.get("backup_retention_days") or 0)
    except (TypeError, ValueError):
        retention = 0
    if retention < 1:
        issues.append("backup_evidence.backup_retention_days must be at least 1.")
    return issues


def destructive_refresh_allowed(
    *,
    refresh_mode: str,
    force: bool,
    confirm: str,
    backup_evidence: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    if refresh_mode not in DESTRUCTIVE_REFRESH_MODES:
        return True, []
    issues = validate_backup_evidence(backup_evidence)
    if not force:
        issues.append("force=true is required for destructive Clinical refresh modes.")
    if confirm != DESTRUCTIVE_CONFIRMATION_PHRASE:
        issues.append(f"confirm must equal {DESTRUCTIVE_CONFIRMATION_PHRASE}.")
    return not issues, issues


def build_accepted_refresh_manifest(
    *,
    batch_id: str,
    refresh_mode: str,
    refresh_started_at: str,
    refresh_completed_at: str,
    validation: dict[str, Any],
    export_manifest: dict[str, Any] | None,
    backup_evidence: dict[str, Any] | None,
    accepted_by: str = "clinical-container-apps-job",
    rollback_notes: str = "",
    notes: str = "",
) -> dict[str, Any]:
    validation_status = str(validation.get("status") or "unknown")
    row_count_total = _sum_row_counts(export_manifest) or _sum_row_counts(validation)
    file_count_total = _file_count(export_manifest)
    quality_status = "passed" if validation_status == "passed" and row_count_total > 0 else "failed"
    source_tables = []
    if export_manifest and isinstance(export_manifest.get("files"), list):
        source_tables = [
            {
                "source_table": row.get("source_table") or row.get("table"),
                "row_count": int(row.get("row_count") or 0),
                "file_count": 1,
            }
            for row in export_manifest["files"]
            if isinstance(row, dict)
        ]
    return {
        "source_system": SOURCE_SYSTEM,
        "refresh_contract_version": ACCEPTED_REFRESH_CONTRACT_VERSION,
        "batch_id": batch_id,
        "extraction_batch_id": batch_id,
        "refresh_mode": refresh_mode,
        "refresh_started_at": refresh_started_at,
        "refresh_completed_at": refresh_completed_at,
        "accepted_at": _now() if quality_status == "passed" else None,
        "accepted_by": accepted_by if quality_status == "passed" else None,
        "quality_status": quality_status,
        "validation_status": validation_status,
        "row_count_total": row_count_total,
        "file_count_total": file_count_total,
        "source_tables": source_tables,
        "data_root": (export_manifest or {}).get("export_path", ""),
        "manifest_path": (export_manifest or {}).get("manifest_path", ""),
        "backup_evidence": sanitize_metadata(backup_evidence or {}),
        "rollback_notes": rollback_notes,
        "notes": notes,
    }


def build_monitor_payloads(
    *,
    run_id: str,
    batch_id: str,
    refresh_mode: str,
    status: str,
    started_at: str,
    ended_at: str,
    row_count: int,
    file_count: int,
    validation_status: str,
    backup_evidence_present: bool,
    error_message: str | None = None,
) -> dict[str, dict[str, Any]]:
    job_run_id = f"clinical-scheduled-{hashlib.sha256(run_id.encode()).hexdigest()[:16]}"
    metadata = sanitize_metadata(
        {
            "batch_id": batch_id,
            "refresh_mode": refresh_mode,
            "scheduler": "azure_container_apps_job",
            "validation_status": validation_status,
            "backup_evidence_present": backup_evidence_present,
        }
    )
    return {
        "job_run": {
            "job_run_id": job_run_id,
            "source_system": SOURCE_SYSTEM,
            "job_type": "scheduled_postgresql_refresh_export",
            "external_run_id": run_id,
            "status": status,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": 0,
            "rows_processed": row_count,
            "files_processed": file_count,
            "error_count": 1 if error_message else 0,
            "error_message": error_message,
            "metadata_json": metadata,
        },
        "status_event": {
            "event_id": f"{job_run_id}-event",
            "event_type": "scheduled_postgresql_refresh_export",
            "source_system": SOURCE_SYSTEM,
            "status": "healthy" if status == "completed" else status,
            "severity": "info" if not error_message else "error",
            "message": "Clinical PostgreSQL refresh/export completed." if not error_message else "Clinical PostgreSQL refresh/export failed.",
            "related_resource_id": "azure://app-service/app-teemails-clinical-dev",
            "related_job_run_id": job_run_id,
            "event_time": ended_at,
            "metadata_json": metadata,
        },
        "active_edge": {
            "active_edge_id": f"{job_run_id}-edge",
            "edge_id": "clinical.postgresql.publishes_to.monitor",
            "source_node_id": "clinical-postgresql",
            "target_node_id": "monitor",
            "job_run_id": job_run_id,
            "state": "completed" if status == "completed" else status,
            "started_at": started_at,
            "ended_at": ended_at,
            "rows_processed": row_count,
            "files_processed": file_count,
            "error_count": 1 if error_message else 0,
            "metadata_json": metadata,
        },
    }


def run_clinical_scheduler_refresh(
    *,
    refresh_mode: str = "incremental_demo_refresh",
    batch_id: str | None = None,
    dry_run: bool = True,
    force: bool = False,
    confirm: str = "",
    backup_evidence: dict[str, Any] | None = None,
    seed: int = 42,
    scale: int = 1,
    export_root: str | None = None,
    incremental_fn: RunFn | None = None,
    seed_fn: RunFn | None = None,
    validate_fn: RunFn | None = None,
    export_fn: RunFn | None = None,
    publisher_fn: PublisherFn | None = None,
) -> dict[str, Any]:
    if refresh_mode not in ALLOWED_REFRESH_MODES:
        raise ValueError(f"Unsupported Clinical refresh mode: {refresh_mode}")

    started_at = _now()
    resolved_batch_id = batch_id or f"clinical_scheduled_{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    allowed, guardrail_issues = destructive_refresh_allowed(
        refresh_mode=refresh_mode,
        force=force,
        confirm=confirm,
        backup_evidence=backup_evidence,
    )
    plan = {
        "source_system": SOURCE_SYSTEM,
        "batch_id": resolved_batch_id,
        "refresh_mode": refresh_mode,
        "dry_run": dry_run,
        "allowed_to_execute": allowed,
        "guardrail_issues": guardrail_issues,
        "destructive": refresh_mode in DESTRUCTIVE_REFRESH_MODES,
        "backup_evidence_required": refresh_mode in DESTRUCTIVE_REFRESH_MODES,
        "backup_evidence_present": bool(backup_evidence),
    }
    if dry_run:
        return {"status": "dry_run", "plan": plan, "executed": False}
    if not allowed:
        raise PermissionError("; ".join(guardrail_issues))

    active_incremental = incremental_fn or run_incremental_generation
    active_seed = seed_fn or run_seed_generation
    active_validate = validate_fn or validate_database
    active_export = export_fn or export_database_batch

    refresh_result: dict[str, Any] | None = None
    validation: dict[str, Any]
    export_manifest: dict[str, Any] | None = None
    with SessionLocal() as db:
        if refresh_mode == "incremental_demo_refresh":
            refresh_result = active_incremental(db, seed=seed, scale=scale, extraction_batch_id=resolved_batch_id)
        elif refresh_mode == "full_reseed":
            refresh_result = active_seed(
                records=None,
                seed=seed,
                force=True,
                profile="demo",
            )
        validation = active_validate(db)
        if validation.get("status") == "passed":
            export_manifest = active_export(db, batch_id=resolved_batch_id, root=export_root)

    ended_at = _now()
    accepted_manifest = build_accepted_refresh_manifest(
        batch_id=resolved_batch_id,
        refresh_mode=refresh_mode,
        refresh_started_at=started_at,
        refresh_completed_at=ended_at,
        validation=validation,
        export_manifest=export_manifest,
        backup_evidence=backup_evidence,
        rollback_notes="Use Azure PostgreSQL point-in-time restore evidence captured before destructive refresh.",
    )
    status = "completed" if accepted_manifest["quality_status"] == "passed" else "failed"
    payloads = build_monitor_payloads(
        run_id=resolved_batch_id,
        batch_id=resolved_batch_id,
        refresh_mode=refresh_mode,
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        row_count=int(accepted_manifest["row_count_total"]),
        file_count=int(accepted_manifest["file_count_total"]),
        validation_status=str(accepted_manifest["validation_status"]),
        backup_evidence_present=bool(backup_evidence),
        error_message=None if status == "completed" else "Clinical validation/export did not meet acceptance criteria.",
    )
    if publisher_fn:
        for payload in payloads.values():
            publisher_fn(payload)
    return {
        "status": status,
        "plan": plan,
        "executed": True,
        "refresh_result": refresh_result,
        "validation": validation,
        "export_manifest": export_manifest,
        "accepted_refresh_manifest": accepted_manifest,
        "monitor_payloads": payloads,
    }
