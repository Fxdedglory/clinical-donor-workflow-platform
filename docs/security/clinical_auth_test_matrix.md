# Clinical Authentication Test Matrix

Date: 2026-05-29

Use this matrix before enabling broader Clinical auth, Entra ID, or partner access. Do not print passwords, tokens, session cookies, client secrets, or database URLs in test output.

## Route And Prefix Tests

| Test | Expected |
|---|---|
| `GET https://teemails.com/Clinical/api/monitoring/health` | 200 JSON |
| `GET https://teemails.com/Clinical/api/auth/me` without auth | 401 JSON |
| `GET https://teemails.com/api/auth/me` | 404 or non-Clinical response |
| Clinical frontend bundle under `/Clinical` calls `/Clinical/api/...` | Pass |
| Direct Azure hostname calls `/api/...` | Pass |
| Local Vite dev calls configured/local API base | Pass |

## Login Tests

| Scenario | User type | Expected |
|---|---|---|
| Valid non-MFA internal demo login | internal | Access token returned and UI loads |
| Valid MFA-required internal demo login | internal admin/QA/ops/analyst | MFA challenge returned; UI shows MFA-needed state until MFA screen is implemented |
| Valid partner demo login | external partner | MFA challenge returned |
| Invalid username | any | 401; failed auth audit event |
| Invalid password | any | 401; failed auth audit event |
| Inactive user | any | 403 or 401 depending on backend path |
| Locked user | any | Access denied until lock expiry |

## MFA Tests

| Scenario | Expected |
|---|---|
| Login for MFA-required role returns challenge ID | Pass |
| MFA verify with valid code returns tokens | Pass |
| MFA verify with invalid code fails and audits event | Pass |
| Expired MFA challenge fails | Pass |
| React UI can complete MFA | Planned |

## Session And Cookie Tests

| Scenario | Expected |
|---|---|
| Bearer token works for `/api/auth/me` | Pass |
| Access cookie path is scoped appropriately behind `/Clinical` | Pass after cookie hardening |
| Refresh token can renew session | Pass |
| Logout revokes backend session | Planned |
| Logout clears local browser token payload | Pass |
| Expired token returns 401 without frontend crash | Pass |

## Role And Permission Tests

| Role | Key expected access |
|---|---|
| System Administrator | user management, producer controls, system admin |
| Donor Intake Coordinator | donor intake and referral workflow |
| Clinical Reviewer | clinical review and eligibility |
| Quality Assurance Specialist | QMS, CAPA, audit, training follow-up |
| Vendor Operations Analyst | vendor SLA and incidents |
| Operations Manager | queues, operational dashboards, escalation |
| Business Technology Analyst | AI governance and workflow intelligence |
| Partner External User | partner portal only, organization-scoped |
| Supplier External User | compatibility role for partner/supplier portal |

Negative tests:

- Partner user cannot access internal admin routes.
- Supplier/partner user cannot see other partner organizations.
- Non-admin user cannot run generation/export operations requiring `system.admin`.
- User without `security.audit` cannot read full audit logs.

## Database Permission Tests

| Test | Expected |
|---|---|
| Runtime role is not superuser | Pass |
| Runtime role cannot create database | Pass |
| Runtime role cannot create role | Pass |
| Runtime role cannot create schema objects | Pass |
| Runtime role can read/write session and audit records | Pass |
| Runtime role permissions on user/role tables are reviewed | Follow-up |

## Monitoring And Audit Tests

| Event | Expected |
|---|---|
| login_success | Security/user access event emitted |
| login_failure | Security/user access event emitted |
| mfa_challenge | Security/user access event emitted |
| mfa_success | Security/user access event emitted |
| mfa_failure | Security/user access event emitted |
| logout | Security/user access event emitted |
| access_denied | Security/user access event emitted |
| admin_action | Security event emitted |

## Safe Verification Commands

```powershell
cd E:\Clinical_Donor_Screening_Quality_Workflow_Platform
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

For production auth tests, use browser DevTools and redact:

- passwords
- tokens
- cookies
- session IDs
- database URLs
- client secrets
