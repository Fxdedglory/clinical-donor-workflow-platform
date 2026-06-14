# Clinical Deployment Dry-Run Results

Task: `CLINICAL-DEPLOY-01`

Release baseline: `8e41b07 Add clinical deployment integration inventory`

Dry-run date: 2026-06-14

Scope: deployment packaging and startup validation only. No deploy, cloud resource creation, DNS change, Docker, Kubernetes, real credential use, live Azure test, or backend workflow logic change was performed.

## Dirty-File Guard

Initial guard commands:

```powershell
git status --short
git diff -- backend/app/cli.py
```

Result:

- `backend/app/cli.py` remained the only dirty tracked file before DEPLOY-01 edits.
- The existing diff was inspected and preserved.
- `backend/app/cli.py` was not modified, formatted, staged, or committed for DEPLOY-01.

## Commands Run

| Command | Result |
| --- | --- |
| `cd frontend; npm run build` | Passed. Vite built `frontend/dist/index.html`, `frontend/dist/assets/index-AQpG53Hw.js`, and `frontend/dist/assets/index-CxYjXdMF.css`. |
| `.\.venv\Scripts\python.exe scripts\start_app_service.py --check` | Passed. Reported `startup_mode=fastapi_react`, `port=8000`, `serve_frontend=True`, `frontend_dist_dir=frontend/dist`, `production_security_gate=passed`, `status=ok`. |
| Local startup smoke on `PORT=8037` with `SERVE_FRONTEND=true` | Passed. `scripts/start_app_service.py` started Uvicorn and served the built SPA. |
| `GET http://127.0.0.1:8037/api/health` | Passed. Returned JSON with `status=ok`, environment `dev`, and `startup_mode=fastapi_react`. |
| `GET http://127.0.0.1:8037/clinical/dashboard` with `Accept: text/html` | Passed. Returned HTTP 200 and the React root from `frontend/dist/index.html`. |
| `GET http://127.0.0.1:8037/health` with `Accept: text/html` | Passed. Returned HTTP 200 and the React root when HTML was requested. |
| `GET http://127.0.0.1:8037/assets/index-AQpG53Hw.js` | Passed. Returned HTTP 200 for a built Vite asset. |
| Production gate in-memory safe placeholder shape | Passed. `passed=True`, `production_like=True`, `environment=prod`. |
| Production gate in-memory unsafe local shape | Rejected as expected. Failure codes: `secret_key_unsafe`, `encryption_key_missing`, `cookie_secure_disabled`, `cors_wildcard`, `cors_local_origin`, `database_url_sqlite`, `mfa_dev_bypass_unsafe`. |
| `.\.venv\Scripts\python.exe -m alembic heads` | Passed. Reported `202606130003 (head)`. |

## Frontend Static Serving Verification

- `frontend/dist/index.html` exists after `npm run build`.
- `frontend/dist/assets/` contains hashed Vite JavaScript and CSS assets.
- `SERVE_FRONTEND=true` with `FRONTEND_DIST_DIR=frontend/dist` allows FastAPI to serve `/`, `/health` HTML responses, `/assets/...`, and SPA fallback routes such as `/clinical/dashboard`.
- API routes remain under `/api/...`; `/api/health` returned JSON during the same local startup smoke.

## Production Gate Dry-Run

The production gate was exercised with in-memory dictionaries only. No real credentials, PostgreSQL connection, Azure Blob operation, or Key Vault operation was attempted.

- A production-shaped placeholder config with PostgreSQL URL shape, secure cookies, production CORS, DB-backed audit mode, safe export defaults, PHI redaction enabled, auth enabled, and demo bypass disabled passed the gate.
- An unsafe local config with SQLite, placeholder secrets, insecure cookies, wildcard/local CORS, and predictable MFA bypass was rejected.

## Blockers

- Production PostgreSQL target is not provisioned and no production `DATABASE_URL` is available.
- Production `SECRET_KEY`, `ENCRYPTION_KEY`, backup encryption key, and provider credentials are not available by design.
- Product Owner, Security/Compliance, and Operations signoff remains pending.
- Live Azure WORM validation remains pending and was not run.
- Live Azure Key Vault signing validation remains pending and was not run.
- DNS for `clinical.teemails.com` is not configured by DEPLOY-01.

## Validation Summary

Full validation commands were run after this dry-run document and the focused packaging tests were added.

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed. Status `passed`; local warning inventory remained 5 production-hardening warnings because production secrets are intentionally absent. |
| `.\.venv\Scripts\python.exe -m pytest` | Passed: 299 passed, 7 skipped, 1 existing Starlette/httpx deprecation warning. |
| `cd frontend; npm run build` | Passed. Vite built production assets into `frontend/dist`. |
| `.\.venv\Scripts\python.exe -m pip check` | Passed: no broken requirements found. |
| `cd frontend; npm audit --audit-level=high` | Passed: 0 vulnerabilities. |
| `.\.venv\Scripts\python.exe scripts\start_app_service.py --check` | Passed. Reported `status=ok`, `serve_frontend=True`, and `frontend_dist_dir=frontend/dist`; local production-hardening warnings remained 5. |
| `.\.venv\Scripts\python.exe -m alembic heads` | Passed: `202606130003 (head)`. |
| `git diff --check` | Passed with line-ending normalization warnings only for protected `backend/app/cli.py` and updated `docs/clinical-deployment-runbook.md`; no whitespace errors. |

## Verdict

DEPLOY-01 dry-run verdict: packaging and startup path are ready for DEPLOY-02 environment provisioning, subject to final validation and the remaining external blockers above. The repo is not production-deployed by this task.
