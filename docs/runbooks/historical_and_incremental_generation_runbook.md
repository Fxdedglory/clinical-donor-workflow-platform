# Historical And Incremental Generation Runbook

Run against local or non-production databases first. Do not run large or enterprise profiles against Azure PostgreSQL until capacity, backup, and rollback steps are approved.

## Historical Baseline

```powershell
.\.venv\Scripts\python.exe scripts\run_data_producer.py seed `
  --profile demo `
  --seed 42 `
  --force `
  --confirm
```

Override the historical range:

```powershell
.\.venv\Scripts\python.exe scripts\run_data_producer.py seed `
  --profile small `
  --start-date 2025-07-01 `
  --end-date 2026-05-29 `
  --seed 42 `
  --force `
  --confirm
```

## Incremental Generation

Incremental generation reads current DB state and references existing donors, users, partner organizations, tissue types, eligibility rules, vendors, and workflow records.

```powershell
.\.venv\Scripts\python.exe scripts\run_data_producer.py incremental `
  --profile demo `
  --seed 43 `
  --confirm
```

## Validate And Export

```powershell
.\.venv\Scripts\python.exe scripts\run_data_producer.py validate --confirm

.\.venv\Scripts\python.exe scripts\run_data_producer.py export `
  --batch-id clinical_demo_export `
  --confirm
```

## Continuous Mode

```powershell
.\.venv\Scripts\python.exe scripts\run_data_producer.py continuous `
  --interval-seconds 30 `
  --cycles 1 `
  --profile demo `
  --seed 42 `
  --confirm
```

Use `demo` first on Azure. Move to `small` only after backups and Monitor health checks are clean. `medium`, `large`, and `enterprise` require PostgreSQL capacity review and external export storage.
