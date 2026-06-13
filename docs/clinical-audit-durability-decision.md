# Clinical Audit Durability Decision

Status: RC1 implementation plan documented; production migration deferred

RC0 decision date: 2026-06-12

RC1 update date: 2026-06-13

## Current Behavior

Clinical workflow commits append operation records to:

```text
metadata/workflow_operations.json
```

The shared writer in `backend/app/services/clinical_workflows.py`:

- creates the `metadata` directory if missing;
- reads the existing JSON array;
- appends the new operation record;
- writes the full JSON array back to disk.

Audit operation entries include operation id, workflow, entity type, entity id, actor, timestamp, preview hash, confirmation status, before/after status, reason, and changed fields.

## Why This Is Acceptable For RC0

- The file-backed audit trail is simple, testable, and already covered by module tests.
- It preserves the Preview -> Commit pattern and confirms the platform writes workflow evidence on successful commits.
- It is useful for local development, demos, and release-candidate functional validation.

## Risks Of Filesystem-Only Audit Storage

| Risk | Impact |
| --- | --- |
| Single-file overwrite pattern | Concurrent commits can race and lose entries without file locking or transactional storage. |
| Local filesystem dependency | Container/app-service restarts, redeploys, or ephemeral disks can lose audit data. |
| No immutable retention controls | File edits/deletes are not governed by database permissions, object immutability, or retention policies. |
| Limited queryability | Reporting must read and filter the full JSON file rather than indexed audit records. |
| Backup ambiguity | Audit durability depends on whether the metadata directory is included in backup and deployment plans. |
| Scaling limits | Full-file read/write grows poorly as workflow volume increases. |

## Recommended Production Path

Use both database-backed audit storage and object-storage mirroring.

Primary path:

- Add an append-only `operational.clinical_workflow_operations` table.
- Write audit operation records transactionally alongside clinical commits.
- Add indexes for workflow, entity type, entity id, actor, timestamp, and commit confirmation.
- Restrict update/delete permissions at the database role level.

Durability mirror:

- Mirror each operation to object storage, ideally append-only or immutable/WORM-capable storage.
- Partition by UTC date and workflow prefix.
- Include operation checksum or signed manifest support in a later compliance hardening sprint.

## Future Migration Plan

1. Create an Alembic migration for `operational.clinical_workflow_operations`.
2. Add a new audit repository service with dual-write support:
   - database insert as the source of query truth;
   - JSON/object mirror for external evidence packages.
3. Backfill existing `metadata/workflow_operations.json` into the database with a one-time script.
4. Update report and quality audit evidence readers to query the database first.
5. Keep JSON export generation for evidence packages, not as the primary operational store.
6. Add tests for transactional insert, idempotent backfill, and object mirror failure handling.
7. Add deployment runbook steps for backup/restore and retention policy verification.

## RC0 Decision

Do not implement production audit storage in RC0.

Reason:

- RC0 is a hardening pass and should not add a broad persistence migration beyond documentation/test safety.
- The existing audit writer is validated and already used consistently by clinical modules.
- Production durability needs a designed migration, retention policy, and deployment review rather than an opportunistic table addition.

## RC1 Readiness Update

RC1 did not migrate workflow audit storage. The implementation plan is now documented in:

```text
docs/clinical-audit-durability-implementation-plan.md
```

RC1 confirms that filesystem JSON remains acceptable for local demos and automated release-candidate tests only. It is not approved as the production source of truth.

## RC2 Follow-Up

Prioritize database-backed workflow operation audit and object-storage mirroring before production go-live or any external compliance package workflow.

Minimum RC2 scope:

1. Add `operational.clinical_workflow_operations`.
2. Add append-only database permissions and update/delete rejection.
3. Backfill existing `metadata/workflow_operations.json`.
4. Switch audit evidence and report audit activity readers to database-first behavior.
5. Add object-storage mirror support if deployment storage and retention settings are approved.
