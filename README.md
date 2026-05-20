# Clinical Donor Screening & Quality Workflow Platform

Enterprise-style healthcare operations platform for donor intake, governed AI-assisted donor screening, centralized workflow orchestration, function-first routing, master data records, decision routing, RBAC-secured transitions, audit trails, QMS/change control, SOP training, vendor SLA monitoring, actionable notifications, escalations, AI governance, and operational intelligence dashboards.

Repository: `github.com/Fxdedglory/clinical-donor-workflow-platform`

## Project Overview

This project simulates internal enterprise healthcare software rather than a portfolio CRUD app. Donor records enter role-owned operational queues, rule-based decision support flags clinical risk, workflow tasks are routed through a state machine, escalations are created for overdue work, notifications link users back to assigned work, and regulated activities are traceable through audit logs.

The latest upgrade adds a function-first enterprise route layer. Routes now represent business functions and master data entities such as `/donor/{id}`, `/review/{id}`, `/capa/{id}`, `/task/{id}`, and `/workflow-intelligence`; the logged-in role determines visible widgets, actions, and operational context inside the same route. Workspace buttons now trigger authorized workflow transitions instead of directly modifying records; the orchestration engine validates role, state, decision matrices, AI governance requirements, SLA routing, notifications, audit events, transition history, and task creation.

Resume themes demonstrated:

- Enterprise healthcare workflow systems analysis
- Role-centered operational workspace architecture
- Regulated operational workflow design
- RBAC security architecture with JWT authentication
- Governed AI-assisted clinical decision support concepts
- Explainability, human override tracking, and AI audit review
- Workflow intelligence, bottleneck analysis, and operational optimization
- Enterprise decision matrices and centralized state orchestration
- Workflow-linked notifications with deep-link routing
- QMS/change control, SOP training, CAPA, and auditability
- Vendor SLA operations and escalation handling
- Administrative workflow ownership and operational dashboards

## Architecture

