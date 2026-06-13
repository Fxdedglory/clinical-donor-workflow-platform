# Clinical Azure WORM Operator Checklist

Post-RC-11 update date: 2026-06-13

Post-RC-12 manifest signing update date: 2026-06-13

Post-RC-13 Azure Key Vault signing readiness update date: 2026-06-13

Post-RC-14 Azure Key Vault live signing checklist update date: 2026-06-13

## Scope

This checklist is for operators preparing Azure Blob WORM validation evidence. Repository commands remain safe by default and must not create Azure resources, upload objects, or call Azure APIs unless the operator explicitly enables live validation.

## Before Dry Run

- Confirm the target environment mode (`APP_ENV`, `ENVIRONMENT`, or `CLINICAL_ENV`).
- Confirm Azure Blob is the approved WORM provider before setting Azure mirror variables.
- Confirm no raw credential values are placed in `.env`, shell history, script arguments, or evidence paths.
- Confirm manifest signing mode and key reference are approved if signed manifest evidence is required.
- If `AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault`, confirm `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false` for dry-run evidence unless live Key Vault signing has separate approval.
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
- `manifest_signing_summary.signature_key_ref` contains only the approved reference, not key material
- `manifest_signing_summary.signature_verification_status` is acceptable for the selected signing mode
- `manifest_signing_summary.azure_key_vault_real_io_enabled` matches the approved validation phase
- `manifest_signing_summary.azure_key_vault_sdk_available` is understood before live Key Vault signing
- dedicated Key Vault signing evidence from `scripts\check_azure_key_vault_signing_readiness.py --json --evidence-out` is retained if Key Vault signing is in scope
- `blocking_issues` are either resolved or accepted as the dry-run reason for a blocked result
- `prefix_safety_status.status` is acceptable for the intended phase

## Before Live Validation

Live validation remains optional and skipped by default. Before setting `CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true`, confirm:

- the storage account is non-production or explicitly approved for validation;
- the container has approved immutability and legal hold settings configured outside the repository;
- `AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX` is dedicated to validation, such as `workflow-audit/live-validation-test`;
- managed identity or workload identity has least-privilege blob data access;
- `azure-storage-blob` and `azure-identity` are installed in the runtime image;
- `azure-keyvault-keys` and `azure-identity` are installed if live Key Vault signing is enabled;
- `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true` and `--live-sign` are approved before any Key Vault network call;
- the Key Vault key name/reference is dedicated to validation or override approval is recorded;
- compliance owners approved any `--live-write` execution.
- manifest checksum and signature verification behavior is understood: local HMAC can verify in-repo, `azure_key_vault` can verify through an injected fake client or approved real I/O, and external KMS or Azure Key Vault placeholders remain pending provider verification.

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
- Key Vault credential mode is unsafe or SDK dependencies are missing when Key Vault real I/O is enabled;
- Key Vault live signing is requested without the explicit live environment flag;
- checksum verification does not return `verified`;
- manifest signature verification reports `failed` or `missing_signature`;
- Azure policy evidence does not match the approved retention or legal hold expectation;
- output contains data that appears to be raw credentials or PHI/ePHI.

## Package Handoff

The final operator package should include the sanitized evidence JSON, command stdout, approval references, Azure policy evidence, identity assignment evidence, manifest signing key-reference evidence, and recovery drill summary. Do not delete WORM validation objects unless compliance owners approve cleanup.
