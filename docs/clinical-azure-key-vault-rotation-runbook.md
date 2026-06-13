# Clinical Azure Key Vault Rotation Runbook

Post-RC-15 update date: 2026-06-13

## Purpose

This runbook prepares signing-key rotation for clinical audit manifests. The repository validates metadata readiness only; it does not create keys, rotate Key Vault versions, grant identities, or call Azure during normal validation.

## Required Metadata

For rotation readiness:

```text
AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS=180
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME=<approved-next-key-name>
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION=<approved-next-key-version>
```

Use a next key name/version that is non-secret metadata and already approved by the Key Vault owner.

## Dry-Run Validation

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --evidence-out <approved-evidence-path>\key-vault-signing-evidence.json
```

Confirm:

- `lifecycle_summary.rotation_required=true`;
- `lifecycle_summary.rotation_interval_days` matches the approved cadence;
- `lifecycle_summary.current_key_reference` is the current signing key metadata;
- `lifecycle_summary.next_key_reference` points to the approved next key metadata;
- `lifecycle_summary.rotation_status=ready`;
- `lifecycle_summary.blocking_issues=[]`.

## Rotation Procedure

1. Open a change record with current key reference, next key reference, rotation reason, and rollback owner.
2. Confirm current manifests can still be verified with the current key version.
3. Confirm the next key version exists and has least-privilege sign/verify access for the approved identity.
4. Capture dry-run readiness evidence with real I/O disabled.
5. During the approved window, update hosted settings to the next key reference and key version.
6. If live validation is approved, run the live sign/verify command against a non-PHI validation checksum.
7. Retain the prior key version according to the retirement policy so historical manifest verification remains possible.
8. Capture access-log review evidence for both current and next key use.

## Stop Conditions

Stop rotation if readiness evidence contains lifecycle blockers, the next key version is missing, identity permissions are broader than approved, access logs are unavailable, live validation signs unexpected payloads, or any output includes raw credentials, key material, PHI, or ePHI.

## Rollback

Rollback means restoring the previous hosted key reference and version, then capturing readiness evidence again. Do not delete or purge the next key from this repository workflow; key deletion or purge decisions require Key Vault owner approval.
