# Legacy Production Deployment Notes

This file previously documented a Docker Compose and Streamlit production path. That path is obsolete for the teemails portfolio target.

Current target:

```text
React/Vite operational frontend
  -> FastAPI backend on Azure App Service
  -> Azure Database for PostgreSQL
  -> downstream Snowflake/dbt/Power BI analytics later
```

Use these current docs instead:

- `docs/azure/app_service_hosting_plan.md`
- `docs/azure/app_settings_reference.md`
- `docs/azure/final_azure_deployment_execution_plan.md`
- `docs/architecture/streamlit_removal_plan.md`
- `docs/architecture/powerbi_analytics_strategy.md`

Do not use Docker, uv, Kubernetes, or the former Streamlit deployment path for Azure hosting.
