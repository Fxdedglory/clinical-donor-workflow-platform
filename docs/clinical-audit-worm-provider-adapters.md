# Clinical Audit WORM Provider Adapters

Post-RC-08 update date: 2026-06-13

## Purpose

Post-RC-08 adds a provider adapter readiness layer for workflow audit WORM mirroring. It keeps local development deterministic and prepares the codebase for future cloud object storage integration without requiring real cloud credentials or performing network calls in tests.

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

The Azure provider is readiness-only in Post-RC-08. It validates configuration, reports expected object URI prefix, reports capability assumptions, and exposes checksum verification as `not_checked` until real SDK integration is approved.

No Azure SDK import is required for readiness checks. Real methods are guarded and reserved for a later provider integration sprint.

## Readiness Summary

`provider_readiness_summary` returns:

- provider name;
- mirror mode;
- expected URI prefix;
- capability flags;
- validation errors and warnings;
- Azure account/container/prefix/credential-mode readiness details;
- `network_calls_performed=false`.

## Known Limitations

- Azure object upload/list/head/read operations are not implemented.
- Provider immutability and legal hold are configuration assumptions only.
- Real cloud SDK integration, credential acquisition, and provider checksum readback remain future work.
