# Clinical Azure Blob WORM Readiness

Post-RC-08 update date: 2026-06-13

Post-RC-09 SDK operations foundation update date: 2026-06-13

Post-RC-10 live readiness harness update date: 2026-06-13

Post-RC-11 validation evidence package update date: 2026-06-13

Post-RC-12 manifest signing foundation update date: 2026-06-13

Post-RC-13 Azure Key Vault signing readiness update date: 2026-06-13

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

Live validation is opt-in and skipped by default. To enable future live tests, set:

```text
CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true
AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX=workflow-audit/live-validation-test
```

The live test prefix must be dedicated to non-production validation. Ambiguous or production-like prefixes are rejected unless `AUDIT_OBJECT_MIRROR_AZURE_LIVE_ALLOW_PRODUCTION_PREFIX=true` is set after change-control approval.

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

Post-RC-10 adds:

- pytest marker `azure_worm_live`;
- skipped-by-default integration skeletons under `tests/integration`;
- dry-run readiness script `scripts/check_azure_worm_readiness.py`;
- prefix and live-write safety guards;
- operational checklist in `docs/clinical-azure-worm-live-validation.md`.

Post-RC-11 adds:

- sanitized `--evidence-out` JSON artifact generation for dry-run and approved live-write checks;
- evidence summaries for provider, account/container/prefix readiness, credential mode, immutability, legal hold, checksum validation, blockers, warnings, and validation result;
- tests proving dry-run evidence does not upload objects or perform network calls;
- operator checklist and evidence template documents.

Post-RC-12 adds:

- manifest signing modes for disabled, checksum placeholder, local HMAC, external KMS placeholder, and Azure Key Vault placeholder;
- local HMAC signature verification for dev/test manifests;
- production gate failures for required signing with disabled or checksum-placeholder modes;
- evidence output fields for manifest signing metadata and verification status.

Post-RC-13 adds:

- real-capable `azure_key_vault` manifest signing and verification hooks behind `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO`;
- injectable fake-client tests for Key Vault canonical payload signing, verification, tamper failure, key reference metadata, and SDK-missing behavior;
- sanitized evidence fields for Key Vault provider readiness, credential mode, SDK availability, and real-I/O state;
- production gate checks for Key Vault signing metadata, safe credential mode, and SDK dependencies when real I/O is enabled.

Readiness checks do not perform network calls or import the Azure SDK. Real SDK construction is attempted only when `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` and no fake/test client is injected.

## Dependency Behavior

Local/dev/test can run without Azure packages when real I/O is disabled. If real Azure I/O is enabled, production gates and provider validation require:

- `azure-storage-blob`;
- `azure-identity` for identity-based credential modes.

If real Azure Key Vault signing I/O is enabled, production gates require:

- `azure-keyvault-keys`;
- `azure-identity`.

Missing dependencies fail clearly before real object operations proceed.

## Fake-Client Test Strategy

Unit tests inject an in-memory fake client that implements the provider boundary:

- `upload_object`
- `get_object_properties`
- `list_objects`
- `download_object`

The fake validates payload bytes, metadata checksum storage, URI construction, idempotent writes, prefix listing, matching checksum verification, and mismatch detection without using credentials or the network.

## Dry-Run Readiness Command

Run:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json
```

The command prints provider readiness, real-I/O state, live-test flag state, live-test prefix status, and blocking issues. It does not upload objects or perform network calls unless `--live-write` is explicitly supplied.

To retain a sanitized artifact for release evidence, run:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json --evidence-out <approved-evidence-path>\azure-worm-validation-evidence.json
```

The evidence artifact intentionally excludes raw credentials and PHI/ePHI. It reports `upload_attempted=false` and `network_calls_performed=false` in dry-run mode.
It also reports manifest signing mode, required flag, algorithm, key reference, and signature verification status without exposing key material.

## Future Integration Path

1. Add approved Azure SDK dependencies to the deployment environment if live Azure writes are enabled.
2. Validate managed-identity or workload-identity role assignment against the target container.
3. Run the dry-run readiness script and retain the JSON output.
4. Generate and retain sanitized evidence with `--evidence-out`.
5. Run a non-production live-cloud smoke test against a disposable WORM-ready container using the `azure_worm_live` marker.
6. Verify upload with redacted audit metadata payloads only.
7. Read back object properties and checksum metadata.
8. Validate immutability and legal-hold status from Azure APIs.
9. Link manifest payload storage to mirror records and manifest metadata.
10. If Key Vault signing is approved, validate `azure_key_vault` signing and verification first with fake-client tests, then with opt-in live Key Vault evidence.
11. Verify manifest checksum and signature status in the recovery drill summary.
12. Run production recovery drills with compliance signoff.

See `docs/clinical-azure-worm-live-validation.md`, `docs/clinical-azure-worm-validation-evidence-template.md`, `docs/clinical-azure-worm-operator-checklist.md`, `docs/clinical-audit-manifest-signing.md`, and `docs/clinical-azure-key-vault-signing-readiness.md` for the full validation, evidence, and signing checklist.
