# Microsoft Entra ID Future Integration Plan

## Purpose

Move internal staff authentication from platform-native demo accounts to Microsoft Entra ID while preserving partner portal least-privilege access and auditability.

## Internal Users

Future target:

- Microsoft Entra ID for internal staff SSO.
- App roles mapped to existing platform roles.
- Group-based assignment for:
  - System Administrator
  - Donor Intake Coordinator
  - Clinical Reviewer
  - Quality Assurance Specialist
  - Vendor Operations Analyst
  - Operations Manager
  - Business Technology Analyst

## Recommended Pattern

1. Register an Entra app for the Clinical platform.
2. Configure redirect URI for the hosted React/App Service route.
3. Use Authorization Code with PKCE.
4. Validate issuer, audience, nonce, and token signature.
5. Map Entra `oid` or `sub` to `dim_auth_identity`.
6. Map app roles/groups to `dim_role`.
7. Preserve platform audit events for login, logout, role resolution, and denied access.

## Current State

Current auth remains platform-native:

- JWT access and refresh tokens.
- Password policy.
- MFA foundation.
- User session records.
- Security audit logging.

No Entra ID code was added in this pass.

## Future Backlog

- Add OIDC config settings.
- Add Entra login route.
- Add callback route.
- Add `identity_provider="Microsoft Entra ID"` records.
- Add role/group mapping table or config.
- Add token validation tests.
- Add admin migration path for existing demo users.
- Decide whether partner users also use Entra External ID or remain platform-native.
