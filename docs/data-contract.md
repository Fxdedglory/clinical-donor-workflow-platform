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
- affected table
- record identifier
- old value
- new value
- timestamp

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

