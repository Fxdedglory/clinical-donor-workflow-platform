# Clinical Security Readiness

RC1 review date: 2026-06-13

RC2 update date: 2026-06-13

Post-RC-02 PHI/export hardening update date: 2026-06-13

Post-RC-03 production startup gate update date: 2026-06-13

Post-RC-04 route drift and analytics suppression update date: 2026-06-13

Post-RC-06 WORM mirror foundation update date: 2026-06-13

Post-RC-07 WORM provider readiness update date: 2026-06-13

Scope: Release Candidate Security / Production Readiness Pass. This review documents the current security posture without adding new clinical modules or introducing new heavyweight scanners.

## Repository-Native Review Process

| Area | Command or source | RC1 result |
| --- | --- | --- |
| Worktree hygiene | `git status --short`; `git diff -- backend/app/cli.py` | Only protected `backend/app/cli.py` was dirty at start. It contains pre-existing seed-data timestamp/referral edits and is excluded from RC1 changes. |
| Secret/config scan | `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed. Required docs exist, generated paths are ignored, tracked high-signal secret patterns are absent. |
| Tracked secret check | `git ls-files .env .env.example ...` plus targeted `rg` scan for secret/config names | `.env` is ignored and not tracked; `.env.example` intentionally contains local/demo placeholders. |
| Python dependency consistency | `.\.venv\Scripts\python.exe -m pip check` | Passed. No broken installed requirements found. |
| Python dependency inventory | `pyproject.toml`, `requirements.txt` | No repo-native vulnerability scanner such as `pip-audit` or `safety` is configured. Do not add one in RC1 without platform approval. |
| Frontend dependency review | `cd frontend; npm audit --audit-level=high` | Failed with two high-severity advisories through Vite/esbuild. Suggested npm fix requires a Vite 8 major upgrade, so remediation is deferred to RC2 compatibility testing. |
| Frontend dependency inventory | `frontend/package.json`, `frontend/package-lock.json` | Lockfile is present. Current Vite dependency resolves to Vite 7.x and esbuild 0.27.x in the lockfile. |

## RC2 Dependency Update

RC2 completed the bounded frontend dependency remediation:

- upgraded `vite` from `^7.2.4` to `^8.0.16`;
- upgraded `@vitejs/plugin-react` from `^5.1.1` to `^6.0.2`;
- confirmed local Node `v24.11.0` satisfies Vite 8 and plugin engine requirements;
- ran `npm run build` successfully with Vite `8.0.16`;
- ran `npm audit --audit-level=high` successfully with `found 0 vulnerabilities`.

No RC2 Vite/esbuild release exception remains open.

## Sensitive Configuration Handling

Production deployments must inject sensitive values through managed app settings, deployment secrets, or an equivalent secret store. They must not use repository defaults or local `.env` values.

| Setting | Local/dev expectation | Production expectation |
| --- | --- | --- |
| `APP_ENV` | `dev` is acceptable locally. | Set `APP_ENV=prod` and use it as the operational signal for stricter deployment gates. |
| `DATABASE_URL` | Local or container database URL may use demo credentials. | Use production database credentials, TLS, least-privilege runtime user, and a rotation plan. |
| `SECRET_KEY` | Demo placeholder exists for local bootstrapping. | Generate a strong unique value outside Git. Rotate with a planned session invalidation window. |
| `ENCRYPTION_KEY` | May be empty while field-level encryption is not implemented. | Required before production-grade sensitive-field encryption is enabled. Store outside Git. |
| `BACKUP_ENCRYPTION_KEY` | May be empty for local demos. | Required before hosted backup routines are enabled. |
| `COOKIE_SECURE` | `false` can be used for local HTTP. | Set `true` behind HTTPS. |
| `COOKIE_SAMESITE` | `lax` is acceptable locally. | Prefer `lax`; review partner portal redirect requirements before changing. |
| `CORS_ORIGINS` | Localhost origins are acceptable. | Restrict to approved production domains only. |
| `MFA_DEV_BYPASS_CODE` | Predictable local value exists for development. | Must not be predictable or enabled as a bypass in production. |
| Email/API provider keys | Empty or console provider is acceptable. | Store `SENDGRID_API_KEY`, `MAILGUN_API_KEY`, SMTP credentials, or cloud provider secrets outside Git. |
| `CLOUDFLARE_TUNNEL_TOKEN` | Developer-local only if used. | Do not commit; rotate if copied outside the managed environment. |

## Local/Dev Versus Production Assumptions

Local and demo environments are allowed to prioritize reproducible workflows and seed data. Production must treat the same clinical records as PHI/ePHI-bearing data and enforce stricter controls.

| Control | Local/dev assumption | Production assumption |
| --- | --- | --- |
| Authentication | JWT auth, session records, and RBAC are enabled for operational routes. | Same, plus hardened secrets, cookie security, and external identity/MFA roadmap completion. |
| Demo credentials | Seeded/demo passwords can exist locally. | No shared demo credentials. Seeded users must be removed, disabled, or reset during deployment. |
| Audit storage | `metadata/workflow_operations.json` supports local evidence and testability; local filesystem WORM mirror simulation, manifest generation, and recovery drill helpers are available for development/testing. | Database-backed append-only audit storage is primary; object-storage/WORM mirror provider, retention, legal hold, real signatures, and recovery drill evidence must be approved before production evidence immutability signoff. |
| Export delivery | Clinical analytics/compliance exports store metadata and row-count contracts. | External warehouse/clearinghouse delivery remains out of scope until dedicated controls are implemented. |
| PHI masking | Post-RC-02 includes deterministic export/audit redaction profiles. Post-RC-04 adds small-cell suppression for aggregate report/export count cells. Post-RC-05 adds lightweight UI masking. | Centralized UI field policy and approved external delivery controls remain production gate items. |
| Dependency scanning | Preflight, `pip check`, and `npm audit` are used in RC1. | CI should include an approved Python vulnerability scanner and npm audit policy gate. |

## Post-RC-02 PHI/ePHI Export Hardening

Post-RC-02 added `backend/app/services/clinical_phi.py` as a lightweight sensitivity registry and profile redactor. The implementation is intentionally deterministic and limited to export-like/reporting/audit surfaces; it is not a full policy engine.

Hardened endpoints:

- `POST /api/clinical/reports/analytics-exports/preview`
- `POST /api/clinical/reports/analytics-exports`
- `POST /api/clinical/quality/compliance-exports/preview`
- `POST /api/clinical/quality/compliance-exports`
- `GET /api/clinical/quality/audit-evidence`
- `GET /api/clinical/reports/audit-activity`

Implemented profiles:

- `aggregate_safe`
- `internal_detail`
- `compliance_evidence`
- `external_safe`
- `audit_metadata`

Generic foundation commit hardening:

- `POST /api/clinical/workflows/commit` now requires an internal authenticated user with `clinical_admin.manage` or `system.admin`.
- External partner/supplier users are rejected even if they can reach the route.
- Module-specific commit endpoints remain the preferred path for real clinical workflows.

## Post-RC-03 Production Startup Gates

Post-RC-03 adds `backend/app/services/production_security_gates.py` and wires it into `backend/app/main.py`. Production-like startup now fails closed before the application opens traffic when critical security, audit, export, auth, or database defaults are unsafe.

Production-like values are `prod`, `production`, `stage`, and `staging` from `APP_ENV`, `ENVIRONMENT`, or `CLINICAL_ENV`.

The gate blocks:

- default or missing `SECRET_KEY` and `ENCRYPTION_KEY`;
- insecure cookie settings;
- wildcard or localhost CORS origins;
- `DEBUG=true` and reload/dev startup modes;
- missing, SQLite, non-PostgreSQL, or localhost `DATABASE_URL`;
- JSON-only workflow audit storage;
- unsafe default export profiles or disabled PHI/ePHI redaction;
- broadly enabled generic foundation commit;
- disabled authentication, demo auth bypass, demo user mode, or predictable MFA bypass code.

Local/dev mode returns warnings instead of raising, and `scripts/preflight_check.py` reports the warning inventory without requiring production secrets.

Reference: `docs/clinical-production-security-gates.md`.

## Post-RC-04 Route Drift And Small-Cell Suppression

Post-RC-04 adds `tests/test_clinical_route_permission_drift.py`, which enumerates registered FastAPI routes under `/api/clinical` and verifies sensitive routes remain documented in `docs/clinical-api-inventory.md` and classified in the RBAC model.

Route category tokens include:

- `public_or_health`
- `internal_read`
- `internal_mutation`
- `clinical_admin`
- `compliance_export`
- `analytics_export`
- `audit_evidence`
- `external_partner_denied`
- `generic_foundation_restricted`

Post-RC-04 also adds `backend/app/services/clinical_reporting_privacy.py` for deterministic small-cell suppression. For `aggregate_safe` and `external_safe` report/export profiles, nonzero count cells below 5 are replaced with suppression metadata before responses or export row-count contracts are returned. Authorized `internal_detail` usage remains visible for operational review.

## Post-RC-06 Object/WORM Audit Mirror Foundation

Post-RC-06 adds `backend/app/services/clinical_audit_mirror.py` and migration `202606130002_clinical_audit_worm_mirror.py`.

Implemented:

- append-only `operational.clinical_workflow_audit_mirror_events`;
- disabled mode by default;
- local filesystem mirror simulation for deterministic development/testing;
- future object-storage provider placeholders without network calls;
- SHA-256 checksum over canonical redacted audit payloads;
- optional versus required mirror failure policy;
- replay helper for DB audit rows without successful mirror attempts;
- production gate checks when `AUDIT_OBJECT_MIRROR_REQUIRED=true`.

Not implemented:

- Azure/AWS/GCP SDK integration;
- provider-side immutable retention or legal hold creation;
- real cryptographic signing;
- external evidence delivery.

## Post-RC-07 WORM Provider Readiness

Post-RC-07 adds `backend/app/services/clinical_audit_manifest.py` and migration `202606130003_clinical_audit_worm_manifests.py`.

Implemented:

- deterministic signed manifest foundation over successful mirror events;
- append-only `operational.clinical_workflow_audit_mirror_manifests`;
- checksum-placeholder signature metadata without requiring real signing keys;
- local simulation checksum verification for mirrored payloads;
- manifest/object URI and checksum mismatch detection;
- read-only recovery drill summary comparing DB audit rows to mirror records;
- production startup gate checks for required retention policy, legal hold reference, manifest policy, and signature key reference.

Not implemented:

- real Azure/AWS/GCP object listing or checksum readback;
- provider-side immutable retention or legal-hold enforcement;
- real cryptographic signing or external key management;
- automated restore, delete, or production audit mutation.

## Known Findings

| Finding | Severity | Evidence | RC1 disposition | Remediation |
| --- | --- | --- | --- | --- |
| Vite/esbuild advisories from `npm audit` | High | RC1 `npm audit --audit-level=high` reported two high-severity advisories and recommended a Vite 8 major upgrade. | Resolved in RC2 with bounded Vite 8 / React plugin 6 upgrade. | Continue to run `npm audit --audit-level=high` in release validation. |
| Production defaults are fail-open if not overridden | High | `SECRET_KEY`, `COOKIE_SECURE=false`, `MFA_DEV_BYPASS_CODE=000000`, local CORS/database defaults, and optional encryption keys exist as defaults/examples. | Resolved in Post-RC-03 with production-like startup gates. | Keep deployment settings aligned to `docs/clinical-production-security-gates.md`. |
| Workflow audit remains filesystem-backed | High | `metadata/workflow_operations.json` full-file append pattern. | Resolved by Post-RC-01 DB-backed append-only audit storage with JSON mirror/fallback; Post-RC-06 adds WORM mirror foundation; Post-RC-07 adds manifest and recovery drill foundations. | Add real provider SDK integration, retention policy enforcement, legal hold automation, and real signature controls before production evidence immutability signoff. |
| Generic foundation workflow commit lacks user auth | Medium | `/api/clinical/workflows/commit` requires confirmation header but does not require an authenticated user. | Resolved in Post-RC-02. | Continue to prefer module-specific commit endpoints and keep generic commit admin-only. |
| Report audit activity is available through broad report-read access | Medium | `/api/clinical/reports/audit-activity` uses report read guard. | Documented as minimum-necessary review item. | RC2: split audit activity access behind `audit.review` or a dedicated audit reporting permission. |
| No repository-native Python vulnerability scanner | Medium | `pyproject.toml` dev extras include pytest/httpx/ruff only. | Documented. | RC2: add approved scanner to CI after dependency policy is agreed. |
| Route-permission drift tests were missing | Medium | New clinical routes could be added without matching inventory/RBAC docs. | Resolved in Post-RC-04 with live FastAPI route drift tests for sensitive routes. | Keep docs and category tests updated as routes are added. |
| Small aggregate cohorts could disclose re-identification risk | Medium | Report/export counts previously returned visible nonzero values below 5. | Resolved for aggregate report/export count cells in Post-RC-04. | Review threshold with compliance owners before external analytics sharing. |

## Remediation Plan

1. Keep the Post-RC-03 production startup gate enabled and expand it as new production-only flags are introduced.
2. Keep frontend dependency audit in release validation after the RC2 Vite 8 remediation.
3. Configure real object-storage/WORM provider integration for workflow audit evidence if immutable off-database evidence is required.
4. Split report audit activity and export metadata permissions where compliance owners require least-privilege separation.
5. Add CI-visible vulnerability scanning for Python and frontend dependencies using approved tooling.
6. Add centralized UI field policy and production policy signoff before external delivery.
7. Keep the Post-RC-04 route drift and small-cell suppression tests in release validation.
8. Keep signed manifest and recovery drill evidence in production readiness review once provider integration is approved.
