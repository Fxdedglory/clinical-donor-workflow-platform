# Clinical Donor Screening & Quality Workflow Platform

Enterprise-style healthcare operations platform for donor intake, governed AI-assisted donor screening, role-centered operational workspaces, RBAC-secured workflow orchestration, audit trails, QMS/change control, SOP training, vendor SLA monitoring, notification routing, escalations, AI governance, and operational intelligence dashboards.

Repository: `github.com/Fxdedglory/clinical-donor-workflow-platform`

## Project Overview

This project simulates internal enterprise healthcare software rather than a portfolio CRUD app. Donor records enter role-owned operational queues, rule-based decision support flags clinical risk, workflow tasks are routed through a state machine, escalations are created for overdue work, notifications link users back to assigned work, and regulated activities are traceable through audit logs.

The latest upgrade adds a Business Technology Analyst workspace for enterprise AI governance and workflow intelligence. AI risk logic is now database-governed, explainable, auditable, human-reviewable, and visible through heatmaps, Sankey flow analysis, override trends, SLA prediction validation, escalation matrices, and a rule simulation sandbox.

Resume themes demonstrated:

- Enterprise healthcare workflow systems analysis
- Role-centered operational workspace architecture
- Regulated operational workflow design
- RBAC security architecture with JWT authentication
- Governed AI-assisted clinical decision support concepts
- Explainability, human override tracking, and AI audit review
- Workflow intelligence, bottleneck analysis, and operational optimization
- QMS/change control, SOP training, CAPA, and auditability
- Vendor SLA operations and escalation handling
- Administrative workflow ownership and operational dashboards

## Architecture

