"""Guarded tiny ADLS upload smoke test for the Clinical app process."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CONFIRMATION_PHRASE = "UPLOAD_TINY_ADLS_SMOKE"
SOURCE_TABLE = "adls_smoke"


UploadFn = Callable[
    [list[dict[str, str]], str, str, str],
    list[dict[str, Any]],
]


def _safe_partition(value: str) -> str:
    return value.replace("\\", "_").replace("/", "_").replace(":", "").replace(" ", "_")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_tiny_adls_smoke_batch(
    lake_root: Path,
    *,
    source_system: str,
    batch_id: str | None = None,
    base_path: str = "bronze",
) -> dict[str, Any]:
    generated_at = datetime.now(UTC)
    extraction_date = generated_at.date().isoformat()
    safe_source = _safe_partition(source_system)
    safe_batch = _safe_partition(batch_id or f"adls_smoke_{safe_source}_{generated_at:%Y%m%dT%H%M%SZ}")

    parquet_path = (
        lake_root
        / base_path
        / f"source_system={safe_source}"
        / f"source_table={SOURCE_TABLE}"
        / f"extraction_date={extraction_date}"
        / f"extraction_batch_id={safe_batch}"
        / "part-00000.parquet"
    )
    schema_path = lake_root / "_schemas" / f"source_system={safe_source}" / f"{SOURCE_TABLE}.json"
    manifest_path = (
        lake_root
        / "manifests"
        / f"source_system={safe_source}"
        / f"extraction_date={extraction_date}"
        / f"{safe_batch}.json"
    )

    row = {
        "source_system": source_system,
        "source_table": SOURCE_TABLE,
        "source_record_id": f"{safe_source}-{safe_batch}-001",
        "source_created_at": generated_at.isoformat(),
        "source_updated_at": generated_at.isoformat(),
        "extraction_batch_id": safe_batch,
        "generated_at": generated_at.isoformat(),
        "extraction_date": extraction_date,
        "is_deleted": False,
        "operation_type": "insert",
        "smoke_value": 1,
    }

    import pyarrow as pa
    import pyarrow.parquet as pq

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([row])
    compression = "snappy"
    try:
        pq.write_table(table, parquet_path, compression=compression)
    except Exception:
        compression = "uncompressed"
        pq.write_table(table, parquet_path)

    parquet_hash = _sha256(parquet_path)
    schema_payload = {
        "source_system": source_system,
        "source_table": SOURCE_TABLE,
        "extraction_batch_id": safe_batch,
        "generated_at": generated_at.isoformat(),
        "compression": compression,
        "columns": [{"name": field.name, "type": str(field.type)} for field in table.schema],
    }
    _write_json(schema_path, schema_payload)

    parquet_blob = parquet_path.relative_to(lake_root).as_posix()
    schema_blob = schema_path.relative_to(lake_root).as_posix()
    manifest_blob = manifest_path.relative_to(lake_root).as_posix()
    manifest_payload = {
        "source_system": source_system,
        "source_table": SOURCE_TABLE,
        "extraction_batch_id": safe_batch,
        "extraction_date": extraction_date,
        "generated_at": generated_at.isoformat(),
        "row_count": 1,
        "file_count": 1,
        "compression": compression,
        "files": [
            {
                "path": parquet_blob,
                "row_count": 1,
                "checksum_sha256": parquet_hash,
                "schema_path": schema_blob,
            }
        ],
    }
    _write_json(manifest_path, manifest_payload)

    upload_plan = [
        {"source_path": str(parquet_path), "blob_name": parquet_blob},
        {"source_path": str(manifest_path), "blob_name": manifest_blob},
        {"source_path": str(schema_path), "blob_name": schema_blob},
    ]
    return {
        "source_system": source_system,
        "source_table": SOURCE_TABLE,
        "batch_id": safe_batch,
        "extraction_date": extraction_date,
        "row_count": 1,
        "compression": compression,
        "upload_plan": upload_plan,
        "uploaded_paths": [item["blob_name"] for item in upload_plan],
    }


def upload_files_with_managed_identity(
    upload_plan: list[dict[str, str]],
    account_name: str,
    container: str,
    auth_mode: str,
) -> list[dict[str, Any]]:
    if auth_mode != "managed_identity":
        raise ValueError("Only DATA_LAKE_AUTH_MODE=managed_identity is supported.")
    if not account_name:
        raise ValueError("DATA_LAKE_ACCOUNT_NAME is required.")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential,
    )
    container_client = service.get_container_client(container)

    uploaded: list[dict[str, Any]] = []
    for item in upload_plan:
        source_path = Path(item["source_path"])
        content_type = "application/json" if source_path.suffix == ".json" else "application/octet-stream"
        with source_path.open("rb") as handle:
            container_client.upload_blob(
                name=item["blob_name"],
                data=handle,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
        uploaded.append({"path": item["blob_name"], "status": "uploaded"})
    return uploaded


def run_adls_smoke_upload(
    *,
    source_system: str = "clinical",
    uploader: UploadFn | None = None,
) -> dict[str, Any]:
    account_name = os.getenv("DATA_LAKE_ACCOUNT_NAME", "")
    container = os.getenv("DATA_LAKE_CONTAINER", "datalake")
    auth_mode = os.getenv("DATA_LAKE_AUTH_MODE", "managed_identity")
    base_path = os.getenv("DATA_LAKE_BASE_PATH", "bronze")
    active_uploader = uploader or upload_files_with_managed_identity

    with tempfile.TemporaryDirectory(prefix=f"{source_system}-adls-smoke-") as tmp_dir:
        batch = create_tiny_adls_smoke_batch(
            Path(tmp_dir),
            source_system=source_system,
            base_path=base_path,
        )
        uploaded = active_uploader(batch["upload_plan"], account_name, container, auth_mode)

    uploaded_paths = [item.get("path") or item.get("blob_name", "") for item in uploaded]
    return {
        "source_system": source_system,
        "status": "uploaded",
        "file_count": len(uploaded),
        "row_count": batch["row_count"],
        "uploaded_paths": uploaded_paths,
        "batch_id": batch["batch_id"],
        "auth_mode": auth_mode,
        "account_name": account_name,
        "container": container,
        "error": None,
    }
