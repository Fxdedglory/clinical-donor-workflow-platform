# Clinical Azure Key Vault Live Validation

Post-RC-14 update date: 2026-06-13

Post-RC-15 lifecycle readiness update date: 2026-06-13

## Purpose

This runbook defines the skipped-by-default Azure Key Vault signing live validation harness. It prepares the repository for approved live sign/verify evidence without creating Azure resources, requiring credentials in normal validation, or making network calls by default.

## Safety Defaults

Normal validation is dry-run only:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json
```

Live signing requires both:

```text
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true
```

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --live-sign
```

Live tests are marked `azure_key_vault_live` and skip unless the environment flag is set.

## Required Configuration

```text
AUDIT_MANIFEST_SIGNING_REQUIRED=true
AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault
AUDIT_MANIFEST_SIGNING_ALGORITHM=rsa-pss-sha256
AUDIT_MANIFEST_SIGNING_KEY_REF=keyvault://clinical-audit/manifest-validation-test/v1
AUDIT_MANIFEST_AZURE_KEY_VAULT_URL=https://<vault-name>.vault.azure.net
AUDIT_MANIFEST_AZURE_KEY_NAME=manifest-validation-test
AUDIT_MANIFEST_AZURE_KEY_VERSION=<approved-key-version>
AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE=managed_identity
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS=<approved-rotation-days>
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME=<approved-next-key-name>
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION=<approved-next-key-version>
AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF=<approved-retirement-policy-ref>
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF=<approved-access-log-review-ref>
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF=<approved-incident-recovery-ref>
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true
```

Set lifecycle requirement flags to `false` when the corresponding rotation, retirement, access-log review, or incident recovery control is not in scope for the validation window.

The key name or key reference must clearly identify a non-production validation key. Ambiguous or production-like identifiers are refused unless this override is approved:

```text
AUDIT_MANIFEST_AZURE_KEY_VAULT_LIVE_ALLOW_PRODUCTION_KEY=true
```

## Azure Resource Checklist

- Key Vault exists in an approved validation subscription/resource group.
- Key is dedicated to validation or separately approved for the test.
- Key version is recorded.
- HSM expectation is approved if `AUDIT_MANIFEST_AZURE_KEY_VAULT_REQUIRE_HSM=true`.
- Diagnostic logging and access logging are enabled.
- Key lifecycle, retirement, access-log review, and incident recovery references are approved if those controls are required.
- No PHI/ePHI is used in the validation payload.

## Identity And Permissions

- Managed identity or workload identity is assigned.
- Identity has least-privilege sign and verify permissions only.
- No inline client secrets, connection strings, shared keys, or plain secrets are used.
- Role assignment or access policy evidence is retained with the package.

## Runtime Checklist

- `azure-keyvault-keys` is installed in the runtime image.
- `azure-identity` is installed in the runtime image.
- Production security gates pass for the target environment.
- Dry-run readiness evidence has been captured before live signing.

## Evidence Capture

Dry-run evidence:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --evidence-out <approved-evidence-path>\key-vault-signing-evidence.json
```

Live sign/verify evidence:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --live-sign --evidence-out <approved-evidence-path>\key-vault-live-signing-evidence.json
```

Expected evidence includes generated time, environment mode, signing mode, real-I/O state, live flag state, signing/verification attempted flags, network-call flag, vault URL configured status, key name/version/reference metadata, credential mode, SDK availability, algorithm, lifecycle summary, blockers, warnings, and validation result.

## Failure Triage

- If live tests are disabled, confirm `CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true`.
- If key identifier safety fails, use a dedicated validation key or obtain override approval.
- If SDK checks fail, install `azure-keyvault-keys` and `azure-identity`.
- If credential mode fails, switch to managed/workload identity or another approved identity mode.
- If lifecycle readiness fails, resolve the missing rotation, retirement, access-log, or incident recovery reference before signoff.
- If sign/verify fails, retain stdout, evidence JSON, Key Vault logs, identity logs, and deployment settings for incident review.

## Rollback And Disable

Set these values to disable live signing:

```text
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false
```

Do not delete validation evidence unless compliance owners approve. Disable or remove temporary validation identity grants after signoff if they are not part of the target runtime posture.

## Signoff

Record:

- approver;
- validation date and environment;
- Key Vault name and key version evidence;
- identity permission evidence;
- dry-run evidence artifact path;
- live evidence artifact path, if live signing ran;
- access-log export or screenshot reference;
- lifecycle readiness evidence and follow-up items for rotation, access logging, and incident recovery.

## Known Limitations

- The harness does not create Key Vaults, keys, identities, or role assignments.
- Live signing remains opt-in and is not part of normal CI.
- The harness signs a non-PHI manifest checksum only.
- Key rotation automation, access-log ingestion, and incident recovery automation remain future work, but repository-safe readiness metadata and runbooks are now documented.