```text
Streamlit role-centered operations console
        |
        v
FastAPI REST API -- JWT/RBAC dependencies
        |
        +-- Auth, users, roles, permissions
        +-- Role workspace engine and workspace configuration
        +-- Donor intake and clinical review workflow
        +-- Database-governed AI screening and explainability engine
        +-- AI governance, override tracking, and workflow intelligence
        +-- Workflow task engine
        +-- Notification bell and workflow alert routing
        +-- Workflow state machine and transition rules
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
- `operational.role_workspace_config`
- `operational.role_navigation_config`
- `operational.role_dashboard_widget`
- `operational.workflow_state_machine`
- `operational.workflow_transition_rule`
- `operational.workflow_assignment_rule`
- `operational.fact_workflow_task`
- `operational.fact_notification`
- `operational.fact_escalation_event`
- `operational.fact_sop_training_assignment`
- `operational.fact_training_completion`
- `operational.fact_audit_log`
- `operational.dim_ai_risk_rule`
- `operational.dim_ai_model_version`
- `operational.fact_ai_decision`
- `operational.fact_ai_override_event`
- `operational.fact_workflow_timeline_event`

Clinical, QMS, and vendor tables:

- `operational.fact_donor_review`
- `operational.dim_sop`
- `operational.fact_change_control`
- `operational.dim_vendor`
- `operational.fact_vendor_incident`
- `operational.dim_risk_category`

## Features

- JWT login, logout, token refresh, session expiration, password hashing, and protected routes
- Seven enterprise roles: System Administrator, Donor Intake Coordinator, Clinical Reviewer, Quality Assurance Specialist, Vendor Operations Analyst, Operations Manager, Business Technology Analyst
- Role-permission bridge for route-level authorization
- Dynamic workspace engine that generates navigation, widgets, KPIs, queues, workbench columns, and task actions from role metadata
- Business Technology Analyst workspace for AI risk dashboarding, workflow intelligence, AI governance, risk rule configuration, escalation analytics, AI audit review, and operational trends
- Database-driven AI risk rules with active/inactive status, condition operator, score delta, severity, and auto-escalation governance
- AI explainability panel showing triggered rules, score contributions, escalation reasons, workflow impact, confidence level, and historical comparisons
- Human-in-the-loop override tracking with override reason, reviewer, before/after decision, notification routing, and workflow timeline events
- Operational intelligence visualizations: risk distribution heatmap, workflow bottleneck Sankey diagram, human override trend, SLA prediction accuracy chart, escalation root cause matrix, and workflow queue heatmap
- Rule simulation sandbox for previewing risk threshold and escalation impact without changing production workflows
- System Administrator governance workspace with admin-only role, workspace, workflow, audit, system health, and integration surfaces
- Admin workspace preview mode for inspecting operational role workspaces without making admin a queue participant
- User administration surface for create, disable, password reset, and role assignment workflows
- Workflow task engine with owner, role, priority, status, workflow state, queue name, due date, related record, and escalation level
- Workflow transition engine for intake-to-clinical, clinical-to-QA, QA approval/rejection, vendor escalation, and operations-manager routing
- Top-right notification bell with unread counts, priority indicators, target record metadata, and mark-as-read workflow
- Escalation engine for overdue donor review, SLA, and QMS tasks
- SOP training assignment and acknowledgement tracking
- Role responsibility center with job descriptions, assigned workflows, and operational KPIs
- Enterprise operations, workforce, compliance, vendor, donor, and audit dashboards
- Expanded audit trail with login activity, workflow changes, permission/user changes, escalation events, and IP address fields
- Faker-powered demo data for donors, tasks, escalations, SLA incidents, SOP revisions, training assignments, notifications, and audit events
- Seeded AI governance data for risk rules, model versioning, AI decisions, override events, and workflow timeline traces

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
- `analyst` - Business Technology Analyst

## Screenshots

Design concept used for the original dashboard direction:

![Dashboard concept](docs/screenshots/concept-dashboard.png)

Rendered role-centered workspaces:

![Admin governance workspace](docs/screenshots/workspace-admin-governance.png)

![Clinical workspace preview](docs/screenshots/workspace-clinical.png)

![AI governance workspace](docs/screenshots/workspace-ai-governance.png)

![Mobile AI governance workspace](docs/screenshots/workspace-ai-governance-mobile.png)

![Mobile intake workspace](docs/screenshots/workspace-intake-mobile.png)

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

1. Sign in as `sysadmin` and confirm the default workspace is Platform Governance, not an operational donor or vendor queue.
2. Use Workspace Mode to preview Clinical Reviewer, Donor Intake Coordinator, QA, Vendor Ops, Business Technology Analyst, or Operations Manager workspaces.
3. Open Workspace Configuration to review role navigation, widget assignment, notification types, and workbench columns.
4. Sign in as `intake`, create a draft donor intake, and route a task with `submit_to_clinical_review`.
5. Sign in as `clinical` and confirm the new clinical task appears in the Clinical Review Workbench.
6. Use a clinical action such as Request QA Review, Escalate Case, Approve Donor, or Reject Donor.
7. Sign in as `qa` to review investigations, CAPA queue, deviations, and SOP compliance.
8. Sign in as `vendorops` to review SLA monitor, incident queue, and vendor escalations.
9. Sign in as `opsmanager` to review enterprise backlog, workforce load, escalation center, and queue management.
10. Sign in as `analyst` to review AI governance metrics, workflow bottleneck visualizations, rule simulation, AI audit traces, and human override trends.

## Healthcare/QMS Concepts

- **Clinical screening:** Donor review combines structured intake data, clinical notes, risk flags, risk score, reviewer decision, and exception escalation.
- **AI governance:** The risk engine is transparent, database-governed, explainable, auditable, and owned by the Business Technology Analyst without source-code edits.
- **Decision support:** The risk engine recommends actions without replacing clinical judgment; reviewer overrides are captured as governed AI lifecycle events.
- **Role immersion:** Each role loads a department-specific workspace with its own navigation, KPIs, widgets, queue columns, workflow actions, and notifications.
- **Workflow ownership:** Major operational events create tasks with owners, due dates, priority, workflow state, queue name, and escalation paths.
- **Workflow routing:** State-machine transitions route work from Intake to Clinical Review to QA and Operations Management while creating tasks, notifications, and audit events.
- **Workflow intelligence:** Queue heatmaps, bottleneck flow analysis, SLA prediction validation, escalation matrices, and operational recommendations support process optimization.
- **Audit trail:** Login, logout, donor decisions, workflow changes, user changes, training completion, and escalations are logged with before/after values.
- **QMS workflow:** Change requests include SOP linkage, risk level, approval status, CAPA requirement, due dates, and investigation notes.
- **SOP training:** SOP revisions can be assigned to roles or users and tracked through acknowledgement status and overdue training.
- **Vendor governance:** Vendor incidents track uptime, ticket aging, SLA breach status, impact, and operational response.

## API Endpoint Groups

- `/api/auth`
- `/api/admin`
- `/api/workspaces`
- `/api/donors`
- `/api/reviews`
- `/api/risk-analysis`
- `/api/ai-governance`
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
- Local LLM or OpenAI abstraction layer for governed clinical note summarization
- AI drift scoring with model performance thresholds and approval workflow
- Approval-chain designer for QMS and donor exceptions
- Email, Teams, Slack, and SMS notification adapters
- Power BI export or semantic model integration
- Azure deployment path
- SharePoint document-control integration
- Deeper non-conformance and CAPA lifecycle expansion