```text
Streamlit function-first operations console
        |
        v
FastAPI REST API -- JWT/RBAC dependencies
        |
        +-- Auth, users, roles, permissions
        +-- Functional route engine and role visibility lens
        +-- Master data registry and route context resolver
        +-- Role workspace engine and workspace configuration
        +-- Donor intake and clinical review workflow
        +-- Database-governed AI screening and explainability engine
        +-- AI governance, override tracking, and workflow intelligence
        +-- Central workflow orchestration engine
        +-- Decision matrices and transition event history
        +-- Workflow task engine
        +-- Notification bell and workflow alert routing
        +-- Contextual action ribbon and workflow timelines
        +-- Enterprise search
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
- `operational.workflow_transition_event`
- `operational.workflow_assignment_rule`
- `operational.workflow_escalation_rule`
- `operational.workflow_notification_rule`
- `operational.workflow_navigation_route`
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
- Function-first enterprise routing for master data, workflow operations, analytics, and administration routes
- Route context resolver that parses URL query parameters, validates role visibility, loads master/workflow data, builds breadcrumbs, and returns authorized actions
- Master data routes including `/donor`, `/capa`, `/investigation`, `/vendor`, `/sop`, `/user`, and `/ai-rule`
- Workflow routes including `/workflow`, `/review`, `/escalation`, `/incident`, `/task`, and `/notification`
- Analytics routes including `/dashboard`, `/operations`, `/workload`, `/sla`, `/drift-analysis`, and `/workflow-intelligence`
- Dynamic workspace engine that generates navigation, widgets, KPIs, queues, workbench columns, and task actions from role metadata
- Centralized workflow orchestration engine for state validation, role authorization, decision matrices, SLA timers, task creation, notifications, audit events, and transition history
- Expanded workflow state machine for Draft Intake, Pending Intake Validation, Pending Clinical Review, Clinical Review In Progress, Pending Additional Information, High Risk Escalation, QA Investigation, CAPA Investigation, Clinical Re-Review, Operations Escalation, Approved, Rejected, and Closed
- Workflow transition event history for who changed what, from/to state, action taken, notes, and decision context
- Deep-link notification routing that opens the exact function route with record context without unsafe Streamlit session-state mutation
- Contextual action ribbon that renders different workflow actions on the same route based on role, permission, and workflow state
- Workflow-aware action modals for AI override, CAPA creation, reassignment, priority escalation, QA review, and rejection rationale
- Workflow timeline and related-record panels on detail routes
- Enterprise search across donors, workflows, CAPAs, investigations, incidents, AI rules, users, vendors, tasks, and notifications
- Business Technology Analyst workspace for AI risk dashboarding, workflow intelligence, AI governance, risk rule configuration, escalation analytics, AI audit review, and operational trends
- Database-driven AI risk rules with active/inactive status, condition operator, score delta, severity, and auto-escalation governance
- AI explainability panel showing triggered rules, score contributions, escalation reasons, workflow impact, confidence level, and historical comparisons
- Human-in-the-loop override tracking with override reason, reviewer, before/after decision, notification routing, and workflow timeline events
- Operational intelligence visualizations across roles: intake aging heatmap, documentation matrix, clinical risk heatmap, SLA timeline, escalation funnel, QA CAPA heatmap, investigation Sankey, vendor SLA heatmap, incident timeline, enterprise queue heatmap, workforce load balancer, AI workflow bottleneck Sankey, override trends, SLA prediction accuracy, escalation root cause matrix, and workflow queue heatmap
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

![Workflow notification deep link](docs/screenshots/workflow-orchestration-deeplink.png)

![Business Technology Analyst workflow intelligence](docs/screenshots/business-technology-analyst-intelligence.png)

![Function route review detail](docs/screenshots/functional-route-review.png)

![Function route workflow intelligence](docs/screenshots/functional-route-intelligence.png)

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

1. Sign in as `sysadmin` and confirm the default route is governance-focused administration, not an operational donor or vendor queue.
2. Use the visibility lens to preview how Clinical Reviewer, Donor Intake Coordinator, QA, Vendor Ops, Business Technology Analyst, or Operations Manager see the same function routes.
3. Open `/admin/workspaces` and `/admin/workflow-engine` to review role navigation, widget assignment, notification types, state-machine metadata, and workbench columns.
4. Sign in as `clinical`, open `/review`, and select a donor review detail route such as `/review/1441`.
5. Confirm the contextual action ribbon shows clinical actions while the timeline and related-record panels preserve workflow continuity.
6. Use the notification bell and confirm a record-specific alert opens the exact function route, for example `/review/{id}`, `/task/{id}`, or `/capa/{id}`.
7. Search for a donor, workflow, CAPA, incident, AI rule, or user from the sidebar and open the returned function route.
8. Sign in as `qa` and open `/capa` or `/investigation` to review QMS-specific actions and compliance context.
9. Sign in as `opsmanager` to review `/operations`, `/workload`, `/escalation`, and `/sla`.
10. Sign in as `analyst` to review `/workflow-intelligence`, `/drift-analysis`, `/ai-rule`, AI governance metrics, bottleneck visualizations, rule simulation, AI audit traces, transition context, and human override trends.

## Healthcare/QMS Concepts

- **Clinical screening:** Donor review combines structured intake data, clinical notes, risk flags, risk score, reviewer decision, and exception escalation.
- **AI governance:** The risk engine is transparent, database-governed, explainable, auditable, and owned by the Business Technology Analyst without source-code edits.
- **Decision support:** The risk engine recommends actions without replacing clinical judgment; reviewer overrides are captured as governed AI lifecycle events.
- **Function-first routing:** Routes model enterprise functions and master data rather than departments; role determines visibility, context, and actions inside the same route.
- **Role immersion:** Each role receives its own navigation, KPIs, widgets, queue columns, workflow actions, and notifications without duplicating URL structures.
- **Workflow ownership:** Major operational events create tasks with owners, due dates, priority, workflow state, queue name, and escalation paths.
- **Workflow routing:** State-machine transitions route work from Intake to Clinical Review to QA and Operations Management while creating tasks, notifications, and audit events.
- **Central orchestration:** Workflow actions are validated by a centralized engine that checks role authorization, current state, decision matrices, AI override rules, SLA routing, notification rules, and transition history before mutating records.
- **Actionable notifications:** Bell notifications carry workflow task context and route users into exact function routes with preserved record context.
- **Workflow intelligence:** Queue heatmaps, bottleneck flow analysis, SLA prediction validation, escalation matrices, and operational recommendations support process optimization.
- **Audit trail:** Login, logout, donor decisions, workflow changes, user changes, training completion, and escalations are logged with before/after values.
- **QMS workflow:** Change requests include SOP linkage, risk level, approval status, CAPA requirement, due dates, and investigation notes.
- **SOP training:** SOP revisions can be assigned to roles or users and tracked through acknowledgement status and overdue training.
- **Vendor governance:** Vendor incidents track uptime, ticket aging, SLA breach status, impact, and operational response.

## API Endpoint Groups

- `/api/auth`
- `/api/admin`
- `/api/workspaces`
- `/api/workspaces/transition-events`
- `/api/workspaces/states`
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
- `/api/routes`

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
