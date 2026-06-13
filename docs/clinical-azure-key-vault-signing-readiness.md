# Clinical Azure Key Vault Signing Readiness

Post-RC-13 update date: 2026-06-13

## Purpose

This runbook documents the Azure Key Vault signing SDK operations readiness foundation for clinical audit WORM manifests. The repository now has a real-capable signing and verification path, but local validation remains SDK-free and network-free unless real I/O is explicitly enabled.

## Safety Boundary

Normal tests and dry-run evidence do not contact Azure Key Vault. Real SDK construction is attempted only when all of these are true:

- `AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault`;
- `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true`;
- no fake signing client is injected;
- required Key Vault metadata and safe credential mode are configured.

`azure_key_vault_placeholder` remains metadata-only and reports pending provider verification. Use `azure_key_vault` for the real-capable operation path.

## Required Environment Variables

```text
AUDIT_MANIFEST_SIGNING_REQUIRED=true
AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault
AUDIT_MANIFEST_SIGNING_ALGORITHM=rsa-pss-sha256
AUDIT_MANIFEST_SIGNING_KEY_REF=keyvault://clinical-audit/manifest/v1
AUDIT_MANIFEST_AZURE_KEY_VAULT_URL=https://<vault-name>.vault.azure.net
AUDIT_MANIFEST_AZURE_KEY_NAME=clinical-audit-manifest
AUDIT_MANIFEST_AZURE_KEY_VERSION=<approved-key-version>
AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE=managed_identity
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_REQUIRE_HSM=false
```

Real I/O also requires `azure-keyvault-keys` and `azure-identity` in the runtime image. The repository does not require those packages for local/dev/test.

## Credential Mode Assumptions

Approved modes are non-inline-secret identity modes: `managed_identity`, `workload_identity`, `default_azure_credential`, `entra_id`, `azure_identity`, and `azure_cli`.

Do not use inline client secrets, shared keys, connection strings, SAS tokens, or plain secrets for manifest signing configuration.

## Fake-Client Test Strategy

Unit tests inject a deterministic fake client with:

- `sign(algorithm, digest)`;
- `verify(algorithm, digest, signature)`.

The fake signs the SHA-256 digest of the canonical manifest signing payload. Tests cover deterministic signing, verification success, tamper failure, key reference metadata, SDK-missing readiness, evidence sanitization, and production gate behavior without Azure credentials or network calls.

## Verification Behavior

- `azure_key_vault` with real I/O disabled returns pending provider signing/verification.
- `azure_key_vault` with an injected fake client can sign and verify locally.
- Tampered manifest payloads fail verification because the canonical manifest checksum changes.
- Missing SDK/configuration failures return explicit reasons before a network call can occur.

## Evidence Output

Sanitized Azure WORM evidence may include:

- signing provider readiness;
- real-I/O enabled/disabled state;
- vault URL configured/unconfigured only;
- key name, key version, and key reference metadata;
- credential mode;
- SDK availability;
- signature verification status.

Evidence must not include key material, private keys, raw credentials, secrets, PHI, or ePHI.

## Live Validation Checklist

Before enabling real Key Vault I/O:

1. Confirm the Key Vault, key, key version, and HSM expectation are approved.
2. Confirm managed/workload identity has least-privilege sign and verify permissions.
3. Confirm Key Vault diagnostic logging and access logging are enabled.
4. Install `azure-keyvault-keys` and `azure-identity` in the target runtime image.
5. Run production gates and dry-run WORM readiness with real I/O disabled.
6. Enable real I/O only in an approved non-production validation environment.
7. Sign and verify a non-PHI manifest.
8. Retain operation evidence, key version, identity assignment, access logs, and recovery drill output.

## Known Limitations

- This foundation does not create Azure resources.
- Live Key Vault validation is not run by default.
- Key rotation, key retirement, access-log review workflow, and incident recovery runbooks remain future operational work.
- Manifest signing does not replace provider-side immutable retention, legal hold, or Azure Blob WORM validation.
