# HubSpot Alignment Note

HubSpot remains an external SaaS/free-trial source. This repo should not implement HubSpot extraction, credentials, or downstream warehouse models.

## Expected HubSpot Company Fields

| HubSpot field | Future mapping |
|---|---|
| `hs_object_id` | HubSpot source company key |
| `name` | Candidate match to ERP customer/account and Clinical partner/customer organization |
| `domain` | Secondary company/account match key |
| `industry` | Company segmentation |
| `lifecyclestage` | Lead/customer lifecycle |
| `createdate`, `hs_lastmodifieddate` | Source metadata/watermarks |
| `hubspot_owner_id` | Future owner-to-HR-worker bridge |

## Expected HubSpot Contact Fields

| HubSpot field | Future mapping |
|---|---|
| `hs_object_id` | HubSpot contact key |
| `email` | Contact identity key |
| `firstname`, `lastname` | Contact attributes |
| `associatedcompanyid` | Company/account relationship |
| `hubspot_owner_id` | Future HR worker owner mapping |
| `createdate`, `lastmodifieddate` | Source metadata/watermarks |

## Expected HubSpot Deal Fields

| HubSpot field | Future mapping |
|---|---|
| `hs_object_id` | HubSpot deal key |
| `dealname` | Opportunity/deal descriptor |
| `dealstage` | Pipeline stage |
| `pipeline` | Pipeline key |
| `amount` | Revenue/opportunity amount |
| `closedate` | Fiscal-period alignment |
| `associatedcompanyid` | ERP customer/account and Clinical partner/customer alignment |
| `hubspot_owner_id` | Future HR worker owner mapping |

## Matching Strategy

1. Match HubSpot companies to ERP customers and Clinical organizations through a curated cross-reference table.
2. Use normalized `name` and `domain` as candidate match inputs, not guaranteed keys.
3. Map HubSpot contacts to companies first, then to partner/customer context.
4. Map HubSpot owners to HR workers by verified email or an explicit owner crosswalk.
5. Keep HubSpot keys source-native; EDW surrogate keys are downstream only.
