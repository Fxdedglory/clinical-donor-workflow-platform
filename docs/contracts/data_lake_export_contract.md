# Clinical Data Lake Export Contract

## Purpose

The Clinical Donor Platform can export clinical workflow source tables to a local bronze data lake layout using compressed Parquet. The exporter is read-only against the application database and prepares future handoff to Azure object storage and Snowflake.

## Layout

```text
datalake/
  bronze/
    source_system=clinical/
      source_table=<table_name>/
        extraction_date=YYYY-MM-DD/
          extraction_batch_id=<batch_id>/
            part-00000.parquet
  manifests/
    source_system=clinical/
      extraction_date=YYYY-MM-DD/
        <batch_id>.json
  _schemas/
    source_system=clinical/
      source_table=<table_name>.json
```

## Inputs

`scripts/export_to_parquet_lake.py` supports two modes:

- Database read-only mode using `DATABASE_URL`.
- Fixture mode using `--fixture-root` with CSV files for local smoke tests.

Database mode exports the selected source/domain models exposed by the data producer service. Fixture mode is intended for tests and local validation when a PostgreSQL connection is not available.

## Required Metadata Columns

Every Parquet file must include:

- `source_system`
- `source_table`
- `source_record_id`
- `source_created_at`
- `source_updated_at`
- `extraction_batch_id`
- `generated_at`
- `extraction_date`
- `is_deleted`
- `operation_type`

## Operation Types

Allowed values:

- `snapshot`
- `insert`
- `update`
- `delete`

The initial exporter writes `snapshot` unless source rows already provide a more specific operation type.

## Runtime Database Role

The exporter should use the same least-privilege runtime database role used by the application when possible. The role needs `SELECT` access to exported source/domain tables and must not require schema ownership or administrative privileges.

## Manifest

Each export writes a manifest with:

- `source_system`
- `extraction_batch_id`
- `generated_at`
- `lake_root`
- `file_count`
- `row_count`
- file-level row counts
- file-level SHA-256 checksums
- compression codec
- schema paths
- export mode, either `database_read_only` or `fixture`

## Validation

`scripts/validate_parquet_lake.py` verifies:

- manifests exist
- referenced Parquet files exist
- row counts match the manifest
- required metadata columns exist
- partition path components exist
- schema files exist

## Git Policy

Generated lake output is ignored:

- `datalake/`
- `data/datalake/`
- `data/lake/`
- `*.parquet`

Do not commit generated Parquet files, local manifests, local schemas, or large smoke-test output.
