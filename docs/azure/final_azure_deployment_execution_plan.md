# Final Azure Deployment Execution Plan

This is a future execution checklist. Do not provision resources until explicitly approved.

## Preflight

1. Confirm target subscription ID and tenant.
2. Re-run Azure inventory to avoid duplicate resources.
3. Confirm App Service Linux Python quota in the chosen region.
4. Confirm PostgreSQL Flexible Server availability if hosted persistence is required.
5. Confirm Cloudflare/portfolio routing decision for `/Clinical`.
6. Confirm the repo is clean and pushed.

## No-Duplicate Inventory Commands

```powershell
az account show --output table
az group list --output table
az appservice plan list --output table
az webapp list --output table
az postgres flexible-server list --output table
az storage account list --output table
az monitor app-insights component show --app <name> --resource-group <rg>
```

## Proposed Resource Names

Use only after approval:

- Resource group: `rg-teemails-portfolio-dev-eus2`
- App Service Plan: `asp-teemails-portfolio-linux-dev-eus2`
- Web App: `app-teemails-clinical-dev-eus2`
- PostgreSQL server: `psql-teemails-portfolio-dev-eus2`
- Database: `clinical_donor_workflow`
- App Insights: `appi-teemails-clinical-dev-eus2`

## Deployment Steps

1. Create or reuse resource group.
2. Create or reuse Linux App Service Plan.
3. Create Clinical Web App with Python 3.12 runtime.
4. Configure app settings from `app_settings_reference.md`.
5. Create PostgreSQL database only if approved.
6. Configure `DATABASE_URL` with TLS.
7. Deploy code from GitHub or ZIP.
8. Build React frontend:

```powershell
cd frontend
npm install
npm run build
cd ..
```

9. Run startup check:

```powershell
python scripts/start_app_service.py --check
```

10. Run migrations:

```powershell
python -m alembic upgrade head
```

11. Seed controlled demo data:

```powershell
python scripts/run_data_producer.py seed --records 1200 --seed 42 --confirm
```

12. Validate:

```powershell
python scripts/run_data_producer.py validate --confirm
```

13. Smoke test:

```text
/api/health
React operational shell
System Health
Data Producer
Partner Portal
Power BI analytics route plan at /analytics
```

## Rollback

1. Keep previous deployment artifact available.
2. Disable data producer API if needed:

```text
ENABLE_DATA_PRODUCER_API=false
```

3. Restore previous App Service deployment slot or previous ZIP if slots are not used.
4. Do not delete databases during rollback without separate approval.

## Commands Not To Run Without Approval

```powershell
az group create
az appservice plan create
az webapp create
az postgres flexible-server create
az resource delete
az group delete
az deployment group create
```
