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

Notifications are rendered through the top-right workspace bell rather than a dedicated navigation page. The `action_route` maps the alert back to a role workspace tab.

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

- Draft Intake
- Pending Intake Review
- Pending Clinical Review
- Clinical Escalation
- Pending QA Review
- CAPA Investigation
- Vendor SLA Investigation
- Approved
- Rejected
- Closed

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

