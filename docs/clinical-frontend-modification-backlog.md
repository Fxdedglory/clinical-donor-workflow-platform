# Clinical Frontend Modification Backlog

Task: `CLINICAL-FRONTEND-MOD-00`

Date: `2026-06-15`

This backlog prepares future frontend implementation work. It does not authorize deployment, DNS, `clinical.teemails.com` launch activation, backend workflow changes, database schema changes, dependency remediation, or broad redesign.

## Classification Key

| Classification | Meaning |
| --- | --- |
| `safe_now` | Frontend-only change that can be implemented against the current UI contracts |
| `needs_backend_contract` | Requires approved API/data/workflow contract or backend behavior confirmation |
| `needs_design_decision` | Requires Product Owner or design acceptance before implementation |
| `needs_auth_or_deployment_approval` | Requires security, auth, SSO, hosting, DNS, TLS, or deployment approval |
| `blocked_by_dirty_worktree` | Must not proceed while it would touch protected or unrelated dirty files |
| `defer` | Valuable but not next-sprint work |

## Prioritized Backlog

| Priority | Item | Classification | Scope | Acceptance signal |
| ---: | --- | --- | --- | --- |
| 1 | Normalize Clinical route header anatomy | `safe_now` | Completed in `CLINICAL-FE-04` with shared route header and dashboard shell alignment | Route headers scan consistently on desktop and mobile without changing endpoints |
| 2 | Standardize filter and action bars | `safe_now` | Apply consistent filter grouping, wrapping, and action priority across patients, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin | Dense route controls wrap cleanly and primary action remains obvious |
| 3 | Extract reusable clinical state components | `safe_now` | Completed in `CLINICAL-FE-04` for loading, empty, selected-row, and retry/error route states | Routes use consistent state copy and visual treatment |
| 4 | Status badge vocabulary review | `safe_now` | Completed in `CLINICAL-FE-04` for frontend label normalization and common tone mapping | Same status means same color/tone across modules |
| 5 | Modal Preview -> Commit visual standardization | `safe_now` | Partially completed in `CLINICAL-FE-04` with shared modal header, step indicator, validation summary, and commit labels | Representative modals show consistent validation, preview, commit, cancel, and error states |
| 6 | Dense table mobile summaries | `needs_design_decision` | Convert highest-density table rows into mobile summaries with optional detail expansion for orders, billing, quality, reports, and patient detail | Mobile views reduce horizontal scroll while preserving key identifiers and status |
| 7 | Clinical dashboard operational content | `needs_backend_contract` | Replace dashboard placeholder with module status, workflow operations, recent audit activity, and next-action summaries | Dashboard renders approved backend fields and graceful empty/error states |
| 8 | Patient/donor detail timeline polish | `safe_now` | Improve detail route hierarchy for demographics, contacts, insurance, consents, audit activity, and handoffs | Patient detail reads as a stable clinical record view even during partial API failures |
| 9 | Screening eligibility badge clarity | `safe_now` | Improve result, deferral, override, and eligibility status labeling in screening pages | Eligibility state is readable without opening every detail panel |
| 10 | Orders/results worklist refinement | `safe_now` | Tighten worklist priority columns, result flags, critical acknowledgement, and cancel/correction affordances | Ordering and critical result actions are visually distinct and compact |
| 11 | Care plan aging and task hierarchy | `safe_now` | Clarify goals, interventions, tasks, progress, close state, and overdue/priority signaling | Care plan page highlights aging and next task without extra scanning |
| 12 | Billing/revenue cycle work queue hierarchy | `safe_now` | Refine insurance verification, charges, claims, payments, denials, and account context | Work queue separates billing state, payer state, and user action clearly |
| 13 | Quality evidence/export gating copy | `safe_now` | Clarify audit evidence export, CAPA links, adverse event, closure, and evidence profile messaging | Quality export users see what is included, suppressed, or approval-gated |
| 14 | Reports export profile guidance | `safe_now` | Improve copy for aggregate safe, external safe, audit metadata, internal detail, and compliance evidence profiles | Export preview clearly explains redaction and suppression before commit |
| 15 | Clinical admin configuration layout | `safe_now` | Reduce density in config lists and align configure actions, version history, RBAC, and recent audit | Admin page remains scannable with many configuration sections |
| 16 | Keyboard and focus audit | `needs_design_decision` | Review tab order, focus rings, modal focus behavior, and screen-reader labels | Accessibility issues are documented and small fixes are queued |
| 17 | Route-level visual smoke automation | `needs_design_decision` | Decide whether to commit a lightweight screenshot or route-smoke harness instead of relying on local ignored CDP scripts | Future frontend sprints have repeatable visual evidence |
| 18 | Auth/SSO-aware navigation | `needs_auth_or_deployment_approval` | Personalize navigation beyond current local role checks, or integrate future Entra ID/SSO behavior | Security approves role/navigation contract |
| 19 | Activate `clinical.teemails.com` launch path | `needs_auth_or_deployment_approval` | Enable public app launch links only after hosting, DNS, TLS, health checks, and approvals | Clinical launcher action is explicitly approved and validated |
| 20 | New UI component library or broad redesign | `defer` | Evaluate only if current CSS/component approach cannot support future Product Owner design requirements | Separate design-system decision package exists |
| 21 | Backend workflow or audit contract changes | `needs_backend_contract` | Any change to commit endpoints, audit entries, workflow transitions, or PHI/export payloads | API tests and Project OS preview/commit rules are updated |
| 22 | Protected seed/demo CLI cleanup | `blocked_by_dirty_worktree` | `backend/app/cli.py` has unrelated protected dirty changes | Separate authorized backend/data task owns any CLI edits |

