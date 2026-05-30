# Authentication Experience Plan

Date: 2026-05-29

Scope: Clinical Donor Platform native authentication experience, with future Microsoft Entra ID readiness. This plan does not implement Entra login and does not remove the existing role model.

## Target Experience

Public Clinical routes:

- `/Clinical`
- `/Clinical/login`
- `/Clinical/logout`
- `/Clinical/forgot-password`
- `/Clinical/reset-password`
- `/Clinical/request-access`

Authenticated Clinical routes:

- `/Clinical/profile`
- `/Clinical/preferences`
- Existing operational sections such as dashboard, partner portal, QMS, data producer, exports, analytics, and health.

## Current Implementation

The React app now has route-aware native auth screens:

- Home/access center.
- Login.
- MFA verification form using existing `/api/auth/mfa/verify`.
- Logout page that calls backend logout before clearing local state.
- Forgot password page using `/api/auth/password-reset/request`.
- Reset password page using `/api/auth/password-reset/confirm`.
- Request access page using `/api/auth/access-request`.
- Profile page using `/api/auth/me`.
- Preferences page using `/api/auth/me/preferences`.

The frontend infers `/Clinical` as its API base when served through Cloudflare path routing.

## Native Auth Flow

1. User opens `/Clinical/login`.
2. User submits username/email and password.
3. Backend validates native credentials.
4. If MFA is required, backend returns an MFA challenge.
5. User submits MFA code.
6. Backend creates session, returns token payload, sets auth cookies, and logs security events.
7. Frontend stores the token payload and routes to `/Clinical/dashboard`.

## Logout Flow

1. User opens `/Clinical/logout` or clicks sign out.
2. Frontend calls `/api/auth/logout` with the current Bearer token.
3. Backend revokes the active session, clears cookies, and logs logout.
4. Frontend clears local token state.

## Audit Event Coverage

Security events are emitted through existing `SecurityAudit` records and flow to:

- `/api/monitoring/security-events`
- `/api/monitoring/user-access`

Important event families:

- `LOGIN`
- `FAILED_LOGIN`
- `LOGIN_LOCKED`
- `LOGIN_BLOCKED_APPROVAL_STATUS`
- `LOGOUT`
- `TOKEN_REFRESH`
- `MFA_CHALLENGE_CREATED`
- `MFA_VERIFICATION`
- `MFA_VERIFICATION_FAILED`
- `PASSWORD_RESET_REQUEST`
- `PASSWORD_RESET_COMPLETED`
- `PASSWORD_CHANGE`
- `PASSWORD_CHANGE_FAILED`
- `PROFILE_UPDATE`
- `USER_PREFERENCE_UPDATE`
- `ACCESS_REQUEST_SUBMITTED`
- `SUPPLIER_INVITATION_ACCEPTED`

## Entra ID Preparation

Future Entra work should preserve these route contracts:

- `/Clinical/login` can become the native/SSO choice page.
- `/Clinical/auth/callback` should be added when Entra is implemented.
- `/Clinical/logout` should revoke local app session and initiate Entra logout when applicable.
- `/Clinical/request-access` can route internal users to Entra group assignment and external users to Entra B2B/External ID onboarding.

## Open Items

- Replace localStorage token persistence with a safer session-cookie model or Entra-compatible session later.
- Configure `APP_BASE_URL=https://teemails.com/Clinical` in Azure so reset/setup links point to public routes.
- Add admin UI for reviewing `ACCESS_REQUEST_SUBMITTED` events.
- Add full route guards by permission once deep module routes are implemented.
