# Notification Preferences Plan

Date: 2026-05-29

## Goal

Give Clinical users a simple profile-level preference surface while preserving auditability and future Entra compatibility.

## Current Implementation

Authenticated route:

- `/Clinical/preferences`

API routes:

- `GET /api/auth/me/preferences`
- `PATCH /api/auth/me/preferences`

Stored preference key:

- `notification_preferences`

Default frontend options:

- task assignments
- partner notifications
- document requests
- approval requests
- security alerts

Updating preferences logs:

- `USER_PREFERENCE_UPDATE`

The event flows to:

- `/api/monitoring/security-events`
- `/api/monitoring/user-access`

## Future Preference Categories

Internal users:

- clinical review assignments
- QA/CAPA escalation
- vendor SLA escalation
- data producer completion/failure
- security alerts

Partner users:

- document requests
- submission status updates
- approval requests
- information requested
- expiring access reminders

Admins:

- access requests
- failed login spikes
- backup/restore warnings
- validation failures
- export failures

## Delivery Channels

Current:

- Stored app preferences only.

Future:

- email
- in-app notifications
- Monitoring Platform alert summaries
- Microsoft Teams or Outlook integrations after Entra and Graph planning

## Security Notes

- Preferences must not override security-critical alerts for privileged users.
- Partner notification preferences must remain organization-scoped.
- Preference updates should remain auditable.
- Do not store secrets, tokens, or protected health information in preference payloads.
