# Clinical Audit WORM Provider Adapters

Post-RC-08 update date: 2026-06-13

Post-RC-09 SDK operations foundation update date: 2026-06-13

## Purpose

Post-RC-08 adds a provider adapter readiness layer for workflow audit WORM mirroring. Post-RC-09 adds a guarded Azure Blob SDK operations foundation. Local development stays deterministic, tests use fake clients, and no real cloud credentials or network calls are required unless real Azure I/O is explicitly enabled.

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

## Known Limitations

- Azure SDK operations are foundation code paths and remain behind `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO`.
- Live-cloud integration tests are not implemented.
- Provider immutability and legal hold are configuration assumptions only; enforcement must be configured in Azure.
- Provider-side retention/legal hold validation and live recovery drills remain future work.
