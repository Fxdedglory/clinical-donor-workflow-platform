# Clinical Azure Key Vault Access-Log Review

Post-RC-15 update date: 2026-06-13

## Purpose

This runbook defines repository-safe access-log review readiness for Azure Key Vault manifest signing. The repository records whether review evidence is documented; it does not query Azure Monitor, export logs, or inspect live Key Vault audit data.

## Required Metadata

```text
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REQUIRED=true
AUDIT_MANIFEST_AZURE_KEY_VAULT_ACCESS_LOG_REVIEW_REF=monitor://clinical-key-vault/access-log-review-monthly
```

The reference should point to an approved query, dashboard, evidence package, ticket, or review control. Do not place raw log exports with PHI/ePHI, access tokens, or credentials in configuration.

## Review Scope

Access-log evidence should confirm:

- signing and verification calls came from the approved managed/workload identity;
- no inline-secret credential path was used;
- key name and key version match approved metadata;
- live validation used non-PHI payloads;
- failed or denied operations were triaged;
- unexpected principals, source networks, or operation types were escalated.

## Cadence

At minimum, review access logs before production signoff, after each approved live validation, during key rotation, after identity changes, and during incident recovery. Compliance owners may require a monthly or release-based cadence.

## Evidence Capture

Run dry-run readiness after setting the access-log review reference:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --evidence-out <approved-evidence-path>\key-vault-signing-evidence.json
```

Confirm `lifecycle_summary.access_log_review_status=documented` and retain the linked access-log evidence outside the repository.

## Stop Conditions

Stop signoff if logs are unavailable, expected Key Vault operations cannot be correlated to the approved identity, unexpected principals are present, output contains credentials or PHI/ePHI, or review evidence is missing while access-log review is required.
