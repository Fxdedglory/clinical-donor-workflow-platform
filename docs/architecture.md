# Architecture

The platform is organized as function-first enterprise workflow software. Routes represent business functions and master data entities, while role configuration determines which routes, widgets, actions, and operational context a user can see. A role is still more than a permission set, but it no longer creates a separate URL structure.

```text
frontend/app.py
  Authenticated Streamlit shell
  Reads st.query_params["route"]
  Renders function route navigation, notification bell, search, and route pages

frontend/views/functional_routes.py
  Route-aware master data, workflow, analytics, and administration renderer
  Contextual action ribbon, workflow-aware dialogs, workflow timeline,
  related records, collections, and operational visualizations

backend/app/routes/functional_routes.py
  Navigation, route resolution, enterprise search, and notification-open API

backend/app/services/functional_routes.py
  Central route catalog, role visibility checks, master data loading,
  workflow context loading, breadcrumbs, role lens, authorized actions,
  related records, timeline data, analytics payloads, and route helpers

frontend/views/role_workspace.py
  Legacy-compatible renderer for admin configuration and existing
  role workspace components reused by function routes

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

## Function Route Model

```text
Master data routes
  /donor/{id}
  /capa/{id}
  /investigation/{id}
  /vendor/{id}
  /sop/{id}
  /user/{id}
  /ai-rule/{id}

Workflow operation routes
  /workflow/{id}
  /review/{id}
  /escalation/{id}
  /incident/{id}
  /task/{id}
  /notification/{id}

Analytics and intelligence routes
  /dashboard
  /operations
  /workload
  /sla
  /drift-analysis
  /workflow-intelligence

Administration routes
  /admin/users
  /admin/workspaces
  /admin/workflow-engine
  /admin/permissions
  /admin/responsibility-center
```

The same route can render different views by role. For example, `/capa/84` gives QA users investigation and compliance actions, operations managers escalation and staffing context, and Business Technology Analysts workflow-intelligence context.

## Route Resolution Flow

```text
Streamlit login form
  -> POST /api/auth/login
  -> JWT access token + refresh token
  -> Streamlit stores session token
  -> route query param determines requested function route
  -> GET /api/routes/navigation
  -> FastAPI resolves actual or admin-preview role visibility
  -> GET /api/routes/resolve?route=/review/{id}
  -> functional route engine parses route, loads entity/workflow context,
     validates role permissions, builds breadcrumbs, loads timeline,
     loads related records, and returns authorized action ribbon metadata
  -> Streamlit renders the route-aware operational page
```

## Legacy Workspace Compatibility

The role workspace metadata remains valuable because it defines operational identity, dashboard visibility, and workbench configuration. It is now consumed as a role visibility and layout lens rather than as the primary routing architecture.

```text
frontend/app.py
  Loads /api/workspaces/me
  Uses workspace metadata for current role, notification bell, and
  admin preview context

frontend/views/role_workspace.py
  Continues to support admin configuration surfaces and reusable
  operational components
```

## Request Flow

```text
Function route requested
  -> route catalog resolves the route group and kind
  -> route engine validates permissions for the active role
  -> master data or workflow record is loaded
  -> role lens selects widgets, actions, and context
  -> contextual action ribbon is rendered
  -> timeline and related records preserve operational continuity
```

## Workflow Transition Flow

```text
Role user selects workflow action
  -> action ribbon opens a workflow-aware dialog when extra rationale is required
  -> POST /api/workspaces/transition
  -> workflow_orchestration validates source role and current state
  -> decision matrix determines target state, priority, task type, and notification type
  -> AI governance layer runs when clinical decisions require recommendation review
  -> related task changes workflow_state/status
  -> downstream role task is created when needed
  -> target role receives workflow-linked notification with function route
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
  -> notifies Clinical Reviewer at /review/{id}
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
  -> analyst routes visualize override trends, rule frequency,
     risk heatmaps, SLA prediction accuracy, escalation roots,
     and bottleneck flow patterns
```

## Notification Routing Flow

```text
User opens notification bell
  -> POST /api/notifications/{id}/open
  -> notification is marked read
  -> backend returns the notification action_route, for example /review/{id}
  -> Streamlit updates st.query_params["route"]
  -> route engine reloads the exact record, workflow state,
     role-authorized actions, timeline, and related records
```

## Data Layers

- `staging`: reserved for future raw imports
- `operational`: source-of-truth workflow and configuration tables
- `marts`: dashboard and reporting views

## Enterprise Modules

- Authentication and RBAC
- Functional route engine
- Master data registry
- Route-aware layout renderer
- Contextual action ribbon
- Workflow-aware action modals
- Workflow timeline service
- Related records panel
- Enterprise search
- Dynamic role workspace engine
- Role navigation and widget configuration
- Workflow state machine and transition rules
- Workflow task engine
- Notification bell and function-route alert routing
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
- Expanded audit trail
