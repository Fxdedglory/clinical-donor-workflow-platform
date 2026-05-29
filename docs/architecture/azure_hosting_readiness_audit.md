# Azure Hosting Readiness Audit

Date: 2026-05-29

Mode: repository audit and no-provisioning implementation pass. No Azure resources were created, updated, deleted, deployed, or provisioned.

## Executive Summary

The Clinical Donor Platform is a mature FastAPI + Streamlit + SQLAlchemy/PostgreSQL workflow application with JWT/RBAC, partner portal scoping, QMS/CAPA, audit logging, workflow routing, vendor SLA monitoring, and rich seed data.

The main hosting blocker is not application capability; it is deployment packaging. The current repo still contains Docker Compose, Dockerfiles, `uv.lock`, and README/runbook instructions centered on Docker/uv. Those artifacts can remain as legacy/local references, but the Azure App Service path must use standard Python virtual environments, `pip install -r requirements.txt`, a custom startup command, and Azure Database for PostgreSQL.

## Existing Architecture

| Area | Current state |
|---|---|
| Backend framework | FastAPI in `backend/app/main.py` |
| Frontend framework | Streamlit in `frontend/app.py` and `frontend/views/*` |
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

uv artifacts present:

- `uv.lock`
- `[tool.uv]` section in `pyproject.toml`
- README local setup currently references `uv venv`, `uv pip`, and `uv run`

These are deployment blockers only if used for the Azure hosting path. They were not deleted in this pass. The no-Docker/no-uv App Service path is now documented separately.

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
| Data producer operations | Added DB-backed service, CLI, API controls, and admin UI surface |
| Run history/validation/export metadata | Added file-backed metadata under ignored `data/generated` and `data/exports` |
| Generated data ignored | Added `.gitignore` rules and `.gitkeep` placeholders |
| Python local execution | Blocked in current shell by Windows Store alias; documented in runbook |
| PostgreSQL availability | Still requires local or Azure PostgreSQL; no resource provisioned |
| Entra ID | Planned only, not implemented |

## GitHub Status At Audit Time

- Branch: `main`
- Remote: `https://github.com/Fxdedglory/clinical-donor-workflow-platform.git`
- Working tree was clean before this implementation pass.

## Bottom Line

The app can move toward Azure App Service without removing legacy Docker/uv artifacts. The recommended first hosted shape is Streamlit as the public App Service process and FastAPI as a localhost companion process started by `scripts/start_app_service.py`, backed by Azure Database for PostgreSQL when persistence is required.
