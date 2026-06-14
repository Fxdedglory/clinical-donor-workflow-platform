# Clinical FE-02 Route Polish

Task: `CLINICAL-FE-02`

Baseline inputs:

- `docs/clinical-backend-connected-visual-verification.md`
- `docs/clinical-swiss-theme-frontend-implementation.md`
- `docs/clinical-figma-design-context.md`
- `metadata/visual_audit/clinical/fe01_backend_connected/`

## Before / After Summary

FE-01 backend-connected verification showed no page-level horizontal overflow, but dense secondary panels in Orders, Billing, Quality, Reports, and Patient Detail split identifiers and short status labels into vertical fragments.

FE-02 keeps the existing backend workflows and API behavior intact while improving route-specific density:

- Long clinical identifiers now render as monospace, copy-friendly, single-line values with title tooltips.
- Compact clinical tables use internal scroll only when unavoidable.
- Billing and Quality secondary panels use wider two-column desktop grids.
- Orders worklist now prioritizes order, catalog, state, and action so the row action remains visible.
- Patient contact, insurance, consent, and activity tables use fewer display columns.
- Reports panels use wider audit/export sections while preserving suppression and export-profile indicators.

## Routes Changed

- `/clinical/orders`
- `/clinical/billing`
- `/clinical/quality`
- `/clinical/reports`
- `/clinical/patients/:id`

## Dense Layout Strategy

The shared clinical table path now supports opt-in compact rendering. Compact tables use semantic cell classes for identifiers, tokens, dates, contact values, statuses, priorities, and result flags. The default table rendering remains unchanged for legacy donor/QMS surfaces.

Route-specific changes:

- Orders: compressed the worklist into priority columns and kept `Open` visible; result/detail tables use compact internal scrolling.
- Billing: compressed charges, claims, payments, denials, and insurance verification into summary columns with formatted money and status chips.
- Quality: widened secondary panels and compressed investigation, status history, export, and linkage tables.
- Reports: widened report/audit/export panels and kept suppressed metrics visible without raw suppressed counts.

## Patient Detail Field Strategy

Patient detail uses compact display rows for contacts, insurance, consents, and audit activity. Email and phone values stay single-line and readable; insurance payer/member ID is grouped so the member identifier remains visible and copy-friendly. PHI-aware rendering and fallback state remain intact.

## Reports / Suppression UX Strategy

Reports preserve the existing aggregate-safe behavior. Suppressed metrics remain labeled with suppression badges and thresholds, raw suppressed counts remain hidden, and export-profile/redaction indicators remain visible in both desktop and mobile captures.

## Screenshot Evidence

Updated backend-connected screenshots were captured with the seeded local demo database:

```text
metadata/visual_audit/clinical/fe02_route_polish/
```

Captured files:

- `clinical-orders-desktop.png`
- `clinical-billing-desktop.png`
- `clinical-quality-desktop.png`
- `clinical-reports-desktop.png`
- `clinical-patient-detail-desktop.png`
- `clinical-orders-mobile.png`
- `clinical-billing-mobile.png`
- `clinical-quality-mobile.png`
- `clinical-reports-mobile.png`
- `clinical-patient-detail-mobile.png`
- `manifest.json`

The generated manifest reported no page-level horizontal overflow, no vertical identifier fragments, no framework overlay, and no console errors for the captured routes.

## Remaining FE-03 Recommendations

1. Add focused frontend tests for compact clinical table rendering, patient detail fallback, and suppression indicators.
2. Add route-level visual regression automation for the Clinical workspace.
3. Continue modal-level polish for Preview -> Commit workflows after route panels are accepted.
4. Review mobile table interaction affordances with Product Owner once FE-02 screenshots are accepted.
