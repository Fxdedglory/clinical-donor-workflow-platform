# Password Reset Workflow

Date: 2026-05-29

## Current Native Workflow

Public routes:

- `/Clinical/forgot-password`
- `/Clinical/reset-password`

API routes:

- `POST /api/auth/password-reset/request`
- `POST /api/auth/password-reset/confirm`

## Request Flow

1. User enters work email.
2. Backend looks up active native user.
3. Backend creates a single-use password reset token record.
4. Backend sends a reset email if email delivery is configured.
5. Backend logs `PASSWORD_RESET_REQUEST`.
6. Frontend always shows a neutral response so account existence is not disclosed.

## Confirm Flow

1. User opens `/Clinical/reset-password?token=<token>`.
2. User enters a new password.
3. Backend validates token type, hash, user, expiry, and reuse.
4. Backend validates password policy and password history.
5. Backend updates password hash.
6. Backend revokes existing sessions.
7. Backend logs `PASSWORD_RESET_COMPLETED`.

## Azure Configuration Requirement

Set the app base URL to the public Clinical path before relying on password emails:

```text
APP_BASE_URL=https://teemails.com/Clinical
```

Do not commit real SMTP credentials or app secrets.

## Future Entra Behavior

When internal users move to Microsoft Entra ID:

- Internal users should recover passwords through Microsoft account recovery.
- Clinical native reset should remain only for legacy/native partner accounts if still needed.
- Password reset events should still be normalized into Monitoring user-access events.

## Security Considerations

- Never expose whether an email exists.
- Never log reset tokens.
- Reset tokens are single-use and time-limited.
- Passwords must satisfy backend policy.
- Existing sessions are revoked after reset.
- Monitoring should show reset request/completion counts, not token values.
