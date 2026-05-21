# Clinical Donor Screening & Quality Workflow Platform

Enterprise-style healthcare operations platform for donor referral intake, donor eligibility screening, tissue recovery suitability, processing release, governed AI-assisted decision support, centralized workflow orchestration, function-first routing, master data records, RBAC-secured transitions, audit trails, QMS/CAPA/deviation workflows, SOP training, vendor SLA monitoring, actionable notifications, escalations, AI governance, and operational intelligence dashboards.

Repository: `github.com/Fxdedglory/clinical-donor-workflow-platform`

## Project Overview

This project simulates internal donor-services and regulated tissue-processing software rather than a portfolio CRUD app. Donor referrals enter operational queues, eligibility rules evaluate administrative exclusions, medical/social history, infectious disease results, tissue-specific suitability, recovery windows, QMS release checks, and final disposition outcomes. Workflow tasks are routed through a state machine, escalations are created for overdue work, notifications link users back to exact records, and regulated activities are traceable through audit logs.

The latest upgrade adds security, compliance, and production-hardening foundations on top of the donor eligibility decision engine and QMS workflow expansion. Routes represent donor-services functions and master data entities such as `/donor/{id}`, `/referral/{id}`, `/screening/{id}`, `/medical-review/{id}`, `/recovery/{id}`, `/processing-release/{id}`, `/release/{id}`, `/deviation/{id}`, `/capa/{id}`, `/eligibility-rule/{id}`, `/task/{id}`, and `/workflow-intelligence`; the logged-in role determines visible widgets, actions, and operational context inside the same route. Buttons trigger authorized workflow transitions instead of directly modifying records; the orchestration engine validates role, state, decision matrices, SLA routing, notifications, audit events, transition history, and task creation.

The latest upgrade adds a supplier portal and multi-tenant collaboration foundation: supplier organizations, external supplier users, invitation and approval flows, organization-scoped task/document/signature access, supplier dashboards, background-event records, and supplier auditability without requiring Azure or external identity-provider dependencies.

Resume themes demonstrated:

- Enterprise healthcare workflow systems analysis
- Donor eligibility, recovery suitability, and processing release workflow modeling
- Role-centered operational workspace architecture
- Regulated operational workflow design
- RBAC security architecture with JWT authentication
- Persistent sessions, MFA foundations, security audit logging, and secure document access
- HIPAA-oriented sensitive-field encryption and FDA 21 CFR Part 11 electronic-record concepts
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
        +-- Donor referral intake and eligibility review workflow
        +-- Donor eligibility decision engine
        +-- Infectious disease, tissue suitability, recovery, and release matrices
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
- `operational.dim_donor`
- `operational.dim_referral_source`
- `operational.dim_tissue_type`
- `operational.dim_eligibility_rule`
- `operational.dim_infectious_disease_test`
- `operational.dim_disposition`
- `operational.fact_donor_screening`
- `operational.fact_eligibility_decision`
- `operational.fact_infectious_disease_result`
- `operational.fact_medical_social_history`
- `operational.fact_recovery_suitability`
- `operational.fact_processing_release`
- `operational.fact_deviation`
- `operational.fact_capa`
- `operational.fact_security_audit`
- `operational.dim_user_session`
- `operational.dim_auth_identity`
- `operational.dim_mfa_configuration`
- `operational.dim_secure_document`
- `operational.fact_document_access`
- `operational.dim_organization`
- `operational.dim_account_type`
- `operational.dim_user_preference`
- `operational.dim_sidebar_state`
- `operational.dim_deployment_environment`
- `operational.dim_user_approval_status`
- `operational.fact_password_reset_token`
- `operational.fact_system_health`
- `operational.fact_security_incident`
- `operational.fact_data_export`
- `operational.dim_supplier_relationship`
- `operational.dim_external_invitation`
- `operational.dim_document_version`
- `operational.fact_signature_event`
- `operational.fact_background_job`
- `operational.fact_realtime_event`
- `operational.dim_training_record`
- `operational.fact_validation_evidence`

Legacy compatibility, QMS, and vendor tables:

- `operational.fact_donor_review`
- `operational.dim_sop`
- `operational.fact_change_control`
- `operational.dim_vendor`
- `operational.fact_vendor_incident`
- `operational.dim_risk_category`

## Features

