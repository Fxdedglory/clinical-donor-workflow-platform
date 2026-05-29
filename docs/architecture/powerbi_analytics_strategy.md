# Power BI Analytics Strategy

## Decision

Clinical analytics should flow through the downstream data platform and Power BI Service, not Streamlit.

Future route:

```text
https://teemails.com/analytics
```

## Target Flow

```text
ERP Simulator
HR Workforce Platform
Clinical Donor Platform
        |
        v
Data_Platform_Engineer_Cloud_Platform
        |
        v
Snowflake
        |
        v
dbt L1/L2/L3
        |
        v
Power BI Service
        |
        v
teemails.com/analytics
```

## Clinical Analytics Domains

Future Power BI datasets and reports should cover:

- donor referral intake and screening throughput
- eligibility decision outcomes
- medical/social history risk patterns
- infectious disease testing turnaround
- tissue recovery suitability
- processing release cycle time
- QMS deviations and CAPA aging
- partner portal submission lifecycle
- vendor SLA breaches
- audit and workflow activity
- clinical review queue aging

## Implementation Options

| Option | Description | Fit |
|---|---|---|
| Power BI Service links | `teemails.com/analytics` links to secured Power BI apps/reports. | Lowest complexity first step. |
| Secure embed for organization | Embed Power BI reports for authenticated internal users. | Good later fit if Entra ID is in place. |
| Power BI Embedded capacity | App owns embedding experience and capacity. | Higher cost; not recommended initially. |
| Public publish-to-web | Public iframe-style reporting. | Not appropriate for clinical/partner-style demos. |

## Access Model

Recommended:

- Internal portfolio viewers authenticate through Microsoft Entra ID.
- Power BI workspace roles control report access.
- App roles map to report audiences where feasible.
- Partner-facing analytics are separated from internal clinical/QMS analytics.

## What This Repo Should Do

This repo should:

- Generate realistic clinical source-system data.
- Expose operational APIs.
- Export source batches.
- Track data freshness and validation.
- Document future handoff semantics.

This repo should not:

- Implement Snowflake models.
- Implement dbt transformations.
- Host production analytics dashboards.
- Embed Power BI before the downstream platform is ready.
