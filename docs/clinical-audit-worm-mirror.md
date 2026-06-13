# Clinical Audit WORM Mirror

Post-RC-06 update date: 2026-06-13

Post-RC-07 provider readiness update date: 2026-06-13

Post-RC-08 cloud provider adapter readiness update date: 2026-06-13

Post-RC-09 Azure Blob SDK operations foundation update date: 2026-06-13

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

Signed manifest ledger:

```text
operational.clinical_workflow_audit_mirror_manifests
```

## Architecture

Workflow commit audit order is:

1. append redacted audit event to `operational.clinical_workflow_audit_events`;
2. preserve the existing JSON mirror/fallback write;
3. optionally write object/WORM mirror payload;
4. append mirror attempt metadata to `operational.clinical_workflow_audit_mirror_events`.

The mirror ledger is append-only. It records attempts rather than updating the immutable audit row.

Post-RC-07 adds deterministic signed-manifest, verification, and recovery drill helpers. These are provider-readiness foundations only; they do not create cloud retention policies or call object-storage SDKs.

Post-RC-08 adds provider adapter readiness for local filesystem and Azure Blob Storage. Azure readiness validates configuration and reports capabilities without importing the Azure SDK during dry-run checks.

Post-RC-09 adds a guarded Azure Blob SDK operations foundation. Azure upload, stat/head, metadata read, prefix listing, and checksum verification run through a fakeable client boundary. Real Azure SDK construction requires `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true`; local/test fake-client paths do not require Azure credentials or network calls.

## Mirror Service

The service lives in:

```text
backend/app/services/clinical_audit_mirror.py
```

Manifest, verification, and recovery drill helpers live in:

```text
backend/app/services/clinical_audit_manifest.py
```

Provider adapters live in:

```text
backend/app/services/clinical_audit_mirror_providers.py
```

Supported modes:

| Mode | Behavior |
| --- | --- |
| `disabled` | Default. No object/WORM mirror is attempted. |
| `local_filesystem` | Writes deterministic JSON payloads under a configured local directory for development/testing simulation. |
| `object_storage` + `azure_blob` provider | Azure Blob provider mode. Validates provider config and expected URI prefix; guarded SDK operations are available only when real I/O is explicitly enabled or a test client is injected. |
| `object_storage` + other provider | Placeholder configuration mode for future provider integration. No network calls are performed by this foundation. |

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

## Signed Manifest Foundation

Manifest payloads use:

```text
schema_version = clinical.workflow_audit.manifest.v1
hash_algorithm = sha256
signature_algorithm = sha256-placeholder
```

A manifest includes:

- manifest id;
- generated timestamp and system actor;
- environment;
- mirror mode, provider, and URI prefix;
- retention policy reference;
- legal hold flag and reference;
- mirrored operation ids;
- mirror object URIs and checksums;
- audit event count;
- manifest checksum;
- optional checksum-derived signature placeholder.

Manifest ids are deterministic for the mirror inventory and readiness settings. Manifest checksums are SHA-256 over canonical JSON excluding the checksum and placeholder signature value. If signed manifests are required locally or in test, the placeholder signature is derived from the manifest checksum, configured algorithm, and key reference; no real key material is required or loaded.

Generated manifests can be persisted to:

```text
operational.clinical_workflow_audit_mirror_manifests
```

The manifest table is append-only. It records manifest metadata, not the full manifest payload, so the manifest payload should be retained with the evidence package when real object storage is enabled.

## Configuration

Local/default settings:

```text
AUDIT_OBJECT_MIRROR_MODE=disabled
AUDIT_OBJECT_MIRROR_REQUIRED=false
AUDIT_OBJECT_MIRROR_LOCAL_ROOT=metadata/audit_worm_mirror
AUDIT_OBJECT_MIRROR_URI_PREFIX=local-worm://clinical-audit
AUDIT_OBJECT_MIRROR_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=false
AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED=false
```

Future provider placeholders:

```text
AUDIT_OBJECT_MIRROR_MODE=object_storage
AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob
AUDIT_OBJECT_MIRROR_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_RETENTION_POLICY=RET-7Y-WORM
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE=LH-CLINICAL-AUDIT
AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=true
AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED=true
AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM=sha256-placeholder
AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF=audit-manifest-key-v1
```

Azure Blob readiness settings:

```text
AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL=https://<account>.blob.core.windows.net
AUDIT_OBJECT_MIRROR_AZURE_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_AZURE_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=false
AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=true
```