- JWT login, logout, refresh-token rotation, persistent browser session restoration, session revocation, password hashing with Argon2id support, and protected routes
- MFA foundation for sysadmin, analyst, operations manager, and QA roles with TOTP/email-OTP-ready verification flow
- Password policy enforcement, failed-login lockout, password reset token flow, password history foundations, and account approval-state controls
- Account setup and password reset email-link flow for platform-native users
- HIPAA-oriented application-layer encryption for sensitive donor identifiers, donor names, clinical notes, medical/social history notes, infectious disease results, and protected document storage URIs
- Security audit log for login, logout, failed login, MFA verification, password reset, sensitive record access, route denial, document access, workflow transitions, user changes, and session revocation
- Secure document handling with access-controlled document listing, signed document links, token expiration, and download audit logging
- FDA 21 CFR Part 11 concept modeling through authenticated workflow actions, electronic signature metadata, attributable timestamps, immutable-style transition history, and before/after audit trails
- Supplier portal with organization-scoped external login, MFA, supplier task queue, document requests, supplier approvals, and activity feed
- Supplier invitation and approval workflow with signed onboarding links, approval states, platform-native external accounts, and security audit logging
- Multi-tenant organization isolation for supplier users across workflow tasks, documents, notifications, route resolution, and search
- Organization-scoped document exchange with document version records, document access logs, supplier-submitted classification, and review status
- Electronic signature events with re-authentication, signature reason, signature meaning, timestamp, user attribution, and immutable-style signature hash
- Background job and realtime event foundation for SLA monitoring, supplier notifications, document workflows, and future live activity streams
- Persistent user preferences for sidebar collapse state, last route, recently viewed records, pinned records, and notification preferences
- SysAdmin System Health surface for DB, auth, email, document storage, backup posture, uptime, and active sessions
- Production deployment scaffolding with Cloudflare Tunnel, optional Nginx reverse proxy, HTTPS/HSTS/CSP headers, teemails.com routing, Certbot renewal support, and encrypted daily PostgreSQL backup container
- Eight enterprise roles: System Administrator, Donor Intake Coordinator, Clinical Reviewer, Quality Assurance Specialist, Vendor Operations Analyst, Operations Manager, Business Technology Analyst, Supplier External User
- Role-permission bridge for route-level authorization
- Function-first enterprise routing for master data, workflow operations, analytics, and administration routes
- Route context resolver that parses URL query parameters, validates role visibility, loads master/workflow data, builds breadcrumbs, and returns authorized actions
- Master data routes including `/donor`, `/eligibility-rule`, `/infectious-disease-test`, `/tissue-type`, `/release`, `/deviation`, `/capa`, `/investigation`, `/vendor`, `/sop`, `/user`, and `/ai-rule`
- Workflow routes including `/referral`, `/screening`, `/medical-review`, `/qa-review`, `/recovery`, `/processing-release`, `/workflow`, `/escalation`, `/incident`, `/task`, and `/notification`
- Analytics routes including `/dashboard`, `/operations`, `/workload`, `/sla`, `/drift-analysis`, and `/workflow-intelligence`
- Supplier collaboration routes including `/supplier`, `/supplier-documents`, `/supplier-approvals`, and `/admin/suppliers`
- Dynamic workspace engine that generates navigation, widgets, KPIs, queues, workbench columns, and task actions from role metadata
- Centralized workflow orchestration engine for state validation, role authorization, decision matrices, SLA timers, task creation, notifications, audit events, and transition history
- Expanded workflow state machine for Referral Received, Intake In Progress, Pending Administrative Screen, Pending Medical Social History Review, Pending Infectious Disease Review, Pending Tissue Suitability Review, Pending Recovery Suitability Review, Pending Medical Director Review, Pending QA Review, Recovery Authorized, Processing Hold, Pending Processing Release, Released for Clinical Use, Released for Research Use, Quarantine, Rejected, Destroyed, and Closed
- Workflow transition event history for who changed what, from/to state, action taken, notes, and decision context
- Deep-link notification routing that opens the exact function route with record context without unsafe Streamlit session-state mutation
- Contextual action ribbon that renders different workflow actions on the same route based on role, permission, and workflow state
- Configurable donor eligibility rule engine with administrative, medical/social history, infectious disease, tissue-specific, recovery suitability, processing release, QMS compliance, customer restriction, and export restriction categories
- Donor record pages showing referral source, workflow state, eligibility status, tissue types under review, infectious disease results, medical/social history flags, recovery suitability, QA/QMS status, linked CAPAs/deviations, final disposition, workflow timeline, related tasks, and action ribbon
- Donor-specific workflow states from Referral Received through Processing Release, Quarantine, Rejected, Destroyed, and Closed
- Processing release matrix for sterility testing, bioburden, environmental monitoring, packaging QC, labeling, traceability, chain of custody, deviations, and CAPA linkage
- QMS expansion with dedicated deviation and CAPA master records
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
- Workflow transition engine for referral intake, administrative screening, medical/social history review, infectious disease review, tissue suitability, recovery authorization, QA review, processing release, vendor escalation, and operations-manager routing
- Top-right notification bell with unread counts, priority indicators, target record metadata, and mark-as-read workflow
- Escalation engine for overdue donor review, SLA, and QMS tasks
- SOP training assignment and acknowledgement tracking
- Role responsibility center with job descriptions, assigned workflows, and operational KPIs
- Enterprise operations, workforce, compliance, vendor, donor, and audit dashboards
- Expanded audit trail with login activity, workflow changes, permission/user changes, escalation events, and IP address fields
- Faker-powered demo data for donors, tasks, escalations, SLA incidents, SOP revisions, training assignments, notifications, and audit events
- Dense donor-services demo data including 1,000+ donor master records, active referrals, infectious disease result sets, medical/social history reviews, tissue/recovery suitability checks, processing releases, deviations, CAPAs, workflow tasks, notifications, and 2,000+ audit events
- Seeded AI governance data for risk rules, model versioning, AI decisions, override events, and workflow timeline traces

