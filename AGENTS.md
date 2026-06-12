# Clinical Platform Project OS

## Source Of Truth

Repository implementation is not the source of truth. Build and change the platform from approved product specifications, approved clinical and donor workflow requirements, approved Figma or screenshot designs, approved data model specifications, and approved API/workflow contracts. Treat existing code as implementation evidence that must be reconciled to those artifacts.

## Operating Workflow

Every implementation task should follow this sequence:

1. Read `AGENTS.md`.
2. Inspect current repository state with `git status --short`.
3. Inventory relevant routes, components, services, schemas, data, seeds, and tests.
4. Compare implementation against approved product requirements.
5. Produce a scoped gap analysis when the requested work changes product behavior.
6. Implement only the approved sprint scope.
7. Run repository validation commands.
8. Commit cohesive changes with a clear message when requested.

## Product-First Methodology

Clinical and donor workflows must be designed around real operational behavior, not generic CRUD screens. Use module requirements and workflow contracts to drive UI, API, schema, and audit design.

Core modules include patient/donor management, scheduling, donor screening and eligibility, EMR encounters, orders/results, care plans, billing/insurance, quality/compliance, reporting, clinical administration, audit, RBAC, and approvals.

## Preview And Commit Pattern

All clinically meaningful workflows should follow:

```text
Draft -> Validate -> Preview -> Commit
```

Preview endpoints validate payloads and return a reviewable summary without mutating durable clinical state. Commit endpoints perform the durable mutation only after explicit confirmation.

## Commit Confirmation Requirement

All commit endpoints for clinical workflows must reject missing or invalid confirmation headers. The required header is:

```text
X-Confirm-Generation: true
```

This applies to registration, scheduling, screening, encounters, orders, billing, claims, quality events, adverse events, deferrals, and administrative configuration changes.

## Workflow Operation Audit

Committed clinical workflows must write an append-only operation record to:

```text
metadata/workflow_operations.json
```

Audit entries should include operation id, workflow, entity type, entity id, actor, timestamp, preview hash, confirmation status, before/after status, reason, and changed fields.

## Dirty-File Protection

The working tree may contain user or generated changes. Do not overwrite, reformat, revert, stage, or commit unrelated dirty files. If a dirty file is related to the task, inspect it and work with it. If a dirty file is explicitly protected by the user, do not modify it unless the user explicitly authorizes that change.

## Validation Commands

Use these validation commands for Sprint-level work:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_check.py
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

For backend-only changes, run focused pytest first and then the full validation set when feasible. For frontend route or UI work, run the frontend build before committing.
