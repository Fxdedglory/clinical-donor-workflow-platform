from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.config import settings
from app.database import get_db
from app.models import User
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
    _: User = Depends(require_permission("system.admin")),
    db: Session = Depends(get_db),
) -> dict:
    return source_freshness(db)


@router.get("/api/monitoring/validation")
def monitoring_validation(
    _: User = Depends(require_permission("system.admin")),
) -> dict:
    return latest_validation_result()


@router.get("/api/monitoring/export-manifest")
def monitoring_export_manifest(
    _: User = Depends(require_permission("system.admin")),
) -> dict:
    return latest_export_manifest()
