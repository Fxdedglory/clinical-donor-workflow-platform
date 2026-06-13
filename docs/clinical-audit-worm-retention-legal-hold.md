# Clinical Audit WORM Retention And Legal Hold

Post-RC-07 update date: 2026-06-13

Post-RC-08 Azure readiness update date: 2026-06-13

Post-RC-09 Azure SDK operations foundation update date: 2026-06-13

## Purpose

This checklist documents provider readiness assumptions for workflow audit WORM evidence. It does not create retention policies or legal holds in any cloud provider.

## Required Provider Capabilities

The approved production target should support:

- immutable retention policy;
- legal hold or equivalent preservation control;
- object versioning or append-only semantics;
- access logging;
- checksum or content hash verification;
- lifecycle policy review;
- backup and restore testing;
- least-privilege runtime identity.

## Configuration References

Production policy can require these settings:

```text
AUDIT_OBJECT_MIRROR_REQUIRED=true
AUDIT_OBJECT_MIRROR_MODE=object_storage
AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob_immutability
AUDIT_OBJECT_MIRROR_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL=https://<account>.blob.core.windows.net
AUDIT_OBJECT_MIRROR_AZURE_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_AZURE_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=false
AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=true
AUDIT_OBJECT_MIRROR_RETENTION_POLICY=RET-7Y-WORM
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE=LH-CLINICAL-AUDIT
AUDIT_OBJECT_MIRROR_MANIFEST_REQUIRED=true
AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED=true
AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM=sha256-placeholder
AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF=audit-manifest-key-v1
```

The placeholder signature algorithm is acceptable only for local/test and readiness evidence. A real provider-backed signing or key-management design remains future work.

## Startup Gate Behavior

Production startup fails when object/WORM mirroring is required but the provider/container/prefix settings are missing.

When manifest/signature policy is required, startup also fails for:

- missing retention policy reference;
- legal hold required without a legal hold reference;
- signature required without manifest required;
- signed manifests required without signature algorithm or key reference.
- Azure Blob required without account URL, container, prefix, or safe credential mode.
- Azure Blob real I/O enabled without required SDK dependencies.
- Azure Blob immutability, legal hold, or checksum validation required without supporting readiness settings.

Local/dev/test mode reports these as warnings only when the policy flags are explicitly set.

## Provider Integration Path

Azure Blob SDK operation paths now exist behind `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO`. Future Azure/AWS/GCP integration should add:

- upload client with no raw PHI/ePHI payloads beyond redacted audit metadata;
- provider-side immutability policy validation;
- legal-hold status validation;
- object checksum readback;
- manifest object write and retention;
- real signature or key-management integration;
- operational replay guidance with change-control approval.
- live-cloud recovery drills with compliance signoff.

Azure Blob integration should prefer managed identity or workload identity. Inline account keys, connection strings, shared keys, plain secrets, and inline SAS tokens are not acceptable production credential modes.

## Known Limitations

- The repository currently provides provider readiness, local simulation, fake-client Azure tests, and guarded Azure SDK operation paths.
- Retention and legal hold controls must be configured and proven in the selected cloud provider.
- Live Azure validation, provider-side immutability readback, and legal-hold enforcement checks remain future work.
- Legal/compliance owners must approve retention duration, hold naming, and evidence package export procedures.