## Demo Credentials

Default password for all demo users:

```text
ClinicalDemo!2026
```

Demo MFA code for roles that require MFA:

```text
000000
```

Demo users:

- `sysadmin` - System Administrator
- `intake` - Donor Intake Coordinator
- `clinical` - Clinical Reviewer
- `qa` - Quality Assurance Specialist
- `vendorops` - Vendor Operations Analyst
- `opsmanager` - Operations Manager
- `analyst` - Business Technology Analyst
- `supplier` - Supplier External User

## Screenshots

Design concept used for the original dashboard direction:

![Dashboard concept](docs/screenshots/concept-dashboard.png)

Rendered enterprise route/workspace examples:

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

Production deployment and recovery runbooks:

- `docs/PROD_DEPLOYMENT.md`
- `docs/SECURITY_ARCHITECTURE.md`
- `docs/BACKUP_RECOVERY.md`

Recommended public deployment for `https://teemails.com` is the Cloudflare Tunnel path in `docs/PROD_DEPLOYMENT.md`, using the production Compose `cloudflared` profile.

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
4. Sign in as `intake`, open `/referral`, and review referral intake records with authorization, time-of-death, chain-of-custody, and documentation context.
5. Sign in as `clinical`, open `/medical-review`, `/screening`, or `/recovery`, and review donor eligibility stages, infectious disease matrices, medical/social history risks, and tissue suitability outcomes.
6. Confirm the contextual action ribbon shows donor-services actions such as Validate Intake, Continue Infectious Disease Review, Request Medical Director Review, Authorize Recovery, Submit to QA Review, and Reject Donor.
7. Use the notification bell and confirm a record-specific alert opens the exact function route, for example `/donor/{id}`, `/processing-release/{id}`, `/deviation/{id}`, `/capa/{id}`, or `/task/{id}`.
8. Sign in as `qa` and open `/qa-review`, `/release`, `/deviation`, or `/capa` to review processing holds, deviations, CAPA, traceability, and release status.
9. Sign in as `opsmanager` to review `/operations`, `/workload`, `/escalation`, and `/sla`.
10. Sign in as `analyst` to review `/workflow-intelligence`, `/drift-analysis`, `/eligibility-rule`, `/ai-rule`, rule outcome distribution, override trends, decision matrix performance, bottleneck visualizations, and AI audit traces.

## Healthcare/QMS Concepts

- **Donor eligibility workflow:** The master workflow models referral intake, administrative exclusion screening, medical/social history review, infectious disease review, tissue-specific eligibility, recovery suitability, QA review, medical director escalation, processing release, and final disposition.
- **Decision matrices:** Configurable rules evaluate administrative, infectious disease, recovery, processing release, and QMS conditions without source-code edits.
- **Clinical screening:** Donor review combines structured intake data, clinical notes, eligibility flags, reviewer decision, and exception escalation.
- **AI governance:** The risk engine is transparent, database-governed, explainable, auditable, and owned by the Business Technology Analyst without source-code edits.
- **Decision support:** The risk engine recommends actions without replacing clinical judgment; reviewer overrides are captured as governed AI lifecycle events.
- **Function-first routing:** Routes model enterprise functions and master data rather than departments; role determines visibility, context, and actions inside the same route.
- **Role immersion:** Each role receives its own navigation, KPIs, widgets, queue columns, workflow actions, and notifications without duplicating URL structures.
- **Workflow ownership:** Major operational events create tasks with owners, due dates, priority, workflow state, queue name, and escalation paths.
- **Workflow routing:** State-machine transitions route work from referral intake to administrative screen, medical/social review, infectious disease review, recovery suitability, QA release, and operations escalation while creating tasks, notifications, and audit events.
- **Central orchestration:** Workflow actions are validated by a centralized engine that checks role authorization, current state, decision matrices, AI override rules, SLA routing, notification rules, and transition history before mutating records.
- **Actionable notifications:** Bell notifications carry workflow task context and route users into exact function routes with preserved record context.
- **Workflow intelligence:** Queue heatmaps, bottleneck flow analysis, SLA prediction validation, escalation matrices, and operational recommendations support process optimization.
- **Audit trail:** Login, logout, donor decisions, workflow changes, user changes, training completion, and escalations are logged with before/after values.
- **QMS workflow:** Change requests include SOP linkage, risk level, approval status, CAPA requirement, due dates, and investigation notes.
- **QMS release workflow:** Release checks include sterility, bioburden, environmental monitoring, packaging QC, labeling verification, traceability, chain of custody, deviations, CAPA linkage, and disposition.
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
- `/api/eligibility`
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
- Production hardening beyond the current `teemails.com` runbook, including managed PostgreSQL, object storage, and external monitoring integrations
- SharePoint document-control integration
- Deeper non-conformance and CAPA lifecycle expansion
