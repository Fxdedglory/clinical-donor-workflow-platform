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

Supplier, partner, and external accounts are foundations only. They are scoped by organization and approval state, but the supplier portal is intentionally not implemented yet.

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

Users cannot rely on hidden frontend controls for security. API calls validate permissions and workflow role authorization.

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

## External-Ready Foundations

Future supplier access must enforce:

- organization scoping
- approval workflow
- MFA
- least-privilege role assignment
- document-level access checks
- audit logging for every access and export

External users must never see unrestricted donor data, internal operational queues, or other supplier organizations.
