# Clinical Deployment Package Manifest

Task: `CLINICAL-DEPLOY-01`

Release baseline: `8e41b07 Add clinical deployment integration inventory`

Preferred deployment option: single Azure App Service-style application serving FastAPI plus the built React frontend from the same host.

Recommended public URL: `https://clinical.teemails.com`

## Runtime Entry

```powershell
python scripts/start_app_service.py
```

The hosting platform should inject `$PORT`. `scripts/start_app_service.py` defaults to `8000` for local dry runs, sets `backend/` on `PYTHONPATH`, and starts `app.main:app` with Uvicorn on `0.0.0.0`.

Startup readiness check:

```powershell
python scripts/start_app_service.py --check
```

## Required Runtime Files And Directories

| Path | Purpose |
| --- | --- |
| `backend/app/` | FastAPI application, clinical routers, services, schemas, security gates, static frontend serving. |
| `scripts/start_app_service.py` | Production-style startup entry point and dry-run startup check. |
| `scripts/preflight_check.py` | Local release validation and configuration preflight. |
| `alembic.ini` | Alembic command configuration. |
| `database/migrations/` | Database migration chain; current head expected at `202606130003 (head)`. |
| `requirements.txt` | Python runtime dependency source. |
| `frontend/dist/index.html` | Built React SPA entry point for `SERVE_FRONTEND=true`. |
| `frontend/dist/assets/` | Built Vite JavaScript/CSS/static assets. |
| `docs/clinical-production-env-template.md` | Placeholder-only production settings checklist for deployment configuration. |
| `docs/clinical-deployment-env-vars.md` | Full environment variable inventory from deployment planning. |
| `docs/clinical-production-security-gates.md` | Fail-closed production safety gate reference. |
| `docs/clinical-site-integration-manifest.json` | Site-wide integration handoff manifest; do not treat it as a deployable secret. |

## Build Artifacts

Frontend build command:

```powershell
cd frontend
npm run build
```

Expected artifact shape:

- `frontend/dist/index.html` exists.
- `frontend/dist/assets/` contains hashed `.js` and `.css` files from Vite.
- The built frontend must not be committed unless the Product Owner explicitly approves a generated artifact commit.
- `SERVE_FRONTEND=true` and `FRONTEND_DIST_DIR=frontend/dist` allow FastAPI to serve `/`, `/assets/...`, and SPA routes such as `/clinical/dashboard`.

## Exclusions

Do not include the following in the production runtime package unless a later approved packaging process says otherwise:

- `backend/app/cli.py` dirty local changes; this file is protected and was not touched for DEPLOY-01.
- `.env`, `.env.*`, local credential files, real secrets, inline provider keys, or personal developer settings.
- `.venv/`, `venv/`, `node_modules/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`.
- `frontend/dist/` in Git history; include it only as a deployment build artifact.
- `data/generated/`, `data/exports/`, `data/backups/`, `datalake/`, `data/datalake/`, `data/lake/`, `data/synthetic/`, `data/monitoring/`.
- `logs/`, `*.log`, local dry-run stdout/stderr captures.
- `metadata/visual_audit/`, `metadata/production_evidence/`, screenshots, QA captures, generated evidence bundles, and local dry-run artifacts.
- SQLite/database files: `*.sqlite`, `*.sqlite3`, `*.db`.
- Demo seed outputs or local demo user material. `scripts/seed_clinical_demo_data.py` remains local/non-prod only.

## Database And Migrations

- Production `DATABASE_URL` must be PostgreSQL. SQLite is blocked by production gates.
- Run Alembic from a controlled deployment shell or job after backup and before production traffic is enabled.
- Current expected migration head: `202606130003 (head)`.
- Do not create broad clinical database migrations for DEPLOY-01.

## Health Checks

| Endpoint | Expected use |
| --- | --- |
| `/api/health` | Lightweight API startup health JSON. |
| `/health` | API health JSON, or frontend index when the client explicitly accepts HTML and `SERVE_FRONTEND=true`. |
| `/api/monitoring/health` | Database-aware monitoring health; use after the PostgreSQL target is configured. |
| `/clinical/dashboard` | SPA fallback check for built frontend routing. |

## Release Notes

- DEPLOY-01 packaging is documentation and dry-run validation only.
- No cloud resources, DNS changes, Docker, Kubernetes, live Azure tests, or real Azure credentials are required.
- `backend/app/cli.py` is the only accepted dirty tracked file in the local working tree and must remain unstaged.
