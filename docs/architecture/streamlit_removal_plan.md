# Streamlit Removal Plan

Date: 2026-05-29

## Decision

Streamlit is removed from the long-term Clinical Donor Platform hosting strategy. The production target is now:

```text
React/Vite operational frontend
  -> FastAPI backend
  -> PostgreSQL operational source database
  -> downstream data platform later
  -> Snowflake
  -> dbt L1/L2/L3
  -> Power BI Service
  -> teemails.com/analytics
```

Analytics dashboards should not be maintained as Streamlit dashboards. Operational screens remain in the Clinical application. Analytics move to Power BI.

## Streamlit Touchpoints Found

| Area | Files / references | Disposition |
|---|---|---|
| Streamlit app shell | `frontend/app.py` | Remove from production path and replace with React/Vite shell. |
| Streamlit UI helpers | `frontend/components/*` | Remove; presentation-only code. |
| Streamlit pages | `frontend/views/*` | Remove from production path; business logic remains in FastAPI services/routes. |
| Python dependency | `requirements.txt`, `pyproject.toml` | Remove `streamlit`; remove UI-only `pandas`/`plotly` if not used by backend. |
| App Service startup | `scripts/start_app_service.py` | Replace two-process Streamlit+FastAPI startup with single FastAPI process. |
| README local run commands | `README.md` | Replace Streamlit run commands with React/Vite build/dev instructions. |
| Azure docs | `docs/azure/*` | Update to App Service hosting FastAPI + built React frontend. |
| Legacy Docker docs | `docs/PROD_DEPLOYMENT.md`, `docs/BACKUP_RECOVERY.md` | Mark as legacy/obsolete for the new target. |
| Docker frontend artifact | `docker/frontend.Dockerfile` and Compose frontend service | No longer a valid target; keep only as legacy unless a future cleanup deletes Docker artifacts. |

## Files Removed Or Replaced In This Refactor

The following Streamlit production UI files are removed and replaced by React/Vite files:

- `frontend/app.py`
- `frontend/components/*`
- `frontend/views/*`
- `frontend/pages/README.md`

Replacement files:

- `frontend/package.json`
- `frontend/index.html`
- `frontend/src/main.jsx`
- `frontend/src/App.jsx`
- `frontend/src/styles.css`

## Preserved Business Logic

No backend clinical workflow logic is removed. The following remain the source of operational behavior:

- FastAPI routers under `backend/app/routes`
- SQLAlchemy models under `backend/app/models`
- Workflow orchestration and functional route services under `backend/app/services`
- Data producer service under `backend/app/services/data_producer.py`
- Alembic migrations under `database/migrations`

## Follow-Up Work

- Expand React/Vite operational screens beyond the initial admin shell.
- Add route-level React pages for donor queue, partner portal, QMS, vendor SLA, documents, and audit review.
- Keep analytics out of the operational UI except summary links/status cards.
- Build Snowflake/dbt/Power BI analytics downstream in `E:\Data_Platform_Engineer_Cloud_Platform`, not in this repo.
