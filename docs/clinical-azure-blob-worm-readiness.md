# Clinical Azure Blob WORM Readiness

Post-RC-08 update date: 2026-06-13

## Purpose

This checklist documents Azure Blob Storage readiness assumptions for clinical workflow audit WORM evidence. It does not create Azure resources, assign roles, configure immutability, or upload objects.

## Required Settings

```text
AUDIT_OBJECT_MIRROR_REQUIRED=true
AUDIT_OBJECT_MIRROR_MODE=object_storage
AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob
AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL=https://<account>.blob.core.windows.net
AUDIT_OBJECT_MIRROR_AZURE_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_AZURE_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity
AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=true
AUDIT_OBJECT_MIRROR_RETENTION_POLICY=RET-7Y-WORM
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE=LH-CLINICAL-AUDIT
```

`managed_identity`, `workload_identity`, or another approved non-inline secret mode should be used for credential mode. Inline account keys, connection strings, shared keys, plain secrets, and inline SAS tokens are blocked by production gates when Azure mirroring is required.

## Provider Capabilities Expected

The future Azure integration should prove:

- immutable container or blob retention policy;
- legal hold support;
- object metadata or tag support for checksum and manifest linkage;
- object listing by prefix;
- object head/stat by URI;
- checksum or content hash readback;
- access logging and lifecycle policy review;
- least-privilege managed identity access.

## Current Foundation

Post-RC-08 provides:

- Azure provider config validation;
- expected URI prefix reporting;
- capability flags;
- SDK-free readiness checks;
- production startup gate enforcement for required Azure settings;
- recovery drill provider readiness summary.

It does not perform network calls or import the Azure SDK during readiness checks.

## Future Integration Path

1. Add approved Azure SDK dependency.
2. Implement managed-identity credential acquisition.
3. Implement upload with redacted audit metadata payloads only.
4. Read back object properties and metadata.
5. Verify checksum/ETag/content hash.
6. Validate immutability and legal-hold status.
7. Link manifest payload storage to mirror records and manifest metadata.
8. Run production recovery drills with compliance signoff.
