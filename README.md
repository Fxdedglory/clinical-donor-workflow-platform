# Clinical Donor Screening & Quality Workflow Platform

Enterprise-style healthcare operations platform for donor intake, AI-assisted donor screening, RBAC-secured workflow orchestration, audit trails, QMS/change control, SOP training, vendor SLA monitoring, notifications, escalations, and operational dashboards.

Repository: `github.com/Fxdedglory/clinical-donor-workflow-platform`

## Project Overview

This project simulates internal enterprise healthcare software rather than a portfolio CRUD app. Donor records enter operational queues, rule-based decision support flags clinical risk, workflow tasks are assigned to role owners, escalations are created for overdue work, notifications alert users, and regulated activities are traceable through audit logs.

Resume themes demonstrated:

- Enterprise healthcare workflow systems analysis
- Regulated operational workflow design
- RBAC security architecture with JWT authentication
- AI-assisted clinical decision support concepts
- QMS/change control, SOP training, CAPA, and auditability
- Vendor SLA operations and escalation handling
- Administrative workflow ownership and operational dashboards

## Architecture

```text
Streamlit enterprise console
        |
        v
FastAPI REST API -- JWT/RBAC dependencies
        |
        +-- Auth, users, roles, permissions
        +-- Donor intake and clinical review workflow
        +-- Rule-based AI screening engine
        +-- Workflow task engine
        +-- Notification center
        +-- Escalation engine
        +-- QMS/change control and SOP training
        +-- Vendor SLA operations
        +-- Audit logging and dashboard aggregation
        |
        v
SQLAlchemy ORM -> PostgreSQL 16
        |
        +-- staging
        +-- operational
        +-- marts
```

Core enterprise tables:

- `operational.dim_user`
- `operational.dim_role`
- `operational.bridge_role_permission`
- `operational.dim_role_responsibility`
- `operational.fact_workflow_task`
- `operational.fact_notification`
- `operational.fact_escalation_event`
- `operational.fact_sop_training_assignment`
- `operational.fact_training_completion`
- `operational.fact_audit_log`

Clinical, QMS, and vendor tables:

- `operational.fact_donor_review`
- `operational.dim_sop`
- `operational.fact_change_control`
- `operational.dim_vendor`
- `operational.fact_vendor_incident`
- `operational.dim_risk_category`

## Features

- JWT login, logout, token refresh, session expiration, password hashing, and protected routes
- Six enterprise roles: System Administrator, Donor Intake Coordinator, Clinical Reviewer, Quality Assurance Specialist, Vendor Operations Analyst, Operations Manager
- Role-permission bridge for route-level authorization
- User management portal for create, disable, password reset, and role assignment workflows
- Workflow task engine with owner, role, priority, status, due date, related record, and escalation level
- In-app notification center with unread counts, priority indicators, and mark-as-read workflow
- Escalation engine for overdue donor review, SLA, and QMS tasks
- SOP training assignment and acknowledgement tracking
- Role responsibility center with job descriptions, assigned workflows, and operational KPIs
- Enterprise operations, workforce, compliance, vendor, donor, and audit dashboards
- Expanded audit trail with login activity, workflow changes, permission/user changes, escalation events, and IP address fields
- Faker-powered demo data for donors, tasks, escalations, SLA incidents, SOP revisions, training assignments, notifications, and audit events

## Demo Credentials

Default password for all demo users:

```text
ClinicalDemo!2026
```

Demo users:

- `sysadmin` - System Administrator
- `intake` - Donor Intake Coordinator
- `clinical` - Clinical Reviewer
- `qa` - Quality Assurance Specialist
- `vendorops` - Vendor Operations Analyst
- `opsmanager` - Operations Manager

## Screenshots

Design concept used for the original dashboard direction:

![Dashboard concept](docs/screenshots/concept-dashboard.png)

Rendered enterprise dashboard:

![Rendered dashboard](docs/screenshots/rendered-dashboard.png)

## Setup Instructions

### Run with Docker Compose

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit dashboard: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

The backend container runs Alembic migrations and seeds demo data on startup.

### Run Locally with uv

Start PostgreSQL first, then from the repository root:

```powershell
uv venv
uv pip install -r requirements.txt
$env:PYTHONPATH="backend"
$env:DATABASE_URL="postgresql+psycopg://clinical_admin:clinical_demo_password@localhost:5432/clinical_donor_workflow"
uv run alembic upgrade head
uv run python -m app.cli seed --records 1200
uv run uvicorn app.main:app --reload --app-dir backend
```

In a second terminal:

```powershell
$env:API_URL="http://localhost:8000"
uv run streamlit run frontend/app.py
```

## Demo Workflow

1. Sign in as `sysadmin` and review Enterprise Ops KPIs, escalated tasks, unread notifications, QMS workload, and vendor incidents.
2. Open Admin Portal to review users, roles, and workflow configuration assumptions.
3. Open Responsibility Center to inspect role job descriptions, assigned workflows, and KPIs.
4. Open Task Workbench and update a donor review, SLA investigation, or SOP deviation task.
5. Open Notifications and mark an assignment or escalation notice as read.
6. Sign in as `clinical` and confirm the user can access donor/task work but receives `403` for admin-only routes.
7. Open Donor Review, record a donor decision, then confirm Audit Logs and Task Workbench reflect the workflow event.
8. Open Compliance to review SOP training, QMS change control, CAPA flags, and audit activity.
9. Open Vendor SLA to review incidents, uptime, breach counts, and resolution metrics.

## Healthcare/QMS Concepts

- **Clinical screening:** Donor review combines structured intake data, clinical notes, risk flags, risk score, reviewer decision, and exception escalation.
- **Decision support:** The risk engine is transparent and auditable; it recommends actions without replacing clinical judgment.
- **Workflow ownership:** Major operational events create tasks with owners, due dates, priority, and escalation paths.
- **Audit trail:** Login, logout, donor decisions, workflow changes, user changes, training completion, and escalations are logged with before/after values.
- **QMS workflow:** Change requests include SOP linkage, risk level, approval status, CAPA requirement, due dates, and investigation notes.
- **SOP training:** SOP revisions can be assigned to roles or users and tracked through acknowledgement status and overdue training.
- **Vendor governance:** Vendor incidents track uptime, ticket aging, SLA breach status, impact, and operational response.

## API Endpoint Groups

- `/api/auth`
- `/api/admin`
- `/api/donors`
- `/api/reviews`
- `/api/risk-analysis`
- `/api/workflow-tasks`
- `/api/notifications`
- `/api/escalations`
- `/api/training`
- `/api/audit-logs`
- `/api/change-control`
- `/api/vendors`
- `/api/dashboard`
- `/api/enterprise-dashboard`

## Future Roadmap

- OCR/PDF ingestion for donor document packets
- Local LLM or OpenAI abstraction layer for clinical note summarization
- Configurable risk rule UI backed by persisted rules
- Approval-chain designer for QMS and donor exceptions
- Email, Teams, Slack, and SMS notification adapters
- Power BI export or semantic model integration
- Azure deployment path
- SharePoint document-control integration
- Deeper non-conformance and CAPA lifecycle expansion
