"""Run the guarded Clinical refresh/export job outside App Service startup."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.clinical_scheduler_guardrails import (  # noqa: E402
    DESTRUCTIVE_CONFIRMATION_PHRASE,
    build_accepted_refresh_manifest,
    destructive_refresh_allowed,
)
from app.services.data_producer import run_incremental_generation, validate_database  # noqa: E402
from app.services.monitor_publisher import MonitorPublisher  # noqa: E402
from scripts.export_to_parquet_lake import export_to_parquet_lake  # noqa: E402
from scripts.upload_parquet_lake_to_adls import upload_parquet_lake_to_adls  # noqa: E402
from scripts.validate_parquet_lake import validate_parquet_lake  # noqa: E402


ALLOWED_REFRESH_MODES = {"export_only", "incremental_demo_refresh", "full_reseed"}


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _job_batch_id() -> str:
    return os.getenv("CLINICAL_JOB_BATCH_ID") or f"clinical_scheduled_{datetime.now(UTC):%Y%m%dT%H%M%SZ}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _load_backup_evidence() -> dict[str, Any] | None:
    raw_json = os.getenv("CLINICAL_JOB_BACKUP_EVIDENCE_JSON")
    raw_path = os.getenv("CLINICAL_JOB_BACKUP_EVIDENCE_FILE")
    if raw_json:
        return json.loads(raw_json)
    if raw_path:
        return json.loads(Path(raw_path).read_text(encoding="utf-8"))
    return None


def _sum_validation_rows(validation: dict[str, Any]) -> int:
    row_counts = validation.get("row_counts")
    if isinstance(row_counts, dict):
        return sum(int(value or 0) for value in row_counts.values())
    return 0


def _upload_accepted_manifest(
    *,
    source_path: Path,
    batch_id: str,
    account_name: str,
    container: str,
    auth_mode: str,
    dry_run: bool,
) -> dict[str, Any]:
    blob_name = f"accepted-output/source_system=clinical/manifests/{batch_id}.json"
    if dry_run:
        return {"source_path": str(source_path), "blob_name": blob_name, "status": "dry_run"}
    if auth_mode != "managed_identity":
        raise ValueError("Only DATA_LAKE_AUTH_MODE=managed_identity is supported for Clinical scheduled jobs.")
    if not account_name:
        raise ValueError("DATA_LAKE_ACCOUNT_NAME is required for Clinical scheduled jobs.")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    with source_path.open("rb") as handle:
        service.get_container_client(container).upload_blob(
            name=blob_name,
            data=handle,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )
    return {"source_path": str(source_path), "blob_name": blob_name, "status": "uploaded"}


def run_job() -> dict[str, Any]:
    started_monotonic = time.monotonic()
    started_at = _now()
    batch_id = _job_batch_id()
    refresh_mode = os.getenv("CLINICAL_JOB_REFRESH_MODE", "export_only")
    if refresh_mode not in ALLOWED_REFRESH_MODES:
        raise ValueError(f"Unsupported Clinical refresh mode: {refresh_mode}")
    if refresh_mode == "full_reseed":
        backup_evidence = _load_backup_evidence()
        allowed, issues = destructive_refresh_allowed(
            refresh_mode=refresh_mode,
            force=_bool_env("CLINICAL_JOB_FORCE", False),
            confirm=os.getenv("CLINICAL_JOB_CONFIRM", ""),
            backup_evidence=backup_evidence,
        )
        if not allowed:
            raise PermissionError("; ".join(issues))
        raise PermissionError(
            f"{DESTRUCTIVE_CONFIRMATION_PHRASE} was supplied, but full_reseed is intentionally disabled in V2.4-F."
        )

    lake_root = Path(os.getenv("CLINICAL_JOB_LAKE_ROOT", "/tmp/clinical/lake"))
    result_path = Path(os.getenv("CLINICAL_JOB_RESULT_PATH", "/tmp/clinical/job_result.json"))
    accepted_manifest_path = Path(os.getenv("CLINICAL_JOB_ACCEPTED_MANIFEST_PATH", f"/tmp/clinical/accepted/{batch_id}.json"))
    seed = int(os.getenv("CLINICAL_JOB_SEED") or datetime.now(UTC).strftime("%Y%m%d%H%M%S"))
    scale = int(os.getenv("CLINICAL_JOB_INCREMENTAL_SCALE", "1"))
    upload_adls = _bool_env("CLINICAL_JOB_UPLOAD_ADLS", True)
    dry_run_upload = _bool_env("CLINICAL_JOB_ADLS_DRY_RUN", False)
    account_name = os.getenv("DATA_LAKE_ACCOUNT_NAME", "")
    container = os.getenv("DATA_LAKE_CONTAINER", "datalake")
    auth_mode = os.getenv("DATA_LAKE_AUTH_MODE", "managed_identity")
    publisher = MonitorPublisher()
    run: dict[str, Any] = {
        "run_id": batch_id,
        "run_type": refresh_mode,
        "status": "running",
        "started_at": started_at,
        "finished_at": "",
        "duration_seconds": 0,
        "row_counts": {},
        "validation_status": "not_run",
    }
    manifest: dict[str, Any] | None = None
    try:
        refresh_result: dict[str, Any] | None = None
        with SessionLocal() as db:
            if refresh_mode == "incremental_demo_refresh":
                refresh_result = run_incremental_generation(
                    db,
                    seed=seed,
                    scale=scale,
                    extraction_batch_id=batch_id,
                )
                if refresh_result.get("status") != "succeeded":
                    raise RuntimeError(f"Clinical incremental refresh failed: {refresh_result.get('errors')}")
            validation = validate_database(db)

        if validation.get("status") != "passed":
            raise RuntimeError(f"Clinical validation failed: {validation.get('errors')}")
        manifest = export_to_parquet_lake(lake_root=lake_root, batch_id=batch_id, source_system="clinical")
        parquet_validation = validate_parquet_lake(lake_root, source_system="clinical", batch_id=batch_id)
        if parquet_validation["status"] != "passed":
            raise RuntimeError(f"Clinical Parquet validation failed: {parquet_validation['issues']}")

        upload_result: dict[str, Any] = {"status": "skipped", "file_count": 0}
        if upload_adls:
            upload_result = upload_parquet_lake_to_adls(
                lake_root=lake_root,
                source_system="clinical",
                batch_id=batch_id,
                account_name=account_name,
                container=container,
                auth_mode=auth_mode,
                dry_run=dry_run_upload,
                delete_local_after_upload=False,
            )

        finished_at = _now()
        accepted_manifest = build_accepted_refresh_manifest(
            batch_id=batch_id,
            refresh_mode=refresh_mode,
            refresh_started_at=started_at,
            refresh_completed_at=finished_at,
            validation=validation,
            export_manifest=manifest,
            backup_evidence=None,
            rollback_notes="No destructive refresh performed. PostgreSQL point-in-time restore required before any future full reseed.",
            notes="Clinical external scheduler V2.4-F proof execution.",
        )
        _write_json(accepted_manifest_path, accepted_manifest)
        accepted_upload = {"status": "skipped", "file_count": 0}
        if upload_adls:
            accepted_upload = _upload_accepted_manifest(
                source_path=accepted_manifest_path,
                batch_id=batch_id,
                account_name=account_name,
                container=container,
                auth_mode=auth_mode,
                dry_run=dry_run_upload,
            )
        duration = time.monotonic() - started_monotonic
        run.update(
            {
                "status": "succeeded",
                "finished_at": finished_at,
                "duration_seconds": f"{duration:.3f}",
                "row_counts": validation.get("row_counts", {}),
                "validation_status": "passed",
            }
        )
        manifest["upload"] = {
            "status": "uploaded" if upload_adls and not dry_run_upload else "dry_run" if upload_adls else "skipped",
            "file_count": upload_result.get("file_count", 0),
            "container": upload_result.get("container"),
            "account_name": upload_result.get("account_name"),
        }
        manifest["accepted_refresh"] = {
            "local_manifest_path": str(accepted_manifest_path),
            "upload": accepted_upload,
            "quality_status": accepted_manifest["quality_status"],
        }
        publisher.publish_cycle(run=run, manifest=manifest, status="completed")
        result = {
            "status": "succeeded",
            "source_system": "clinical",
            "job_type": "scheduled_postgresql_refresh_export",
            "refresh_mode": refresh_mode,
            "batch_id": batch_id,
            "row_count": int(manifest.get("row_count") or _sum_validation_rows(validation)),
            "file_count": int(manifest.get("file_count") or 0),
            "duration_seconds": f"{duration:.3f}",
            "validation_status": "passed",
            "parquet_validation_status": parquet_validation["status"],
            "adls_upload": manifest["upload"],
            "accepted_refresh": manifest["accepted_refresh"],
            "monitor_publish_enabled": publisher.configured,
            "refresh_result": refresh_result,
        }
        _write_json(result_path, result)
        return result
    except Exception as exc:
        finished_at = _now()
        run.update(
            {
                "status": "failed",
                "finished_at": finished_at,
                "duration_seconds": f"{time.monotonic() - started_monotonic:.3f}",
            }
        )
        publisher.publish_cycle(run=run, manifest=manifest, status="failed", error=str(exc))
        result = {
            "status": "failed",
            "source_system": "clinical",
            "job_type": "scheduled_postgresql_refresh_export",
            "refresh_mode": refresh_mode,
            "batch_id": batch_id,
            "duration_seconds": run["duration_seconds"],
            "validation_status": run.get("validation_status", "failed"),
            "error": str(exc),
            "monitor_publish_enabled": publisher.configured,
        }
        _write_json(result_path, result)
        raise


def main() -> int:
    result = run_job()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
