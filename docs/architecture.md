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

backend/app/routes/suppliers.py
  Supplier portal API for supplier organizations, signed invitations,
  approval states, supplier dashboard payloads, supplier document
  submission, internal document reviews, review notifications, task
  responses, electronic signatures, and background jobs

backend/app/services/ai_governance.py
  Database-governed rule orchestration, decision recording, override
  tracking, timeline events, workflow intelligence, and sandbox analysis

backend/app/services/tenant_access.py
  Organization-scoped access helpers used by task, document, route,
  supplier, workspace, and search flows to protect external tenant data

backend/app/auth
  Argon2id/bcrypt password verification, JWT creation/validation,
  persistent session records, refresh-token rotation, MFA challenge
  flow, password reset tokens, current user lookup, permission dependencies

backend/app/models
  SQLAlchemy operational tables for donors, QMS, vendors, users,
  tasks, notifications, escalations, workspaces, workflow rules,
  AI governance rules, AI decisions, overrides, timeline events,
  security audit, secure documents, sessions, MFA config, and
  external identity foundations

database/migrations
  Alembic-managed schemas, tables, indexes, and mart views
```

## Function Route Model

```text
Master data routes
  /donor/{id}
  /eligibility-rule/{id}
  /infectious-disease-test/{id}
  /tissue-type/{id}
  /release/{id}
  /deviation/{id}
  /capa/{id}
  /investigation/{id}
  /vendor/{id}
  /sop/{id}
  /user/{id}
  /ai-rule/{id}

Workflow operation routes
  /referral/{id}
  /screening/{id}
  /medical-review/{id}
  /qa-review/{id}
  /recovery/{id}
  /processing-release/{id}
  /escalation/{id}
  /incident/{id}
  /task/{id}
  /notification/{id}
  /supplier
  /supplier-documents/{id}
  /supplier-approvals/{id}

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
  /admin/suppliers
```

The same route can render different views by role. For example, `/capa/84` gives QA users corrective action and compliance context, operations managers escalation and staffing context, and Business Technology Analysts workflow-intelligence context.

## Donor Eligibility Workflow

```text
Referral Received
  -> Referral Intake
  -> Administrative Exclusion Screen
  -> Medical / Social History Review
  -> Infectious Disease Eligibility Review
  -> Tissue-Specific Eligibility Review
  -> Operational Recovery Suitability Review
  -> Quality & Compliance Review
  -> Automated Rule Resolution
  -> Medical Director Review if needed
  -> Recovery Authorization
  -> Processing Release
  -> Final Disposition
```

Final disposition values:

- Clinical Transplant
- Tissue Processing
- Research Use
- Quarantine
- Destruction
- Rejected / Deferred

The donor master record persists beyond workflow execution. Workflow tasks, eligibility decisions, infectious disease results, medical/social history reviews, recovery suitability checks, processing release records, deviations, CAPAs, notifications, and audit events link back to `operational.dim_donor`.

## Security And Compliance Foundations

This project models security controls expected in regulated healthcare operations software. It is not a certified HIPAA or FDA 21 CFR Part 11 system, but it demonstrates the implementation concepts:

- Persistent authentication with access tokens, refresh-token rotation, HTTPOnly API cookies, Streamlit browser-session restoration, and session revocation.
- MFA foundation for higher-risk roles, currently using a demo verification code with TOTP/email-OTP-ready tables.
- Application-layer AES-256-GCM encryption helpers for sensitive donor identifiers, donor names, clinical notes, medical/social history notes, infectious disease result values, and protected document storage URIs.
- Security audit events for authentication, failed access, sensitive record access, user changes, workflow transitions, document actions, MFA, password reset, and session revocation.
- Part 11 concept support through attributable workflow transitions, electronic signature metadata, before/after audit logging, timestamped transition history, and role-validated approvals.
- Secure document handling through access-controlled document APIs, signed download links, token expiration, and document access logs.
- Supplier portal support through native account types, organization-scoped RBAC, supplier relationship records, invitation approval states, external-user flags, MFA policy, supplier task queues, document exchange, and electronic signature events.
- Production deployment scaffolding for `teemails.com` through Cloudflare Tunnel, optional Nginx reverse proxy config, HTTPS/HSTS/CSP headers, secure-cookie flags, Certbot renewal support, encrypted backups, and SysAdmin system health monitoring.

## Decision Engine

`backend/app/services/eligibility_engine.py` evaluates database-governed `operational.dim_eligibility_rule` rows. Each rule has a category, condition field/operator/value, outcome, severity, review requirement, required role, SOP reference, active flag, and version. The engine builds a donor context from master data and facts, evaluates matching rules, records `fact_eligibility_decision`, updates donor eligibility status/final disposition, and feeds route analytics.

Decision matrix categories:

- Administrative
- Medical Social History
- Infectious Disease
- Tissue Specific
- Recovery Suitability
- Processing Release
- QMS Compliance
- Customer Restriction
- Country / Export Restriction

## Route Resolution Flow

```text
Streamlit login form
  -> POST /api/auth/login
  -> JWT access token + refresh token
  -> Streamlit stores session token
  -> route query param determines requested function route
  -> GET /api/routes/navigation
  -> FastAPI resolves actual or admin-preview role visibility
  -> GET /api/routes/resolve?route=/donor/{id}
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

## Supplier Collaboration Flow

```text
Internal user creates supplier organization
  -> POST /api/suppliers/organizations
  -> supplier relationship is created against Internal Operations

Internal user sends invitation
  -> POST /api/suppliers/invitations
  -> signed single-use invitation token is generated
  -> email delivery/background job/security audit events are recorded

Supplier accepts invitation
  -> /?supplier_invite=...
  -> supplier account is created with Supplier External User role
  -> account remains Pending Approval until internal approval

Supplier works scoped queue
  -> /supplier
  -> tasks, documents, notifications, signatures, search, and route context
     are filtered by organization_id
  -> supplier can submit documents, respond to tasks, and apply
     re-authenticated electronic signatures

Internal reviewer resolves supplier evidence
  -> POST /api/suppliers/documents/{document_id}/review
  -> review status is written to document version history
  -> document access, security audit, operational audit, realtime event,
     background job, and supplier notification records are created
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
  submit_admin_screen
  -> Pending Medical Social History Review
  -> creates Medical Social History Review task
  -> notifies Clinical Reviewer at /donor/{id}
  -> writes audit event
```

## AI Governance Flow

```text
Business Technology Analyst configures active AI risk rules
  -> rules persist in operational.dim_ai_risk_rule
  -> donor eligibility routes call governed rule engines
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
  -> backend returns the notification action_route, for example /donor/{id}
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
- Donor eligibility decision engine
- Infectious disease review matrix
- Tissue and recovery suitability matrix
- Processing release matrix
- Deviation and CAPA QMS records
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
