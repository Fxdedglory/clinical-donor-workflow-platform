# Clinical Parquet Lake Export Runbook

## Local Setup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`pyarrow` is required for Parquet read/write support. The preferred compression is Snappy. If Snappy is not available locally, rerun with `--compression zstd` or `--compression none` and document the fallback.

## Fixture Smoke Export

Use fixture mode when PostgreSQL is unavailable or when you need a read-only test that does not touch the application database.

```powershell
$fixtureRoot = "E:\temp\clinical-parquet-fixture"
$lakeRoot = "E:\temp\clinical-parquet-lake"

Remove-Item -Recurse -Force $fixtureRoot,$lakeRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $fixtureRoot | Out-Null
@"
donor_id,created_at,updated_at
DNR-TEST-001,2026-05-01T10:00:00Z,2026-05-02T10:00:00Z
"@ | Set-Content -Encoding utf8 "$fixtureRoot\dim_donor.csv"

.\.venv\Scripts\python.exe scripts\export_to_parquet_lake.py `
  --fixture-root $fixtureRoot `
  --lake-root $lakeRoot `
  --batch-id clinical_fixture_parquet `
  --source-system clinical

.\.venv\Scripts\python.exe scripts\validate_parquet_lake.py `
  --lake-root $lakeRoot `
  --source-system clinical `
  --batch-id clinical_fixture_parquet
```

## Database Read-Only Export

```powershell
.\.venv\Scripts\python.exe scripts\export_to_parquet_lake.py `
  --lake-root data\datalake `
  --batch-id clinical_db_parquet `
  --source-system clinical `
  --limit-per-table 1000
```

Use `--tables table_a,table_b` to export a smaller subset. The exporter reads data only and does not mutate the database.

## Expected Result

The command writes:

- partitioned bronze Parquet files
- one manifest JSON per batch
- one schema JSON per table

## Troubleshooting

- `pyarrow is required`: install dependencies from `requirements.txt`.
- Database connection failure: confirm the redacted `DATABASE_URL` pattern and use fixture mode if the database is not available.
- Permission denied: confirm the runtime database role has `SELECT` on the exported tables.
- `No manifest files found`: confirm `--lake-root`, `--source-system`, and `--batch-id`.
