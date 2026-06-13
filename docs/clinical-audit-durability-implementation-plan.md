# Clinical Audit Durability Implementation Plan

RC1 planning date: 2026-06-13

Post-RC implementation date: 2026-06-13

Status: Database-backed workflow audit foundation implemented in `CLINICAL-POST-RC-01`. Object/WORM mirror foundation implemented in `CLINICAL-POST-RC-06`; real cloud provider integration remains planned.

Post-RC-06 WORM mirror foundation date: 2026-06-13

## Current Audit Behavior

Committed clinical workflows call the shared writer in `backend/app/services/clinical_workflows.py`. The writer now attempts a DB insert into:

```text
operational.clinical_workflow_audit_events
```

It also preserves the existing JSON mirror:

```text
metadata/workflow_operations.json
```

Each append now:

1. inserts one DB-backed audit event when a DB session is supplied;
2. commits the audit row after the clinical workflow commit has succeeded;
3. creates the metadata directory if needed;
4. reads the existing JSON array;
5. appends one operation;
6. writes the full JSON array back to disk;
7. optionally mirrors the redacted payload to the configured object/WORM target;
8. records mirror attempt metadata in `operational.clinical_workflow_audit_mirror_events`.

Quality audit evidence and report audit activity readers use DB rows first and fall back to JSON when no DB rows are available.

## Production Risks

| Risk | Production impact |
| --- | --- |
| JSON mirror full-file rewrite | JSON remains compatibility evidence only and can still race under high concurrency. |
| Real cloud object provider not implemented | External immutable evidence package storage still requires approved provider SDK integration, retention policy, and legal hold controls. |
| Audit transaction boundary | Current writer records DB audit after the clinical commit succeeds, preserving workflow success but not making the audit insert part of the original domain transaction. |
| Backfill execution pending | Existing JSON rows must be backfilled in each target environment before DB-only evidence review. |
| Backup policy pending | Production backup/restore must explicitly include `operational.clinical_workflow_audit_events`. |

## Recommended Production Target

Use database-backed workflow operation audit as the query source of truth, with object-storage mirroring for evidence package durability in a later hardening sprint.

### Implemented Table Shape

Migration: `database/migrations/versions/202606130001_clinical_workflow_audit_events.py`

Table: `operational.clinical_workflow_audit_events`

Historical RC1 planning used the proposed name `operational.clinical_workflow_operations`. The implemented post-RC table is `operational.clinical_workflow_audit_events`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | integer primary key | Internal primary key. |
| `operation_id` | string unique indexed | Existing public operation id. |
| `workflow` | string indexed | Example: `patient.create`, `reports.analytics_export`. |
| `entity_type` | string indexed | Example: `clinical_quality_event`. |
| `entity_id` | string indexed | Public identifier or stable entity id. |
| `actor` | string indexed | Human-readable actor label. |
| `timestamp` | timestamptz indexed | Operation timestamp in UTC. |
| `preview_hash` | text | Preview fingerprint. |
| `commit_confirmed` | boolean indexed | True for confirmed commit endpoints. |
| `status_before` | text nullable | Prior workflow status. |
| `status_after` | text nullable | Resulting workflow status. |
| `reason` | text | User/workflow rationale. |
| `changes_json` | json | Changed fields and operation metadata. |
| `source` | string indexed | `workflow_commit` or `json_backfill`. |
| `created_at` | timestamptz | Insert timestamp. |

### Mirror Attempt Table Shape

Migration: `database/migrations/versions/202606130002_clinical_audit_worm_mirror.py`

Table: `operational.clinical_workflow_audit_mirror_events`

| Column | Type | Notes |
| --- | --- | --- |
| `mirror_event_id` | integer primary key | Internal primary key. |
| `operation_id` | string indexed | Existing public operation id. |
| `mirror_mode` | string indexed | `disabled`, `local_filesystem`, `object_storage`, or future provider mode. |
| `mirror_status` | string indexed | `mirrored`, `failed`, `skipped`, or `dry_run`. |
| `payload_profile` | string indexed | `audit_metadata`. |
| `mirrored_at` | timestamptz nullable | Set when a mirror object is written. |
| `mirror_uri` | text nullable | Local simulation URI or future object URI. |
| `mirror_checksum` | string indexed | SHA-256 over canonical redacted payload JSON. |
| `mirror_error` | text nullable | Failure/skip reason. |
| `dry_run` | boolean indexed | True for replay preview. |
| `created_at` | timestamptz indexed | Insert timestamp. |

