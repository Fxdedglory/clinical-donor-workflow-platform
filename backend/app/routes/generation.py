from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.config import settings
from app.database import get_db
from app.models import SecurityAudit, User, UserSessionRecord
from app.services.data_producer import (
    DATA_PRODUCER,
    continuous_state,
    export_database_batch,
    generation_runs,
    generation_status,
    latest_export_manifest,
    latest_validation_result,
    run_incremental_generation,
    run_seed_generation,
    source_freshness,
    validate_database,
)

router = APIRouter(tags=["Clinical Data Producer"])
APP_NAME = "clinical-donor-platform"
STALE_THRESHOLD_MINUTES = 24 * 60


def _hash_ip(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:24]


def _sum_row_counts(run: dict) -> int:
    row_counts = run.get("row_counts")
    if isinstance(row_counts, dict):
        return sum(int(value or 0) for value in row_counts.values())
    return int(run.get("rows_affected") or 0)


def _monitoring_run_summary(run: dict) -> dict:
    errors = run.get("errors") or []
    return {
        "run_id": run.get("run_id"),
        "run_type": run.get("run_type"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "duration_seconds": run.get("duration_seconds"),
        "rows_affected": _sum_row_counts(run),
        "error_message": "; ".join(errors[:3]) if errors else "",
    }


def _safe_export_summary(manifest: dict) -> dict:
    files = manifest.get("files", [])
    return {
        "batch_id": manifest.get("batch_id"),
        "extraction_batch_id": manifest.get("extraction_batch_id"),
        "generated_at": manifest.get("generated_at"),
        "source_system": manifest.get("source_system"),
        "file_count": len(files),
        "row_count": sum(int(row.get("row_count") or 0) for row in files),
        "files": [
            {
                "table": row.get("table"),
                "row_count": row.get("row_count", 0),
            }
            for row in files
        ],
    }


def _require_confirmation(confirm: bool, action: str) -> None:
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{action} requires confirm=true.",
        )


