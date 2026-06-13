# Clinical Azure WORM Validation Evidence Template

Post-RC-11 update date: 2026-06-13

Post-RC-12 manifest signing update date: 2026-06-13

Post-RC-13 Azure Key Vault signing readiness update date: 2026-06-13

Post-RC-14 Key Vault signing evidence update date: 2026-06-13

## Purpose

This template defines the sanitized evidence artifact produced by the Azure WORM readiness harness. It is repo-safe by default: dry-run mode does not require Azure credentials, does not upload objects, does not perform network calls, and does not include PHI/ePHI or raw credential material.

## Dry-Run Evidence Command

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json --evidence-out metadata\azure-worm-validation-evidence.json
```

The `--evidence-out` path may point to a release evidence folder outside the repository. Do not commit environment-specific evidence packages unless compliance owners explicitly approve the contents and retention location.

## Required Artifact Fields

The JSON artifact uses schema `clinical.azure_worm.validation_evidence.v1` and includes:

- `generated_at`
- `environment_mode`
- `provider`
- `provider_mode`
- `real_io_enabled`
- `live_tests_enabled`
- `live_write_requested`
- `upload_attempted`
- `network_calls_performed`
- `storage_readiness_summary`
- `prefix_safety_status`
- `credential_mode_summary`
- `immutability_requirement_summary`
- `legal_hold_requirement_summary`
- `checksum_validation_summary`
- `manifest_signing_summary`
- `blocking_issues`
- `warnings`
- `validation_result`
- `data_safety_summary`

## Safety Guarantees

The evidence writer only emits whitelisted operational readiness fields. It does not include:

- raw Azure account keys;
- connection strings;
- inline SAS tokens;
- passwords;
- private keys;
- raw credential values;
- local HMAC signing material;
- patient, donor, encounter, order, billing, or clinical free-text payloads.

`storage_readiness_summary` may show configured container and prefix names because operators need to confirm the selected WORM target. The account URL is summarized as configured/unconfigured only.

`manifest_signing_summary` may show signing mode, required flag, algorithm, signature key reference, verification status, Azure Key Vault real-I/O state, key name, key version, credential mode, and SDK availability. It must not include `AUDIT_MANIFEST_LOCAL_HMAC_KEY`, raw Key Vault credentials, client secrets, private keys, or the raw vault URL.

Dedicated Key Vault signing evidence from `scripts/check_azure_key_vault_signing_readiness.py --evidence-out` uses schema `clinical.azure_key_vault.signing_evidence.v1` and records signing attempted, verification attempted, network calls performed, vault URL presence, key metadata, credential mode, SDK availability, blockers, warnings, and validation result. Dry-run evidence must show `signing_attempted=false`, `verification_attempted=false`, and `network_calls_performed=false`.

## Review Outcomes

Use `validation_result` as the first-pass outcome:

- `blocked`: configuration or prefix safety must be resolved before live validation.
- `dry_run_complete`: dry-run evidence was generated without blockers, but live validation was not enabled.
- `ready_for_live_validation`: configuration is ready for an approved opt-in live validation run.
- `live_write_verified`: an approved live write/stat/checksum check completed and verified.

## Evidence Package Contents

For release review, retain:

- sanitized evidence JSON from `--evidence-out`;
- raw script stdout from the same run;
- production security gate output, if this is a hosted release;
- Azure policy exports or screenshots for immutability and legal hold;
- managed/workload identity role assignment evidence;
- manifest signing configuration approval and key-reference evidence;
- Azure Key Vault key/version, identity permission, and access-log evidence when `azure_key_vault` signing is approved;
- dedicated Key Vault signing evidence JSON when `--live-sign` is approved;
- approval reference for the live-test prefix;
- live pytest and `--live-write` output only if live validation was separately approved.
