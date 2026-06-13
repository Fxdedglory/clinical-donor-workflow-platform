# Clinical Audit Manifest Signing

Post-RC-12 update date: 2026-06-13

Post-RC-13 Azure Key Vault SDK readiness update date: 2026-06-13

Post-RC-14 Azure Key Vault live validation harness update date: 2026-06-13

## Purpose

This runbook defines the repository-safe cryptographic signing foundation for workflow audit WORM manifests. It adds deterministic signing and verification behavior without requiring live Azure Key Vault, external KMS credentials, cloud resources, or network calls during local validation.

## Signing Modes

| Mode | Behavior | Production posture |
| --- | --- | --- |
| `disabled` | No signature is produced. | Fails when manifest signing is required. |
| `checksum_placeholder` | Deterministic checksum-derived placeholder for compatibility. | Non-production only; fails when signing is required in production-like environments. |
| `local_hmac_sha256` | Uses `AUDIT_MANIFEST_LOCAL_HMAC_KEY` to produce a deterministic HMAC signature. Verification is supported locally. | Dev/test only unless explicitly allowed for a production-like dry run. |
| `external_kms_placeholder` | Validates external KMS metadata and marks provider verification pending. No network calls. | Accepted as a production-safe placeholder when key reference and algorithm are configured. |
| `azure_key_vault_placeholder` | Validates Azure Key Vault metadata and marks provider verification pending. No network calls. | Accepted as a production-safe placeholder when vault URL, key name, key reference, and algorithm are configured. |
| `azure_key_vault` | Real-capable Azure Key Vault signing/verification path behind `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO`. Fake-client tests exercise the operation contract without Azure credentials. | Accepted as readiness configuration when metadata and safe credential mode are configured. Real I/O also requires SDK packages. |

## Configuration

Preferred settings:

```text
AUDIT_MANIFEST_SIGNING_REQUIRED=true
AUDIT_MANIFEST_SIGNING_MODE=external_kms_placeholder
AUDIT_MANIFEST_SIGNING_ALGORITHM=rsa-pss-sha256
AUDIT_MANIFEST_SIGNING_KEY_REF=kms://clinical-audit-manifest-key-v1
AUDIT_MANIFEST_LOCAL_HMAC_KEY=
AUDIT_MANIFEST_ALLOW_LOCAL_SIGNING_IN_PRODUCTION=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_URL=
AUDIT_MANIFEST_AZURE_KEY_NAME=
AUDIT_MANIFEST_AZURE_KEY_VERSION=
AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE=
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=false
AUDIT_MANIFEST_AZURE_KEY_VAULT_REQUIRE_HSM=false
```

Legacy compatibility settings are still read when the preferred settings are absent:

```text
AUDIT_OBJECT_MIRROR_SIGNATURE_REQUIRED
AUDIT_OBJECT_MIRROR_SIGNATURE_ALGORITHM
AUDIT_OBJECT_MIRROR_SIGNATURE_KEY_REF
```

Use the preferred `AUDIT_MANIFEST_*` settings for new deployments and release evidence.

## Local HMAC Dev/Test Flow

`local_hmac_sha256` is intended for deterministic unit tests and local verification:

```text
AUDIT_MANIFEST_SIGNING_REQUIRED=true
AUDIT_MANIFEST_SIGNING_MODE=local_hmac_sha256
AUDIT_MANIFEST_SIGNING_ALGORITHM=hmac-sha256
AUDIT_MANIFEST_SIGNING_KEY_REF=local-dev-hmac-key-v1
AUDIT_MANIFEST_LOCAL_HMAC_KEY=<local test value outside Git>
```

The key value must not be logged, committed, written into evidence artifacts, or copied into release docs. Evidence may record that local signing material is configured, but never records the material itself.

## Azure Key Vault Readiness Flow

`azure_key_vault` is the real-capable provider mode. It remains safe by default because real SDK construction is blocked unless:

```text
AUDIT_MANIFEST_SIGNING_REQUIRED=true
AUDIT_MANIFEST_SIGNING_MODE=azure_key_vault
AUDIT_MANIFEST_SIGNING_ALGORITHM=rsa-pss-sha256
AUDIT_MANIFEST_SIGNING_KEY_REF=keyvault://clinical-audit/manifest/v1
AUDIT_MANIFEST_AZURE_KEY_VAULT_URL=https://<vault-name>.vault.azure.net
AUDIT_MANIFEST_AZURE_KEY_NAME=clinical-audit-manifest
AUDIT_MANIFEST_AZURE_KEY_VERSION=<approved-key-version>
AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE=managed_identity
AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true
```

Approved credential modes are non-inline-secret identity modes such as `managed_identity`, `workload_identity`, `default_azure_credential`, `entra_id`, `azure_identity`, and `azure_cli`. Inline client secrets, account keys, shared keys, connection strings, and SAS-style values are blocked by production gates.

