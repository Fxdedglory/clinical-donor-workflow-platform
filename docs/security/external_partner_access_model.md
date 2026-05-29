# External Partner Access Model

## Goal

Support OPO-like partner organizations with limited portal access while protecting internal clinical operations, QMS investigations, audit trails, and system administration.

## Partner User Concepts

Partner users are external users with:

- `is_external=true`
- `external_user_flag=true`
- `organization_id` set
- partner/supplier role assignment
- approval status controlled by internal admins
- MFA required for high-risk access

## Allowed Partner Capabilities

Partner users may access:

- Partner Portal dashboard.
- Their organization's submissions.
- Their organization's quality complaints.
- Their organization's document exchange.
- Their organization's partner-visible workflow statuses.
- Assigned partner task responses.
- Their own notifications.

Partner users must not access:

- Internal donor review queues.
- Full donor medical/social history outside partner-visible workflow.
- Internal QMS investigation details unless explicitly shared.
- Other partner organizations.
- User administration.
- System health.
- Data producer controls.

## Data Isolation Rule

Every partner-facing table should preserve `organization_id` scoping where applicable. The route layer should apply organization filters for external users and return not-found style responses rather than cross-tenant authorization details.

## Future Entra External Access

Possible later options:

- Keep platform-native partner accounts.
- Use Microsoft Entra External ID for partner users.
- Use one partner tenant integration per strategic partner only if cost/complexity is justified.

Do not implement external identity federation until the hosted app, internal Entra ID, and partner workflow boundaries are stable.
