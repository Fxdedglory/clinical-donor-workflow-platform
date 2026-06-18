import React, { useEffect, useMemo, useState } from "react";
import {
  CLINICAL_USER_ID,
  getClinicalHealth,
  getClinicalRecentEvents,
  sendClinicalEvent
} from "./api";
import "./styles.css";

const portfolioNavItems = [
  {
    "label": "Home",
    "href": "https://teemails.com/"
  },
  {
    "label": "ERP",
    "href": "https://teemails.com/ERP"
  },
  {
    "label": "HR",
    "href": "https://teemails.com/HR"
  },
  {
    "label": "Clinical",
    "href": "https://teemails.com/Clinical"
  },
  {
    "label": "Monitor",
    "href": "https://teemails.com/Monitor"
  },
  {
    "label": "Analytics",
    "href": "https://teemails.com/Analytics"
  },
  {
    "label": "About-me",
    "href": "https://teemails.com/about-me"
  }
];
const appNavItems = [
  {
    "label": "Command Center",
    "path": "/Clinical/",
    "key": "dashboard"
  },
  {
    "label": "Intake",
    "path": "/Clinical/intake",
    "key": "intake"
  },
  {
    "label": "Screening",
    "path": "/Clinical/screening",
    "key": "screening"
  },
  {
    "label": "Scheduling",
    "path": "/Clinical/scheduling",
    "key": "scheduling"
  },
  {
    "label": "Clinical Review",
    "path": "/Clinical/review",
    "key": "review"
  },
  {
    "label": "Quality",
    "path": "/Clinical/quality",
    "key": "quality"
  },
  {
    "label": "Vendor Ops",
    "path": "/Clinical/vendor-ops",
    "key": "vendorOps"
  },
  {
    "label": "Reports",
    "path": "/Clinical/reports",
    "key": "reports"
  },
  {
    "label": "Administration",
    "path": "/Clinical/administration",
    "key": "administration"
  }
];
const moduleConfigs = {
  "dashboard": {
    "eyebrow": "Meridian Clinical",
    "title": "Donor services command center.",
    "description": "Manage donor intake, screening, scheduling, clinical eligibility review, QA release evidence, vendor operations, and analytics readiness in an Evergen-aligned workflow.",
    "panelTitle": "Operating model",
    "panelText": "Donor Services \u00b7 Quality Workflow \u00b7 Technology Analyst View",
    "panelStatus": "Clinical rebuild active",
    "primaryTable": "screening",
    "secondaryTable": "quality",
    "workbenchTitle": "Eligibility Workbench",
    "rolesTitle": "Evergen-Aligned Roles"
  },
  "intake": {
    "title": "Intake",
    "eyebrow": "Referral registration, demographics, consent",
    "description": "Capture donor referral packets, demographics, contact details, consent state, intake notes, and case readiness for downstream screening.",
    "idPrefix": "DON",
    "owner": "Intake Coordinator",
    "rows": [
      {
        "id": "DON-10481",
        "description": "New referral packet",
        "status": "Intake Review",
        "owner": "Intake Coordinator"
      },
      {
        "id": "DON-10482",
        "description": "Consent verification",
        "status": "Needs Outreach",
        "owner": "Intake Coordinator"
      },
      {
        "id": "DON-10483",
        "description": "Demographics update",
        "status": "Ready",
        "owner": "Technology Analyst"
      },
      {
        "id": "DON-10484",
        "description": "Insurance/contact validation",
        "status": "In Progress",
        "owner": "Intake Coordinator"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.donor_intake.created",
        "label": "Create Donor Intake",
        "idPrefix": "DON",
        "rowDescription": "New donor intake case",
        "rowStatus": "Created",
        "owner": "Intake Coordinator"
      },
      {
        "eventType": "clinical.consent.verified",
        "label": "Verify Consent",
        "idPrefix": "CONS",
        "rowDescription": "Consent verification",
        "rowStatus": "Verified",
        "owner": "Intake Coordinator"
      },
      {
        "eventType": "clinical.demographics.updated",
        "label": "Update Demographics",
        "idPrefix": "DEM",
        "rowDescription": "Demographic update",
        "rowStatus": "Updated",
        "owner": "Technology Analyst"
      },
      {
        "eventType": "clinical.intake.packet.completed",
        "label": "Complete Intake Packet",
        "idPrefix": "PKT",
        "rowDescription": "Intake packet completion",
        "rowStatus": "Completed",
        "owner": "Intake Coordinator"
      }
    ]
  },
  "screening": {
    "title": "Screening",
    "eyebrow": "Eligibility, medical history, deferrals",
    "description": "Review medical history, eligibility criteria, deferral rules, infectious disease readiness, and evidence gaps before clinical disposition.",
    "idPrefix": "SCR",
    "owner": "Clinical Reviewer",
    "rows": [
      {
        "id": "SCR-77811",
        "description": "Medical history questionnaire",
        "status": "Clinical Review",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "SCR-77812",
        "description": "Eligibility criteria check",
        "status": "Exception",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "SCR-77813",
        "description": "Infectious disease readiness",
        "status": "Ready",
        "owner": "QA Specialist"
      },
      {
        "id": "SCR-77814",
        "description": "Deferral rule review",
        "status": "Needs Evidence",
        "owner": "Clinical Reviewer"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.screening.started",
        "label": "Start Screening",
        "idPrefix": "SCR",
        "rowDescription": "Screening workflow",
        "rowStatus": "Started",
        "owner": "Clinical Reviewer"
      },
      {
        "eventType": "clinical.eligibility.checked",
        "label": "Run Eligibility Check",
        "idPrefix": "ELG",
        "rowDescription": "Eligibility check",
        "rowStatus": "Checked",
        "owner": "Clinical Reviewer"
      },
      {
        "eventType": "clinical.deferral.flagged",
        "label": "Flag Deferral",
        "idPrefix": "DEF",
        "rowDescription": "Deferral flag",
        "rowStatus": "Flagged",
        "owner": "Clinical Reviewer"
      },
      {
        "eventType": "clinical.evidence.requested",
        "label": "Request Evidence",
        "idPrefix": "EVD",
        "rowDescription": "Evidence request",
        "rowStatus": "Requested",
        "owner": "QA Specialist"
      }
    ]
  },
  "scheduling": {
    "title": "Scheduling",
    "eyebrow": "Appointments, review slots, vendor windows",
    "description": "Coordinate donor screening appointments, provider review slots, vendor collection windows, follow-ups, and escalation windows.",
    "idPrefix": "APT",
    "owner": "Scheduling",
    "rows": [
      {
        "id": "APT-55021",
        "description": "Donor screening appointment",
        "status": "Confirmed",
        "owner": "Scheduling"
      },
      {
        "id": "APT-55022",
        "description": "Provider review slot",
        "status": "Pending",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "APT-55023",
        "description": "Vendor collection window",
        "status": "At Risk",
        "owner": "Vendor Operations"
      },
      {
        "id": "APT-55024",
        "description": "Follow-up review",
        "status": "Scheduled",
        "owner": "Operations Manager"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.appointment.scheduled",
        "label": "Schedule Appointment",
        "idPrefix": "APT",
        "rowDescription": "Donor appointment",
        "rowStatus": "Scheduled",
        "owner": "Scheduling"
      },
      {
        "eventType": "clinical.appointment.rescheduled",
        "label": "Reschedule",
        "idPrefix": "APT",
        "rowDescription": "Appointment reschedule",
        "rowStatus": "Rescheduled",
        "owner": "Scheduling"
      },
      {
        "eventType": "clinical.vendor_window.confirmed",
        "label": "Confirm Vendor Window",
        "idPrefix": "VEN",
        "rowDescription": "Vendor collection window",
        "rowStatus": "Confirmed",
        "owner": "Vendor Operations"
      },
      {
        "eventType": "clinical.followup.created",
        "label": "Create Follow-up",
        "idPrefix": "FUP",
        "rowDescription": "Follow-up task",
        "rowStatus": "Created",
        "owner": "Operations Manager"
      }
    ]
  },
  "review": {
    "title": "Clinical Review",
    "eyebrow": "Disposition, notes, lab readiness",
    "description": "Support clinical reviewers with eligibility disposition, lab readiness, clinical notes, escalations, and signoff evidence.",
    "idPrefix": "REV",
    "owner": "Clinical Reviewer",
    "rows": [
      {
        "id": "REV-30210",
        "description": "Eligibility disposition",
        "status": "Pending Signoff",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "REV-30211",
        "description": "Clinical notes review",
        "status": "In Progress",
        "owner": "Clinical Reviewer"
      },
      {
        "id": "REV-30212",
        "description": "Lab readiness evidence",
        "status": "Ready",
        "owner": "QA Specialist"
      },
      {
        "id": "REV-30213",
        "description": "Escalated case review",
        "status": "Urgent",
        "owner": "Operations Manager"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.review.opened",
        "label": "Open Review",
        "idPrefix": "REV",
        "rowDescription": "Clinical review opened",
        "rowStatus": "Opened",
        "owner": "Clinical Reviewer"
      },
      {
        "eventType": "clinical.disposition.recorded",
        "label": "Record Disposition",
        "idPrefix": "DSP",
        "rowDescription": "Eligibility disposition",
        "rowStatus": "Recorded",
        "owner": "Clinical Reviewer"
      },
      {
        "eventType": "clinical.lab_readiness.confirmed",
        "label": "Confirm Lab Readiness",
        "idPrefix": "LAB",
        "rowDescription": "Lab readiness confirmation",
        "rowStatus": "Confirmed",
        "owner": "QA Specialist"
      },
      {
        "eventType": "clinical.case.escalated",
        "label": "Escalate Case",
        "idPrefix": "ESC",
        "rowDescription": "Escalated clinical case",
        "rowStatus": "Escalated",
        "owner": "Operations Manager"
      }
    ]
  },
  "quality": {
    "title": "Quality",
    "eyebrow": "QA audit, deviations, CAPA, release evidence",
    "description": "Manage QA release readiness, documentation audits, deviation reviews, CAPA follow-up, and compliance sampling.",
    "idPrefix": "QA",
    "owner": "QA Specialist",
    "rows": [
      {
        "id": "QA-8011",
        "description": "Release evidence audit",
        "status": "Ready",
        "owner": "QA Specialist"
      },
      {
        "id": "QA-8012",
        "description": "Deviation review",
        "status": "CAPA Open",
        "owner": "QA Specialist"
      },
      {
        "id": "QA-8013",
        "description": "Document completeness",
        "status": "Pass",
        "owner": "Technology Analyst"
      },
      {
        "id": "QA-8014",
        "description": "Compliance sampling",
        "status": "Scheduled",
        "owner": "QA Specialist"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.qa.audit.started",
        "label": "Start QA Audit",
        "idPrefix": "QA",
        "rowDescription": "QA audit",
        "rowStatus": "Started",
        "owner": "QA Specialist"
      },
      {
        "eventType": "clinical.deviation.created",
        "label": "Create Deviation",
        "idPrefix": "DEV",
        "rowDescription": "Deviation record",
        "rowStatus": "Created",
        "owner": "QA Specialist"
      },
      {
        "eventType": "clinical.capa.updated",
        "label": "Update CAPA",
        "idPrefix": "CAPA",
        "rowDescription": "CAPA update",
        "rowStatus": "Updated",
        "owner": "QA Specialist"
      },
      {
        "eventType": "clinical.release_evidence.approved",
        "label": "Approve Release Evidence",
        "idPrefix": "REL",
        "rowDescription": "Release evidence approval",
        "rowStatus": "Approved",
        "owner": "QA Specialist"
      }
    ]
  },
  "vendorOps": {
    "title": "Vendor Operations",
    "eyebrow": "Supplier portal, SLA, partner coordination",
    "description": "Coordinate partner document requests, vendor SLA exceptions, collection confirmations, and supplier portal readiness.",
    "idPrefix": "VEN",
    "owner": "Vendor Operations",
    "rows": [
      {
        "id": "VEN-2001",
        "description": "Partner document request",
        "status": "Pending Vendor",
        "owner": "Vendor Operations"
      },
      {
        "id": "VEN-2002",
        "description": "Supplier SLA exception",
        "status": "Escalated",
        "owner": "Vendor Operations"
      },
      {
        "id": "VEN-2003",
        "description": "Collection confirmation",
        "status": "Confirmed",
        "owner": "Vendor Operations"
      },
      {
        "id": "VEN-2004",
        "description": "Portal access review",
        "status": "Needs Admin",
        "owner": "System Administrator"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.vendor.document_requested",
        "label": "Request Vendor Document",
        "idPrefix": "VEN",
        "rowDescription": "Vendor document request",
        "rowStatus": "Requested",
        "owner": "Vendor Operations"
      },
      {
        "eventType": "clinical.vendor.sla_exception.created",
        "label": "Create SLA Exception",
        "idPrefix": "SLA",
        "rowDescription": "Vendor SLA exception",
        "rowStatus": "Created",
        "owner": "Vendor Operations"
      },
      {
        "eventType": "clinical.collection.confirmed",
        "label": "Confirm Collection",
        "idPrefix": "COL",
        "rowDescription": "Collection confirmation",
        "rowStatus": "Confirmed",
        "owner": "Vendor Operations"
      },
      {
        "eventType": "clinical.vendor_portal.access_reviewed",
        "label": "Review Portal Access",
        "idPrefix": "PORT",
        "rowDescription": "Vendor portal access review",
        "rowStatus": "Reviewed",
        "owner": "System Administrator"
      }
    ]
  },
  "reports": {
    "title": "Reports",
    "eyebrow": "Clinical analytics readiness",
    "description": "Prepare donor services analytics for cycle time, eligibility outcomes, QA readiness, vendor SLA, and operational throughput.",
    "idPrefix": "RPT",
    "owner": "Technology Analyst",
    "rows": [
      {
        "id": "RPT-CLIN-001",
        "description": "Donor services executive summary",
        "status": "Ready",
        "owner": "Power BI"
      },
      {
        "id": "RPT-CLIN-002",
        "description": "Eligibility outcomes",
        "status": "Ready",
        "owner": "Snowflake"
      },
      {
        "id": "RPT-QA-003",
        "description": "QA release readiness",
        "status": "Draft",
        "owner": "Power BI"
      },
      {
        "id": "RPT-VEN-004",
        "description": "Vendor SLA exceptions",
        "status": "Draft",
        "owner": "Snowflake"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.report.run",
        "label": "Run Report",
        "idPrefix": "RPT",
        "rowDescription": "Clinical report run",
        "rowStatus": "Run",
        "owner": "Technology Analyst"
      },
      {
        "eventType": "clinical.report.exported",
        "label": "Export Report",
        "idPrefix": "EXP",
        "rowDescription": "Clinical report export",
        "rowStatus": "Exported",
        "owner": "Technology Analyst"
      },
      {
        "eventType": "clinical.analytics.snapshot.created",
        "label": "Create Snapshot",
        "idPrefix": "SNAP",
        "rowDescription": "Clinical analytics snapshot",
        "rowStatus": "Created",
        "owner": "Data Engineering"
      },
      {
        "eventType": "clinical.quality_dashboard.refreshed",
        "label": "Refresh Quality Dashboard",
        "idPrefix": "DASH",
        "rowDescription": "Quality dashboard refresh",
        "rowStatus": "Refreshed",
        "owner": "Technology Analyst"
      }
    ]
  },
  "administration": {
    "title": "Administration",
    "eyebrow": "Roles, security, integrations, audit evidence",
    "description": "Configure clinical roles, supplier access, audit settings, data lake telemetry, and technology analyst workflow controls.",
    "idPrefix": "ADM",
    "owner": "System Administrator",
    "rows": [
      {
        "id": "ROLE-INTAKE",
        "description": "Intake Coordinator",
        "status": "Active",
        "owner": "Donor intake"
      },
      {
        "id": "ROLE-CLINICAL",
        "description": "Clinical Reviewer",
        "status": "Active",
        "owner": "Eligibility review"
      },
      {
        "id": "ROLE-QA",
        "description": "QA Specialist",
        "status": "Active",
        "owner": "Release evidence"
      },
      {
        "id": "ROLE-VENDOR",
        "description": "Vendor Operations",
        "status": "Active",
        "owner": "Supplier portal"
      },
      {
        "id": "ROLE-TECH-ANALYST",
        "description": "Technology Analyst",
        "status": "Active",
        "owner": "Data quality/integration"
      },
      {
        "id": "INT-DATALAKE",
        "description": "Azure data lake event stream",
        "status": "Connected",
        "owner": "raw/apps/clinical/events"
      }
    ],
    "actions": [
      {
        "eventType": "clinical.admin.user.created",
        "label": "Create User",
        "idPrefix": "USR",
        "rowDescription": "Clinical user account",
        "rowStatus": "Created",
        "owner": "System Administrator"
      },
      {
        "eventType": "clinical.admin.role.updated",
        "label": "Update Role",
        "idPrefix": "ROLE",
        "rowDescription": "Clinical role update",
        "rowStatus": "Updated",
        "owner": "System Administrator"
      },
      {
        "eventType": "clinical.admin.vendor_access.updated",
        "label": "Update Vendor Access",
        "idPrefix": "VACC",
        "rowDescription": "Vendor access update",
        "rowStatus": "Updated",
        "owner": "System Administrator"
      },
      {
        "eventType": "clinical.admin.audit.exported",
        "label": "Export Audit Evidence",
        "idPrefix": "AUD",
        "rowDescription": "Audit evidence export",
        "rowStatus": "Exported",
        "owner": "QA Specialist"
      }
    ]
  }
};
const dashboardMetrics = [
  {
    "label": "Active Donor Cases",
    "value": "248",
    "delta": "+18 this week",
    "tone": "good"
  },
  {
    "label": "Eligibility Queue",
    "value": "37",
    "delta": "8 urgent",
    "tone": "warning"
  },
  {
    "label": "QA Release Ready",
    "value": "91%",
    "delta": "+4.3%",
    "tone": "good"
  },
  {
    "label": "Vendor SLA",
    "value": "96.2%",
    "delta": "2 exceptions",
    "tone": "neutral"
  }
];
const roleCards = [
  [
    "Intake Coordinator",
    "Registers donor referrals, confirms demographics, documents consents, and starts screening packets."
  ],
  [
    "Clinical Reviewer",
    "Reviews eligibility evidence, medical history, lab readiness, and clinical disposition."
  ],
  [
    "QA Specialist",
    "Audits documentation, deviations, corrective actions, and release-readiness evidence."
  ],
  [
    "Vendor Operations",
    "Coordinates supplier portals, document requests, partner follow-ups, and service-level exceptions."
  ],
  [
    "Operations Manager",
    "Monitors throughput, staffing load, cycle time, and escalation queues."
  ],
  [
    "Technology Analyst",
    "Owns workflow configuration, data quality, integrations, reporting readiness, and audit evidence."
  ]
];

