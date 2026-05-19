# Architecture

The platform is organized as role-centered enterprise workflow software. A role is not only a permission set; it defines operational identity, workspace layout, navigation, widgets, workbench columns, notifications, task actions, and workflow ownership.

```text
frontend/app.py
  Authenticated Streamlit shell
  Loads /api/workspaces/me
  Renders role-native navigation, notification bell, and workspace pages

frontend/views/role_workspace.py
  Dynamic workspace renderer for role dashboards, queues, workbenches,
  donor intake form, workspace configuration, workflow configuration,
  system health, and integration management

backend/app/routes/workspaces.py
  Workspace API, admin workspace config API, transition API

backend/app/services/workspace_config.py
  Seeded role metadata, role tabs, widgets, queue columns,
  workflow states, transition rules, and assignment rules

backend/app/services/workspace_engine.py
  Runtime workspace payload generation, role-specific KPIs,
  widget data, queue scoping, and workflow transition execution

backend/app/auth
  Password hashing, JWT creation/validation, current user lookup,
  permission dependencies

backend/app/models
  SQLAlchemy operational tables for donors, QMS, vendors, users,
  tasks, notifications, escalations, workspaces, and workflow rules

database/migrations
  Alembic-managed schemas, tables, indexes, and mart views
```

## Request Flow

```text
Streamlit login form
  -> POST /api/auth/login
  -> JWT access token + refresh token
  -> Streamlit stores session token
  -> GET /api/workspaces/me
  -> FastAPI resolves actual or admin-preview role
  -> Workspace engine loads role_workspace_config
  -> Workspace engine returns navigation, KPIs, widgets, queue, actions, notifications
  -> Streamlit renders the role-native operational workspace
```

## Workflow Transition Flow

```text
Role user selects workflow action
  -> POST /api/workspaces/transition
  -> transition rule validates source role
  -> related task changes workflow_state/status
  -> downstream role task is created when needed
  -> target role receives notification
  -> donor/change/vendor record is updated when applicable
  -> audit log captures before/after transition event
```

Example:

```text
Donor Intake Coordinator
  submit_to_clinical_review
  -> Pending Clinical Review
  -> creates Clinical Review Workbench task
  -> notifies Clinical Reviewer
  -> writes audit event
```

## Data Layers

- `staging`: reserved for future raw imports
- `operational`: source-of-truth workflow and configuration tables
- `marts`: dashboard and reporting views

## Enterprise Modules

- Authentication and RBAC
- Dynamic role workspace engine
- Role navigation and widget configuration
- Workflow state machine and transition rules
- Workflow task engine
- Notification bell and role-aware alert routing
- Escalation engine
- SOP training and acknowledgement
- Responsibility center
- System administrator governance workspace
- Role-specific dashboards and workbenches
- Expanded audit trail
