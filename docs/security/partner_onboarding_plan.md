# Partner Onboarding Plan

Date: 2026-05-29

## Goal

Support partner and supplier access requests without weakening the existing Clinical role model. Native partner access remains available now; future partner identity should align with Microsoft Entra B2B or External ID.

## Current Capabilities

Existing backend support:

- Partner organizations.
- Supplier/partner relationships.
- External invitations.
- Partner invitation preview and acceptance.
- Organization-scoped partner access.
- Partner portal permissions through `Partner External User` and `Supplier External User`.
- Security audit events for invitation acceptance and partner actions.

New public intake route:

- `/Clinical/request-access`

New API route:

- `POST /api/auth/access-request`

The access request endpoint records an auditable `ACCESS_REQUEST_SUBMITTED` event. It does not automatically create a user, organization, invitation, or role assignment.

## Recommended Review Workflow

1. Partner user submits request.
2. Monitoring Platform surfaces `ACCESS_REQUEST_SUBMITTED`.
3. Clinical administrator validates organization, business reason, and sponsor.
4. Administrator creates or reuses partner organization.
5. Administrator issues external invitation.
6. Partner accepts invitation and creates native account.
7. Administrator approves account.
8. Future: assign Entra B2B/External ID identity and map to partner-scoped role.

## Future Entra B2B Alignment

For partner users:

- Identity provider: Microsoft Entra B2B or Entra External ID.
- Role: `Partner_User` or `Partner_Manager`.
- Scope: one partner organization unless explicitly approved.
- Expiration: required for temporary/vendor access.
- Audit: login, access denied, partner route use, document activity, approvals, and admin changes.

## Least-Privilege Rules

- Partner users may access partner portal routes only.
- Partner users may see only their organization records.
- Partner users may not access internal admin, clinical review, QMS administration, data producer, or audit administration routes.
- Supplier users should use compatibility routes only until the partner model is fully unified.

## Monitoring Requirements

The following must flow to monitoring endpoints:

- Access request submitted.
- Invitation created.
- Invitation accepted.
- Account approved or rejected.
- Partner login success/failure.
- Partner document upload.
- Partner approval/acknowledgement.
- Partner access denied.

## Open Items

- Build admin review screen for access requests.
- Add explicit access-request persistence table if audit-only records become insufficient.
- Add Entra B2B invitation lifecycle once Entra is implemented.