const basePath = "/Clinical/";
const appName = "Meridian Clinical";
const modulePrefix = "clinical";
const classPrefix = "clinical";
const userId = CLINICAL_USER_ID;
const getHealth = getClinicalHealth;
const getRecentEvents = getClinicalRecentEvents;
const sendEvent = sendClinicalEvent;

function getCurrentPath() {
  const pathname = window.location.pathname;

  if (pathname === basePath.slice(0, -1)) {
    return basePath;
  }

  return pathname.startsWith(basePath.slice(0, -1)) ? pathname : basePath;
}

function pageKey(pathname) {
  const match = appNavItems
    .filter((item) => item.path !== basePath)
    .sort((left, right) => right.path.length - left.path.length)
    .find((item) => pathname.startsWith(item.path));

  return match?.key || "dashboard";
}

function makeId(prefix) {
  return `${prefix}-${Date.now().toString().slice(-6)}-${Math.random().toString(16).slice(2, 6)}`.toUpperCase();
}

function statusTone(status = "") {
  const normalized = String(status).toLowerCase();

  if (
    normalized.includes("ready") ||
    normalized.includes("active") ||
    normalized.includes("confirmed") ||
    normalized.includes("approved") ||
    normalized.includes("pass") ||
    normalized.includes("posted") ||
    normalized.includes("published") ||
    normalized.includes("completed")
  ) return "good";

  if (
    normalized.includes("urgent") ||
    normalized.includes("exception") ||
    normalized.includes("risk") ||
    normalized.includes("hold") ||
    normalized.includes("capa") ||
    normalized.includes("pending") ||
    normalized.includes("needs") ||
    normalized.includes("created")
  ) return "warning";

  return "neutral";
}

