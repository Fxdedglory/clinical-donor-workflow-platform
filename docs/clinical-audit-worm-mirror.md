# Clinical Audit WORM Mirror

Post-RC-06 update date: 2026-06-13

## Purpose

Post-RC-06 adds an object-storage / WORM audit mirroring foundation for clinical workflow audit evidence. It does not replace the database-backed append-only audit table and does not add real cloud SDK calls.

Primary audit query source:

```text
operational.clinical_workflow_audit_events
```

Compatibility mirror/fallback:

```text
metadata/workflow_operations.json
```

WORM mirror attempt ledger:

```text
operational.clinical_workflow_audit_mirror_events
```

## Architecture

Workflow commit audit order is:

1. append redacted audit event to `operational.clinical_workflow_audit_events`;
2. preserve the existing JSON mirror/fallback write;
3. optionally write object/WORM mirror payload;
4. append mirror attempt metadata to `operational.clinical_workflow_audit_mirror_events`.

The mirror ledger is append-only. It records attempts rather than updating the immutable audit row.

## Mirror Service

The service lives in:

```text
backend/app/services/clinical_audit_mirror.py
```

Supported modes:

| Mode | Behavior |
| --- | --- |
| `disabled` | Default. No object/WORM mirror is attempted. |
| `local_filesystem` | Writes deterministic JSON payloads under a configured local directory for development/testing simulation. |
| `object_storage` | Placeholder configuration mode for future provider integration. No network calls are performed by this foundation. |

Local filesystem simulation writes objects under:

```text
metadata/audit_worm_mirror/workflow-audit/{workflow}/yyyy/mm/{operation_id}.json
```

Existing mirror objects are not overwritten. If a target already exists with the same checksum, the write is treated as idempotent. If the checksum differs, the mirror attempt fails.

## Payload And Checksum

Mirror payloads use:

```text
schema_version = clinical.workflow_audit.mirror.v1
payload_profile = audit_metadata
redacted = true
```

The payload contains the same workflow operation shape already used by the audit writer. Changes are defensively passed through the existing audit redactor before checksum calculation and mirror write.

Checksums are SHA-256 over canonical JSON:

```text
json.dumps(payload, sort_keys=True, separators=(",", ":"))
```

The checksum is stored in `clinical_workflow_audit_mirror_events.mirror_checksum`.

## Configuration

Local/default settings:

```text
AUDIT_OBJECT_MIRROR_MODE=disabled
AUDIT_OBJECT_MIRROR_REQUIRED=false
AUDIT_OBJECT_MIRROR_LOCAL_ROOT=metadata/audit_worm_mirror
AUDIT_OBJECT_MIRROR_URI_PREFIX=local-worm://clinical-audit
AUDIT_OBJECT_MIRROR_PREFIX=workflow-audit
```

Future provider placeholders:

```text
AUDIT_OBJECT_MIRROR_MODE=object_storage
AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob_immutability
AUDIT_OBJECT_MIRROR_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_PREFIX=workflow-audit
```

Production simulation flag:

```text
AUDIT_OBJECT_MIRROR_ALLOW_LOCAL_PRODUCTION_SIMULATION=true
```

Use the simulation flag only for production-like dry runs. It does not make local filesystem storage production WORM storage.

## Failure Policy

If the mirror is optional:

- DB audit append remains authoritative;
- mirror failure is recorded in `clinical_workflow_audit_mirror_events`;
- JSON mirror/fallback behavior is preserved.

If the mirror is required:

- DB audit append still happens first;
- mirror failure records a failed mirror attempt when possible;
- the writer raises an audit mirror error so the failure is visible to the caller.

Production startup gates fail when `AUDIT_OBJECT_MIRROR_REQUIRED=true` but mirror settings are missing, disabled, or using local filesystem without explicit simulation approval.

## Replay / Backfill

`mirror_unmirrored_workflow_audit_events` mirrors existing DB audit rows that do not already have a successful non-dry-run mirror event.

Replay behavior:

- non-destructive;
- idempotent by operation id and checksum;
- skips already mirrored operation ids;
- can run in dry-run mode without writing files or mirror metadata;
- never deletes DB audit rows or the JSON mirror.

## Retention And Legal Hold Assumptions

Production WORM storage must be approved outside this code foundation. The target provider should support:

- immutable retention policy;
- legal hold;
- versioning or append-only object semantics;
- access logging;
- lifecycle policy review;
- backup and recovery testing;
- checksum verification during evidence review.

## Recovery Procedure

1. Restore database audit rows from approved database backup if needed.
2. Compare `clinical_workflow_audit_events` against successful mirror events.
3. Use replay to mirror unmirrored rows into the approved target.
4. Verify object checksums match `mirror_checksum`.
5. Preserve `metadata/workflow_operations.json` as compatibility evidence; do not delete it during recovery.

## Known Limitations

- No real Azure/AWS/GCP SDK integration is implemented.
- Local filesystem simulation is not WORM storage.
- Signed manifests and legal-hold automation remain future work.
- Provider credential validation is limited to configuration shape in the production startup gate.
