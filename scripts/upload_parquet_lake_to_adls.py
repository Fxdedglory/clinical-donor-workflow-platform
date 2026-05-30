"""Upload a local Clinical Parquet lake batch to ADLS Gen2 using managed identity."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

DEFAULT_ACCOUNT_NAME = os.getenv("DATA_LAKE_ACCOUNT_NAME", "")
DEFAULT_CONTAINER = os.getenv("DATA_LAKE_CONTAINER", "datalake")
DEFAULT_AUTH_MODE = os.getenv("DATA_LAKE_AUTH_MODE", "managed_identity")
DEFAULT_BASE_PATH = os.getenv("DATA_LAKE_BASE_PATH", "bronze")


def _safe_partition(value: str) -> str:
    return value.replace("\\", "_").replace("/", "_").replace(":", "").replace(" ", "_")


def _manifest_files(lake_root: Path, source_system: str, batch_id: str) -> list[Path]:
    pattern = f"manifests/source_system={_safe_partition(source_system)}/extraction_date=*/{_safe_partition(batch_id)}.json"
    return sorted(lake_root.glob(pattern))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_blob_name(lake_root: Path, path: Path) -> str:
    return path.relative_to(lake_root).as_posix()


def _existing_source_files(lake_root: Path, manifest_path: Path, manifest: dict[str, Any]) -> list[Path]:
    files = {manifest_path}
    for entry in manifest.get("files", []):
        for key in ("parquet_path", "schema_path"):
            value = entry.get(key)
            if not value:
                continue
            candidate = Path(value)
            if candidate.exists():
                files.add(candidate)
                continue
            relative_candidate = lake_root / value
            if relative_candidate.exists():
                files.add(relative_candidate)
    return sorted(files)


def collect_upload_plan(lake_root: Path, source_system: str, batch_id: str) -> list[dict[str, str]]:
    manifests = _manifest_files(lake_root, source_system, batch_id)
    if not manifests:
        raise FileNotFoundError(f"No manifest found for source_system={source_system} batch_id={batch_id} under {lake_root}")

    plan: list[dict[str, str]] = []
    seen: set[str] = set()
    for manifest_path in manifests:
        manifest = _load_json(manifest_path)
        for source_path in _existing_source_files(lake_root, manifest_path, manifest):
            blob_name = _relative_blob_name(lake_root, source_path)
            if blob_name in seen:
                continue
            seen.add(blob_name)
            plan.append({"source_path": str(source_path), "blob_name": blob_name})
    return sorted(plan, key=lambda item: item["blob_name"])


def _content_type(path: Path) -> str:
    if path.suffix.lower() == ".json":
        return "application/json"
    if path.suffix.lower() == ".parquet":
        return "application/octet-stream"
    return "application/octet-stream"


def upload_plan(
    plan: list[dict[str, str]],
    *,
    account_name: str,
    container: str,
    auth_mode: str,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if dry_run:
        return [{**item, "status": "dry_run"} for item in plan]
    if auth_mode != "managed_identity":
        raise ValueError("Only DATA_LAKE_AUTH_MODE=managed_identity is supported. Storage keys are intentionally unsupported.")
    if not account_name:
        raise ValueError("DATA_LAKE_ACCOUNT_NAME or --account-name is required.")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    credential = DefaultAzureCredential()
    service = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=credential)
    container_client = service.get_container_client(container)

    results: list[dict[str, Any]] = []
    for item in plan:
        source_path = Path(item["source_path"])
        blob_name = item["blob_name"]
        with source_path.open("rb") as handle:
            container_client.upload_blob(
                name=blob_name,
                data=handle,
                overwrite=True,
                content_settings=ContentSettings(content_type=_content_type(source_path)),
            )
        results.append({**item, "status": "uploaded"})
    return results


def upload_parquet_lake_to_adls(
    *,
    lake_root: Path,
    source_system: str,
    batch_id: str,
    account_name: str = DEFAULT_ACCOUNT_NAME,
    container: str = DEFAULT_CONTAINER,
    auth_mode: str = DEFAULT_AUTH_MODE,
    dry_run: bool = False,
    delete_local_after_upload: bool = False,
) -> dict[str, Any]:
    plan = collect_upload_plan(lake_root, source_system, batch_id)
    results = upload_plan(plan, account_name=account_name, container=container, auth_mode=auth_mode, dry_run=dry_run)
    if delete_local_after_upload and not dry_run:
        batch_dirs = {Path(item["source_path"]).parent for item in plan if "extraction_batch_id=" in Path(item["source_path"]).as_posix()}
        for directory in sorted(batch_dirs, reverse=True):
            shutil.rmtree(directory, ignore_errors=True)
    return {
        "source_system": source_system,
        "extraction_batch_id": batch_id,
        "account_name": account_name,
        "container": container,
        "auth_mode": auth_mode,
        "dry_run": dry_run,
        "delete_local_after_upload": delete_local_after_upload,
        "file_count": len(results),
        "files": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake-root", type=Path, required=True)
    parser.add_argument("--source-system", default="clinical")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--account-name", default=DEFAULT_ACCOUNT_NAME)
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--auth-mode", default=DEFAULT_AUTH_MODE)
    parser.add_argument("--base-path", default=DEFAULT_BASE_PATH, help="Documented lake layer. Upload paths remain relative to lake root.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delete-local-after-upload", action="store_true")
    args = parser.parse_args()

    result = upload_parquet_lake_to_adls(
        lake_root=args.lake_root,
        source_system=args.source_system,
        batch_id=args.batch_id,
        account_name=args.account_name,
        container=args.container,
        auth_mode=args.auth_mode,
        dry_run=args.dry_run,
        delete_local_after_upload=args.delete_local_after_upload,
    )
    result["base_path"] = args.base_path
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
