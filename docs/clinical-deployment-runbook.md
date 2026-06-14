# Clinical Deployment Runbook

Task: `CLINICAL-DEPLOY-00`

Release baseline: `f7d186f Finalize clinical frontend QA polish`

This runbook is a deployment planning handoff. It does not authorize production deployment, cloud resource creation, DNS changes, Docker, Kubernetes, or clinical workflow behavior changes.

## Current Deployment Inventory

| Area | Inventory result |
| --- | --- |
| Backend framework | FastAPI in `backend/app/main.py` |
| Frontend framework | React/Vite under `frontend/` |
| Frontend build command | `cd frontend; npm run build` |
| Backend start command | `python scripts/start_app_service.py` |
| Startup check | `python scripts/start_app_service.py --check` |
| Production port behavior | `scripts/start_app_service.py` reads `$PORT`, defaulting to `8000`, and runs Uvicorn on `0.0.0.0` |
| Static serving | FastAPI serves `frontend/dist` when `SERVE_FRONTEND=true` and `frontend/dist/index.html` exists |
| Separate frontend required | No for Option 1; yes only if Option 2 is selected |
| Health endpoints | `/health`, `/api/health`, `/api/monitoring/health` |
| Clinical status endpoints | `/api/clinical/status`, `/api/clinical/modules` |
| Migration command | `python -m alembic upgrade head` |
| Migration head check | `python -m alembic heads` |
| Local demo seed command | `python scripts/seed_clinical_demo_data.py` |
| Legacy broad seed command | `python -m app.cli seed --records 1200 --seed 42`; do not touch `backend/app/cli.py` during this sprint |
| Database type | PostgreSQL required |
| SQLite production status | Disallowed by production security gate |
| WORM/Key Vault live tests | Skipped by default; require explicit approval and environment flags |
| Target architecture | No Docker, no uv, no Kubernetes; managed Python host plus PostgreSQL |

## Pre-Deployment Checklist

1. Confirm deployment commit and branch.
2. Confirm `git status --short` has no unexpected release files.
3. Confirm `backend/app/cli.py` dirty local changes are not staged or included unless separately approved.
4. Confirm hosting option: single App Service-style host or split frontend/backend.
5. Confirm public URL decision: recommended `clinical.teemails.com`.
6. Confirm target PostgreSQL database is provisioned and backed up.
7. Confirm production app settings are configured from `docs/clinical-production-env-template.md` and checked against `docs/clinical-deployment-env-vars.md`.
8. Confirm generated `SECRET_KEY`, `ENCRYPTION_KEY`, and `DATABASE_URL` are stored outside Git.
9. Confirm production `CORS_ORIGINS` has no wildcard, localhost, or loopback.
10. Confirm `COOKIE_SECURE=true`.
11. Confirm WORM/Key Vault live validation status is explicitly accepted as pending or approved.
12. Confirm Product Owner, Security/Compliance, and Operations signoff owners.

## Build Steps

Python dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Startup check:

```powershell
python scripts/start_app_service.py --check
```

Start app:

```powershell
python scripts/start_app_service.py
```

Expected single-app runtime:

- `SERVE_FRONTEND=true`
- `FRONTEND_DIST_DIR=frontend/dist`
- FastAPI serves React routes and `/api/...` from one host.

## Migration Steps

1. Confirm target database backup and rollback point.
2. Confirm Alembic can connect to the target `DATABASE_URL`.
3. Record current revision:

   ```powershell
   python -m alembic current
   ```

4. Record head:

   ```powershell
   python -m alembic heads
   ```

5. Apply migrations:

   ```powershell
   python -m alembic upgrade head
   ```

6. Confirm the clinical sprint migrations and Post-RC audit migrations from `docs/clinical-migration-runbook.md` are applied.
7. Do not run destructive downgrade after real workflow commits without explicit data-retention approval.

## Seed and Demo-Data Policy

