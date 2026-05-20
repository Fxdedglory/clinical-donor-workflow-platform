# Data Contract

## Donor Review

Required fields:

- `donor_id`
- `donor_name`
- `age`
- `blood_type`
- `intake_status`

Risk outputs:

- `risk_score`
- `risk_level`
- `risk_flags`
- `recommended_action`
- `review_priority`

Workflow fields:

- `reviewer_id`
- `created_at`
- `updated_at`
- `reviewed_at`
- `rejection_reason`

## Donor Eligibility Master Data

`operational.dim_donor` stores the persistent donor master record:

- donor identifier
- linked legacy review id
- donor demographics
- referral source
- time of death
- source organization
- donor history flags
- current workflow state
- eligibility status
- final disposition

`operational.dim_referral_source` stores referral source organizations.

`operational.dim_tissue_type` stores tissue-specific suitability parameters:

- tissue type
- age range
- ischemic time limit
- preservation window
- SOP reference

`operational.dim_disposition` stores final disposition options:

- Clinical Transplant
- Tissue Processing
- Research Use
- Quarantine
- Destruction
- Rejected / Deferred

## Donor Eligibility Workflow Facts

`operational.fact_donor_screening` captures the staged screening outcomes:

- administrative outcome
- medical/social outcome
- infectious disease outcome
- tissue suitability outcome
- recovery suitability outcome
- QA outcome
- automated rule outcome
- current decision

`operational.fact_medical_social_history` tracks donor history risk flags:

- cancer history
- neurological disease
- autoimmune disease
- transmissible disease history
- IV drug use
- incarceration history
- travel exposure
- high-risk behavior
- unknown history

`operational.fact_infectious_disease_result` links donor records to `dim_infectious_disease_test` and tracks result value, specimen window validity, reviewer, and review status.

`operational.fact_recovery_suitability` tracks recovery readiness:

- refrigeration timing
- body cooling status
- trauma contamination
- blood draw timing
- hospital release status
- recovery environment
- recovery window
- outcome

`operational.fact_processing_release` tracks release readiness:

- sterility testing
- bioburden status
- environmental monitoring
- packaging QC
- labeling verification
- traceability verification
- chain of custody
- deviation/CAPA linkage
- release status
- final disposition

`operational.fact_deviation` and `operational.fact_capa` track QMS non-conformance and corrective action records.

## Eligibility Rule Engine

`operational.dim_eligibility_rule` stores configurable donor eligibility rules:

- rule name
- rule category
- condition field
- condition operator
- condition value
- outcome
- severity
- review requirement
- required role
- SOP reference
- active flag
- version
- created / approved metadata

Rule categories:

- Administrative
- Medical Social History
- Infectious Disease
- Tissue Specific
- Recovery Suitability
- Processing Release
- QMS Compliance
- Customer Restriction
- Country / Export Restriction

`operational.fact_eligibility_decision` records rule execution:

- donor
- rule
- decision stage
- outcome
- severity
- reason
- review requirement
- required role
- triggered rules
- final disposition
- creator and timestamp

## Audit Log

Each audit record captures:

- user
- action type
- affected table / entity type
- record identifier / entity id
- old value
- new value
- IP address when available
- timestamp

## Authentication and RBAC

Users are stored in `operational.dim_user` with:

- username
- email
- hashed password
- role reference
- active flag
- last login

Roles are stored in `operational.dim_role`. Permissions are mapped through
`operational.bridge_role_permission`.

## Workflow Task

Every major operational activity can create a task:

- task type
- assigned user
- assigned role
- priority
- status
- workflow state
- queue name
- due date
- related record type
- related record id
- escalation level

Task statuses:

- Pending
- Assigned
- In Progress
- Blocked
- Escalated
- Completed
- Rejected

## Notification

In-app notifications capture:

- user
- title
- message
- type
- priority
- related record type
- related record id
- action route
- read/unread state
- creation timestamp

Notifications are rendered through the top-right bell rather than a separate inbox page. The `action_route` stores an exact function route such as `/donor/{id}`, `/processing-release/{id}`, `/deviation/{id}`, `/capa/{id}`, `/task/{id}`, or `/workflow-intelligence`, so clicking an alert reloads the record with workflow state, authorized actions, timeline, and related records intact.

## Functional Route Context

The route engine resolves each URL into a route context:

- route path
- route key
- route group
- route kind
- entity type
- entity payload or collection rows
- workflow state
- related task
- role lens
- authorized action ribbon
- workflow timeline
- related records
- breadcrumbs
- analytics payload when applicable

