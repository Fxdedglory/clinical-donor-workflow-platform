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
  AI governance visualizations, rule configuration, AI audit review,
  system health, and integration management

backend/app/routes/workspaces.py
  Workspace API, admin workspace config API, transition API

backend/app/services/workspace_config.py
  Seeded role metadata, role tabs, widgets, queue columns,
  workflow states, transition rules, and assignment rules

backend/app/services/workspace_engine.py
  Runtime workspace payload generation, role-specific KPIs,
  widget data, queue scoping, and available action discovery

backend/app/services/workflow_orchestration.py
  Central workflow engine for role-authorized transitions, current-state
  validation, decision matrices, AI override governance, SLA task routing,
  workflow-linked notifications, audit logging, transition events, and
  timeline continuity

backend/app/routes/ai_governance.py
  Analyst-owned AI governance API for dashboards, governed rules,
  AI decisions, override events, explainability traces, and simulations

backend/app/services/ai_governance.py
  Database-governed rule orchestration, decision recording, override
  tracking, timeline events, workflow intelligence, and sandbox analysis

backend/app/auth
  Password hashing, JWT creation/validation, current user lookup,
  permission dependencies

backend/app/models
  SQLAlchemy operational tables for donors, QMS, vendors, users,
  tasks, notifications, escalations, workspaces, workflow rules,
  AI governance rules, AI decisions, overrides, and timeline events

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
  -> workflow_orchestration validates source role and current state
  -> decision matrix determines target state, priority, task type, and notification type
  -> AI governance layer runs when clinical decisions require recommendation review
  -> related task changes workflow_state/status
  -> downstream role task is created when needed
  -> target role receives workflow-linked notification with deep-link route
  -> donor/change/vendor record is updated when applicable
  -> workflow_transition_event captures from/to state, action, user, notes, and decision context
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

## AI Governance Flow

```text
Business Technology Analyst configures active AI risk rules
  -> rules persist in operational.dim_ai_risk_rule
  -> donor intake/review calls governed risk engine
  -> fact_ai_decision stores score, recommendation, triggered rules,
     confidence, escalation reasons, workflow stage, and model version
  -> workflow timeline records AI score and escalation events
  -> clinical reviewer may accept or override recommendation
  -> fact_ai_override_event captures reviewer, reason, prior decision,
     new decision, and timestamp
  -> analyst workspace visualizes override trends, rule frequency,
     risk heatmaps, SLA prediction accuracy, escalation roots,
     and bottleneck flow patterns
```

## Notification Routing Flow

```text
User opens notification bell
  -> POST /api/notifications/{id}/open
  -> notification is marked read
  -> workflow_orchestration.route_to_record resolves page_key by role,
     record type, and workflow state
  -> Streamlit writes query parameters only
  -> app reloads into the correct role tab with record context
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
- Business Technology Analyst AI governance workspace
- Database-governed AI rule engine
- AI explainability and human override tracking
- Workflow intelligence analytics and rule simulation sandbox
- Workflow transition event history
- Workflow navigation routes for role-aware record deep links
- Expanded audit trail
