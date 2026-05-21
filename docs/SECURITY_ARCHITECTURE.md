# Security Architecture

This platform models regulated healthcare security concepts for donor eligibility, QMS, processing release, and operational workflow records. It is not a certified HIPAA or FDA 21 CFR Part 11 system, but it demonstrates the technical control patterns those environments expect.

## Native Identity Model

The application uses platform-native accounts.

Core tables:

- `operational.dim_user`
- `operational.dim_account_type`
- `operational.dim_organization`
- `operational.dim_user_approval_status`
- `operational.dim_auth_identity`
- `operational.dim_user_session`
- `operational.dim_mfa_configuration`

Supported account types:

- `internal`
- `supplier`
- `partner`
- `external`

Supplier accounts are active in the Supplier Portal. Partner and external auditor account types remain future-ready foundations. Supplier access is scoped by organization, approval state, MFA policy, route permissions, document access, and workflow assignment.

## Authentication Flow

```text
Login
  -> password verification
  -> failed-login lockout check
  -> approval status check
  -> MFA policy check
  -> access token issued
  -> refresh token stored as hash in dim_user_session
  -> Streamlit restores session after refresh
```

Access tokens are short lived. Refresh tokens rotate and are revocable through logout or logout-all.

## MFA Foundation

MFA is required by policy for:

- System Administrator
- Business Technology Analyst
- Operations Manager
- Quality Assurance Specialist

The current demo supports a TOTP/email-OTP-ready challenge flow. Production providers can be added behind the existing MFA configuration table.

## Authorization Model

Authorization is enforced in four places:

- API dependencies
- route resolution
- workflow transition engine
- document access service
- tenant access checks for organization-scoped records

Users cannot rely on hidden frontend controls for security. API calls validate permissions and workflow role authorization.

## Supplier Portal And Multi-Tenant Isolation

Supplier collaboration is modeled with:

- `operational.dim_supplier_relationship`
- `operational.dim_external_invitation`
- `operational.dim_document_version`
- `operational.fact_signature_event`
- `operational.fact_background_job`
- `operational.fact_realtime_event`
- `operational.dim_training_record`
- `operational.fact_validation_evidence`

External supplier users are assigned the `Supplier External User` role and an `organization_id`. API routes, task queries, document APIs, route resolution, workspace queues, and search apply organization scoping so Supplier A cannot see Supplier B records or internal donor queues. Supplier users receive `/supplier`, `/supplier-documents`, `/supplier-approvals`, `/task`, and `/notification` visibility, while internal supplier administration remains under `/admin/suppliers`.

Supplier onboarding supports signed invitation links, pending approval, internal approval/rejection/suspension/revocation, MFA-enabled account creation, and security audit events.

Supplier document review is internal-only. Supplier users can submit organization-scoped documents and view their own review status, but review outcomes require internal `suppliers.manage` or `documents.manage` authority plus an internal account. Reviews create document access records, security audit events, operational audit entries, realtime activity events, background notification jobs, and supplier-visible notifications.

## Encryption Model

Sensitive donor and clinical fields are encrypted before persistence where supported by the data model:

- donor identifiers
- donor names
- clinical notes
- medical/social history notes
- infectious disease result values
- protected document storage URIs

Notifications and audit events should use masked donor context when sensitive fields are not required.

## Audit And Electronic Record Concepts

Compliance-oriented traceability is modeled with:

- `fact_audit_log`
- `fact_security_audit`
- `workflow_transition_event`
- `fact_document_access`
- `fact_ai_override_event`

Workflow approvals include authenticated user identity, timestamps, reasons, transition history, and electronic signature metadata where workflow actions require it.

## Secure Document Handling

Documents are not served from public directories. Document APIs require authorization, issue signed links, expire tokens, and log access events.

## Account Recovery And Setup

User administration can create platform-native accounts and send single-use setup links to the user's email address. The login screen exposes password-reset requests, and reset links open the app with a `reset_token` query parameter so the user can set a new password without an administrator seeing it.

Password reset and account setup links are:

- signed JWTs
- tied to `fact_password_reset_token`
- single use
- short lived
- audit logged
- followed by session revocation after password reset

Production email delivery requires an outbound sender such as SMTP, SendGrid, or Mailgun. Cloudflare Email Routing may remain in place for inbound forwarding, but reset/setup emails must be sent by a transactional provider authenticated for `@teemails.com`.

## External-Ready Foundations

Supplier access now enforces:

- organization scoping
- approval workflow
- MFA
- least-privilege role assignment
- document-level access checks
- audit logging for every access and export

External users must never see unrestricted donor data, internal operational queues, or other supplier organizations.
