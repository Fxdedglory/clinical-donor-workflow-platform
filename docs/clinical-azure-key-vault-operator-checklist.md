# Clinical Azure Key Vault Operator Checklist

Post-RC-14 update date: 2026-06-13

Post-RC-15 lifecycle readiness update date: 2026-06-13

## Scope

This checklist is for operators preparing Azure Key Vault signing readiness or live sign/verify evidence for clinical audit WORM manifests. Repository commands remain safe by default and must not call Azure unless live validation is explicitly enabled.

## Before Dry Run

- Confirm `AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault` only when Key Vault signing readiness is intended.
- Confirm no raw credentials are placed in `.env`, shell history, script arguments, or evidence paths.
- Confirm `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false` for dry-run evidence.
- Confirm the selected key name/reference is non-PHI and non-secret metadata.
- Confirm lifecycle requirement flags and `*_REF` values match approved rotation, access-log review, and incident recovery controls.
- Confirm `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=false` unless live signing has approval.

## Dry-Run Evidence

Run:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --evidence-out <approved-evidence-path>\key-vault-signing-evidence.json
```

Review:

- `signing_attempted=false`
- `verification_attempted=false`
- `network_calls_performed=false`
- `data_safety_summary.contains_raw_credentials=false`
- `data_safety_summary.contains_key_material=false`
- `vault_summary.vault_url_configured` reports presence only, not the raw URL
- `credential_mode_summary.mode` uses an approved identity mode
- `sdk_availability` is understood before live validation
- `lifecycle_summary` shows required rotation, retirement, access-log review, and incident recovery controls as documented
- `blocking_issues` are resolved or accepted as dry-run blockers

## Before Live Validation

Confirm:

- Key Vault resource is approved for validation.
- Key name/reference includes `validation`, `test`, `sandbox`, or `nonprod`, or override approval is recorded.
- Key version is documented.
- Managed identity or workload identity has least-privilege sign and verify permissions.
- `azure-keyvault-keys` and `azure-identity` are installed.
- Key Vault diagnostic/access logging is enabled.
- Key lifecycle, rotation, access-log review, and incident recovery references are approved when required.
- `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true`.
- `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true`.
- Compliance owners approved `--live-sign`.

## Live Validation Command

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --live-sign --evidence-out <approved-evidence-path>\key-vault-live-signing-evidence.json
```

Optional marked pytest, after the same approval:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_azure_key_vault_signing_live_integration.py -m azure_key_vault_live
```

## Stop Conditions

Stop and retain evidence if:

- live flag is disabled;
- key identifier is ambiguous or production-like without approved override;
- SDK dependencies are missing;
- credential mode is unsafe;
- signing or verification fails;
- output appears to contain credentials, key material, PHI, or ePHI;
- access logs do not show the expected managed/workload identity.

## Package Handoff

Include dry-run evidence, live evidence if run, command stdout, Key Vault key/version evidence, identity permission evidence, SDK/runtime evidence, access-log evidence, approval references, and follow-up items.

Include lifecycle evidence from `lifecycle_summary` when rotation, retirement, access-log review, or incident recovery readiness is required.

## Disable Procedure

After validation, set:

```text
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false
```

Remove temporary validation-only permissions if approved. Preserve evidence artifacts according to compliance retention guidance.

## Signoff

Record approver, date, environment, command results, evidence paths, key version, identity, lifecycle references, and unresolved risks for rotation, access logging, and incident recovery.