## Recommended Sprint Sequence

### CLINICAL-FE-04 - Clinical Route-Level Refinement And Usability Polish

Completed.

Scope:

- Route header/action consistency.
- Shared clinical empty/loading/error components.
- Status badge vocabulary cleanup.
- Frontend-only modal Preview -> Commit visual alignment.
- Focused route-state polishing for patient detail, scheduling, screening, encounters, orders, care plans, billing, quality, reports, and admin.

Boundaries:

- No backend workflow logic changes.
- No database schema changes.
- No deployment.
- No DNS or `clinical.teemails.com` activation.
- No site-wide, HR, or ERP repo changes.
- No dependency remediation or new UI library.

Evidence:

- `docs/clinical-fe04-route-polish-summary.md`
- Validation passed: preflight, pytest, frontend build, npm audit, app-service startup check, and Vite preview route smoke.

### CLINICAL-FE-05 - Mobile Dense-Route Interaction

Recommended next sprint.

Scope:

- Product/design review of mobile row summaries.
- Detail expansion patterns for dense clinical tables.
- Mobile keyboard/focus review.

Dependency:

- Design decision for mobile dense-table behavior.

### CLINICAL-FE-06 - Dashboard Contract And Operational Summary

Scope:

- Implement a real Clinical dashboard after backend data contract approval.
- Include module status, workflow operations, audit activity, next actions, and deployment-readiness messaging.

Dependency:

- Approved backend contract and seeded/demo data expectations.

### CLINICAL-FE-07 - Visual QA Automation

Scope:

- Decide and implement a lightweight committed route-smoke or screenshot evidence harness.
- Avoid heavy tooling unless Product/Security/Ops accept it.

Dependency:

- Design and engineering decision on test ownership and artifact storage.

### CLINICAL-FE-LAUNCH - Production Launch Activation

Scope:

- Only after separate approval: activate production launch path and public URL behavior for `https://clinical.teemails.com`.

Dependencies:

- Clinical hosting approved.
- DNS and TLS complete.
- Health checks passing.
- Product/Security/Ops approval recorded.
- teemails launcher action explicitly approved.

## Blockers And Risks

- `backend/app/cli.py` remains protected dirty work and must not be included in frontend planning commits.
- `clinical.teemails.com` remains a recommended future URL only; no active launch link is approved.
- Startup checks still report local production-hardening warnings that must be resolved or explicitly configured before production.
- FE-03 visual QA evidence is strong but uses local CDP scripts under ignored metadata rather than a committed browser-test suite.
- The frontend is concentrated in `App.jsx`, so broad changes can have wide blast radius. Future implementation should make small route-level changes and verify each route.
- Several workflow modals are separate implementations, increasing consistency risk for Preview -> Commit copy and action states.
- Clinical dashboard remains foundation-level until backend dashboard data contract is approved.
