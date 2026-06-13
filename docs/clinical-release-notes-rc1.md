# Clinical Release Notes RC1

Release candidate: RC1 Security / Production Readiness Pass

Review date: 2026-06-13

RC2 dependency update: the Vite/esbuild advisories recorded in RC1 were remediated in RC2 with a bounded Vite 8 and React plugin 6 upgrade.

## Baseline

Latest accepted baseline commit:

```text
ee40f42 Hardening pass for clinical release candidate
```

Sprints 0 through 11 and RC0 are complete. RC1 adds security and production-readiness documentation without adding new clinical modules.

## Completed Clinical Modules

- Patient / Donor Registration
- Scheduling
- Screening / Eligibility
- EMR / Encounters
- Orders / Results
- Care Plans
- Billing / Insurance
- Quality / Compliance
- Clinical Administration
- Reporting / Analytics Readiness
- Workflow audit foundation
- RBAC and external partner restriction foundation

## RC1 Additions

- Security readiness review with repo-native scan process, environment expectations, known findings, and remediation plan.
- RBAC enforcement review updates, including route-level notes and RC2 remediation items.
- Export permission review for analytics exports, compliance exports, audit evidence, report audit activity, and RBAC metadata.
- PHI/ePHI field inventory by clinical module with masking, encryption, and retention considerations.
- Audit durability implementation plan for database-backed append-only audit plus object-storage mirror.
- Production readiness runbook with environment variables, migration, validation, smoke testing, rollback, and limitations.
- Demo script covering end-to-end clinical workflow presentation.
- Lightweight documentation inventory tests.

## Validation Status

RC1 readiness checks performed during the pass:

- `.\.venv\Scripts\python.exe scripts\preflight_check.py` passed.
- `.\.venv\Scripts\python.exe -m pip check` passed.
- `cd frontend; npm audit --audit-level=high` reported two high-severity Vite/esbuild advisories requiring a Vite 8 major upgrade.

Final sprint validation must include:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

## Known Limitations

- Production workflow audit storage is not yet database-backed.
- PHI/ePHI masking and redaction are documented but not implemented.
- Frontend dependency audit had unresolved high-severity Vite/esbuild advisories in RC1; this was resolved in RC2.
- Production startup does not yet reject unsafe default secrets and cookie settings.
- Generic foundation workflow commit endpoint is confirmation-guarded but not user-authenticated.
- Report audit activity currently rides on report-read access and should be reviewed for least privilege.
- External integrations remain out of scope: Snowflake, dbt, Power BI, FHIR/HL7, clearinghouse submission, notification delivery, and approval execution.

## Next-Phase Recommendations

1. Implement database-backed append-only workflow audit and backfill existing JSON operations.
2. Add production startup safety gates for secret/cookie/MFA/encryption defaults.
3. Continue frontend dependency audit checks after the RC2 Vite/esbuild remediation.
4. Add generated route-permission and export-permission drift tests.
5. Define and implement PHI masking/export profiles.
6. Complete external identity/MFA production design before broad go-live.
