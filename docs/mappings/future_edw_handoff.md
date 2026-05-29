# Future EDW Handoff

This repo remains the Clinical source-system simulator. Future ingestion, Snowflake, dbt L1/L2/L3, Power BI, and `teemails.com/analytics` should be implemented outside this repo.

## Future Raw/Staging Pattern

Suggested raw uniqueness:

```text
source_system + source_table + source_record_id
```

Suggested incremental watermarks:

```text
source_updated_at, extracted_at, extraction_batch_id
```

Suggested source freshness:

```text
GET /api/monitoring/source-freshness
GET /api/monitoring/validation
GET /api/monitoring/export-manifest
```

## Future Conformed Dimensions

| Dimension | Source inputs |
|---|---|
| `dim_site` | Producer site context plus ERP/HR site crosswalks |
| `dim_partner_organization` | `dim_organization`, supplier relationships, HubSpot companies |
| `dim_worker` | Clinical `dim_user` for internal users plus HR worker crosswalk |
| `dim_vendor_partner` | Clinical vendors, ERP vendors, Clinical partner organizations |
| `dim_product_material` | Clinical tissue types, ERP items/materials |
| `dim_fiscal_period` | Derived from Clinical timestamps and aligned to ERP/HR periods |

## Future Facts

| Fact | Clinical source inputs |
|---|---|
| `fact_donor_screening` | Donor, screening, medical/social history, infectious results |
| `fact_eligibility_decision` | Eligibility decisions and rules |
| `fact_partner_submission` | Partner submissions, statuses, documents, messages |
| `fact_quality_event` | Deviations, CAPAs, complaints |
| `fact_vendor_sla` | Vendor incidents and SLA breach status |
| `fact_audit_event` | Audit, security audit, workflow transitions, signatures |

## Azure Seed/Producer Plan After Contract Pass

Do not run these until explicitly approved:

```powershell
az webapp ssh --resource-group rg-teemails-portfolio-dev-wcus --name app-teemails-clinical-dev
python scripts/run_data_producer.py seed --records 1200 --seed 42 --force --confirm
python scripts/run_data_producer.py incremental --seed 43 --scale 1 --confirm
python scripts/run_data_producer.py validate --confirm
python scripts/run_data_producer.py export --batch-id azure_seed_clinical_20260529 --confirm
```

After seeding, validate:

```text
https://teemails.com/Clinical
https://teemails.com/Clinical/api/health
https://teemails.com/Clinical/api/generation/status
```
