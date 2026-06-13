# Clinical Azure WORM Validation Evidence Template

Post-RC-11 update date: 2026-06-13

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
- patient, donor, encounter, order, billing, or clinical free-text payloads.

`storage_readiness_summary` may show configured container and prefix names because operators need to confirm the selected WORM target. The account URL is summarized as configured/unconfigured only.

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
- approval reference for the live-test prefix;
- live pytest and `--live-write` output only if live validation was separately approved.
