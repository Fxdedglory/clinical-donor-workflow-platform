# Clinical Data Producer Runbook

## Purpose

The data producer makes the Clinical Donor Platform behave like a living regulated source system. It creates and mutates clinical donor, partner portal, QMS, vendor SLA, document, audit, and workflow activity.

## Data Domains

Generated or mutated domains include:

- donor referrals
- donor screenings
- eligibility decisions
- medical/social history
- infectious disease results
- tissue and recovery suitability
- processing release records
- partner portal submissions
- partner messages and document submissions
- partner quality complaints
- workflow tasks and responses
- QMS deviations and CAPAs
- vendor SLA incidents
- audit events
- realtime/system activity
- training expirations/completions

## Safety Controls

- Write operations require `--confirm` in CLI.
- API write operations require `confirm=true`.
- Continuous mode defaults to finite cycles.
- Infinite mode requires explicit `allow_infinite=true` and `DATA_PRODUCER_ALLOW_INFINITE=true`.
- Interval and cycle guardrails are enforced.
- Stop-file path: `data/generated/STOP_CONTINUOUS`.
- Generated metadata and exports are ignored by Git.

## CLI Commands

Seed:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py seed --records 1200 --seed 42 --confirm
```

Incremental:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py incremental --scale 1 --seed 42 --confirm
```

Validate:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py validate --confirm
```

Export:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py export --batch-id smoke_batch --confirm
```

One-cycle continuous:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py continuous --interval-seconds 1 --cycles 1 --scale 1 --seed 42 --confirm
```

Status:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py status
```

Stop:

```powershell
.\.venv\Scripts\python scripts\run_data_producer.py stop --confirm
```

## API Endpoints

Read:

- `GET /api/generation/status`
- `GET /api/generation/runs`
- `GET /api/generation/continuous/status`
- `GET /api/monitoring/source-freshness`
- `GET /api/monitoring/validation`
- `GET /api/monitoring/export-manifest`

Write:

- `POST /api/generation/seed?confirm=true`
- `POST /api/generation/incremental?confirm=true`
- `POST /api/generation/validate?confirm=true`
- `POST /api/generation/export?confirm=true`
- `POST /api/generation/continuous/start?confirm=true`
- `POST /api/generation/continuous/stop?confirm=true`

All producer API routes require `system.admin`.

## Metadata Outputs

Ignored metadata path:

```text
data/generated/
```

Ignored export path:

```text
data/exports/<batch_id>/
```

Each export batch includes:

- CSV files for source tables
- `manifest.json`
- row counts
- checksums
- `source_system`
- `extraction_batch_id`
- extracted timestamps