function emitDomainEvent(eventType, payload = {}) {
  sendEvent({
    eventType,
    aggregateType: payload.aggregateType || "ui",
    aggregateId: payload.aggregateId || payload.path || `${modulePrefix}-ui`,
    actorUserId: userId,
    sensitivityClassification: "public_internal",
    payload: {
      ...payload,
      emittedAt: new Date().toISOString()
    }
  });
}

function PortfolioRibbon() {
  return (
    <header className="portfolio-ribbon">
      <a className="portfolio-brand" href="https://teemails.com/">
        <span className="portfolio-mark">T</span>
        <span>
          <strong>teemails</strong>
          <small>Portfolio workspace</small>
        </span>
      </a>

      <nav className="portfolio-nav" aria-label="Portfolio navigation">
        {portfolioNavItems.map((item) => (
          <a
            key={item.label}
            className={item.label === "Clinical" ? "active" : ""}
            href={item.href}
            onClick={() => emitDomainEvent(`${modulePrefix}.portfolio.nav_clicked`, { label: item.label, href: item.href })}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  );
}

function StatusPill({ children, tone = "neutral" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function DataTable({ rows }) {
  return (
    <div className={`${classPrefix}-table`}>
      {rows.map((row) => (
        <div className={`${classPrefix}-table-row`} key={row.id}>
          <strong>{row.id}</strong>
          <span>{row.description}</span>
          <StatusPill tone={statusTone(row.status)}>{row.status}</StatusPill>
          <b>{row.owner}</b>
        </div>
      ))}
    </div>
  );
}

function createActionRow(action, moduleKey, moduleConfig) {
  const timestamp = new Date();
  const id = makeId(action.idPrefix || moduleConfig.idPrefix || moduleKey.toUpperCase());

  return {
    id,
    description: action.rowDescription || action.label,
    status: action.rowStatus || "Created",
    owner: action.owner || moduleConfig.owner || "Operations",
    createdAt: timestamp.toISOString(),
    sourceAction: action.label,
    sourceEventType: action.eventType
  };
}

function DashboardPage({ worklists }) {
  const priorityRows = [
    ...(worklists[moduleConfigs.dashboard.primaryTable] || []).slice(0, 2),
    ...(worklists[moduleConfigs.dashboard.secondaryTable] || []).slice(0, 2)
  ];

  return (
    <>
      <section className="hero-card">
        <div>
          <p className="eyebrow">{moduleConfigs.dashboard.eyebrow}</p>
          <h1>{moduleConfigs.dashboard.title}</h1>
          <p>{moduleConfigs.dashboard.description}</p>
        </div>

        <div className="hero-panel">
          <strong>{moduleConfigs.dashboard.panelTitle}</strong>
          <span>{moduleConfigs.dashboard.panelText}</span>
          <StatusPill tone="good">{moduleConfigs.dashboard.panelStatus}</StatusPill>
        </div>
      </section>

      <section className="metric-grid">
        {dashboardMetrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <StatusPill tone={metric.tone}>{metric.delta}</StatusPill>
          </article>
        ))}
      </section>

      <section className="two-column">
        <Card title={moduleConfigs.dashboard.workbenchTitle}>
          <DataTable rows={priorityRows} />
        </Card>

        <Card title={moduleConfigs.dashboard.rolesTitle}>
          <div className="role-grid">
            {roleCards.map(([role, description]) => (
              <div className="role-card" key={role}>
                <strong>{role}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </>
  );
}

function ModulePage({ moduleKey, config, rows, onAction }) {
  return (
    <>
      <section className="module-header-card">
        <div>
          <p className="eyebrow">{config.eyebrow}</p>
          <h1>{config.title}</h1>
          <p>{config.description}</p>
        </div>

        <div className="action-grid">
          {config.actions.map((action) => (
            <button
              key={action.eventType}
              type="button"
              onClick={() => onAction(moduleKey, action)}
            >
              {action.label}
            </button>
          ))}
        </div>
      </section>

      <Card title={`${config.title} Worklist`}>
        <DataTable rows={rows} />
      </Card>
    </>
  );
}

function AdministrationPage({ worklists, onAction }) {
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("Loading event API state");

  function refreshApiState() {
    setStatus("Loading event API state");

    Promise.allSettled([getHealth(), getRecentEvents(10)])
      .then(([healthResult, eventsResult]) => {
        if (healthResult.status === "fulfilled") {
          setHealth(healthResult.value);
        }

        if (eventsResult.status === "fulfilled") {
          setEvents(Array.isArray(eventsResult.value?.events) ? eventsResult.value.events : []);
        }

        if (healthResult.status === "fulfilled" || eventsResult.status === "fulfilled") {
          setStatus("Connected");
        } else {
          setStatus("Event API pending");
        }
      })
      .catch(() => setStatus("Event API pending"));
  }

  useEffect(() => {
    refreshApiState();
  }, []);

  const config = moduleConfigs.administration;

  return (
    <>
      <ModulePage
        moduleKey="administration"
        config={config}
        rows={worklists.administration}
        onAction={onAction}
      />

      <Card title={`${appName} Data Lake Events`}>
        <div className="admin-api-panel">
          <div>
            <p className="muted">
              Recent {appName} domain events written to the Azure data lake through the {appName} App Service managed identity.
            </p>
            <StatusPill tone={status === "Connected" ? "good" : "warning"}>{status}</StatusPill>
          </div>

          <button type="button" onClick={refreshApiState}>Refresh API State</button>
        </div>

        {health && (
          <pre className="json-block">{JSON.stringify(health, null, 2)}</pre>
        )}

        {events.length > 0 ? (
          <div className="event-list">
            {events.slice(0, 8).map((event, index) => (
              <div className="event-row" key={event.event_id || event.blob_name || index}>
                <strong>{event.event_type || `${modulePrefix}.event`}</strong>
                <span>{event.blob_name || event.aggregate_id || event.event_id}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No recent events returned yet.</strong>
            <span>Use the action buttons to generate data lake events.</span>
          </div>
        )}
      </Card>
    </>
  );
}

function Card({ title, children }) {
  return (
    <section className="card">
      <div className="card-title">
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function initialWorklists() {
  return Object.fromEntries(
    Object.entries(moduleConfigs)
      .filter(([key]) => key !== "dashboard")
      .map(([key, config]) => [key, config.rows || []])
  );
}

function App() {
  const [path, setPath] = useState(getCurrentPath());
  const [worklists, setWorklists] = useState(initialWorklists);

  const key = useMemo(() => pageKey(path), [path]);

  useEffect(() => {
    function onPopState() {
      setPath(getCurrentPath());
    }

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    emitDomainEvent(`${modulePrefix}.page.viewed`, {
      path,
      page: key,
      aggregateType: "page"
    });

    document.title = key === "dashboard" ? `${appName} | teemails` : `${appName} | ${key}`;
  }, [path, key]);

  useEffect(() => {
    const dateKey = new Date().toISOString().slice(0, 10);
    const storageKey = `${modulePrefix}-table-snapshot-${dateKey}`;

    if (window.localStorage.getItem(storageKey)) {
      return;
    }

    const tables = Object.fromEntries(
      Object.entries(worklists).map(([tableName, rows]) => [
        tableName,
        rows.map((row) => ({ ...row }))
      ])
    );

    emitDomainEvent(`${modulePrefix}.table.snapshot`, {
      aggregateType: "table_snapshot",
      aggregateId: `${modulePrefix}.tables.${dateKey}`,
      tables,
      tableNames: Object.keys(tables)
    });

    window.localStorage.setItem(storageKey, "true");
  }, []);

  function navigate(nextPath) {
    window.history.pushState({}, "", nextPath);
    setPath(getCurrentPath());

    emitDomainEvent(`${modulePrefix}.app.nav_clicked`, {
      path: nextPath,
      page: pageKey(nextPath)
    });
  }

  function handleAction(moduleKey, action) {
    const config = moduleConfigs[moduleKey];
    const row = createActionRow(action, moduleKey, config);

    setWorklists((current) => ({
      ...current,
      [moduleKey]: [row, ...(current[moduleKey] || [])]
    }));

    emitDomainEvent(action.eventType, {
      aggregateType: moduleKey,
      aggregateId: row.id,
      module: config.title,
      action: action.label,
      row
    });

    emitDomainEvent(`${modulePrefix}.table.row.created`, {
      aggregateType: "table",
      aggregateId: `${modulePrefix}.${moduleKey}.${row.id}`,
      table: moduleKey,
      row
    });
  }

  let content = <DashboardPage worklists={worklists} />;

  if (key !== "dashboard" && key !== "administration") {
    content = (
      <ModulePage
        moduleKey={key}
        config={moduleConfigs[key]}
        rows={worklists[key] || []}
        onAction={handleAction}
      />
    );
  }

  if (key === "administration") {
    content = <AdministrationPage worklists={worklists} onAction={handleAction} />;
  }

  return (
    <>
      <PortfolioRibbon />

      <div className={`${classPrefix}-shell`}>
        <aside className={`${classPrefix}-sidebar`}>
          <div className={`${classPrefix}-product`}>
            <span className={`${classPrefix}-product-mark`}>{"C"}</span>
            <div>
              <strong>{appName}</strong>
              <small>{"Donor Services"}</small>
            </div>
          </div>

          <nav className={`${classPrefix}-nav`} aria-label={`${appName} navigation`}>
            {appNavItems.map((item) => (
              <button
                key={item.path}
                type="button"
                className={path === item.path || (item.path !== basePath && path.startsWith(item.path)) ? "active" : ""}
                onClick={() => navigate(item.path)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="sidebar-footer">
            <span>Environment</span>
            <strong>Portfolio Dev</strong>
            <StatusPill tone="good">Events live</StatusPill>
          </div>
        </aside>

        <main className={`${classPrefix}-main`}>
          {content}
        </main>
      </div>
    </>
  );
}

export default App;
