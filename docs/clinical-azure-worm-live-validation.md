# Clinical Azure WORM Live Validation

Post-RC-10 update date: 2026-06-13

## Purpose

This runbook defines the skipped-by-default Azure Blob WORM live integration readiness harness. It prepares the repository for future live validation without requiring credentials, creating Azure resources, or running network calls during normal tests.

## Safety Defaults

Normal validation does not contact Azure.

Live tests run only when:

```text
CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true
```

Live writes also require an operator to run:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --live-write
```

Dry-run readiness remains the default:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json
```

## Required Azure Assumptions

- Storage account is non-production or explicitly approved for validation.
- Container is dedicated to clinical audit WORM validation or has an approved isolated test prefix.
- Blob versioning, immutable retention, and legal hold settings are configured outside this repository.
- Retention period is approved by compliance owners before `AUDIT_OBJECT_MIRROR_REQUIRED=true`.
- Legal hold reference and naming convention are approved.
- Managed identity or workload identity has least-privilege blob data permissions.
- Inline account keys, connection strings, shared keys, plain secrets, and inline SAS tokens are not used.

## Required Configuration

```text
AUDIT_OBJECT_MIRROR_MODE=object_storage
AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob
AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL=https://<account>.blob.core.windows.net
AUDIT_OBJECT_MIRROR_AZURE_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_AZURE_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true
AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=true
AUDIT_OBJECT_MIRROR_RETENTION_POLICY=RET-7Y-WORM
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE=LH-CLINICAL-AUDIT
CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true
AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX=workflow-audit/live-validation-test
```

The live test prefix must clearly identify a dedicated non-production test location. Ambiguous or production-like prefixes are refused unless this override is set after change-control approval:

```text
AUDIT_OBJECT_MIRROR_AZURE_LIVE_ALLOW_PRODUCTION_PREFIX=true
```

## Validation Steps

1. Run the dry-run readiness script and retain the JSON output.
2. Confirm no blocking issues are present.
3. Confirm `real_io_enabled=true`, `live_tests_enabled=true`, and the live test prefix is dedicated.
4. Run the marked pytest file only after the dry-run is approved:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_azure_worm_live_integration.py -m azure_worm_live
```

5. If approved, run the script with `--live-write` to perform one write/stat/list/checksum check under the live test prefix.
6. Capture object URI, checksum, object metadata, Azure container policy screenshots or exports, and test output.
7. Retain evidence with the release readiness package.

## Rollback And Cleanup

- Do not delete WORM evidence objects unless compliance owners approve the action.
- Prefer a short-lived validation prefix in a non-production WORM container.
- Record every manual cleanup action with the object URI, actor, timestamp, and approval reference.
- If a live validation write fails, keep the failed script output and provider error for incident review.

## Evidence To Capture

- Dry-run readiness JSON.
- Live pytest output, if run.
- `--live-write` output, if run.
- Azure storage account and container policy export.
- Identity assignment and least-privilege role evidence.
- Retention policy and legal hold approval references.
- Recovery drill summary for any accepted live evidence package.

## Known Limitations

- The repository does not create Azure resources.
- The harness does not enforce provider-side immutability or legal hold from code.
- Live tests are not part of normal CI and must remain opt-in.
- Real cryptographic manifest signing remains future work.
