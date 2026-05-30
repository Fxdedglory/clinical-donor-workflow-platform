"""Export Clinical source data to a partitioned Parquet lake layout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

REQUIRED_METADATA_COLUMNS = [
    "source_system",
    "source_table",
    "source_record_id",
    "source_created_at",
    "source_updated_at",
    "extraction_batch_id",
    "generated_at",
    "extraction_date",
    "is_deleted",
    "operation_type",
]


def _pyarrow() -> tuple[Any, Any]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency guard.
        raise SystemExit("pyarrow is required for Parquet export. Run: pip install -r requirements.txt") from exc
    return pa, pq


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_partition(value: str) -> str:
    return value.replace("\\", "_").replace("/", "_").replace(":", "").replace(" ", "_")


def _read_fixture_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _infer_extraction_date(rows: list[dict[str, str]], fallback: str) -> str:
    for row in rows:
        value = row.get("generated_at") or row.get("extracted_at") or row.get("source_updated_at") or row.get("updated_at")
        if value:
            return str(value)[:10]
    return fallback


def _normalize_rows(
    rows: list[dict[str, Any]],
    *,
    table_name: str,
    source_system: str,
    extraction_batch_id: str,
    generated_at: str,
    extraction_date: str,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        item = {key: "" if value is None else str(value) for key, value in row.items()}
        original_source = item.get("source_system", "")
        if original_source and original_source != source_system:
            item.setdefault("source_subsystem", original_source)
        item["source_system"] = source_system
        item["source_table"] = table_name
        item["source_record_id"] = item.get("source_record_id") or f"{table_name}-{idx}"
        item["source_created_at"] = item.get("source_created_at") or item.get("created_at") or item.get("submitted_at") or generated_at
        item["source_updated_at"] = item.get("source_updated_at") or item.get("updated_at") or item.get("changed_at") or item.get("submitted_at") or item.get("created_at") or generated_at
        item["extraction_batch_id"] = extraction_batch_id
        item["generated_at"] = item.get("generated_at") or generated_at
        item["extraction_date"] = extraction_date
        item["is_deleted"] = item.get("is_deleted") or "false"
        item["operation_type"] = item.get("operation_type") or ("delete" if item["is_deleted"].lower() == "true" else "snapshot")
        normalized.append(item)
    return normalized


def _db_rows(selected_tables: set[str] | None, limit_per_table: int | None) -> list[tuple[str, list[dict[str, Any]], list[str]]]:
    from app.database import SessionLocal
    from app.services.data_producer import (
        EXPORT_MODELS,
        _record_timestamp,
        _serialize_cell,
        _source_record_id,
    )
    from sqlalchemy import select

    tables: list[tuple[str, list[dict[str, Any]], list[str]]] = []
    with SessionLocal() as db:
        for table_name, model in EXPORT_MODELS:
            if selected_tables and table_name not in selected_tables:
                continue
            columns = [column.name for column in model.__table__.columns]
            statement = select(model)
            if limit_per_table:
                statement = statement.limit(limit_per_table)
            rows: list[dict[str, Any]] = []
            for record in db.execute(statement).scalars().all():
                row = {column: _serialize_cell(getattr(record, column)) for column in columns}
                row["source_record_id"] = _source_record_id(record, model)
                row["source_created_at"] = _record_timestamp(record, "created_at", "submitted_at", "opened_at")
                row["source_updated_at"] = _record_timestamp(record, "updated_at", "changed_at", "submitted_at", "created_at", "opened_at")
                rows.append(row)
            tables.append((table_name, rows, columns))
    return tables


def _fixture_rows(fixture_root: Path, selected_tables: set[str] | None) -> list[tuple[str, list[dict[str, Any]], list[str]]]:
    tables = []
    for path in sorted(fixture_root.glob("*.csv")):
        table_name = path.stem
        if selected_tables and table_name not in selected_tables:
            continue
        rows, headers = _read_fixture_csv(path)
        tables.append((table_name, rows, headers))
    return tables


def export_to_parquet_lake(
    *,
    lake_root: Path,
    batch_id: str | None = None,
    source_system: str = "clinical",
    fixture_root: Path | None = None,
    tables: list[str] | None = None,
    limit_per_table: int | None = None,
    compression: str = "snappy",
) -> dict[str, Any]:
    pa, pq = _pyarrow()
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    extraction_batch_id = batch_id or f"parquet_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    fallback_date = date.today().isoformat()
    selected_tables = set(tables or [])
    source_tables = (
        _fixture_rows(fixture_root, selected_tables or None)
        if fixture_root
        else _db_rows(selected_tables or None, limit_per_table)
    )
    files: list[dict[str, Any]] = []

    for table_name, rows, headers in source_tables:
        extraction_date = _infer_extraction_date(rows, fallback_date)
        normalized = _normalize_rows(
            rows,
            table_name=table_name,
            source_system=source_system,
            extraction_batch_id=extraction_batch_id,
            generated_at=generated_at,
            extraction_date=extraction_date,
        )
        fieldnames = list(dict.fromkeys([*headers, *REQUIRED_METADATA_COLUMNS, "source_subsystem"]))
        table = pa.table({field: [row.get(field, "") for row in normalized] for field in fieldnames})
        parquet_path = (
            lake_root
            / "bronze"
            / f"source_system={_safe_partition(source_system)}"
            / f"source_table={_safe_partition(table_name)}"
            / f"extraction_date={extraction_date}"
            / f"extraction_batch_id={_safe_partition(extraction_batch_id)}"
            / "part-00000.parquet"
        )
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, parquet_path, compression=compression)
        schema_path = lake_root / "_schemas" / f"source_system={_safe_partition(source_system)}" / f"source_table={_safe_partition(table_name)}.json"
        _write_json(
            schema_path,
            {
                "source_system": source_system,
                "source_table": table_name,
                "fields": [{"name": field.name, "type": str(field.type)} for field in table.schema],
                "generated_at": generated_at,
            },
        )
        files.append(
            {
                "source_table": table_name,
                "parquet_path": str(parquet_path),
                "schema_path": str(schema_path),
                "row_count": table.num_rows,
                "checksum_sha256": _sha256(parquet_path),
                "compression": compression,
                "extraction_date": extraction_date,
            }
        )

    manifest = {
        "source_system": source_system,
        "extraction_batch_id": extraction_batch_id,
        "generated_at": generated_at,
        "lake_root": str(lake_root),
        "layout": "bronze/source_system/source_table/extraction_date/extraction_batch_id",
        "file_count": len(files),
        "row_count": sum(file["row_count"] for file in files),
        "files": files,
        "required_metadata_columns": REQUIRED_METADATA_COLUMNS,
        "mode": "fixture" if fixture_root else "database_read_only",
    }
    manifest_path = (
        lake_root
        / "manifests"
        / f"source_system={_safe_partition(source_system)}"
        / f"extraction_date={date.today().isoformat()}"
        / f"{_safe_partition(extraction_batch_id)}.json"
    )
    manifest["manifest_path"] = str(manifest_path)
    _write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake-root", type=Path, required=True)
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--source-system", default="clinical")
    parser.add_argument("--fixture-root", type=Path, default=None)
    parser.add_argument("--tables", default="", help="Comma-separated table names to export.")
    parser.add_argument("--limit-per-table", type=int, default=None)
    parser.add_argument("--compression", default="snappy")
    args = parser.parse_args()

    manifest = export_to_parquet_lake(
        lake_root=args.lake_root,
        batch_id=args.batch_id,
        source_system=args.source_system,
        fixture_root=args.fixture_root,
        tables=[item.strip() for item in args.tables.split(",") if item.strip()],
        limit_per_table=args.limit_per_table,
        compression=args.compression,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
