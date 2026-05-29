# Conformed Dimension Alignment

## Site Alignment

| Conformed site id | Site code | Clinical role | ERP/HR alignment |
|---|---|---|---|
| `SITE-ALACHUA` | `ALACHUA` | Manufacturing quality and donor operations support | ERP NetSuite/SAP site id and HR ADP site id |
| `SITE-WLAF` | `WLAF` | Biologics manufacturing quality support | ERP NetSuite/SAP site id and HR ADP site id |
| `SITE-EP` | `EP` | Distribution, QA, shared services, portfolio routing | ERP `SITE-EP` and HR `SITE-EP` |
| `SITE-GLENCOE` | `GLENCOE` | Processing support | ERP NetSuite/SAP site id and HR ADP site id |
| `SITE-NEUNK` | `NEUNK` | Germany manufacturing/regulatory support | ERP NetSuite/SAP site id and HR ADP site id |
| `SITE-GLASGOW` | `GLASGOW` | Clinical and regulatory support | ERP NetSuite/SAP site id and HR ADP site id |
| `SITE-MARTON` | `MARTON` | Production and APAC support | ERP NetSuite/SAP site id and HR ADP site id |

The current database schema does not require a `site_id` column on every operational table. The data producer adds site context into JSON detail payloads for newly generated activity, and future EDW logic should use a site crosswalk.

## User And Worker Alignment

| Clinical concept | Clinical key | HR alignment |
|---|---|---|
| Internal clinical reviewer | `dim_user.user_id`, `email` | Future crosswalk to `adp_workers.worker_id` |
| QA user | `dim_user.user_id`, role/department | Future crosswalk to HR worker and department |
| Partner portal user | `dim_user.user_id`, `organization_id` | External user; not an HR worker unless separately onboarded |
| Manager/owner | `assigned_to_user_id`, `business_owner` text | Map to HR only through explicit governance |

## Partner, Vendor, Customer Alignment

- `dim_organization.organization_id` is the Clinical source key for partner organizations.
- ERP `vendor_id` and `customer_id` remain source-native and map through a downstream cross-reference table.
- HubSpot `hs_object_id` remains HubSpot-native and can be matched to Clinical partner/customer organizations by curated mapping, normalized name, and domain.

## Product And Tissue Alignment

| Clinical tissue/product | Clinical source fields | ERP alignment |
|---|---|---|
| Bone | `dim_tissue_type.tissue_name`, `product_or_tissue` | Allograft material family |
| Cornea | `dim_tissue_type.tissue_name`, `product_or_tissue` | Allograft material family |
| Dermal Matrix | `dim_tissue_type.tissue_name`, `product_or_tissue` | Allograft/regenerative medicine product family |
| Heart Valve | `dim_tissue_type.tissue_name`, `product_or_tissue` | Cardiovascular tissue family |
| Skin | `dim_tissue_type.tissue_name`, `product_or_tissue` | Dermal tissue family |
| Tendon | `dim_tissue_type.tissue_name` | Musculoskeletal allograft family |
| Organ | `dim_tissue_type.tissue_name` | Clinical referral concept, not directly ERP-managed |
