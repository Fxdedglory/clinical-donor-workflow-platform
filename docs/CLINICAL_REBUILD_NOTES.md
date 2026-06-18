# Clinical Rebuild Notes

Timestamp: 20260618-161414

Decision:
- Rebuild Clinical as a new Meridian-style portfolio app.
- Use green accent theme.
- Align product workflows with Evergen-style donor services operations.
- Preserve legacy frontend under deprecated/legacy-clinical-20260618-161414/frontend.
- Keep app/backend in place as legacy reference for now.

Legacy backend status:
not-found

Primary roles:
- Intake Coordinator
- Clinical Reviewer
- QA Specialist
- Vendor Operations
- Operations Manager
- System Administrator
- Technology Analyst

Target workflows:
- Donor intake
- Donor screening
- Eligibility review
- Scheduling
- Clinical review
- QA/compliance
- Vendor operations
- Reporting and analytics readiness
- Administration and audit evidence

Target architecture:
teemails.com/Clinical
→ Cloudflare/Astro proxy
→ independent Azure Clinical App Service
→ Clinical event API
→ Azure Data Lake raw/apps/clinical/events
→ later Snowflake/dbt/Power BI