### Append-Only Controls

- Migration adds a trigger that rejects `UPDATE` and `DELETE` for defense in depth.
- Production DB role review should grant application runtime role `INSERT` and `SELECT` on audit and mirror tables.
- Production DB role review should not grant application runtime `UPDATE` or `DELETE` on audit or mirror tables.
- Add indexes for workflow, entity, actor, timestamp, confirmation, and operation id.
- Consider row-level security only after reporting/query paths are finalized.

## Object-Storage Mirror Foundation

Mirror each committed operation to immutable object storage after the database insert succeeds and the JSON compatibility mirror is preserved. Post-RC-06 implements the interface, local simulation, checksum, status ledger, and replay helper. It does not call Azure/AWS/GCP SDKs.

Suggested object key pattern:

```text
workflow-audit/{workflow}/yyyy/mm/{operation_id}.json
```

Mirror content should include:

- canonical operation JSON;
- payload schema version;
- `audit_metadata` profile marker;
- redaction marker;
- SHA-256 checksum recorded in the mirror ledger.

The mirror should be treated as durability and evidence packaging support, not as the primary operational query store.

## Migration Sequence

1. Apply Alembic migration `202606130001_clinical_workflow_audit_events.py`.
2. Deploy shared writer changes in `backend/app/services/clinical_workflows.py`.
3. Confirm successful workflow commits write DB rows and JSON mirror entries.
4. Run JSON backfill where historical `metadata/workflow_operations.json` exists.
5. Confirm `/api/clinical/quality/audit-evidence` reads DB-backed operations with database-first reads.
6. Confirm `/api/clinical/reports/audit-activity` reads DB-backed operations with database-first reads.
7. Apply Alembic migration `202606130002_clinical_audit_worm_mirror.py`.
8. Configure `AUDIT_OBJECT_MIRROR_MODE` for disabled, local simulation, or future object provider placeholder.
9. Keep filesystem JSON as a compatibility mirror/fallback during the next hardening cycle.

## Backfill Plan

1. Read existing `metadata/workflow_operations.json`.
2. Validate each entry has operation id, workflow, entity type/id, actor, timestamp, preview hash, confirmation status, status transition, reason, and changes.
3. Insert idempotently using existing DB operation ids and `operation_id` uniqueness.
4. Record `source` as `json_backfill`.
5. Return a backfill report with inserted, skipped, rejected, and source-deleted status.
6. Preserve `metadata/workflow_operations.json` without deleting or rewriting it.

## Mirror Replay Plan

1. Query `operational.clinical_workflow_audit_events` in timestamp/id order.
2. Query successful non-dry-run mirror attempts by operation id.
3. Skip already mirrored operation ids.
4. Mirror pending audit rows with the same redacted canonical payload shape.
5. Record mirror attempt status, URI, checksum, and error if not running dry-run.
6. Preserve DB audit rows and JSON source without deleting or rewriting them.

## Validation Strategy

Automated validation should cover:

- confirmation header failures still reject before durable mutation;
- successful commit inserts audit rows through the shared writer;
- JSON mirror remains intact and append-only at the file level;
- backfill parses JSON without deleting source JSON;
- readers prefer database rows over filesystem JSON;
- object mirror failures are surfaced and retried without losing database audit rows;
- replay mirrors unmirrored DB audit rows and skips successful mirror attempts;
- application runtime cannot update or delete audit or mirror rows.

Manual validation should cover:

- audit evidence route filters by workflow, actor, entity, module, and date;
- reports audit activity reflects newly committed operations;
- backup and restore include audit rows;
- object-storage immutability/retention and legal hold settings are enabled in production.

## Future Sprint Scope

The next sprint should add real provider SDK integration, signed manifest support, provider-specific retention/legal-hold automation, environment-specific replay execution guidance, and operational backup/restore verification for audit and mirror evidence.