Route groups:

- Master Data: `/donor`, `/eligibility-rule`, `/infectious-disease-test`, `/tissue-type`, `/release`, `/deviation`, `/capa`, `/investigation`, `/vendor`, `/sop`, `/user`, `/ai-rule`
- Workflow Operations: `/referral`, `/screening`, `/medical-review`, `/qa-review`, `/recovery`, `/processing-release`, `/workflow`, `/escalation`, `/incident`, `/task`, `/notification`
- Analytics & Intelligence: `/dashboard`, `/operations`, `/workload`, `/sla`, `/drift-analysis`, `/workflow-intelligence`
- Administration: `/admin/users`, `/admin/workspaces`, `/admin/workflow-engine`, `/admin/permissions`, `/admin/responsibility-center`

The route structure is shared across roles. Role, permission, and workflow state determine visible navigation, widgets, contextual actions, and modal requirements.

## Role Workspace Configuration

`operational.role_workspace_config` defines the role-native workspace:

- role
- workspace name
- workspace purpose
- dashboard layout
- visible tabs
- enabled widgets
- workbench columns
- default queue
- notification types
- theme configuration

`operational.role_navigation_config` defines rendered tabs:

- role
- tab label
- page key
- sort order
- visibility flag
- required permission

`operational.role_dashboard_widget` defines widget ownership:

- role
- widget key
- widget title
- widget type
- widget configuration
- sort order
- enabled flag

## Workflow State Machine

`operational.workflow_state_machine` defines regulated workflow states:

- Referral Received
- Intake In Progress
- Pending Administrative Screen
- Pending Medical Social History Review
- Pending Infectious Disease Review
- Pending Tissue Suitability Review
- Pending Recovery Suitability Review
- Pending Medical Director Review
- Pending QA Review
- Recovery Authorized
- Processing Hold
- Pending Processing Release
- Released for Clinical Use
- Released for Research Use
- Quarantine
- Rejected
- Destroyed
- Closed

Each state also stores:

- allowed roles
- allowed actions
- next possible states
- SLA hours
- escalation rules
- notification rules
- terminal-state flag

`operational.workflow_transition_rule` defines role-aware actions:

- action name
- action label
- from state
- to state
- source role
- target role
- task type
- notification type
- audit action
- SLA hours
- active flag

`operational.workflow_assignment_rule` stores assignment routing metadata for workflow orchestration.

`operational.workflow_transition_event` stores every governed transition:

- record id / type
- from state
- to state
- action taken
- user who performed the transition
- timestamp
- notes
- decision context

`operational.workflow_escalation_rule` stores SLA and stagnation escalation thresholds by workflow state.

`operational.workflow_notification_rule` stores role-aware notification rules for workflow events.

`operational.workflow_navigation_route` maps record type and workflow state back to the correct role-native workspace tab.

## AI Governance

`operational.dim_ai_risk_rule` stores governed risk-scoring rules:

- rule name
- risk category
- condition type
- condition operator
- condition value
- risk score delta
- severity
- auto-escalation flag
- active flag
- created / approved user references
- creation timestamp

`operational.dim_ai_model_version` stores governed engine lifecycle metadata:

- version name
- deployment date
- status
- change summary
- created / approved user references

`operational.fact_ai_decision` stores every AI-assisted recommendation:

- donor id
- model version
- risk score
- recommendation
- triggered rules
- workflow stage
- confidence level
- escalation reasons
- workflow impact
- review / override fields
- creation timestamp

`operational.fact_ai_override_event` stores human-in-the-loop governance events:

- AI decision reference
- reviewer
- override reason
- previous decision
- new decision
- timestamp

`operational.fact_workflow_timeline_event` records AI and workflow trace events:

- related record type / id
- event type
- summary
- structured detail
- actor
- timestamp

## Escalation Event

Escalations capture:

- related task
- escalation type
- trigger reason
- created timestamp
- resolved timestamp
- status

## SOP Training

Training assignments capture:

- SOP
- assigned user or role
- assigned date
- due date
- acknowledgement status

Training completions capture:

- assignment
- completed by user
- completion date
- attestation text

## Change Control

Each change request captures:

- request identifier
- requester
- SOP reference
- reason
- risk level
- approval status
- CAPA requirement
- investigation notes
- implementation due date

## Vendor Incident

Each incident captures:

- vendor and system
- ticket number
- severity
- status
- uptime percentage
- SLA breach flag
- opened/resolved timestamps
- ticket age
- impact summary

