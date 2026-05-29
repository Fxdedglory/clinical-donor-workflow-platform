# Azure Hosting Readiness Audit

Date: 2026-05-29

Mode: repository audit and no-provisioning implementation pass. No Azure resources were created, updated, deleted, deployed, or provisioned.

## Executive Summary

The Clinical Donor Platform is a mature FastAPI + SQLAlchemy/PostgreSQL workflow application with JWT/RBAC, partner portal scoping, QMS/CAPA, audit logging, workflow routing, vendor SLA monitoring, and rich seed data. The former Streamlit UI has been removed from the target architecture and replaced by a React/Vite operational shell.

The main hosting blocker is local runtime availability: this shell still only resolves Python to the Windows Store alias. PostgreSQL 13 and 16 services are installed but stopped. The Azure App Service path uses standard Python virtual environments, `pip install -r requirements.txt`, React/Vite build output, a FastAPI startup command, and Azure Database for PostgreSQL when hosted persistence is approved.

## Existing Architecture

| Area | Current state |
|---|---|
| Backend framework | FastAPI in `backend/app/main.py` |
| Frontend framework | React/Vite under `frontend/src`; FastAPI serves `frontend/dist` when built |
| ORM/database | SQLAlchemy models in `backend/app/models/entities.py`; Alembic migrations under `database/migrations` |
| Persistence target | PostgreSQL 16-oriented schema using `operational`, `staging`, and `marts` schemas |
| Auth/RBAC | JWT access/refresh tokens, route permissions, roles, MFA foundation, security audit logging |
| Partner portal | Organization-scoped partner users, submissions, complaints, documents, invitations, task responses |
| Demo data | `backend/app/cli.py seed` creates seeded donors, QMS, vendor, partner, workflow, audit, and AI governance data |
| API routes | `/api/auth`, `/api/admin`, `/api/dashboard`, `/api/donors`, `/api/reviews`, `/api/vendors`, `/api/partners`, `/api/suppliers`, `/api/workspaces`, `/api/routes`, and others |
| Health route | Existing `/health`; this pass adds `/api/health` |

## Docker And uv Findings

Docker artifacts present:

- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker/backend.Dockerfile`
- `docker/frontend.Dockerfile`
- `docker/nginx.conf`

uv artifacts:

- `uv.lock` was removed.
- `[tool.uv]` was removed from `pyproject.toml`.
- README local setup now uses `python -m venv` and `pip`.

These are deployment blockers only if used for the Azure hosting path. They remain legacy references and are not the target deployment mechanism.

## PostgreSQL Requirements

The current application requires PostgreSQL for full local operation because:

- Models use PostgreSQL-oriented schemas such as `operational`.
- Alembic migrations create and manage schema-level database objects.
- Existing seed logic writes directly through SQLAlchemy sessions.

For Azure, use Azure Database for PostgreSQL Flexible Server when persistent hosted data is needed. Local smoke tests can be deferred until a local PostgreSQL instance and Python 3.12 are available.

## Auth And Partner Access Model

Current security capabilities:

- Platform-native user accounts.
- JWT login, refresh, logout, and session records.
- Role-permission bridge with `system.admin` override.
- MFA foundation and dev bypass code.
- Partner/supplier external users scoped by `organization_id`.
- Security audit records for login, access denial, session, document access, and route access.

Future Azure hardening should add Microsoft Entra ID for internal users and a deliberate external partner access model. See `docs/security`.

## Secrets And Config Risks

`.env.example` contains local placeholder values, not real secrets. Risk areas to keep out of Git:

- real `SECRET_KEY`
- real `ENCRYPTION_KEY`
- real `DATABASE_URL`
- real SMTP/SendGrid/Mailgun keys
- Cloudflare tunnel/API tokens
- Azure service principal or publishing credentials

## Azure Readiness Gaps

| Gap | Status after this pass |
|---|---|
| No-Docker/no-uv run path | Added docs and `scripts/start_app_service.py` |
| App Service app settings reference | Added |
| Data producer operations | Added DB-backed service, CLI, API controls, and React admin surface |
| Run history/validation/export metadata | Added file-backed metadata under ignored `data/generated` and `data/exports` |
| Generated data ignored | Added `.gitignore` rules and `.gitkeep` placeholders |
| Python local execution | Blocked in current shell by Windows Store alias; documented in runbook |
| PostgreSQL availability | PostgreSQL services are installed but stopped; `psql.exe` found under PostgreSQL 16; no Azure resource provisioned |
| Entra ID | Planned only, not implemented |

## GitHub Status At Audit Time

- Branch: `main`
- Remote: `https://github.com/Fxdedglory/clinical-donor-workflow-platform.git`
- Working tree was clean before this implementation pass.

## Bottom Line

The app can move toward Azure App Service as a single FastAPI process serving API routes and built React assets. Streamlit is no longer part of the production target. Azure Database for PostgreSQL remains required for persistent hosted operation.
