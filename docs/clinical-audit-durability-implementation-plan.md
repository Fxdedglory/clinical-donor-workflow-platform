# Clinical Audit Durability Implementation Plan

RC1 planning date: 2026-06-13

Status: Planned for RC2 or a dedicated production-hardening sprint. Not implemented in RC1.

## Current Filesystem JSON Behavior

Committed clinical workflows call the shared writer in `backend/app/services/clinical_workflows.py`. The writer appends operation records to:

```text
metadata/workflow_operations.json
```

Each append currently:

1. creates the metadata directory if needed;
2. reads the existing JSON array;
3. appends one operation;
4. writes the full JSON array back to disk.

This behavior is sufficient for local demos and automated tests, but it is not a production audit store.

## Production Risks

| Risk | Production impact |
| --- | --- |
| Full-file rewrite | Concurrent commits can overwrite each other without locking or transaction isolation. |
| Ephemeral filesystem | Hosted app redeploys or container restarts can lose local metadata. |
| No database transaction coupling | Clinical state can commit while audit append fails, or audit append can succeed outside the same transaction boundary. |
| No immutable controls | File edits/deletes are not governed by database permissions, retention policy, or object immutability. |
| Weak queryability | Reports must scan a JSON file instead of using indexed operational audit rows. |
| Backup ambiguity | Metadata directory retention depends on deployment packaging and backup configuration. |

## Recommended Production Target

Use database-backed workflow operation audit as the query source of truth, with object-storage mirroring for evidence package durability.

### Proposed Table Shape

Table: `operational.clinical_workflow_operations`

| Column | Type | Notes |
| --- | --- | --- |
| `operation_pk` | big integer identity | Internal primary key. |
| `operation_id` | UUID/string unique | Existing public operation id. |
| `workflow` | text indexed | Example: `patient.create`, `reports.analytics_export`. |
| `entity_type` | text indexed | Example: `clinical_quality_event`. |
| `entity_id` | text indexed | Public identifier or stable entity id. |
| `actor_user_id` | integer nullable indexed | Link to user where available. |
| `actor_label` | text | Current actor string for human-readable evidence. |
| `timestamp` | timestamptz indexed | Operation timestamp in UTC. |
| `preview_hash` | text | Preview fingerprint. |
| `commit_confirmed` | boolean indexed | True for confirmed commit endpoints. |
| `status_before` | text nullable | Prior workflow status. |
| `status_after` | text nullable | Resulting workflow status. |
| `reason` | text | User/workflow rationale. |
| `changes` | jsonb | Changed fields and operation metadata. |
| `operation_hash` | text | Hash of canonical operation payload for tamper evidence. |
| `source_path` | text nullable | Backfill source such as `metadata/workflow_operations.json`. |
| `created_at` | timestamptz | Insert timestamp. |

### Append-Only Controls

- Grant application runtime role `INSERT` and `SELECT`.
- Do not grant application runtime `UPDATE` or `DELETE`.
- Add a trigger that rejects `UPDATE` and `DELETE` for defense in depth.
- Add indexes for workflow, entity, actor, timestamp, confirmation, and operation id.
- Consider row-level security only after reporting/query paths are finalized.

## Object-Storage Mirror Option

Mirror each committed operation to immutable object storage after the database insert succeeds.

Suggested object key pattern:

```text
clinical-workflow-operations/yyyy/mm/dd/{workflow}/{operation_id}.json
```

Mirror content should include:

- canonical operation JSON;
- operation hash;
- database `operation_pk`;
- application version/build identifier;
- write timestamp;
- optional batch manifest reference.

The mirror should be treated as durability and evidence packaging support, not as the primary operational query store.

## Migration Sequence

1. Add Alembic migration for `clinical_workflow_operations`.
2. Add a repository/service abstraction around workflow audit writes.
3. Insert workflow operation rows in the same transaction boundary as clinical commits where feasible.
4. Keep JSON append as a temporary compatibility mirror during rollout.
5. Switch audit readers and report evidence endpoints to database-first reads.
6. Add object-storage mirror after database writes are stable.
7. Add deployment settings for storage account/container, immutability policy, and retention.
8. Remove filesystem JSON as primary evidence source after backfill and validation.

## Backfill Plan

1. Read existing `metadata/workflow_operations.json`.
2. Validate each entry has operation id, workflow, entity type/id, actor, timestamp, preview hash, confirmation status, status transition, reason, and changes.
3. Generate missing `operation_hash` values from canonicalized JSON.
4. Insert idempotently using `operation_id` uniqueness.
5. Record `source_path` as `metadata/workflow_operations.json`.
6. Produce a backfill report with inserted, skipped, rejected, and duplicate counts.

## Validation Strategy

Automated validation should cover:

- confirmation header failures still reject before durable mutation;
- successful commit inserts exactly one audit row;
- audit insert participates in rollback when clinical commit fails;
- duplicate backfill is idempotent;
- readers prefer database rows over filesystem JSON;
- object mirror failures are surfaced and retried without losing database audit rows;
- application runtime cannot update or delete audit rows.

Manual validation should cover:

- audit evidence route filters by workflow, actor, entity, module, and date;
- reports audit activity reflects newly committed operations;
- backup and restore include audit rows;
- object-storage immutability/retention settings are enabled in production.

## Future Sprint Scope

RC2 should implement the database table, writer abstraction, backfill script, and database-first readers. Object-storage mirroring can be RC2 if deployment storage is approved, otherwise it should be the next production-hardening sprint.
