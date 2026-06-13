# Clinical Audit Durability Decision

Status: Post-RC database-backed audit foundation implemented; WORM mirror and manifest readiness foundation implemented; cloud provider integration pending

RC0 decision date: 2026-06-12

RC1 update date: 2026-06-13

Post-RC implementation date: 2026-06-13

Post-RC-06 WORM mirror foundation date: 2026-06-13

Post-RC-07 WORM provider readiness date: 2026-06-13

Historical RC1 status: RC1 implementation plan documented in `docs/clinical-audit-durability-implementation-plan.md`.

## Current Behavior

Clinical workflow commits now use the shared writer in `backend/app/services/clinical_workflows.py` to write DB-backed audit rows first, then preserve the existing JSON mirror:

```text
operational.clinical_workflow_audit_events
metadata/workflow_operations.json
```

Successful commit endpoints pass their active DB session into the writer. Evidence and reporting readers use database rows first and fall back to the JSON file when no database audit rows are available.

Post-RC-06 adds an optional object/WORM mirror foundation. When enabled, the writer mirrors the redacted audit payload after the DB audit event is appended and records the mirror attempt in:

```text
operational.clinical_workflow_audit_mirror_events
```

This is the repository's object-storage mirroring foundation; real provider SDK integration and WORM retention setup remain pending.

The JSON mirror remains:

```text
metadata/workflow_operations.json
```

- creates the `metadata` directory if missing;
- reads the existing JSON array;
- appends the new operation record;
- writes the full JSON array back to disk.

Database audit rows include operation id, workflow, entity type, entity id, actor, timestamp, preview hash, confirmation status, before/after status, reason, changed fields as JSON, source, and created timestamp.

Mirror attempt rows include operation id, mirror mode, mirror status, payload profile, mirrored timestamp, mirror URI, checksum, error text, dry-run flag, and created timestamp.

Post-RC-07 adds deterministic signed manifest and recovery drill foundations. Manifest metadata is stored in:

```text
operational.clinical_workflow_audit_mirror_manifests
```

Manifest rows include manifest id, status, mirror mode/provider, URI prefix, audit event count, manifest checksum, signature placeholder metadata, retention policy, legal hold reference, manifest URI, generated timestamp, generated actor, and created timestamp.

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

## Implemented Production Path

database-backed audit storage is now implemented as the primary query path.

Primary path:

- Added append-only `operational.clinical_workflow_audit_events`.
- Added indexes for workflow, entity type, entity id, actor, timestamp, commit confirmation, source, and created timestamp.
- Added a database trigger that rejects `UPDATE` and `DELETE`.
- Kept JSON append as a compatibility mirror and local fallback.
- Added a backfill helper that parses JSON entries into DB rows without deleting the source JSON.

Durability mirror foundation:

- Added `backend/app/services/clinical_audit_mirror.py`.
- Supports disabled mode, local filesystem simulation, provider placeholder configuration, deterministic checksum, optional/required failure policy, and replay of unmirrored DB audit rows.
- Added append-only `operational.clinical_workflow_audit_mirror_events`.
- Added deterministic signed manifest, verification, and recovery drill foundation in Post-RC-07.
- Real cloud SDK integration, immutable retention configuration, legal hold automation, and real cryptographic signing remain pending.

## Remaining Hardening Plan

1. Run Alembic migration `202606130001_clinical_workflow_audit_events.py` in production before go-live.
2. Backfill existing `metadata/workflow_operations.json` using `backfill_workflow_operations_from_json`.
3. Verify audit evidence and report activity endpoints read DB rows after backfill.
4. Configure approved object-storage/WORM target after deployment storage and retention settings are approved.
5. Add real provider SDK integration and real signature support for evidence packages.
6. Execute operational backup/restore drills for `operational.clinical_workflow_audit_events`, mirror records, manifest records, and object checksums.

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

RC2 deferred database-backed workflow audit. `CLINICAL-POST-RC-01` implements the database foundation after RC2.

Completed post-RC scope:

1. Added `operational.clinical_workflow_audit_events`.
2. Added append-only database update/delete rejection.
3. Added JSON backfill helper without deleting source JSON.
4. Switched audit evidence and report audit activity readers to database-first behavior.
5. Preserved JSON mirror/fallback behavior.
6. Left object-storage mirror support for a later approved deployment-storage sprint.

## Post-RC-06 Follow-Up

`CLINICAL-POST-RC-06` adds the mirror foundation:

1. Added append-only `operational.clinical_workflow_audit_mirror_events`.
2. Added local filesystem simulation and future provider placeholders.
3. Added deterministic SHA-256 checksum calculation over canonical redacted audit payloads.
4. Added replay/backfill helper for unmirrored DB audit rows.
5. Added production gate checks when `AUDIT_OBJECT_MIRROR_REQUIRED=true`.
6. Deferred real cloud provider SDK integration, legal hold automation, provider retention policy creation, and signed manifests.

## Post-RC-07 Follow-Up

`CLINICAL-POST-RC-07` adds provider-readiness hardening:

1. Added deterministic manifest generation over successful mirror attempts.
2. Added append-only `operational.clinical_workflow_audit_mirror_manifests`.
3. Added checksum-placeholder signature metadata for local/test readiness without real signing keys.
4. Added local mirror verification for missing payloads, checksum mismatches, and manifest mismatches.
5. Added read-only recovery drill summary for DB audit rows versus mirror evidence.
6. Added production gate checks for required manifest, signature, retention, and legal-hold settings.
7. Deferred real cloud SDK integration, provider-side retention enforcement, legal-hold automation, and real cryptographic signatures.
