# Clinical Frontend Screenshot Evidence Index

Task: `CLINICAL-FRONTEND-QA-00`

Date: `2026-06-15`

Evidence location: `metadata/visual_audit/clinical/frontend_qa/current/`

The screenshot directory is ignored by `.gitignore`; this committed document indexes the generated evidence without committing PNG artifacts or local browser profiles.

## Evidence Summary

| Item | Result |
| --- | --- |
| Manifest | `metadata/visual_audit/clinical/frontend_qa/current/manifest.json` |
| Capture helper | `metadata/visual_audit/clinical/frontend_qa/current/capture-clinical-frontend-qa.mjs` |
| Browser | Installed Chrome through local CDP |
| Browser plugin | Not available |
| Playwright | Not installed; no dependency added |
| Route viewport checks | 39 |
| Screenshots | 43 |
| Route failures | 0 |
| Modal failures | 0 |
| Console events | 0 |
| Sidebar collapse | Passed |
| Mobile drawer | Passed |

## Route Screenshots

| Route | Desktop | Tablet | Mobile |
| --- | --- | --- | --- |
| `/` | `clinical-landing-desktop.png` | `clinical-landing-tablet.png` | `clinical-landing-mobile.png` |
| `/clinical/dashboard` | `clinical-dashboard-desktop.png` | `clinical-dashboard-tablet.png` | `clinical-dashboard-mobile.png` |
| `/clinical/patients` | `clinical-patients-desktop.png` | `clinical-patients-tablet.png` | `clinical-patients-mobile.png` |
| `/clinical/patients/PT-DEMO-001` | `clinical-patient-detail-desktop.png` | `clinical-patient-detail-tablet.png` | `clinical-patient-detail-mobile.png` |
| `/clinical/scheduling` | `clinical-scheduling-desktop.png` | `clinical-scheduling-tablet.png` | `clinical-scheduling-mobile.png` |
| `/clinical/screening` | `clinical-screening-desktop.png` | `clinical-screening-tablet.png` | `clinical-screening-mobile.png` |
| `/clinical/encounters` | `clinical-encounters-desktop.png` | `clinical-encounters-tablet.png` | `clinical-encounters-mobile.png` |
| `/clinical/orders` | `clinical-orders-desktop.png` | `clinical-orders-tablet.png` | `clinical-orders-mobile.png` |
| `/clinical/care-plans` | `clinical-care-plans-desktop.png` | `clinical-care-plans-tablet.png` | `clinical-care-plans-mobile.png` |
| `/clinical/billing` | `clinical-billing-desktop.png` | `clinical-billing-tablet.png` | `clinical-billing-mobile.png` |
| `/clinical/quality` | `clinical-quality-desktop.png` | `clinical-quality-tablet.png` | `clinical-quality-mobile.png` |
| `/clinical/reports` | `clinical-reports-desktop.png` | `clinical-reports-tablet.png` | `clinical-reports-mobile.png` |
| `/clinical/admin` | `clinical-admin-desktop.png` | `clinical-admin-tablet.png` | `clinical-admin-mobile.png` |

## Workflow Modal Screenshots

| Route | Workflow | Screenshot | Result |
| --- | --- | --- | --- |
| `/clinical/patients` | Create Patient / Donor validation | `modal-create-patient-validation-desktop.png` | Passed |
| `/clinical/scheduling` | Book Appointment form | `modal-book-appointment-form-desktop.png` | Passed |
| `/clinical/orders` | Enter Order Result form | `modal-enter-order-result-form-desktop.png` | Passed |
| `/clinical/reports` | Generate Analytics Export preview | `modal-reports-export-preview-desktop.png` | Passed |

## Evidence Interpretation

The clean manifest confirms:

- Required clinical routes rendered in desktop, tablet, and mobile viewports.
- The root route rendered authenticated dashboard content and did not fail route smoke.
- No captured route was blank, showed a framework overlay, or caused page-level horizontal overflow.
- Representative workflow modals opened and fit the desktop viewport.
- Sidebar collapse and mobile drawer interactions worked.
- Console health was clean during the route sweep.
- PHI indicators appeared on dense clinical routes; export profile and suppression indicators appeared where expected.

## Retention Note

The evidence PNGs and manifest are local generated artifacts. Preserve or archive `metadata/visual_audit/clinical/frontend_qa/current/` outside Git when a release evidence bundle needs the raw screenshots.