`AUDIT_OBJECT_MIRROR_AZURE_CONTAINER` and `AUDIT_OBJECT_MIRROR_AZURE_PREFIX` fall back to the generic container and prefix settings when omitted.

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

When manifests or signatures are required, production startup gates also fail if:

- `AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=true` and `AUDIT_OBJECT_MIRROR_RETENTION_POLICY` is empty;
- `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED=true` and `AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE` is empty;
- `AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED=true` without `AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=true`;
- signed manifests are required but `AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF` or algorithm is missing.

When Azure Blob mirroring is required, production startup gates fail if:

- account URL is missing;
- container or prefix is missing after fallback resolution;
- credential mode is missing or describes inline account keys, connection strings, shared keys, plain secrets, or inline SAS tokens;
- real Azure I/O is enabled but `azure-storage-blob` or required Azure identity dependencies are unavailable;
- Azure immutability is required but retention policy reference is missing;
- Azure legal hold is required but legal-hold reference is missing;
- Azure checksum validation is required without a safe credential mode.

## Replay / Backfill

`mirror_unmirrored_workflow_audit_events` mirrors existing DB audit rows that do not already have a successful non-dry-run mirror event.

Replay behavior:

- non-destructive;
- idempotent by operation id and checksum;
- skips already mirrored operation ids;
- can run in dry-run mode without writing files or mirror metadata;
- never deletes DB audit rows or the JSON mirror.

## Verification

`verify_mirror_inventory` verifies mirror payloads through the active provider contract without mutating evidence. Local filesystem verification reads deterministic local objects. Azure verification can use an injected fake client in tests and can use real SDK calls only when Azure real I/O is enabled.

Verification checks:

- successful non-dry-run mirror attempts only;
- mirror object exists according to the active provider;
- provider checksum metadata or downloaded payload checksum matches the recorded mirror checksum;
- optional manifest object URI/checksum matches the mirror record;
- manifest entries without a matching mirror record are reported.

Provider placeholder modes are reported as skipped because no provider contract is available.

Provider readiness dry-runs report:

- selected provider;
- expected object URI prefix;
- capability flags;
- Azure SDK availability without importing it;
- Azure real-I/O enabled/disabled state;
- supported operation methods;
- validation errors and warnings;
- `network_calls_performed=false`.

## Recovery Drill

`audit_mirror_recovery_drill_summary` produces a read-only drill report. It can be scoped by timestamp range and can compare against a manifest.

The drill reports:

- selected DB audit event count;
- successful mirror event count;
- DB audit operation ids missing successful mirror records;
- mirror records outside the selected DB audit set;
- checksum, missing object, and manifest mismatch counts;
- `recovery_ready` flag.

The helper does not restore, delete, or rewrite audit data. Recovery execution remains an operations procedure with database and compliance-owner approval.

Recovery drill summaries now include provider readiness, manifest count, mirrored object count, expected URI prefix, provider capability flags, and provider validation findings.

## Retention And Legal Hold Assumptions

Production WORM storage must be approved outside this code foundation. The target provider should support:

- immutable retention policy;
- legal hold;
- versioning or append-only object semantics;
- access logging;
- lifecycle policy review;
- backup and recovery testing;
- checksum verification during evidence review.

See `docs/clinical-audit-worm-retention-legal-hold.md` for the readiness checklist and provider assumptions.

## Recovery Procedure

1. Restore database audit rows from approved database backup if needed.
2. Compare `clinical_workflow_audit_events` against successful mirror events.
3. Use replay to mirror unmirrored rows into the approved target.
4. Verify object checksums match `mirror_checksum`.
5. Generate or load the signed manifest for the selected evidence package.
6. Run the recovery drill summary to detect missing mirror rows, missing objects, checksum mismatches, or manifest mismatches.
7. Preserve `metadata/workflow_operations.json` as compatibility evidence; do not delete it during recovery.

Detailed drill steps are in `docs/clinical-audit-worm-recovery-drill.md`.

Provider adapter details are in `docs/clinical-audit-worm-provider-adapters.md`.
Azure readiness details are in `docs/clinical-azure-blob-worm-readiness.md`.

## Known Limitations

- Azure Blob SDK operation paths are present but disabled unless `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true`.
- No live-cloud Azure integration tests are implemented.
- Local filesystem simulation is not WORM storage.
- Signed manifests are checksum-placeholder foundations only; real cryptographic signing remains future work.
- Legal-hold automation remains future work.
- Provider-side immutable retention and legal-hold enforcement must be configured and validated in Azure.
