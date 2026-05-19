# Architecture

The upgraded platform is organized as enterprise workflow software:

```text
frontend/app.py
  Streamlit authenticated enterprise console

frontend/views
  Dashboards and workflow surfaces:
  enterprise ops, tasks, notifications, admin, compliance, donor review, vendor SLA

backend/app/auth
  Password hashing, JWT creation/validation, current user lookup, permission dependencies

backend/app/routes
  REST endpoint groups for auth, admin, donors, tasks, notifications, escalations,
  training, QMS, vendors, audit, and dashboards

backend/app/services
  Risk scoring, audit logging, role definitions, task creation, notification dispatch,
  escalation evaluation, dashboard aggregation, and demo seeding

backend/app/models
  SQLAlchemy models mapped to operational fact/dimension tables

database/migrations
  Alembic-managed schemas, tables, indexes, and mart views
```

## Request Flow

```text
Streamlit login form
  -> POST /api/auth/login
  -> JWT access token + refresh token
  -> Streamlit stores session token
  -> API helper sends Authorization: Bearer <token>
  -> FastAPI permission dependency checks role permissions
  -> route executes workflow service
  -> audit log records operational event
```

## Data Layers

- `staging`: reserved for future raw imports
- `operational`: source-of-truth workflow tables
- `marts`: dashboard and reporting views

## Enterprise Modules

- Authentication and RBAC
- Workflow task engine
- Notification center
- Administrator portal
- Escalation engine
- SOP training and acknowledgement
- Responsibility center
- Enterprise dashboards
- Expanded audit trail

