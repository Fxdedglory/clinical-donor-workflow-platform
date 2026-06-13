# Clinical Demo Script

RC1 demo script date: 2026-06-13

Goal: demonstrate the complete clinical workflow foundation while clearly marking production-readiness limitations.

## Opening

1. State that Sprints 0 through 11 and RC0 are complete.
2. State that RC1 focuses on security and production readiness, not new clinical modules.
3. Call out the Preview -> Commit pattern and `X-Confirm-Generation: true` confirmation guard.
4. Call out that production audit durability, PHI masking, and external integrations are future hardening items.

## Patient Registration

1. Open `/clinical/patients`.
2. Review patient/donor list and operational status.
3. Preview a registration or demographic change.
4. Commit with confirmation and point to the resulting patient identifier.
5. Show contacts, insurance, and consents as PHI-bearing surfaces.

## Scheduling

1. Open `/clinical/scheduling`.
2. Review appointments, resources, providers, and appointment types.
3. Preview appointment booking.
4. Commit booking with confirmation.
5. Demonstrate reschedule, cancel, check-in, or no-show as planned lifecycle workflows.

## Screening / Eligibility

1. Open `/clinical/screening`.
2. Review screening sessions and templates.
3. Preview questionnaire or vitals capture.
4. Commit screening result with confirmation.
5. Show supervisor override path and deferral evidence.

## Encounter Documentation

1. Open `/clinical/encounters`.
2. Create or review an encounter.
3. Preview and save a note.
4. Sign the note with confirmation.
5. Demonstrate amendment, diagnosis, allergy, and medication flows.

## Orders / Results

1. Open `/clinical/orders`.
2. Review order catalog and existing orders.
3. Preview an order.
4. Commit the order with confirmation.
5. Add or correct a result and acknowledge critical results.

## Care Plans

1. Open `/clinical/care-plans`.
2. Review active care plans and result-linked flags.
3. Preview a care plan or care plan update.
4. Commit goals, interventions, tasks, or progress.
5. Demonstrate closure with outcome summary.

## Billing / Insurance

1. Open `/clinical/billing`.
2. Review accounts, charges, claims, denials, payments, and work queue.
3. Preview charge capture or insurance verification.
4. Commit billing operation with confirmation.
5. Explain that real clearinghouse submission is out of scope.

## Quality / Compliance

1. Open `/clinical/quality`.
2. Review quality dashboard, quality events, and adverse events.
3. Preview a quality event or adverse event.
4. Commit with confirmation.
5. Add investigation, link CAPA, close event, and review compliance export preview.

## Administration

1. Open `/clinical/admin`.
2. Review configuration versions and RBAC overview.
3. Preview an appointment type, screening template, rule, note template, order catalog, billing code, quality category, approval path, or notification template update.
4. Commit an admin configuration change with confirmation.
5. Explain that approval execution and notification delivery remain future work.

## Reports / Analytics

1. Open `/clinical/reports`.
2. Review dashboard aggregates.
3. Show patient throughput, scheduling utilization, screening outcomes, deferrals, encounter volume, orders/results, care plan aging, billing work queue, quality trends, and audit activity.
4. Preview analytics export.
5. Commit analytics export with confirmation.
6. Explain that external warehouse delivery is planned, not active.

## Audit Evidence

1. Open quality audit evidence or reports audit activity.
2. Filter by workflow, actor, entity type, or date.
3. Show workflow operation fields: operation id, workflow, entity, actor, timestamp, preview hash, status transition, reason, and changes.
4. Explain that RC1 documents the production migration from JSON audit file to database-backed append-only audit storage.

## Security And Readiness Close

1. Show `docs/clinical-security-readiness.md`.
2. Summarize the Vite/esbuild audit finding and RC2 remediation.
3. Show `docs/clinical-phi-field-inventory.md`.
4. Show `docs/clinical-production-readiness-runbook.md`.
5. Close with remaining production items: role-aware UI masking, object-storage audit immutability, external identity/secrets hardening, and governed external delivery. Note that audit durability, production startup gates, dependency hardening, route-permission drift tests, export profiles, and aggregate small-cell suppression have been implemented in post-RC hardening.
