# Clinical PHI/ePHI Field Inventory

RC1 review date: 2026-06-13

Post-RC-02 hardening update date: 2026-06-13

Post-RC-04 small-cell suppression update date: 2026-06-13

Scope: operational clinical models, workflow audit payloads, reports, and export metadata currently implemented under the clinical platform.

## Inventory Summary

| Module | Sensitive fields and examples | PHI/ePHI risk | Export sensitivity | Masking/redaction needs | Retention considerations |
| --- | --- | --- | --- | --- | --- |
| Patients / Donors | `patient_id`, `donor_reference`, first/middle/last name, date of birth, sex at birth, gender identity, preferred language, phone, email, address, city/state/postal code, status. | Critical | Critical when exported or shown with clinical/billing context. | Mask names, contact data, dates of birth, and addresses for non-care roles; consider tokenized patient ids in analytics. | Retain per clinical record retention policy; soft-delete is not a compliance retention substitute. |
| Contacts | Emergency/alternate contact full name, relationship, phone, email, primary flag. | High | High because contact information can identify patient/donor household or next of kin. | Mask contact name, phone, and email outside care coordination roles. | Retain with patient record while active; review deletion/retirement workflows. |
| Insurance | Payer name, member id, group number, plan type, eligibility status, verification status, coverage dates, payer/plan names, verification notes. | Critical | Critical due financial/coverage identifiers. | Mask member id/group number by default; restrict detailed insurance export to billing roles. | Retain under billing/claims policy and contractual payer requirements. |
| Scheduling | Appointment number, patient link, provider/room, appointment type, scheduled start/end, reason, cancellation/no-show reason, check-in time, resources. | High | High when combined with patient id or visit reason; moderate for pure utilization aggregates. | Hide reason fields and patient identifiers in aggregate reports where not needed. | Retain scheduling status history for operational audit and disputes. |
| Screening / Vitals | Session number, patient/donor link, answers JSON, notes, vitals, outcomes, rule results, deferral type/reason, supervisor review flags. | Critical | Critical because questionnaire, vitals, eligibility, and deferral information are direct clinical facts. | Redact free-text notes and answer JSON for non-clinical exports; aggregate eligibility outcomes where possible. | Retain with donor screening/eligibility record and quality evidence policies. |
| Encounters / Notes / Diagnoses / Allergies / Medications | Encounter number, chief complaint, reason, note title/content, amendment reason, diagnosis code/display, allergies, reactions, medication, dose, route, frequency, indication, notes. | Critical | Critical. This is direct EMR content. | Role-aware masking required before external reports; free-text notes need strict export controls. | Signed/amended notes need immutable history expectations and retention aligned to medical record policy. |
| Orders / Results | Order number, order type, clinical indication, ordering provider, result name/value/unit/range/status, abnormal/critical flags, result notes, acknowledgements. | Critical | Critical, especially result values and critical-result acknowledgement. | Mask result values and clinical indication for non-care roles; aggregate result status for analytics. | Retain order/result status history and acknowledgements as clinical evidence. |
| Care Plans | Care plan title/type/priority/reason, goals, interventions, tasks, progress notes, team members, closure reason, outcome summary, linked result flags. | Critical | Critical for detailed exports; moderate for aging aggregates without patient detail. | Mask progress notes, goals, interventions, and patient links in analytics. | Retain active/closed care plans and status history with clinical record. |
| Billing / Claims / Payments / Denials | Account number, patient link, payer name, member id, charges, service dates, codes, claim numbers, amounts, balances, diagnosis code, payment reference, denial reason, resolution notes. | Critical | Critical due financial identifiers and diagnosis/service data. | Mask member id, payment references, free-text denial notes, and diagnosis codes outside billing/authorized roles. | Retain under billing, payer, tax, and regulatory requirements. |
| Quality / Adverse Events | Quality event/adverse event numbers, patient links, source module, severity, owner, description, resolution, adverse event description, immediate action, reporter, investigations, evidence summary, approvals, CAPA/deviation links. | Critical | Critical for adverse events and evidence packages. | Redact patient identifiers and free-text findings for non-QA/non-compliance export contexts. | Retain as quality system evidence; append-only history is required for production. |
| Reports / Analytics | Aggregates, filters, modules, row counts, recent audit operations, status counts, balances, critical-result counts, audit activity. | Moderate to high | High when filters identify small cohorts or audit payloads include entity ids/change details. | Suppress small-cell counts and audit payload details in shared analytics; split audit reports behind dedicated permissions. | Retain generated export metadata and status history with audit evidence. |
| Audit Evidence | Workflow operation id, workflow, entity type/id, actor, timestamp, preview hash, status before/after, reason, changes JSON. | High to critical | Critical when changes include clinical, billing, or quality field values. | Redact change payloads for non-audit users; hash or pseudonymize entity ids in broad analytics. | Production must use append-only durable storage with backup/retention controls. |

## Production Encryption Assumptions

RC1 does not implement a new PHI masking or field-level encryption framework. Production readiness assumes:

- database encryption at rest through the managed database platform;
- TLS in transit for application to database and browser to application traffic;
- encrypted backups with `BACKUP_ENCRYPTION_KEY` or provider-managed equivalent;
- strong `SECRET_KEY` and session/cookie settings injected outside Git;
- future use of `ENCRYPTION_KEY` or managed key services for selected application-level sensitive-field encryption;
- append-only workflow audit storage before production compliance evidence is authoritative.

## Masking And Redaction Future Needs

Post-RC-02 added a lightweight deterministic sensitivity registry in `backend/app/services/clinical_phi.py`. It classifies fields across patients, contacts, insurance, scheduling, screening, encounters, orders, care plans, billing, quality, audit, reports, and admin using these levels:

- `public`
- `internal`
- `phi`
- `ephi`
- `financial`
- `compliance_sensitive`
- `audit_sensitive`

Post-RC-02 also added reusable export profiles, and Post-RC-04 added small-cell suppression for aggregate report/export count cells under safe profiles:

- `aggregate_safe`: default report/analytics profile; redacts direct identifiers, sensitive change details, and nonzero count cells below 5.
- `external_safe`: strict safe-share profile; redacts internal, PHI/ePHI, financial, compliance, audit-sensitive fields, and nonzero count cells below 5.
- `audit_metadata`: default audit evidence profile; avoids raw clinical narratives, note bodies, detailed claim data, and sensitive free text in audit change payloads.
- `internal_detail`: internal detailed profile requiring export, audit, or admin permission.
- `compliance_evidence`: compliance evidence profile requiring compliance, audit, QMS, or admin permission.

Remaining future needs:

1. Define role-aware field visibility for live UI rendering of demographics, contacts, insurance identifiers, clinical notes, results, and billing identifiers.
2. Add production-grade free-text redaction review for notes, adverse event descriptions, investigation findings, denial notes, and audit reasons.
3. Add object-storage/WORM controls for immutable export artifacts if external delivery is later approved.
4. Add production policy signoff for which roles may request `internal_detail` and `compliance_evidence`.
5. Add compliance signoff for the small-cell suppression threshold before external analytics sharing.

## Retention Notes

Retention is not fully encoded in RC1. Soft delete flags, status history tables, and workflow operation audit entries provide implementation evidence, but production retention requires approved policy for:

- patient/donor clinical records;
- donor eligibility and deferral records;
- EMR notes and amendments;
- order/result and critical acknowledgement evidence;
- billing/claims/payments/denial records;
- quality/adverse event/CAPA evidence;
- workflow operation audit and export metadata;
- backups and object-storage mirrors.
