# Clinical Demo Autofill Deployment Result

Date: 2026-06-01

## Scope

Committed, pushed, deployed, and verified the Clinical login demo autofill controls for the hosted teemails Clinical app.

## Git

| Item | Value |
|---|---|
| Branch | `main` |
| Commit | `eb70e3e` |
| Message | `add demo login autofill` |
| Remote | `origin/main` |

## Azure Deployment

| Item | Value |
|---|---|
| Web App | `app-teemails-clinical-dev` |
| Resource group | `rg-teemails-portfolio-dev-wcus` |
| Subscription | `27369a6a-a680-44e3-b04f-244b3e920d6c` |
| Final deployment ID | `b308ab1c-1120-4021-b478-c7fe2ae25506` |
| Final status | `RuntimeSuccessful` |

Deployment note: the first ZIP used Windows-style entry names, which left the frontend unavailable. The final deployment used a Linux-safe forward-slash ZIP and clean App Service deployment. `SCM_DO_BUILD_DURING_DEPLOYMENT=true` and `ENABLE_ORYX_BUILD=true` are enabled for this app so dependencies are restored after clean ZIP deployments.

## Validation

| Check | Result |
|---|---|
| `python -m pytest tests/test_runtime_smoke.py` | 15 passed, 1 warning |
| `npm run build` | Passed |
| `python scripts/start_app_service.py --check` | Passed |
| Secret scan on changed file | No secret values found |
| Live `https://teemails.com/Clinical/login` | 200, frontend index served |

## Browser Verification

Playwright fallback was used because the Browser plugin was not available.

| Control | Expected username | Verified | Password autofill |
|---|---:|---|---|
| Demo User | `clinical` | Yes | Remained empty |
| Demo QA | `qa` | Yes | Remained empty |
| Demo Operations | `opsmanager` | Yes | Remained empty |

Screenshot evidence:

```text
E:\temp\clinical-demo-autofill-live.png
```

## Remaining Notes

- Password entry remains explicit by design. No demo password was embedded or exposed.
- No Snowflake, dbt, Power BI, Airflow, ERP, HR, or Cloudflare router changes were made for this Clinical deployment.
