# Clinical Release Exceptions

RC2 review date: 2026-06-13

## Dependency Advisory Decision

No Vite/esbuild release exception is required for RC2.

RC1 identified two high-severity advisories in the frontend build dependency path:

- `esbuild: Missing binary integrity verification in Deno module enables remote code execution via NPM_CONFIG_REGISTRY`
- `esbuild allows arbitrary file read when running the development server on Windows`

Affected RC1 path:

```text
vite 7.x -> esbuild 0.27.x
```

RC2 decision:

- Perform a bounded upgrade instead of accepting an exception.
- Upgrade direct frontend dependencies only:
  - `vite` to `^8.0.16`
  - `@vitejs/plugin-react` to `^6.0.2`
- Validate that Node `v24.11.0` satisfies the Vite 8 engine.
- Validate build and audit outcomes.

RC2 validation result:

- `npm install vite@^8.0.16 @vitejs/plugin-react@^6.0.2` completed successfully.
- `npm run build` completed successfully with Vite `8.0.16`.
- `npm audit --audit-level=high` reports `found 0 vulnerabilities`.

## Current Release Exceptions

| Exception | Status | Production exposure assumption | Mitigation | Target remediation |
| --- | --- | --- | --- | --- |
| Vite/esbuild advisory exception | Closed / not needed | Build toolchain only; resolved before RC2 signoff. | Vite 8 and React plugin 6 upgrade. | Continue npm audit in release validation. |
| Filesystem workflow audit storage | Open production-readiness limitation | `metadata/workflow_operations.json` is suitable for local/demo RC validation only, not production authoritative audit. | Documented database-backed audit implementation plan. | Post-RC production hardening sprint before go-live. |
| PHI/ePHI masking framework | Open production-readiness limitation | Internal RBAC restricts access, but detailed masking/redaction is not implemented. | PHI inventory and export permission review documented. | Post-RC PHI masking/export profile sprint. |
| Production fail-closed config guard | Open production-readiness limitation | Production safety depends on deployment settings, not startup rejection of unsafe defaults. | Production runbook lists required and disallowed settings. | Post-RC config hardening sprint. |

## Signoff Note

The dependency advisory that triggered RC2 was remediated. Remaining exceptions are production-readiness limitations already represented in the post-RC backlog and should be accepted only for release-candidate signoff, not full production go-live.