Production:

- Do not seed synthetic demo users or demo patients into production with real users unless Product Owner and Operations explicitly approve a controlled demo environment.
- Do not run `scripts/seed_clinical_demo_data.py` against production.
- Do not copy local `.env` values into production.

Non-production/demo:

```powershell
$env:PYTHONPATH = "backend"
$env:DATABASE_URL = "postgresql+psycopg://clinical_admin@127.0.0.1:55432/clinical_donor_workflow"
python scripts/seed_clinical_demo_data.py
```

The deterministic local demo user is `clinical_demo`; it is not a production account policy.

## Production Security Gate Check

Local/dev settings produce warning inventory instead of hard failure:

```powershell
python scripts/preflight_check.py
python scripts/start_app_service.py --check
```

Production-like settings fail closed when unsafe values are present. The gate blocks:

- Placeholder or missing `SECRET_KEY`
- Missing or unsafe `ENCRYPTION_KEY`
- `COOKIE_SECURE=false`
- Unsafe `COOKIE_SAMESITE`
- Wildcard, localhost, or loopback `CORS_ORIGINS`
- `DEBUG=true`
- Reload/dev startup modes
- Missing, SQLite, non-PostgreSQL, localhost, or loopback `DATABASE_URL`
- JSON-only workflow audit storage
- Disabled DB-backed audit requirement
- Unsafe WORM/manifest/Key Vault settings when required
- Unsafe export profiles
- `PHI_REDACTION_ENABLED=false`
- Generic foundation commit broadly enabled
- `AUTHENTICATION_ENABLED=false`
- Demo auth bypass enabled
- Predictable local `MFA_DEV_BYPASS_CODE`

## Smoke Test Endpoints

Minimum HTTP checks:

```text
GET /health
GET /api/health
GET /api/monitoring/health
GET /api/clinical/status
GET /api/clinical/modules
```

Expected:

- `/api/health` returns `status=ok` and environment metadata.
- `/api/monitoring/health` reports `status=ok` when PostgreSQL is reachable; `degraded` means app process is up but DB is not ready.
- `/clinical/dashboard` renders the React shell when frontend dist is served.

## Frontend Route Smoke Checklist

Open these routes after login:

- `/clinical/dashboard`
- `/clinical/patients`
- `/clinical/patients/PT-DEMO-001` or a real non-production patient ID
- `/clinical/scheduling`
- `/clinical/screening`
- `/clinical/encounters`
- `/clinical/orders`
- `/clinical/care-plans`
- `/clinical/billing`
- `/clinical/quality`
- `/clinical/reports`
- `/clinical/admin`

From FE-03 evidence, the local connected visual QA manifest under `metadata/visual_audit/clinical/fe03_final_frontend_qa/` reported 17 route checks, 21 screenshots, no route failures, no modal failures, and zero console events.

## Hosting Option 1: Single Managed App Serving FastAPI and Built React

Example target:

```text
Azure App Service Linux Python runtime
https://clinical.teemails.com
```

Required services:

- Managed Python web app host
- PostgreSQL 16-compatible managed database
- App settings or secret store
- Optional Application Insights or equivalent logging
- Optional Azure Blob WORM and Azure Key Vault after approval

Required build/start:

```powershell
cd frontend
npm install
npm run build
cd ..
python scripts/start_app_service.py
```

Required app settings:

- `APP_ENV=prod`
- `DATABASE_URL=<TLS PostgreSQL URL>`
- `SECRET_KEY=<generated>`
- `ENCRYPTION_KEY=<generated>`
- `APP_BASE_URL=https://clinical.teemails.com`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax`
- `CORS_ORIGINS=https://clinical.teemails.com,https://teemails.com,https://www.teemails.com`
- `STARTUP_MODE=fastapi_react`
- `SERVE_FRONTEND=true`
- `FRONTEND_DIST_DIR=frontend/dist`

Pros:

