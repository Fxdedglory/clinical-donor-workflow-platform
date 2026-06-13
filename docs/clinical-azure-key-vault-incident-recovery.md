# Clinical Azure Key Vault Incident Recovery

Post-RC-15 update date: 2026-06-13

## Purpose

This runbook defines repository-safe readiness for signing-key incident recovery. It covers compromised, disabled, expired, deleted, or misconfigured Azure Key Vault signing keys. It does not perform Azure recovery actions automatically.

## Required Metadata

```text
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_INCIDENT_RECOVERY_REF=runbook://clinical-key-vault/incident-recovery-v1
```

The reference should point to an approved incident runbook, ticket template, tabletop evidence package, or continuity plan. It must not contain secrets, raw access logs with PHI/ePHI, or key material.

## Immediate Actions

1. Preserve the current readiness evidence and application logs.
2. Disable live Key Vault signing by setting `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false` if continued signing could worsen the incident.
3. Notify security, compliance, clinical operations, and the Key Vault owner.
4. Preserve Key Vault audit logs, identity assignment evidence, deployment settings, and manifest evidence packages.
5. Confirm whether historical manifest verification is affected.

## Recovery Paths

- Compromised key: revoke sign permission, rotate to the approved next key, retain old verification evidence under legal/compliance direction.
- Disabled or expired key: restore/enable under Key Vault owner approval or rotate to the next approved key.
- Deleted key: follow Key Vault soft-delete and purge-protection procedures outside this repository.
- Credential or identity misconfiguration: remove unsafe grants, restore least privilege, and rerun dry-run readiness before live validation.

## Evidence To Retain

- Key Vault readiness evidence with `lifecycle_summary.incident_recovery_status=documented`.
- Current and next key references.
- Key Vault access-log review evidence.
- Identity role assignment evidence.
- Manifest verification summary for accepted evidence packages.
- Incident ticket, approval, and recovery timeline.

## Completion Criteria

Recovery is ready when production gates pass, dry-run evidence contains no lifecycle blockers, access-log review evidence is retained, affected manifests have a verification disposition, and compliance owners sign off on any key retirement or purge action.
