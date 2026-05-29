# Source System Key Strategy

## Rules

- Keep Clinical database primary keys source-native.
- Do not create EDW surrogate keys in this app.
- Add EDW-friendly metadata in export batches instead of forcing broad operational schema changes.
- Use explicit crosswalks for Clinical-to-ERP, Clinical-to-HR, and Clinical-to-HubSpot matching.

## Clinical Key Columns

| Concept | Source key | EDW natural key strategy |
|---|---|---|
| Exported source row | `source_system`, `source_table`, `source_record_id` | Raw/staging uniqueness |
| Donor | `donor_pk`, `donor_identifier` | Clinical source donor identity |
| Donor review | `review_id`, `donor_id` | Donor intake/review grain |
| Partner organization | `organization_id` | Clinical-native organization key; future partner/vendor/customer crosswalk |
| Partner submission | `submission_id`, `submission_code` | Partner portal submission grain |
| Internal/partner user | `user_id`, `email` | Source user key; internal users may map to HR workers by email/crosswalk |
| Vendor | `vendor_id` | Clinical vendor/SLA key, mapped to ERP vendor later |
| Tissue type | `tissue_type_id`, `tissue_name` | Clinical tissue/product key mapped to ERP material families |
| QMS deviation/CAPA | `deviation_id`, `capa_id` | Quality event and corrective-action grain |

## Export Metadata Semantics

| Column | Meaning |
|---|---|
| `source_system` | `clinical_donor_platform` |
| `source_table` | Exported table/entity name |
| `source_record_id` | Primary-key value from the exported database row |
| `source_created_at`, `source_updated_at` | Best available source timestamps |
| `ingestion_batch_id`, `extraction_batch_id` | Simulated source extract batch id |
| `generated_at`, `extracted_at` | Export generation/extraction timestamps |

## Crosswalk Policy

Create downstream crosswalks later for:

```text
clinical dim_user.email -> HR adp_workers.worker_id
clinical dim_organization.organization_id -> ERP vendor/customer ids
clinical dim_organization.organization_id -> HubSpot hs_object_id
clinical tissue_type_id/tissue_name -> ERP material/product family
```
