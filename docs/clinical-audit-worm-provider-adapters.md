# Clinical Audit WORM Provider Adapters

Post-RC-08 update date: 2026-06-13

Post-RC-09 SDK operations foundation update date: 2026-06-13

Post-RC-10 live readiness harness update date: 2026-06-13

Post-RC-11 evidence package update date: 2026-06-13

## Purpose

Post-RC-08 adds a provider adapter readiness layer for workflow audit WORM mirroring. Post-RC-09 adds a guarded Azure Blob SDK operations foundation. Local development stays deterministic, tests use fake clients, and no real cloud credentials or network calls are required unless real Azure I/O is explicitly enabled.

Post-RC-10 adds a live integration readiness harness that remains skipped by default. The harness gives operators a future path to validate real Azure write/stat/list/checksum behavior only after explicit environment flags and a dedicated test prefix are configured.

Post-RC-11 adds a sanitized Azure WORM validation evidence package. The package reuses provider readiness output, records dry-run safety fields, and excludes raw credentials and PHI/ePHI.

Service:

```text
backend/app/services/clinical_audit_mirror_providers.py
```

## Provider Contract

Adapters expose:

- `put_object`
- `stat_object`
- `read_object_metadata`
- `list_objects`
- `verify_object_checksum`
- `supports_immutability`
- `supports_legal_hold`
- `supports_retention_policy`
- readiness summary with expected URI prefix and validation findings

## Local Filesystem Provider

The local provider wraps the existing simulation behavior:

```text
local-worm://clinical-audit/workflow-audit/{workflow}/yyyy/mm/{operation_id}.json
```

It supports deterministic writes, object stat, metadata read, listing, and checksum verification. It does not claim WORM immutability, legal hold, or retention-policy enforcement.

## Azure Blob Readiness Provider

The Azure provider now has a small client boundary for upload, stat/head, metadata read, prefix listing, and checksum verification. Tests inject fake clients through the provider constructor or registry. The real SDK wrapper is only constructed when `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` and no test client is injected.

No Azure SDK import is required for readiness checks or fake-client tests. Missing SDK packages do not break local/dev/test unless real Azure I/O is enabled.

The real adapter expects:

- `azure-storage-blob` for Blob service operations;
- `azure-identity` for approved non-secret Azure identity credential modes;
- a pre-created container with provider-side immutability and legal hold configured outside this codebase.

The code does not create Azure resources, assign roles, configure retention, or set legal holds.

## Live Integration Harness

Live tests use the `azure_worm_live` pytest marker and are skipped unless:

```text
CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true
```

They also require:

```text
AUDIT_OBJECT_MIRROR_AZURE_LIVE_TEST_PREFIX=workflow-audit/live-validation-test
```

The prefix guard rejects missing, ambiguous, or production-like prefixes. The dry-run command is:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json
```

The dry-run evidence command is:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json --evidence-out <approved-evidence-path>\azure-worm-validation-evidence.json
```

Use `--live-write` only after change-control approval for one live write/stat/checksum check under the configured test prefix.

## Readiness Summary

`provider_readiness_summary` returns:

- provider name;
- mirror mode;
- expected URI prefix;
- capability flags;
- validation errors and warnings;
- Azure account/container/prefix/credential-mode readiness details;
- SDK and Azure identity package availability;
- real-I/O enabled/disabled state;
- supported operation methods;
- no-network dry-run status;
- `network_calls_performed=false`.

## Evidence Summary

`backend/app/services/clinical_azure_worm_evidence.py` builds a whitelisted JSON artifact with:

- generated timestamp and environment mode;
- provider and provider mode;
- real-I/O, live-test, live-write, upload, and network flags;
- account/container/prefix readiness summary;
- credential mode summary without secret values;
- immutability, legal hold, and checksum requirement summaries;
- blocking issues and warnings from live-readiness and provider-readiness checks;
- validation result and data safety summary.

## Known Limitations

- Azure SDK operations are foundation code paths and remain behind `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO`.
- Live-cloud integration tests are skeletonized and skipped by default.
- Evidence JSON documents readiness posture but does not prove Azure-side immutability without external policy evidence.
- Provider immutability and legal hold are configuration assumptions only; enforcement must be configured in Azure.
- Provider-side retention/legal hold validation and live recovery drills remain future work.