- Simplest deployment and rollback.
- Same-origin frontend/API avoids most CORS complexity.
- Static assets and SPA fallback are already implemented in FastAPI.
- Health endpoints and app shell share one host.
- Best match for current App Service docs.

Cons:

- Frontend and backend scale together.
- Static assets are served by the API process rather than a CDN.
- Any path-routing requirement still needs edge configuration.

Routing implications:

- App routes: `https://clinical.teemails.com/clinical/...`
- API routes: `https://clinical.teemails.com/api/...`
- Static assets: `https://clinical.teemails.com/assets/...`

Security implications:

- Use secure cookies and exact CORS origins.
- Keep Clinical backend as authorization source of truth.
- Do not enable wildcard CORS.

Migration approach:

- Run Alembic from deployment shell or controlled job after backup.
- Smoke `/api/monitoring/health` after migration.

Deployment validation:

```powershell
python scripts/start_app_service.py --check
python -m alembic heads
python -m alembic upgrade head
python scripts/preflight_check.py
python -m pytest
cd frontend
npm run build
```

## Hosting Option 2: Separate Frontend Static Host and Backend API Host

Example target:

```text
Frontend: https://clinical.teemails.com
Backend:  https://clinical-api.teemails.com
```

Required services:

- Static frontend host or CDN-backed site
- Managed Python API host
- PostgreSQL 16-compatible managed database
- App settings or secret store
- Optional Application Insights or equivalent logging
- Optional Azure Blob WORM and Azure Key Vault after approval

Required build/start:

```powershell
cd frontend
$env:VITE_API_BASE_URL = "https://clinical-api.teemails.com"
npm install
npm run build
```

Backend:

```powershell
python scripts/start_app_service.py
```

Required app settings:

- Backend: same production settings as Option 1, with `SERVE_FRONTEND=false` if frontend is not served by FastAPI.
- Backend: `CORS_ORIGINS=https://clinical.teemails.com,https://teemails.com,https://www.teemails.com`
- Frontend build: `VITE_API_BASE_URL=https://clinical-api.teemails.com`

Pros:

- Frontend assets can be CDN-optimized.
- Backend and frontend can scale independently.
- Frontend can fit a larger portfolio static-hosting strategy.

Cons:

- More CORS, cookie, and deployment coordination.
- Requires two deployable artifacts and two health surfaces.
- Production API URL is baked into the frontend build unless runtime config is added later.
- Browser session behavior must be tested across hosts.

Routing implications:

- Frontend routes live on frontend host.
- API calls go to backend host through `VITE_API_BASE_URL`.
- Backend `/health` and `/api/health` are not same-origin with frontend.

Security implications:

- Exact CORS origin list is mandatory.
- Cookies and Authorization headers require cross-origin testing.
- Session/cookie path and SameSite decisions need review.

Migration approach:

- Migrations run only against backend database target.
- Frontend can deploy before or after backend only if API compatibility is preserved.

Deployment validation:

```powershell
python scripts/start_app_service.py --check
python -m alembic heads
python -m alembic upgrade head
python scripts/preflight_check.py
python -m pytest
cd frontend
$env:VITE_API_BASE_URL = "https://clinical-api.teemails.com"
npm run build
npm audit --audit-level=high
```

## Known Local vs Production Differences

| Area | Local | Production expectation |
| --- | --- | --- |
| Database | Local PostgreSQL, often `127.0.0.1:55432` | Managed PostgreSQL with TLS |
| Frontend dev | Vite dev server on `5173` or alternate | Built assets under `frontend/dist` |
| API port | `8000` or local demo `8012` | Platform-injected `$PORT` |
| CORS | Includes localhost/Vite origins | Production origins only |
| Secrets | Local `.env`, placeholders | Hosted settings or secret store |
| Demo data | Synthetic seed allowed | Do not seed unless approved controlled demo environment |
| WORM/Key Vault | Dry-run readiness only | Live validation only after approval |

