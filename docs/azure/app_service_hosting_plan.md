# Azure App Service Hosting Plan

## Target

Host the Clinical Donor Platform as the Clinical app in the teemails portfolio without Docker, uv, or Kubernetes.

Preferred path:

- Azure App Service Linux, Python 3.12 runtime
- FastAPI serves API routes and the built React/Vite frontend from `frontend/dist`
- Azure Database for PostgreSQL Flexible Server for persistent hosted data
- App Service application settings for secrets/config
- Optional Application Insights for request/error telemetry
- Power BI Service hosts future analytics at `teemails.com/analytics`
- Cloudflare or Azure edge routing handled later by the portfolio routing plan

## Runtime Shape

```text
Azure App Service
  public port: FastAPI
  static frontend: React/Vite build served by FastAPI
  database: Azure Database for PostgreSQL

Power BI Service
  future analytics route: teemails.com/analytics
```

The startup helper `scripts/start_app_service.py` starts one FastAPI process on `$PORT`. Streamlit is not part of the target hosting architecture.

## Build/Startup Commands

Build command:

```text
python -m pip install --upgrade pip && python -m pip install -r requirements.txt && cd frontend && npm install && npm run build
```

Startup command:

```text
python scripts/start_app_service.py
```

Check command:

```text
python scripts/start_app_service.py --check
```

## Database

Use PostgreSQL only after explicit Azure provisioning approval. Recommended initial settings:

- PostgreSQL Flexible Server
- Private or public access chosen deliberately based on cost and simplicity
- TLS required
- Separate database for Clinical app
- Connection string stored only in App Service application settings

## Logging And Telemetry

Initial minimum:

- App Service log stream
- Application logs enabled with short retention

Optional:

- Application Insights workspace-based component
- Shared Log Analytics workspace with ingestion cap

## Portfolio Routing

Desired future public path:

```text
https://teemails.com/Clinical
```

Path-based routing should be implemented at Cloudflare Worker, Azure Front Door, or a portfolio gateway. The Clinical app itself should be tested for operation behind a path prefix before production cutover.

Analytics route:

```text
https://teemails.com/analytics
```

The analytics route should point to Power BI Service links or secure embedded Power BI reports after the downstream Snowflake/dbt platform exists. This Clinical repo should not host production analytics dashboards.

## No-Provisioning Boundary

This document is a plan only. Do not run:

```powershell
az group create
az appservice plan create
az webapp create
az postgres flexible-server create
az deployment group create
az resource delete
az provider register
```
