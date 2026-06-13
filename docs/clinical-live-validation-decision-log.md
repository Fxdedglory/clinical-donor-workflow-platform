# Clinical Live Validation Decision Log

Post-RC-16 update date: 2026-06-13

## Current Status

| Validation area | Status | Default behavior |
| --- | --- | --- |
| Azure WORM live validation | Pending external approval | Skipped by default |
| Azure Key Vault live validation | Pending external approval | Skipped by default |

Live tests remain skipped by default because they require approved Azure resources, managed/workload identity permissions, retention/legal-hold policy evidence, diagnostic logging, and compliance change-control approval. Repository validation must remain safe without credentials, network calls, or cloud-side mutations.

## Required Approvals

- Product Owner approval for the validation window and scope.
- Security/Compliance approval for cloud evidence capture.
- Operations approval for resources, identities, and rollback.
- Key Vault owner approval for signing key usage.
- Storage owner approval for WORM container validation.

## Required Environment Variables

Azure WORM live validation:

```text
CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true
AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX=<dedicated-non-production-prefix>
```

Azure Key Vault live validation:

```text
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true
AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault
```

Override flags are allowed only with explicit approval:

```text
AUDIT_OBJECT_MIRROR_AZURE_LIVE_ALLOW_PRODUCTION_PREFIX=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_LIVE_ALLOW_PRODUCTION_KEY=true
```

## Required Resources

- Approved Azure Blob storage account and WORM container.
- Provider-side immutable retention configuration.
- Provider-side legal hold configuration when required.
- Approved Azure Key Vault and signing key version.
- Managed/workload identity with least-privilege storage and sign/verify permissions.
- Azure SDK runtime packages installed in the target validation environment.
- Azure Monitor or approved logging access for evidence review.

## Decision Template For Enabling Live Tests

Decision ID:

Validation area:

Requested window:

Approved resources:

Environment variables approved:

Expected command:

Evidence output path:

Approvers:

Rollback owner:

Decision:

Conditions / stop criteria:

## Rollback / Disable Plan

Set all live flags back to safe defaults:

```text
CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=false
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=false
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false
```

Remove temporary validation-only permissions if approved by resource owners. Preserve evidence artifacts, command output, access logs, and approval records according to compliance retention guidance.
