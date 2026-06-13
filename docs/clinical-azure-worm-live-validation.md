# Clinical Azure WORM Live Validation

Post-RC-10 update date: 2026-06-13

Post-RC-11 evidence package update date: 2026-06-13

Post-RC-12 manifest signing foundation update date: 2026-06-13

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

Dry-run evidence can be retained with a sanitized artifact:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json --evidence-out <approved-evidence-path>\azure-worm-validation-evidence.json
```

## Required Azure Assumptions

- Storage account is non-production or explicitly approved for validation.
- Container is dedicated to clinical audit WORM validation or has an approved isolated test prefix.
- Blob versioning, immutable retention, and legal hold settings are configured outside this repository.
- Retention period is approved by compliance owners before `AUDIT_OBJECT_MIRROR_REQUIRED=true`.
- Legal hold reference and naming convention are approved.
- Managed identity or workload identity has least-privilege blob data permissions.
- Inline account keys, connection strings, shared keys, plain secrets, and inline SAS tokens are not used.
- Manifest signing mode, algorithm, and key reference are approved before signed manifest evidence is accepted.

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

1. Run the dry-run readiness script with `--evidence-out` and retain the sanitized evidence JSON plus command output.
2. Confirm no blocking issues are present.
3. Confirm `upload_attempted=false` and `network_calls_performed=false` for dry-run evidence.
4. Confirm `real_io_enabled=true`, `live_tests_enabled=true`, and the live test prefix is dedicated before approved live validation.
5. Run the marked pytest file only after the dry-run is approved:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_azure_worm_live_integration.py -m azure_worm_live
```

6. If approved, run the script with `--live-write --evidence-out` to perform one write/stat/list/checksum check under the live test prefix.
7. Capture object URI, checksum, object metadata, Azure container policy screenshots or exports, and test output.
8. Retain evidence with the release readiness package.

## Rollback And Cleanup

- Do not delete WORM evidence objects unless compliance owners approve the action.
- Prefer a short-lived validation prefix in a non-production WORM container.
- Record every manual cleanup action with the object URI, actor, timestamp, and approval reference.
- If a live validation write fails, keep the failed script output and provider error for incident review.

## Evidence To Capture

- Sanitized dry-run evidence JSON from `--evidence-out`.
- Dry-run readiness JSON or stdout from the same command.
- Live pytest output, if run.
- `--live-write` output, if run.
- Azure storage account and container policy export.
- Identity assignment and least-privilege role evidence.
- Retention policy and legal hold approval references.
- Recovery drill summary for any accepted live evidence package.
- Manifest signing verification status from the recovery drill, when a manifest is included.

See `docs/clinical-azure-worm-validation-evidence-template.md`, `docs/clinical-azure-worm-operator-checklist.md`, and `docs/clinical-audit-manifest-signing.md` for the required artifact fields, signing modes, and operator handoff checklist.

## Known Limitations

- The repository does not create Azure resources.
- The harness does not enforce provider-side immutability or legal hold from code.
- Live tests are not part of normal CI and must remain opt-in.
- Sanitized evidence proves repository readiness posture; Azure policy enforcement still requires external provider evidence.
- Real Azure Key Vault signing remains future work; Post-RC-12 only validates Key Vault metadata without network calls.
