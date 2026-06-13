# Clinical Audit WORM Recovery Drill

Post-RC-07 update date: 2026-06-13

Post-RC-08 provider readiness update date: 2026-06-13

Post-RC-09 provider verification update date: 2026-06-13

Post-RC-10 live harness update date: 2026-06-13

## Purpose

This drill validates that database workflow audit rows, mirror attempt rows, provider mirror objects, and signed manifests can be reconciled without mutating production evidence.

The drill is read-only. It does not restore, delete, rewrite, or backfill audit data.

## Inputs

- `operational.clinical_workflow_audit_events`
- `operational.clinical_workflow_audit_mirror_events`
- optional `operational.clinical_workflow_audit_mirror_manifests`
- optional signed manifest payload
- local simulation root or future provider object inventory
- provider readiness summary
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

Post-RC-08 also includes provider readiness output:

- provider name and mirror mode;
- expected URI prefix;
- capability flags;
- manifest count;
- mirrored object count;
- provider validation errors and warnings;
- Azure account/container/prefix/credential-mode readiness when Azure Blob is configured.
- Azure SDK availability, real-I/O enabled/disabled state, supported operations, and no-network dry-run status.
- Azure live harness status when `scripts/check_azure_worm_readiness.py --json` is captured with the evidence package.

## Local Drill Procedure

1. Select the audit time window or manifest id under review.
2. Query DB audit rows for the selected window.
3. Query successful non-dry-run mirror records for those operation ids.
4. Verify provider payload checksums against `mirror_checksum`.
5. Compare manifest object URI/checksum entries against mirror records.
6. Review provider readiness output and resolve configuration validation errors.
7. Report missing DB-to-mirror rows, missing local objects, checksum mismatches, manifest mismatches, and mirror rows outside the selected audit set.
8. Preserve all evidence sources after review.

## Recovery Readiness Criteria

The drill is ready for recovery review when:

- every selected DB audit row has a successful mirror record;
- every provider mirror object exists;
- every provider checksum metadata or recomputed payload checksum matches the recorded checksum;
- every manifest object entry matches a mirror event;
- no manifest-only entries exist without a mirror record.
- provider readiness has no validation errors for the configured target.

## Production Procedure

Provider verification now uses the active provider contract. Local filesystem checks remain deterministic. Azure Blob checks can run through fake clients in tests and through real SDK calls only when `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true`. The procedure should still remain read-only until database owners and compliance owners approve a separate restore or replay action.

Post-RC-10 adds skipped-by-default live validation skeletons. If a live Azure validation run is accepted, retain the dry-run readiness JSON, live pytest output, object URI/checksum, and storage policy evidence before running the recovery drill summary.

## Known Limitations

- Azure Blob SDK operation paths are available behind the real-I/O feature flag, and live test skeletons are skipped by default.
- Placeholder signatures do not prove signer identity.
- Provider-side immutable retention and legal hold status are documented assumptions, not enforced by this helper.