When real I/O is enabled without an injected test client, the runtime image must include `azure-keyvault-keys` and `azure-identity`. The repository does not add those packages by default; local/dev/test continues to work without them when real I/O is disabled.

## Azure Key Vault Live Validation Harness

Post-RC-14 adds a skipped-by-default live validation harness. Normal validation does not sign, verify, import a real Key Vault client, require credentials, or perform network calls.

Dry-run readiness:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json
```

Sanitized evidence capture:

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --evidence-out <approved-evidence-path>\key-vault-signing-evidence.json
```

Live signing requires both controls:

```text
CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true
```

```powershell
.\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json --live-sign --evidence-out <approved-evidence-path>\key-vault-live-signing-evidence.json
```

The live harness refuses ambiguous or production-like key names/references unless `AUDIT_MANIFEST_AZURE_KEY_VAULT_LIVE_ALLOW_PRODUCTION_KEY=true` is set after approval. Dedicated non-production identifiers should include clear tokens such as `validation`, `test`, `sandbox`, or `nonprod`.

## Operation Boundary

The signing service exposes an injectable Azure Key Vault client boundary. Unit tests use a fake client with `sign(algorithm, digest)` and `verify(algorithm, digest, signature)` methods. The real wrapper imports Azure SDK modules only when real I/O is enabled and no fake client is supplied.

The provider signs the SHA-256 digest of the canonical signing payload. The manifest stores an `azure-key-vault:<base64-signature>` value, the configured algorithm, and the key reference. It never stores key material, client secrets, or private keys.

## Manifest Behavior

Manifest generation keeps:

- deterministic manifest id;
- manifest checksum over canonical unsigned manifest JSON;
- signing mode;
- signature status;
- signature algorithm;
- signature key reference;
- signature value in the manifest payload when local HMAC or checksum placeholder signing produces one.

The database manifest ledger stores signing metadata only. The full manifest payload should be retained with the evidence package when it is needed for verification.

## Verification Behavior

Verification reports:

- `checksum_status=verified` or `checksum_mismatch`;
- `signature_verification_status=verified` for valid local HMAC signatures;
- `signature_verification_status=verified` for valid Azure Key Vault signatures when verification runs through the enabled provider or fake client;
- `signature_verification_status=verified` for approved live Key Vault validation when both the live environment flag and `--live-sign` are supplied;
- `signature_verification_status=non_production_placeholder` for matching checksum placeholders;
- `signature_verification_status=pending_provider_verification` for external KMS or Azure Key Vault placeholders;
- `signature_verification_status=pending_provider_verification` for `azure_key_vault` when real I/O is disabled;
- `signature_verification_status=failed` for tampered local HMAC or Azure Key Vault manifests.

Recovery drill summaries include `manifest_signature_verification` so operators can see checksum and signature status alongside provider object verification.

## Production Gates

Production-like startup fails when:

- signing is required but mode is disabled;
- signing is required but mode is `checksum_placeholder`;
- `local_hmac_sha256` is configured without explicit local-signing allowance;
- local HMAC signing is configured without local signing material;
- external/KMS or Key Vault mode lacks `AUDIT_MANIFEST_SIGNING_KEY_REF`;
- Azure Key Vault placeholder or real-capable mode lacks vault URL or key name;
- `azure_key_vault` mode lacks a safe `AUDIT_MANIFEST_AZURE_KEY_VAULT_CREDENTIAL_MODE`;
- `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true` but `azure-keyvault-keys` or `azure-identity` is unavailable;
- signing algorithm is missing, deprecated, or unsupported.

Local/dev/test reports the same findings as warnings.

## Azure Key Vault Live Validation Path

Live integration should:

1. Resolve approved managed/workload identity access to Azure Key Vault.
2. Install the minimal Azure SDK packages in the target runtime image.
3. Run dry-run readiness and production gates with real I/O disabled.
4. Enable `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true` only in an approved validation environment.
5. Sign and verify a non-PHI manifest through Key Vault.
6. Retain Key Vault operation evidence, key version, role assignment evidence, access logging evidence, and WORM manifest payload.

## Known Limitations

- No live Azure Key Vault network call runs in normal tests or dry-run readiness.
- The SDK operation path is present, but live Key Vault validation remains opt-in and externally approved.
- The live validation harness verifies one non-PHI manifest checksum only; it does not prove key rotation, access-log ingestion, or incident recovery readiness.
- `checksum_placeholder` is not cryptographic signing.
- Local HMAC is deterministic and testable, but not a production signing architecture unless separately approved.
- Manifest payload signing does not replace provider-side immutable retention, legal hold, or live object verification.
