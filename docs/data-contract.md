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
- read/unread state
- creation timestamp

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

