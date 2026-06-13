# Clinical Azure Blob WORM Readiness

Post-RC-08 update date: 2026-06-13

Post-RC-09 SDK operations foundation update date: 2026-06-13

## Purpose

This checklist documents Azure Blob Storage readiness assumptions for clinical workflow audit WORM evidence. Post-RC-09 adds guarded SDK operation code paths, but this checklist still does not create Azure resources, assign roles, configure immutability, or require real credentials for local/test validation.

## Required Settings

```text
AUDIT_OBJECT_MIRROR_REQUIRED=true
AUDIT_OBJECT_MIRROR_MODE=object_storage
AUDIT_OBJECT_MIRROR_PROVIDER=azure_blob
AUDIT_OBJECT_MIRROR_AZURE_ACCOUNT_URL=https://<account>.blob.core.windows.net
AUDIT_OBJECT_MIRROR_AZURE_CONTAINER=clinical-audit-worm
AUDIT_OBJECT_MIRROR_AZURE_PREFIX=workflow-audit
AUDIT_OBJECT_MIRROR_AZURE_CREDENTIAL_MODE=managed_identity
AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=false
AUDIT_OBJECT_MIRROR_AZURE_IMMUTABILITY_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_LEGAL_HOLD_REQUIRED=true
AUDIT_OBJECT_MIRROR_AZURE_CHECKSUM_VALIDATION_REQUIRED=true
AUDIT_OBJECT_MIRROR_RETENTION_POLICY=RET-7Y-WORM
AUDIT_OBJECT_MIRROR_LEGAL_HOLD_REFERENCE=LH-CLINICAL-AUDIT
```

`managed_identity`, `workload_identity`, or another approved non-inline secret mode should be used for credential mode. Inline account keys, connection strings, shared keys, plain secrets, and inline SAS tokens are blocked by production gates when Azure mirroring is required.

Set `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` only in an environment approved to contact the Azure Blob account. When this flag is false, readiness summaries and fake-client tests do not import the Azure SDK or perform network calls.

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

Post-RC-08 and Post-RC-09 provide:

- Azure provider config validation;
- expected URI prefix reporting;
- capability flags;
- SDK-free readiness checks;
- injectable fake-client operation tests;
- guarded SDK wrapper for upload, stat/head, metadata read, prefix list, and checksum verification;
- real-I/O feature flag;
- production startup gate enforcement for required Azure settings;
- recovery drill provider readiness summary.

Readiness checks do not perform network calls or import the Azure SDK. Real SDK construction is attempted only when `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` and no fake/test client is injected.

## Dependency Behavior

Local/dev/test can run without Azure packages when real I/O is disabled. If real Azure I/O is enabled, production gates and provider validation require:

- `azure-storage-blob`;
- `azure-identity` for identity-based credential modes.

Missing dependencies fail clearly before real object operations proceed.

## Fake-Client Test Strategy

Unit tests inject an in-memory fake client that implements the provider boundary:

- `upload_object`
- `get_object_properties`
- `list_objects`
- `download_object`

The fake validates payload bytes, metadata checksum storage, URI construction, idempotent writes, prefix listing, matching checksum verification, and mismatch detection without using credentials or the network.

## Future Integration Path

1. Add approved Azure SDK dependencies to the deployment environment if live Azure writes are enabled.
2. Validate managed-identity or workload-identity role assignment against the target container.
3. Run a non-production live-cloud smoke test against a disposable WORM-ready container.
4. Verify upload with redacted audit metadata payloads only.
5. Read back object properties and checksum metadata.
6. Validate immutability and legal-hold status from Azure APIs.
7. Link manifest payload storage to mirror records and manifest metadata.
8. Run production recovery drills with compliance signoff.
