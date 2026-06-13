# Clinical Azure Key Vault Key Lifecycle

Post-RC-15 update date: 2026-06-13

## Purpose

This runbook defines repository-safe lifecycle readiness for Azure Key Vault manifest signing keys. It records rotation, next-key, retirement, access-log review, and incident recovery metadata without creating Azure resources, reading secrets, exporting key material, or calling Azure APIs.

## Configuration Surface

Lifecycle readiness is optional until a compliance owner requires it. When a requirement flag is enabled, production-like gates fail unless the matching metadata is complete.

```text
AUDIT_MANIFEST_AZURE_KEY_VAULT_KEY_ROTATION_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS=0
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_NAME=
AUDIT_MANIFEST_AZURE_KEY_VAULT_NEXT_KEY_VERSION=
AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF=
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF=
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF=
```

The `*_REF` values should be non-secret references such as approved runbook IDs, ticket IDs, monitor query IDs, evidence package paths, or policy identifiers. Do not put client secrets, private keys, SAS tokens, raw logs with PHI/ePHI, or Key Vault key material in these values.

## Readiness Evidence

`scripts/check_azure_key_vault_signing_readiness.py --json --evidence-out <path>` now includes `lifecycle_summary` with:

- rotation required flag and interval;
- current logical key reference;
- next logical key reference when configured;
- retirement policy status;
- access-log review status;
- incident recovery status;
- lifecycle blockers and warnings;
- data-safety flags asserting no raw credentials, key material, PHI, or ePHI.

Current and next key references are logical metadata only. HTTPS Key Vault key IDs are reduced to `keyvault://<key-name>/<version>` in lifecycle evidence.

## Gate Behavior

Production-like startup fails when Azure Key Vault signing is required and:

- rotation is required but `AUDIT_MANIFEST_AZURE_KEY_VAULT_ROTATION_INTERVAL_DAYS` is missing or invalid;
- rotation is required but the next key name or version is missing;
- retirement policy readiness is required but `AUDIT_MANIFEST_AZURE_KEY_VAULT_RETIREMENT_POLICY_REF` is missing;
- access-log review readiness is required but `AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF` is missing;
- incident recovery readiness is required but `AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF` is missing.

Local/dev/test environments report the same conditions as warnings unless strict production validation is requested.

## Operating Model

1. Keep lifecycle requirement flags disabled until the corresponding operational control is approved.
2. Add safe placeholder metadata and run dry-run readiness.
3. Resolve lifecycle blockers before enabling required Key Vault signing in a production-like environment.
4. Retain dry-run evidence with release evidence.
5. Execute live rotation, log review, or incident recovery only through approved cloud/change-control procedures.

## Related Runbooks

- `docs/clinical-azure-key-vault-rotation-runbook.md`
- `docs/clinical-azure-key-vault-access-log-review.md`
- `docs/clinical-azure-key-vault-incident-recovery.md`
- `docs/clinical-azure-key-vault-signing-readiness.md`
