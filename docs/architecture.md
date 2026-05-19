# Architecture

The application uses a narrow, portfolio-friendly full-stack architecture:

```text
frontend/app.py
  Streamlit workflow console

backend/app/main.py
  FastAPI app and route registration

backend/app/routes
  REST endpoints for donors, reviews, risk analysis, audit, QMS, vendors, and dashboard metrics

backend/app/services
  Risk scoring, audit logging, dashboard aggregation, seed data

backend/app/models
  SQLAlchemy ORM models mapped to operational schema fact/dimension tables

database/migrations
  Alembic-managed PostgreSQL schemas, tables, indexes, and analytics views
```

The application deliberately separates:

- workflow transactions in `operational`
- reporting views in `marts`
- future raw import landing tables in `staging`

This mirrors how regulated healthcare platforms often separate intake, operational workflow, and reporting concerns.