@router.get("/api/generation/status")
def get_generation_status(
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> dict:
    return generation_status(db)


@router.get("/api/generation/runs")
def get_generation_runs(
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(require_permission("system.admin")),
) -> list[dict]:
    return generation_runs(limit=limit)


@router.post("/api/generation/seed")
def seed_generation(
    payload: dict | None = None,
    confirm: bool = Query(default=False),
    _: User = Depends(require_permission("system.admin")),
) -> dict:
    if not settings.enable_data_producer_api:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Data producer API is disabled.")
    _require_confirmation(confirm, "Seed generation")
    payload = payload or {}
    return run_seed_generation(
        records=int(payload.get("records", 1200)),
        seed=payload.get("seed", 42),
        force=bool(payload.get("force", False)),
    )


@router.post("/api/generation/incremental")
def incremental_generation(
    payload: dict | None = None,
    confirm: bool = Query(default=False),
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> dict:
    if not settings.enable_data_producer_api:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Data producer API is disabled.")
    _require_confirmation(confirm, "Incremental generation")
    payload = payload or {}
    return run_incremental_generation(
        db,
        seed=payload.get("seed", 42),
        scale=int(payload.get("scale", 1)),
        extraction_batch_id=payload.get("extraction_batch_id"),
    )


@router.post("/api/generation/validate")
def validate_generation(
    confirm: bool = Query(default=False),
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> dict:
    _require_confirmation(confirm, "Validation")
    return validate_database(db)


@router.post("/api/generation/export")
def export_generation(
    payload: dict | None = None,
    confirm: bool = Query(default=False),
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> dict:
    _require_confirmation(confirm, "Export")
    payload = payload or {}
    return export_database_batch(db, batch_id=payload.get("batch_id"), root=payload.get("export_root"))


@router.post("/api/generation/continuous/start")
def start_continuous_generation(
    payload: dict | None = None,
    confirm: bool = Query(default=False),
    _: User = Depends(require_permission("system.admin")),
) -> dict:
    if not settings.enable_data_producer_api:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Data producer API is disabled.")
    _require_confirmation(confirm, "Continuous generation")
    payload = payload or {}
    raw_cycles = payload.get("cycles", 1)
    allow_infinite = bool(payload.get("allow_infinite", False))
    cycles = None if allow_infinite and int(raw_cycles or 0) == 0 else int(raw_cycles)
    return DATA_PRODUCER.start(
        interval_seconds=int(payload.get("interval_seconds", 30)),
        cycles=cycles,
        seed=payload.get("seed", 42),
        scale=int(payload.get("scale", 1)),
        export_each_cycle=bool(payload.get("export_each_cycle", False)),
        allow_infinite=allow_infinite,
    )


@router.post("/api/generation/continuous/stop")
def stop_continuous_generation(
    confirm: bool = Query(default=False),
    _: User = Depends(require_permission("system.admin")),
) -> dict:
    _require_confirmation(confirm, "Continuous generation stop")
    return DATA_PRODUCER.stop()


@router.get("/api/generation/continuous/status")
def continuous_generation_status(
    _: User = Depends(require_permission("system.admin")),
) -> dict:
    return continuous_state()


@router.get("/api/monitoring/source-freshness")
def monitoring_source_freshness(
    db: Session = Depends(get_db),
) -> dict:
    validation = latest_validation_result()
    export_manifest = latest_export_manifest()
    latest_run = generation_runs(limit=1)
    try:
        freshness = source_freshness(db)
        freshness_status = "ok"
    except Exception:
        freshness = {"source_system": "CLINICAL_DONOR_PLATFORM", "freshness": []}
        freshness_status = "database_unavailable"
    latest_export_at = export_manifest.get("generated_at")
    latest_generated_at = latest_run[0].get("generated_at") if latest_run else freshness.get("generated_at")
    return {
        "app_name": APP_NAME,
        "source_systems": ["CLINICAL_DONOR_PLATFORM"],
        "latest_generated_at": latest_generated_at,
        "latest_extraction_batch_id": export_manifest.get("extraction_batch_id"),
        "latest_validation_at": validation.get("validated_at"),
        "latest_export_at": latest_export_at,
        "freshness_status": freshness_status,
        "stale_threshold_minutes": STALE_THRESHOLD_MINUTES,
        "source_system": freshness.get("source_system"),
        "latest_source_watermark": freshness.get("latest_source_watermark"),
        "freshness": freshness.get("freshness", []),
    }


@router.get("/api/monitoring/validation")
def monitoring_validation(
) -> dict:
    validation = latest_validation_result()
    return {
        "app_name": APP_NAME,
        "latest_validation_status": validation.get("status", "not_run"),
        "latest_validation_at": validation.get("validated_at"),
        "errors_count": len(validation.get("errors", [])),
        "warnings_count": len(validation.get("warnings", [])),
        "validation_summary": {
            "source_system": validation.get("source_system"),
            "check_count": len(validation.get("checks", [])),
            "errors": validation.get("errors", [])[:25],
            "warnings": validation.get("warnings", [])[:25],
        },
        "validation_artifact_path": "",
    }


@router.get("/api/monitoring/export-manifest")
def monitoring_export_manifest(
) -> dict:
    manifest = latest_export_manifest()
    summary = _safe_export_summary(manifest) if manifest else {}
    return {
        "app_name": APP_NAME,
        "latest_export_batch_id": summary.get("extraction_batch_id") or summary.get("batch_id"),
        "latest_export_at": summary.get("generated_at"),
        "export_file_count": summary.get("file_count", 0),
        "export_row_count": summary.get("row_count", 0),
        "export_manifest_summary": summary,
        "export_status": "ok" if manifest else "no_data",
    }


@router.get("/api/monitoring/run-history")
def monitoring_run_history() -> dict:
    runs = generation_runs(limit=100)
    return {
        "app_name": APP_NAME,
        "recent_generation_runs": [_monitoring_run_summary(run) for run in runs if run.get("run_type") in {"seed", "incremental"}][:25],
        "recent_validation_runs": [_monitoring_run_summary(run) for run in runs if run.get("run_type") == "validation"][:25],
        "recent_export_runs": [_monitoring_run_summary(run) for run in runs if run.get("run_type") == "export"][:25],
    }


@router.get("/api/monitoring/security-events")
def monitoring_security_events(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    try:
        rows = db.execute(select(SecurityAudit).order_by(desc(SecurityAudit.timestamp)).limit(limit)).scalars().all()
    except Exception:
        rows = []
    return {
        "app_name": APP_NAME,
        "events": [
            {
                "event_id": str(row.event_id),
                "timestamp_utc": row.timestamp.isoformat() if row.timestamp else None,
                "app_name": APP_NAME,
                "event_type": row.event_type,
                "severity": "warning" if not row.success else "info",
                "user_id": str(row.user_id) if row.user_id is not None else "",
                "role": "",
                "ip_address": None,
                "hashed_ip": _hash_ip(row.ip_address),
                "user_agent": row.device,
                "route": row.route,
                "status_code": 200 if row.success else 403,
                "message": row.event_type,
            }
            for row in rows
        ],
        "schema_fields": [
            "event_id",
            "timestamp_utc",
            "app_name",
            "event_type",
            "severity",
            "user_id",
            "role",
            "ip_address",
            "hashed_ip",
            "user_agent",
            "route",
            "status_code",
            "message",
        ],
    }


@router.get("/api/monitoring/user-access")
def monitoring_user_access(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    events = []
    try:
        rows = db.execute(select(UserSessionRecord).order_by(desc(UserSessionRecord.created_at)).limit(limit)).scalars().all()
        for row in rows:
            user = db.get(User, row.user_id)
            events.append(
                {
                    "event_id": row.session_id,
                    "timestamp_utc": row.created_at.isoformat() if row.created_at else None,
                    "app_name": APP_NAME,
                    "auth_event_type": "logout" if row.revoked_at else "login_success",
                    "user_id": str(row.user_id),
                    "username": user.username if user else "",
                    "role": user.role if user else "",
                    "is_internal_user": bool(user.is_internal) if user else False,
                    "is_external_user": bool(user.is_external) if user else False,
                    "partner_org_id": str(user.organization_id) if user and user.organization_id else "",
                    "ip_address": None,
                    "hashed_ip": _hash_ip(row.ip_address),
                    "browser": "",
                    "device_type": row.device or "",
                    "cloudflare_ray_id": "",
                    "success": bool(row.is_active and not row.revoked_at),
                    "failure_reason": "",
                }
            )
    except Exception:
        events = []
    return {
        "app_name": APP_NAME,
        "events": events,
        "schema_fields": [
            "event_id",
            "timestamp_utc",
            "app_name",
            "auth_event_type",
            "user_id",
            "username",
            "role",
            "is_internal_user",
            "is_external_user",
            "partner_org_id",
            "ip_address",
            "hashed_ip",
            "browser",
            "device_type",
            "cloudflare_ray_id",
            "success",
            "failure_reason",
        ],
    }
