"""Guarded Clinical historical Parquet export and ADLS upload helpers."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HISTORICAL_CONFIRMATION_PHRASE = "UPLOAD_CLINICAL_HISTORICAL_ADLS_BATCH"

ExportFn = Callable[..., dict[str, Any]]
UploadFn = Callable[..., dict[str, Any]]


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "scripts").exists() and (parent / "requirements.txt").exists():
            return parent
    return current.parents[3]


def _default_lake_root() -> Path:
    configured = os.getenv("DATA_LAKE_LOCAL_ROOT")
    if configured:
        return Path(configured)
    return _project_root() / "data" / "datalake"


def _load_script_functions() -> tuple[ExportFn, UploadFn]:
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from scripts.export_to_parquet_lake import export_to_parquet_lake
    from scripts.upload_parquet_lake_to_adls import upload_parquet_lake_to_adls

    return export_to_parquet_lake, upload_parquet_lake_to_adls


def run_clinical_historical_adls_upload(
    *,
    batch_id: str | None = None,
    lake_root: Path | None = None,
    source_system: str = "clinical",
    export_fn: ExportFn | None = None,
    upload_fn: UploadFn | None = None,
) -> dict[str, Any]:
    """Export the current Clinical database to Parquet and upload it using MI.

    This function intentionally does not generate or mutate Clinical data. Seed
    and validation are separate admin operations; this step only reads the
    current database, writes a local Parquet lake batch, and uploads that batch
    with the configured managed identity.
    """

    extraction_batch_id = batch_id or f"clinical_historical_small_{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    resolved_lake_root = lake_root or _default_lake_root()
    account_name = os.getenv("DATA_LAKE_ACCOUNT_NAME", "")
    container = os.getenv("DATA_LAKE_CONTAINER", "datalake")
    auth_mode = os.getenv("DATA_LAKE_AUTH_MODE", "managed_identity")
    base_path = os.getenv("DATA_LAKE_BASE_PATH", "bronze")

    active_export, active_upload = (export_fn, upload_fn)
    if active_export is None or active_upload is None:
        default_export, default_upload = _load_script_functions()
        active_export = active_export or default_export
        active_upload = active_upload or default_upload

    manifest = active_export(
        lake_root=resolved_lake_root,
        batch_id=extraction_batch_id,
        source_system=source_system,
        compression="snappy",
    )
    upload = active_upload(
        lake_root=resolved_lake_root,
        source_system=source_system,
        batch_id=extraction_batch_id,
        account_name=account_name,
        container=container,
        auth_mode=auth_mode,
        dry_run=False,
        delete_local_after_upload=False,
    )

    uploaded_files = upload.get("files", [])
    uploaded_paths = [
        str(file.get("blob_name") or file.get("path") or "")
        for file in uploaded_files
        if file.get("blob_name") or file.get("path")
    ]
    source_tables = [
        {
            "source_table": file.get("source_table"),
            "row_count": int(file.get("row_count") or 0),
            "extraction_date": file.get("extraction_date"),
        }
        for file in manifest.get("files", [])
    ]

    return {
        "source_system": source_system,
        "status": "uploaded",
        "batch_id": extraction_batch_id,
        "auth_mode": auth_mode,
        "account_name": account_name,
        "container": container,
        "base_path": base_path,
        "lake_root": str(resolved_lake_root),
        "manifest_path": manifest.get("manifest_path"),
        "source_table_count": len(source_tables),
        "row_count": int(manifest.get("row_count") or 0),
        "file_count": int(upload.get("file_count") or len(uploaded_paths)),
        "uploaded_paths": uploaded_paths,
        "source_tables": source_tables,
        "error": None,
    }
