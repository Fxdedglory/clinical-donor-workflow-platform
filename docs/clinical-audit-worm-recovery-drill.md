# Clinical Audit WORM Recovery Drill

Post-RC-07 update date: 2026-06-13

## Purpose

This drill validates that database workflow audit rows, mirror attempt rows, local simulation objects, and signed manifests can be reconciled without mutating production evidence.

The drill is read-only. It does not restore, delete, rewrite, or backfill audit data.

## Inputs

- `operational.clinical_workflow_audit_events`
- `operational.clinical_workflow_audit_mirror_events`
- optional `operational.clinical_workflow_audit_mirror_manifests`
- optional signed manifest payload
- local simulation root or future provider object inventory
- optional start/end timestamp range

## Helper

Use:

```text
backend/app/services/clinical_audit_manifest.py
```

Primary helper:

```text
audit_mirror_recovery_drill_summary
```

It reports selected audit event count, successful mirror event count, missing mirror rows, orphan mirror rows, checksum verification results, manifest mismatches, and a `recovery_ready` flag.

## Local Drill Procedure

1. Select the audit time window or manifest id under review.
2. Query DB audit rows for the selected window.
3. Query successful non-dry-run mirror records for those operation ids.
4. Verify local simulation payload checksums against `mirror_checksum`.
5. Compare manifest object URI/checksum entries against mirror records.
6. Report missing DB-to-mirror rows, missing local objects, checksum mismatches, manifest mismatches, and mirror rows outside the selected audit set.
7. Preserve all evidence sources after review.

## Recovery Readiness Criteria

The drill is ready for recovery review when:

- every selected DB audit row has a successful mirror record;
- every local simulation object exists;
- every recomputed checksum matches the recorded checksum;
- every manifest object entry matches a mirror event;
- no manifest-only entries exist without a mirror record.

## Production Procedure

Future provider integration should replace the local filesystem existence check with provider inventory and object checksum reads. The procedure should still remain read-only until database owners and compliance owners approve a separate restore or replay action.

## Known Limitations

- No Azure/AWS/GCP SDK calls are implemented.
- Placeholder signatures do not prove signer identity.
- Provider-side immutable retention and legal hold status are documented assumptions, not enforced by this helper.
