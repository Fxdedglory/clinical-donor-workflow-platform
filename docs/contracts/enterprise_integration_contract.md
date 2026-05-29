# Enterprise Integration Contract

This Clinical Donor Platform is a regulated clinical workflow source-system simulator. It produces donor screening, partner portal, QMS, vendor SLA, audit, document, and workflow data for future ingestion into the enterprise EDW. Snowflake, dbt, Power BI, and cross-system orchestration stay outside this repo.

## Conformed Dimensions

| Dimension | Clinical source tables/exports | Required alignment |
|---|---|---|
| Site/location | Producer site context in JSON details and future EDW crosswalks | Use shared site ids: `SITE-ALACHUA`, `SITE-WLAF`, `SITE-EP`, `SITE-GLENCOE`, `SITE-NEUNK`, `SITE-GLASGOW`, `SITE-MARTON`. |
| Partner organization | `operational.dim_organization`, partner portal tables | `organization_id` remains Clinical-native; future EDW maps it to ERP vendors/customers where the real-world entity overlaps. |
| Worker/employee | `operational.dim_user` for internal users | Internal users map to HR workers only through verified email or an explicit crosswalk. |
| Vendor | `operational.dim_vendor`, `operational.fact_vendor_incident` | Vendor records can align to ERP vendors by curated cross-reference, normalized name, and system/service context. |
| Product/material/tissue family | `operational.dim_tissue_type`, `product_or_tissue` fields, producer product context | Tissue concepts map to ERP product/material families downstream; do not overwrite source tissue keys. |
| Department | `operational.dim_user.department`, workflow queues | Clinical departments are role/workflow-oriented and should align to HR/ERP departments by mapping, not direct key reuse. |
| Source system | Exported Clinical CSV batches | Exports add `source_system`, `source_table`, `source_record_id`, and source timestamp aliases. |
| Batch/run/extraction metadata | Producer run history, validation, and export manifests | Preserve `ingestion_batch_id`, `extraction_batch_id`, `generated_at`, `extracted_at`, row counts, and checksums. |

## Common Column Expectations

Database tables keep their operational schema. Export batches add EDW-friendly metadata columns:

```text
source_system
source_table
source_record_id
source_created_at
source_updated_at
ingestion_batch_id
extraction_batch_id
generated_at
extracted_at
organization_id
user_id
vendor_id
donor_pk
tissue_type_id
created_at
updated_at
submitted_at
opened_at
closed_at
```

Site and product-family context is currently stored in generated JSON detail payloads where the operational tables already have flexible metadata fields. Future schema migrations may promote those values into first-class columns if the hosted app needs direct filtering.

## Cross-System Rules

- Clinical `SITE-EP` is the conformed Eden Prairie site id and aligns to ERP and HR.
- Clinical internal users are operational app users first; HR worker alignment must use email or a curated worker/user crosswalk.
- Clinical partner organizations can align to ERP vendors, ERP customers, and HubSpot companies only through a future cross-reference table.
- Clinical tissue/product concepts align to ERP material families downstream, especially allograft and regenerative medicine product families.
- Export `source_record_id` is derived from the database primary key for each exported source table.
- Downstream EDW surrogate keys are not created in this source simulator.

## Validation

`backend/app/services/data_producer.py` validates required clinical relationships, timestamp consistency, audit-event integrity, conformed site constants, and product-family mappings. Export batches include checksums and source metadata for future Fivetran/dlt-style raw ingestion.
