# Clinical Azure WORM Operator Checklist

Post-RC-11 update date: 2026-06-13

## Scope

This checklist is for operators preparing Azure Blob WORM validation evidence. Repository commands remain safe by default and must not create Azure resources, upload objects, or call Azure APIs unless the operator explicitly enables live validation.

## Before Dry Run

- Confirm the target environment mode (`APP_ENV`, `ENVIRONMENT`, or `CLINICAL_ENV`).
- Confirm Azure Blob is the approved WORM provider before setting Azure mirror variables.
- Confirm no raw credential values are placed in `.env`, shell history, script arguments, or evidence paths.
- Confirm the selected container and prefix do not contain PHI/ePHI-bearing validation payloads.
- Keep `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=false` unless live validation has change-control approval.

## Dry-Run Evidence

Run:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json --evidence-out <approved-evidence-path>\azure-worm-validation-evidence.json
```

Review:

- `upload_attempted=false`
- `network_calls_performed=false`
- `data_safety_summary.contains_raw_credentials=false`
- `data_safety_summary.contains_phi_ephi=false`
- `blocking_issues` are either resolved or accepted as the dry-run reason for a blocked result
- `prefix_safety_status.status` is acceptable for the intended phase

## Before Live Validation

Live validation remains optional and skipped by default. Before setting `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true`, confirm:

- the storage account is non-production or explicitly approved for validation;
- the container has approved immutability and legal hold settings configured outside the repository;
- `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX` is dedicated to validation, such as `workflow-audit/live-validation-test`;
- managed identity or workload identity has least-privilege blob data access;
- `azure-storage-blob` and `azure-identity` are installed in the runtime image;
- compliance owners approved any `--live-write` execution.

## Live Validation Commands

Run marked tests only after approval:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_azure_worm_live_integration.py -m azure_worm_live
```

Run one write/stat/checksum check only after approval:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json --live-write --evidence-out <approved-evidence-path>\azure-worm-live-evidence.json
```

## Stop Conditions

Stop and retain evidence if any of these occur:

- live-test prefix is missing, ambiguous, or production-like without approved override;
- readiness reports unsafe credential mode;
- SDK dependencies are missing when real I/O is enabled;
- checksum verification does not return `verified`;
- Azure policy evidence does not match the approved retention or legal hold expectation;
- output contains data that appears to be raw credentials or PHI/ePHI.

## Package Handoff

The final operator package should include the sanitized evidence JSON, command stdout, approval references, Azure policy evidence, identity assignment evidence, and recovery drill summary. Do not delete WORM validation objects unless compliance owners approve cleanup.
