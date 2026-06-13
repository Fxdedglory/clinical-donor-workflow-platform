# Clinical Security Readiness

RC1 review date: 2026-06-13

RC2 update date: 2026-06-13

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
| `APP_ENV` | `dev` is acceptable locally. | Set to `prod` and use it as the operational signal for stricter deployment gates. |
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
| Audit storage | `metadata/workflow_operations.json` supports local evidence and testability. | Database-backed append-only audit storage plus object-storage mirroring is required before production signoff. |
| Export delivery | Clinical analytics/compliance exports store metadata and row-count contracts. | External warehouse/clearinghouse delivery remains out of scope until dedicated controls are implemented. |
| PHI masking | No full masking framework in RC1. | Role-aware masking/redaction and export minimum-necessary review are RC2+ items. |
| Dependency scanning | Preflight, `pip check`, and `npm audit` are used in RC1. | CI should include an approved Python vulnerability scanner and npm audit policy gate. |

## Known Findings

| Finding | Severity | Evidence | RC1 disposition | Remediation |
| --- | --- | --- | --- | --- |
| Vite/esbuild advisories from `npm audit` | High | RC1 `npm audit --audit-level=high` reported two high-severity advisories and recommended a Vite 8 major upgrade. | Resolved in RC2 with bounded Vite 8 / React plugin 6 upgrade. | Continue to run `npm audit --audit-level=high` in release validation. |
| Production defaults are fail-open if not overridden | High | `SECRET_KEY`, `COOKIE_SECURE=false`, `MFA_DEV_BYPASS_CODE=000000`, and optional encryption keys exist as defaults/examples. | Documented. No code gate added in RC1. | RC2: add startup validation that rejects unsafe defaults when `APP_ENV=prod`. |
| Workflow audit remains filesystem-backed | High | `metadata/workflow_operations.json` full-file append pattern. | Documented in audit durability plan. | RC2: implement database-backed append-only audit table and migration/backfill. |
| Generic foundation workflow commit lacks user auth | Medium | `/api/clinical/workflows/commit` requires confirmation header but does not require an authenticated user. | Documented as a gap. | RC2: either restrict to admin/test contexts or require authenticated clinical admin permission. |
| Report audit activity is available through broad report-read access | Medium | `/api/clinical/reports/audit-activity` uses report read guard. | Documented as minimum-necessary review item. | RC2: split audit activity access behind `audit.review` or a dedicated audit reporting permission. |
| No repository-native Python vulnerability scanner | Medium | `pyproject.toml` dev extras include pytest/httpx/ruff only. | Documented. | RC2: add approved scanner to CI after dependency policy is agreed. |

## Remediation Plan

1. Add a production startup safety check for `APP_ENV=prod` that rejects default `SECRET_KEY`, insecure cookie settings, predictable MFA bypass, and missing production encryption settings.
2. Keep frontend dependency audit in release validation after the RC2 Vite 8 remediation.
3. Add database-backed workflow operation audit storage with append-only database permissions and object-storage mirroring.
4. Split report audit activity and export metadata permissions where compliance owners require least-privilege separation.
5. Add CI-visible vulnerability scanning for Python and frontend dependencies using approved tooling.
6. Add PHI masking/redaction requirements to export and report workflows before external delivery.
