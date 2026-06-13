# Clinical Audit Manifest Signing

Post-RC-12 update date: 2026-06-13

## Purpose

This runbook defines the repository-safe cryptographic signing foundation for workflow audit WORM manifests. It adds deterministic signing and verification behavior without requiring live Azure Key Vault, external KMS credentials, cloud resources, or network calls.

## Signing Modes

| Mode | Behavior | Production posture |
| --- | --- | --- |
| `disabled` | No signature is produced. | Fails when manifest signing is required. |
| `checksum_placeholder` | Deterministic checksum-derived placeholder for compatibility. | Non-production only; fails when signing is required in production-like environments. |
| `local_hmac_sha256` | Uses `AUDIT_MANIFEST_LOCAL_HMAC_KEY` to produce a deterministic HMAC signature. Verification is supported locally. | Dev/test only unless explicitly allowed for a production-like dry run. |
| `external_kms_placeholder` | Validates external KMS metadata and marks provider verification pending. No network calls. | Accepted as a production-safe placeholder when key reference and algorithm are configured. |
| `azure_key_vault_placeholder` | Validates Azure Key Vault metadata and marks provider verification pending. No network calls. | Accepted as a production-safe placeholder when vault URL, key name, key reference, and algorithm are configured. |

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
- `signature_verification_status=non_production_placeholder` for matching checksum placeholders;
- `signature_verification_status=pending_provider_verification` for external KMS or Azure Key Vault placeholders;
- `signature_verification_status=failed` for tampered local HMAC manifests.

Recovery drill summaries include `manifest_signature_verification` so operators can see checksum and signature status alongside provider object verification.

## Production Gates

Production-like startup fails when:

- signing is required but mode is disabled;
- signing is required but mode is `checksum_placeholder`;
- `local_hmac_sha256` is configured without explicit local-signing allowance;
- local HMAC signing is configured without local signing material;
- external/KMS or Key Vault mode lacks `AUDIT_MANIFEST_SIGNING_KEY_REF`;
- Azure Key Vault placeholder mode lacks vault URL or key name;
- signing algorithm is missing, deprecated, or unsupported.

Local/dev/test reports the same findings as warnings.

## Future Azure Key Vault Path

Future live integration should:

1. Resolve approved managed/workload identity access to Azure Key Vault.
2. Replace `azure_key_vault_placeholder` with a real provider implementation.
3. Sign the canonical manifest checksum through Key Vault without exporting private key material.
4. Verify signatures with public key or Key Vault verify APIs.
5. Retain Key Vault operation evidence, key version, role assignment evidence, and WORM manifest payload.

## Known Limitations

- No real KMS or Azure Key Vault network call is performed by this foundation.
- `checksum_placeholder` is not cryptographic signing.
- Local HMAC is deterministic and testable, but not a production signing architecture unless separately approved.
- Manifest payload signing does not replace provider-side immutable retention, legal hold, or live object verification.
