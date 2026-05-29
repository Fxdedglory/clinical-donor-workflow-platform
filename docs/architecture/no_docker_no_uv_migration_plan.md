# No-Docker / No-uv Migration Plan

## Goal

Provide a clean Azure App Service deployment path that does not rely on Docker, Docker Compose, uv, Kubernetes, AKS, Helm, or container orchestration.

## What Remains

Docker files remain as legacy references only. The frontend Dockerfile and Compose frontend service are obsolete because Streamlit is no longer part of the target architecture:

- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker/backend.Dockerfile`
- `docker/frontend.Dockerfile`
- `docker/nginx.conf`

uv files were removed from the active repo:

- `uv.lock` removed
- `[tool.uv]` removed from `pyproject.toml`

Use only `python -m venv` and `pip install -r requirements.txt`.

## Standard Local Python Path

Recommended Python:

- Python 3.12.x, 64-bit Windows installer from python.org
- Install for the current user or all users
- Enable `Add python.exe to PATH`
- Disable Microsoft Store aliases if `python --version` opens the Store prompt

Setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Run migrations and seed:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.cli seed --records 1200 --seed 42
```

## App Service Startup Strategy

The App Service path uses one public FastAPI process:

- FastAPI listens on `$PORT`
- FastAPI serves API routes under `/api`
- FastAPI serves the built React/Vite frontend from `frontend/dist`
- Analytics are delivered later through Power BI Service, not this app process

Startup helper:

```powershell
python scripts/start_app_service.py --check
python scripts/start_app_service.py
```

Azure startup command:

```text
python scripts/start_app_service.py
```

## Environment Variable Strategy

Use App Service application settings for runtime config:

- `DATABASE_URL`
- `SECRET_KEY`
- `ENCRYPTION_KEY`
- `APP_ENV`
- `APP_BASE_URL`
- `PORT`
- `SERVE_FRONTEND`
- `FRONTEND_DIST_DIR`
- `CORS_ORIGINS`
- email provider settings
- data producer settings

Do not commit `.env`, publishing profiles, database credentials, API keys, or Cloudflare tokens.

## Database Strategy

The app remains PostgreSQL-first. For Azure:

- Use Azure Database for PostgreSQL Flexible Server when persistent hosted state is approved.
- Run Alembic migrations during deployment validation or a controlled one-time admin command.
- Keep local tests independent of cloud resources where possible.

## Generated Data Policy

Generated producer metadata and exports are ignored by Git:

- `data/generated/*`
- `data/exports/*`
- `logs/*`

Only `.gitkeep` placeholders are tracked.

## Deletion Plan

Streamlit frontend files are removed in this pass and replaced by React/Vite. Before deleting Docker/uv artifacts later:

1. Confirm App Service path is working.
2. Confirm README/runbooks no longer depend on Docker/uv.
3. Confirm no CI workflow uses Docker/uv.
4. Remove files in a dedicated cleanup commit.
