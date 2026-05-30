"""Validate locally exported Clinical Parquet lake files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.export_to_parquet_lake import REQUIRED_METADATA_COLUMNS  # noqa: E402


def _pyarrow() -> Any:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency guard.
        raise SystemExit("pyarrow is required for Parquet validation. Run: pip install -r requirements.txt") from exc
    return pq


def _manifest_files(lake_root: Path, source_system: str | None, batch_id: str | None) -> list[Path]:
    manifests = sorted((lake_root / "manifests").glob("source_system=*/extraction_date=*/*.json"))
    if source_system:
        manifests = [path for path in manifests if f"source_system={source_system}" in path.as_posix()]
    if batch_id:
        manifests = [path for path in manifests if path.stem == batch_id]
    return manifests


def validate_parquet_lake(lake_root: Path, source_system: str | None = None, batch_id: str | None = None) -> dict[str, Any]:
    pq = _pyarrow()
    issues: list[str] = []
    checked_files = 0
    checked_rows = 0
    manifests = _manifest_files(lake_root, source_system, batch_id)
    if not manifests:
        issues.append("No manifest files found for the requested filters.")

    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_rows = 0
        for entry in manifest.get("files", []):
            checked_files += 1
            parquet_path = Path(entry["parquet_path"])
            if not parquet_path.exists():
                issues.append(f"Missing Parquet file: {parquet_path}")
                continue
            table = pq.ParquetFile(parquet_path).read()
            checked_rows += table.num_rows
            manifest_rows += table.num_rows
            if table.num_rows != int(entry.get("row_count", -1)):
                issues.append(f"Row count mismatch for {parquet_path}: manifest={entry.get('row_count')} actual={table.num_rows}")
            missing = [column for column in REQUIRED_METADATA_COLUMNS if column not in table.column_names]
            if missing:
                issues.append(f"{parquet_path} missing metadata columns: {missing}")
            for part in ["source_system=", "source_table=", "extraction_date=", "extraction_batch_id="]:
                if part not in parquet_path.as_posix():
                    issues.append(f"{parquet_path} missing partition component {part}")
            schema_path = Path(entry["schema_path"])
            if not schema_path.exists():
                issues.append(f"Missing schema file: {schema_path}")
        if manifest_rows != int(manifest.get("row_count", -1)):
            issues.append(f"Manifest row count mismatch for {manifest_path}: manifest={manifest.get('row_count')} actual={manifest_rows}")

    return {
        "status": "passed" if not issues else "failed",
        "lake_root": str(lake_root),
        "manifest_count": len(manifests),
        "checked_file_count": checked_files,
        "checked_row_count": checked_rows,
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake-root", type=Path, required=True)
    parser.add_argument("--source-system", default=None)
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    result = validate_parquet_lake(args.lake_root, source_system=args.source_system, batch_id=args.batch_id)
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