## Rollback Notes

1. Preserve database backup and deployment artifact before release.
2. Roll back application artifact before considering database changes.
3. Prefer point-in-time restore or backup restore over Alembic downgrade after real clinical writes.
4. Do not delete workflow audit rows, JSON compatibility mirror, object mirror metadata, or evidence manifests during rollback.
5. If split frontend/backend is used, roll back frontend and backend in a compatibility-preserving order.
6. Record rollback owner and decision in go-live signoff notes.

## Human Signoff Gates

Required before production traffic:

- Product Owner signoff
- Security/Compliance signoff
- Operations signoff
- Database backup/rollback approval
- DNS/domain approval
- Hosting target approval
- Production secret-setting approval
- WORM/Key Vault live validation decision recorded as approved, skipped, or deferred

## Azure WORM and Key Vault Status

Current status:

- Dry-run readiness and evidence docs exist.
- Live Azure WORM validation remains pending external resource and approval.
- Live Azure Key Vault signing validation remains pending external resource and approval.
- Do not set `AUDIT_OBJECT_MIRROR_AZURE_ENABLE_REAL_IO=true` or `AUDIT_MANIFEST_AZURE_KEY_VAULT_ENABLE_REAL_IO=true` until the approved live validation window.

Dry-run readiness commands:

```powershell
python scripts/check_azure_worm_readiness.py --json
python scripts/check_azure_key_vault_signing_readiness.py --json
```

These commands do not replace live provider validation.

## CLINICAL-DEPLOY-00 Validation Results

Validation was run locally after the planning docs were created:

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe scripts\preflight_check.py` | Passed; local warning inventory reported 5 production-hardening warnings because production secrets are intentionally absent. |
| `.\.venv\Scripts\python.exe -m pytest` | Passed: 294 passed, 7 skipped, 1 existing Starlette/httpx deprecation warning. |
| `cd frontend; npm run build` | Passed; Vite built production assets into `frontend/dist`. |
| `.\.venv\Scripts\python.exe -m pip check` | Passed: no broken requirements. |
| `cd frontend; npm audit --audit-level=high` | Passed: 0 vulnerabilities. |
| `.\.venv\Scripts\python.exe scripts\start_app_service.py --check` | Passed: `status=ok`; startup mode `fastapi_react`; `serve_frontend=True`; local production-hardening warnings remained 5. |
| `.\.venv\Scripts\python.exe -m alembic heads` | Passed: `202606130003 (head)`. |
| `git diff --check` | Passed: no whitespace errors; Git reported the existing LF-to-CRLF warning for protected `backend/app/cli.py`. |

## CLINICAL-DEPLOY-01 Packaging Dry-Run Artifacts

DEPLOY-01 adds deployment packaging and startup dry-run handoff material:

- `docs/clinical-production-env-template.md`: placeholder-only production settings template for the preferred single-host FastAPI plus React deployment.
- `docs/clinical-deployment-package-manifest.md`: runtime files, excluded generated/local artifacts, startup command, frontend artifact expectations, health checks, and migration head.
- `docs/clinical-deployment-dry-run-results.md`: Vite build result, startup check, same-host static serving smoke, production gate dry-run, migration head, blockers, and final validation results.
- `tests/test_clinical_deployment_packaging_docs.py`: focused guard tests for the manifest, env template, package manifest, dry-run results, and startup check.

## Recommendation

Next step should be `CLINICAL-DEPLOY-02` environment provisioning and blocker remediation: provision the PostgreSQL target, configure App Service-style production settings from the DEPLOY-01 template, approve DNS for `clinical.teemails.com`, and complete Product Owner, Security/Compliance, and Operations signoff. `SITE-WIDE-00` teemails integration planning can run in parallel using `docs/clinical-site-integration-manifest.json`, but it should not wire routes until the domain and hosting target are selected.
